"""Slack notifikace k úkolům – DM přes bota, volitelně webhook pro kanál."""
from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings
from django.utils import timezone

from stores.models import Prodejna
from users.models import WebUser

from .models import Ukol, UkolKomentar, UkolSlackNotifikace
from .slack_prefs import (
    PREF_COMMENT_ALL,
    PREF_COMMENT_MINE,
    PREF_CREATED_ALL,
    PREF_DUE_SOON_ALL,
    PREF_OVERDUE_ALL,
    get_slack_ukoly_prefs,
    global_watcher_ids,
    is_task_mine_for_user,
    user_wants_slack_notification,
)
from .urgency import URGENCY_OVERDUE, URGENCY_URGENT, urgency_for_task

logger = logging.getLogger(__name__)

NOTIFY_TYPES = ("due_soon", "overdue")
DM_EVENT_TYPES = (
    "assigned",
    "due_soon",
    "overdue",
    "awaiting_approval",
    "completed",
    "created",
    "comment",
)

_slack_user_cache: dict[int, str | None] = {}
_slack_id_to_web_user_cache: dict[str, int | None] = {}


class SlackApiError(Exception):
    def __init__(self, error: str, *, status_code: int | None = None):
        super().__init__(error)
        self.error = error
        self.status_code = status_code


def _bot_token() -> str:
    return (getattr(settings, "SLACK_BOT_TOKEN", None) or "").strip()


def _webhook_url() -> str:
    return (getattr(settings, "SLACK_TASKS_WEBHOOK_URL", None) or "").strip()


def _app_base_url() -> str:
    return (getattr(settings, "MOBILMAJAK_APP_URL", None) or "https://mobilmajak.com").rstrip("/")


_SLACK_GET_METHODS = frozenset({"users.lookupByEmail", "users.info"})


def _slack_api(method: str, payload: dict[str, Any]) -> dict:
    token = _bot_token()
    if not token:
        raise SlackApiError("no_bot_token")

    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://slack.com/api/{method}"
    if method in _SLACK_GET_METHODS:
        r = requests.get(url, params=payload, timeout=15, headers=headers)
    else:
        headers["Content-Type"] = "application/json; charset=utf-8"
        r = requests.post(url, json=payload, timeout=15, headers=headers)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise SlackApiError(data.get("error", "unknown_error"), status_code=r.status_code)
    return data


def slack_user_id_for_web_user(user: WebUser | int | None) -> str | None:
    """Vyhledá Slack user ID podle e-mailu (users.lookupByEmail), s in-memory cache."""
    if user is None:
        return None
    if isinstance(user, int):
        try:
            user = WebUser.objects.get(pk=user)
        except WebUser.DoesNotExist:
            return None

    if user.id in _slack_user_cache:
        return _slack_user_cache[user.id]

    email = (user.email or "").strip()
    if not email:
        _slack_user_cache[user.id] = None
        return None

    if not _bot_token():
        return None

    try:
        data = _slack_api("users.lookupByEmail", {"email": email})
        slack_id = data.get("user", {}).get("id")
        _slack_user_cache[user.id] = slack_id
        return slack_id
    except SlackApiError as exc:
        if exc.error == "users_not_found":
            logger.info("Slack uživatel nenalezen pro WebUser #%s (%s)", user.id, email)
            _slack_user_cache[user.id] = None
            return None
        logger.exception("Slack lookup selhal pro WebUser #%s", user.id)
        return None
    except Exception:
        logger.exception("Slack lookup selhal pro WebUser #%s", user.id)
        return None


def web_user_for_slack_id(slack_user_id: str | None) -> WebUser | None:
    """Najde WebUser podle Slack user ID (users.info → e-mail)."""
    sid = (slack_user_id or "").strip()
    if not sid:
        return None
    if sid in _slack_id_to_web_user_cache:
        uid = _slack_id_to_web_user_cache[sid]
        if uid is None:
            return None
        try:
            return WebUser.objects.get(pk=uid, aktivni=True)
        except WebUser.DoesNotExist:
            _slack_id_to_web_user_cache[sid] = None
            return None

    if not _bot_token():
        return None

    try:
        data = _slack_api("users.info", {"user": sid})
        profile = (data.get("user") or {}).get("profile") or {}
        email = (profile.get("email") or "").strip().lower()
        if not email:
            _slack_id_to_web_user_cache[sid] = None
            return None
        user = WebUser.objects.filter(email__iexact=email, aktivni=True).first()
        _slack_id_to_web_user_cache[sid] = user.id if user else None
        if user:
            _slack_user_cache[user.id] = sid
        return user
    except SlackApiError as exc:
        logger.info("Slack users.info selhalo pro %s: %s", sid, exc.error)
        _slack_id_to_web_user_cache[sid] = None
        return None
    except Exception:
        logger.exception("Slack users.info selhalo pro %s", sid)
        return None


def open_slack_modal(trigger_id: str, view: dict) -> bool:
    """Otevře modální dialog (views.open) – textový vstup bez psaní do DM."""
    tid = (trigger_id or "").strip()
    if not tid or not _bot_token():
        return False
    try:
        _slack_api("views.open", {"trigger_id": tid, "view": view})
        return True
    except Exception:
        logger.exception("Slack views.open selhalo")
        return False


def send_slack_dm(slack_user_id: str, text: str, blocks: list | None = None) -> bool:
    """Odešle DM přes chat.postMessage (channel = Slack user ID)."""
    if not slack_user_id or not _bot_token():
        return False

    payload: dict[str, Any] = {
        "channel": slack_user_id,
        "text": text,
        "unfurl_links": False,
        "unfurl_media": False,
    }
    if blocks:
        payload["blocks"] = blocks

    try:
        _slack_api("chat.postMessage", payload)
        return True
    except Exception:
        logger.exception("Slack DM selhala pro channel=%s", slack_user_id)
        return False


def _web_user(pk: int | None) -> WebUser | None:
    if not pk:
        return None
    try:
        return WebUser.objects.get(pk=pk)
    except WebUser.DoesNotExist:
        return None


def _user_display_name(user: WebUser | None, fallback_id: int | None = None) -> str:
    if user:
        name = f"{user.jmeno} {user.prijmeni}".strip()
        if name:
            return name
    return str(fallback_id or "?")


def _assignee_name(task: Ukol) -> str:
    return _user_display_name(_web_user(task.id_prodejce_ukol), task.id_prodejce_ukol)


def _task_title(task: Ukol) -> str:
    return (task.vysledek or task.ukol or f"Úkol #{task.id}").strip().split("\n")[0]


def _task_link_for_assignee(task: Ukol) -> str:
    return f"{_app_base_url()}/tasks/mine?id={task.id}"


def _task_link_for_manager(task: Ukol) -> str:
    return f"{_app_base_url()}/tasks/manage?id={task.id}"


def _format_deadline(task: Ukol) -> str:
    if not task.deadline:
        return "—"
    text = task.deadline.strftime("%d.%m.%Y")
    if task.deadline_cas:
        text += f" {task.deadline_cas.strftime('%H:%M')}"
    return text


def _escape_slack(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _dm_typ_for_event(event_type: str) -> str:
    mapping = {
        "assigned": "dm_assigned",
        "due_soon": "dm_due_soon",
        "overdue": "dm_overdue",
        "awaiting_approval": "dm_awaiting_approval",
        "completed": "dm_completed",
        "created": "dm_created",
        "comment": "dm_comment",
    }
    return mapping[event_type]


def _store_vedouci_user_id(store_id: int | None) -> int | None:
    if not store_id:
        return None
    try:
        store = Prodejna.objects.get(pk=store_id)
        return store.vedouci_user_id
    except Prodejna.DoesNotExist:
        return None


def _recipient_user_ids(task: Ukol, event_type: str) -> list[int]:
    """Vrátí seznam WebUser ID příjemců DM pro danou událost (dle preferencí)."""
    assignee_id = task.id_prodejce_ukol
    zadavatel_id = task.id_prodejce_zadal
    vedouci_id = _store_vedouci_user_id(task.id_prodejny)

    candidates: set[int] = set()

    if event_type == "assigned" and assignee_id:
        candidates.add(assignee_id)
    elif event_type in ("due_soon", "overdue"):
        if assignee_id:
            candidates.add(assignee_id)
        if zadavatel_id:
            candidates.add(zadavatel_id)
        global_key = PREF_DUE_SOON_ALL if event_type == "due_soon" else PREF_OVERDUE_ALL
        candidates.update(global_watcher_ids(global_key))
    elif event_type == "awaiting_approval":
        if zadavatel_id:
            candidates.add(zadavatel_id)
        if vedouci_id:
            candidates.add(vedouci_id)
    elif event_type == "completed":
        if zadavatel_id:
            candidates.add(zadavatel_id)
    elif event_type == "created":
        if zadavatel_id:
            candidates.add(zadavatel_id)
        candidates.update(global_watcher_ids(PREF_CREATED_ALL))

    out: list[int] = []
    for user_id in candidates:
        if user_wants_slack_notification(
            user_id,
            task,
            event_type,
            vedouci_id=vedouci_id,
        ):
            out.append(user_id)
    return out


def _is_manager_recipient(task: Ukol, recipient_id: int) -> bool:
    if recipient_id == task.id_prodejce_ukol:
        return False
    return True


def build_dm_message(
    task: Ukol,
    event_type: str,
    recipient_id: int,
    *,
    comment: UkolKomentar | None = None,
) -> str:
    title = _escape_slack(_task_title(task))
    assignee = _escape_slack(_assignee_name(task))
    deadline = _format_deadline(task)
    link = (
        _task_link_for_manager(task)
        if _is_manager_recipient(task, recipient_id)
        else _task_link_for_assignee(task)
    )

    if event_type == "assigned":
        headline = ":clipboard: Nový přiřazený úkol"
        body = f"Máte nový úkol *{title}*.\nTermín dokončení: {deadline}"
    elif event_type == "due_soon":
        headline = ":hourglass_flowing_sand: Blíží se termín úkolu"
        body = f"*{title}*\nPřiřazeno: {assignee}\nTermín dokončení: {deadline}"
    elif event_type == "overdue":
        headline = ":warning: Úkol po termínu"
        body = f"*{title}*\nPřiřazeno: {assignee}\nTermín dokončení: {deadline}"
    elif event_type == "awaiting_approval":
        headline = ":eyes: Úkol čeká na schválení"
        body = f"*{title}*\nPřiřazeno: {assignee}\nTermín dokončení: {deadline}"
    elif event_type == "completed":
        headline = ":white_check_mark: Úkol dokončen"
        body = f"*{title}*\nPřiřazeno: {assignee}"
    elif event_type == "created":
        if recipient_id == task.id_prodejce_zadal:
            headline = ":inbox_tray: Úkol založen"
            body = f"Založili jste úkol *{title}* pro {assignee}.\nTermín dokončení: {deadline}"
        else:
            zadavatel = _escape_slack(
                _user_display_name(_web_user(task.id_prodejce_zadal), task.id_prodejce_zadal)
            )
            headline = ":new: Nový úkol v systému"
            body = f"*{title}*\nPřiřazeno: {assignee}\nZadal: {zadavatel}\nTermín dokončení: {deadline}"
    elif event_type == "comment" and comment:
        author = _escape_slack(comment.autor_jmeno or f"Uživatel #{comment.autor_id}")
        excerpt = _escape_slack((comment.text or "").strip())
        if len(excerpt) > 280:
            excerpt = excerpt[:277] + "…"
        headline = ":speech_balloon: Nový komentář k úkolu"
        body = f"*{title}*\nOd: {author}\n>{excerpt}"
    else:
        headline = "Úkol"
        body = title

    return f"*{headline}*\n{body}\n<{link}|Otevřít v MOBILMAJAK>"


def _already_sent_dm(
    task: Ukol,
    dm_typ: str,
    recipient_id: int,
    *,
    ref_id: int = 0,
) -> bool:
    return task.slack_notifikace.filter(
        typ=dm_typ,
        recipient_user_id=recipient_id,
        ref_id=ref_id,
    ).exists()


def _recipient_user_ids_for_comment(task: Ukol, comment: UkolKomentar) -> list[int]:
    """Příjemci DM u nového komentáře – řešitel vždy (kromě vlastního), admini dle preferencí."""
    autor_id = comment.autor_id
    vedouci_id = _store_vedouci_user_id(task.id_prodejny)
    recipients: set[int] = set()

    assignee_id = task.id_prodejce_ukol
    if task.typ == "prirazeny" and assignee_id and assignee_id != autor_id:
        recipients.add(assignee_id)

    for user in WebUser.objects.filter(aktivni=True, role="ADMIN").only("id", "slack_ukoly_prefs"):
        if user.id == autor_id or user.id in recipients:
            continue
        prefs = get_slack_ukoly_prefs(user)
        if prefs.get(PREF_COMMENT_ALL):
            recipients.add(user.id)
        elif prefs.get(PREF_COMMENT_MINE) and is_task_mine_for_user(
            task, user.id, vedouci_id=vedouci_id
        ):
            recipients.add(user.id)

    return list(recipients)


def send_slack_dm_to_web_user(
    task: Ukol,
    event_type: str,
    recipient_id: int,
    *,
    comment: UkolKomentar | None = None,
) -> bool:
    """Odešle DM jednomu WebUser; vrací True pokud odesláno."""
    dm_typ = _dm_typ_for_event(event_type)
    ref_id = comment.id if event_type == "comment" and comment else 0
    if _already_sent_dm(task, dm_typ, recipient_id, ref_id=ref_id):
        return False

    user = _web_user(recipient_id)
    slack_id = slack_user_id_for_web_user(user)
    if not slack_id:
        logger.debug(
            "Slack DM přeskočeno – chybí Slack ID pro WebUser #%s (úkol #%s, %s)",
            recipient_id,
            task.id,
            event_type,
        )
        return False

    text = build_dm_message(task, event_type, recipient_id, comment=comment)
    if not send_slack_dm(slack_id, text):
        return False

    UkolSlackNotifikace.objects.create(
        ukol=task,
        typ=dm_typ,
        recipient_user_id=recipient_id,
        ref_id=ref_id,
    )
    logger.info(
        "Slack DM %s odesláno pro úkol #%s → WebUser #%s",
        dm_typ,
        task.id,
        recipient_id,
    )
    return True


def notify_task_event(task: Ukol, event_type: str) -> int:
    """Odešle DM všem příjemcům události. Vrací počet úspěšně odeslaných."""
    if event_type not in DM_EVENT_TYPES:
        return 0
    if not _bot_token():
        logger.debug("SLACK_BOT_TOKEN není nastaven – přeskočeno (%s)", event_type)
        return 0

    sent = 0
    for recipient_id in _recipient_user_ids(task, event_type):
        if send_slack_dm_to_web_user(task, event_type, recipient_id):
            sent += 1
    return sent


def notify_task_comment(task: Ukol, comment: UkolKomentar) -> int:
    """Odešle Slack DM k novému komentáři. Vrací počet odeslaných."""
    if not _bot_token():
        logger.debug("SLACK_BOT_TOKEN není nastaven – přeskočeno (comment)")
        return 0

    sent = 0
    for recipient_id in _recipient_user_ids_for_comment(task, comment):
        if send_slack_dm_to_web_user(task, "comment", recipient_id, comment=comment):
            sent += 1
    return sent


def notify_task_lifecycle_change(
    task: Ukol,
    *,
    is_new: bool = False,
    old_stav: str | None = None,
    old_assignee: int | None = None,
) -> None:
    """Hook po vytvoření / změně úkolu – odešle relevantní Slack DM."""
    if is_new and task.typ == "prirazeny":
        notify_task_event(task, "assigned")
        if task.id_prodejce_zadal:
            notify_task_event(task, "created")
        return

    if old_assignee is not None and task.id_prodejce_ukol != old_assignee and task.typ == "prirazeny":
        notify_task_event(task, "assigned")

    if old_stav is not None and task.stav != old_stav:
        if task.stav == "ceka_schvaleni":
            notify_task_event(task, "awaiting_approval")
        elif task.stav == "hotovo":
            notify_task_event(task, "completed")


def build_slack_payload(task: Ukol, notify_typ: str) -> dict:
    title = _task_title(task)
    assignee = _assignee_name(task)
    deadline = _format_deadline(task)
    link = _task_link_for_manager(task)

    if notify_typ == "overdue":
        headline = ":warning: Úkol po termínu"
        color = "#dc2626"
    else:
        headline = ":hourglass_flowing_sand: Blíží se termín úkolu"
        color = "#d97706"

    text = (
        f"*{headline}*\n"
        f"*{_escape_slack(title)}*\n"
        f"Přiřazeno: {assignee}\n"
        f"Termín dokončení: {deadline}\n"
        f"<{link}|Otevřít v MOBILMAJAK>"
    )

    return {
        "text": f"{headline}: {title}",
        "attachments": [
            {
                "color": color,
                "text": text,
                "mrkdwn_in": ["text"],
            }
        ],
    }


def send_slack_message(task: Ukol, notify_typ: str) -> bool:
    """Odešle webhook do kanálu (legacy fallback)."""
    url = _webhook_url()
    if not url:
        logger.debug("SLACK_TASKS_WEBHOOK_URL není nastaven – přeskočeno")
        return False

    payload = build_slack_payload(task, notify_typ)
    try:
        r = requests.post(
            url,
            json=payload,
            timeout=15,
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        UkolSlackNotifikace.objects.create(ukol=task, typ=notify_typ, recipient_user_id=None)
        logger.info("Slack webhook %s odesláno pro úkol #%s", notify_typ, task.id)
        return True
    except Exception:
        logger.exception("Slack webhook selhal pro úkol #%s typ=%s", task.id, notify_typ)
        return False


def notify_typ_for_task(task: Ukol, now=None) -> str | None:
    """Určí typ notifikace, nebo None pokud není třeba posílat."""
    if task.stav in ("hotovo",):
        return None
    if not task.deadline or task.typ != "prirazeny":
        return None

    urgency = urgency_for_task(task, now)
    if urgency == URGENCY_OVERDUE:
        return "overdue"
    if urgency == URGENCY_URGENT:
        return "due_soon"
    return None


def _deadline_already_notified(task: Ukol, notify_typ: str, recipient_id: int | None) -> bool:
    if _bot_token():
        dm_typ = _dm_typ_for_event(notify_typ)
        return task.slack_notifikace.filter(
            typ=dm_typ,
            recipient_user_id=recipient_id,
            ref_id=0,
        ).exists()
    return task.slack_notifikace.filter(
        typ=notify_typ,
        recipient_user_id__isnull=True,
        ref_id=0,
    ).exists()


def send_deadline_notifications(task: Ukol, notify_typ: str) -> int:
    """Odešle deadline notifikaci – DM pokud je bot token, jinak webhook."""
    if _bot_token():
        return notify_task_event(task, notify_typ)

    if send_slack_message(task, notify_typ):
        return 1
    return 0


def tasks_needing_slack_notify(now=None):
    """Vrátí (task, notify_typ, recipient_id) pro otevřené přiřazené úkoly s termínem."""
    now = now or timezone.now()
    qs = Ukol.objects.filter(
        typ="prirazeny",
        deadline__isnull=False,
        stav__in=Ukol.ACTIVE_STAVY + ("ceka_schvaleni",),
    ).prefetch_related("slack_notifikace")

    out = []
    for task in qs:
        notify_typ = notify_typ_for_task(task, now)
        if not notify_typ:
            continue

        if _bot_token():
            for recipient_id in _recipient_user_ids(task, notify_typ):
                if _deadline_already_notified(task, notify_typ, recipient_id):
                    continue
                out.append((task, notify_typ, recipient_id))
        elif not _deadline_already_notified(task, notify_typ, None):
            out.append((task, notify_typ, None))

    return out
