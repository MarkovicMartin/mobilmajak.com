"""Slack wizard pro zakládání úkolů bez LLM – krokový průvodce s tlačítky."""
from __future__ import annotations

import json
import logging
import re
from datetime import date, timedelta

from django.utils import timezone

from stores.models import Prodejna
from users.models import WebUser
from users.vedouci_utils import is_task_manager, vedouci_store_ids

from .models import SlackTaskDraft, Ukol
from .permissions import assignees_for_store, assignees_storeless
from .slack_notify import _app_base_url, _escape_slack, open_slack_modal, send_slack_dm
from .task_create_service import create_ukol_for_user

logger = logging.getLogger(__name__)

ACTION_PREFIX = "slack_ukol"
MODAL_PREFIX = f"{ACTION_PREFIX}_modal"

# MobilMajak má 6 poboček; ve Slacku je zobrazíme 3+3 (limit 5 tlačítek na řádek).
MAX_PRODEJNY = 6
STORES_PER_ROW = 3

STEP_CHOOSE_TYP = "choose_typ"
STEP_ENTER_TITLE = "enter_title"
STEP_ENTER_VYSLEDEK = "enter_vysledek"
STEP_CHOOSE_STORE = "choose_store"
STEP_CHOOSE_ASSIGNEE = "choose_assignee"
STEP_ENTER_DOD = "enter_dod"
STEP_CHOOSE_DEADLINE = "choose_deadline"
STEP_CHOOSE_PRIORITY = "choose_priority"
STEP_CONFIRM = "confirm"

TEXT_STEPS = frozenset({STEP_ENTER_TITLE, STEP_ENTER_VYSLEDEK, STEP_ENTER_DOD})

PRIORITY_LABELS = {
    "nizka": "Nízká",
    "stredni": "Střední",
    "vysoka": "Vysoká",
}


def _action(action: str, value: str = "") -> str:
    return f"{ACTION_PREFIX}:{action}:{value}"


def _store_action_blocks(buttons: list[dict]) -> list[dict]:
    """Šest poboček = dva řádky po třech tlačítkách."""
    if not buttons:
        return []
    return [
        {"type": "actions", "elements": buttons[i:i + STORES_PER_ROW]}
        for i in range(0, min(len(buttons), MAX_PRODEJNY), STORES_PER_ROW)
    ]


def _btn(text: str, action: str, value: str = "") -> dict:
    return {
        "type": "button",
        "text": {"type": "plain_text", "text": text[:75]},
        "action_id": _action(action, value),
        "value": value or action,
    }


def _section(text: str) -> dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _draft_data(draft: SlackTaskDraft) -> dict:
    if not isinstance(draft.data, dict):
        return {}
    return draft.data


def _save_draft(draft: SlackTaskDraft, *, step: str | None = None, **data_updates) -> SlackTaskDraft:
    data = _draft_data(draft)
    data.update(data_updates)
    draft.data = data
    if step is not None:
        draft.step = step
    draft.save(update_fields=["step", "data", "upraveno"])
    return draft


def _delete_draft(draft: SlackTaskDraft | None) -> None:
    if draft:
        draft.delete()


def _available_stores(user: WebUser) -> list[Prodejna]:
    role = getattr(user, "role", None)
    if role == "ADMIN":
        return list(Prodejna.objects.filter(aktivni=True).order_by("nazev"))
    store_ids = vedouci_store_ids(user)
    if not store_ids:
        return []
    return list(Prodejna.objects.filter(id__in=store_ids, aktivni=True).order_by("nazev"))


def _store_label(store: Prodejna) -> str:
    return (store.nazev_kratkiy or store.nazev or f"Prodejna #{store.id}").strip()


def _deadline_options() -> list[tuple[str, str]]:
    today = timezone.localdate()
    return [
        ("today", today.isoformat()),
        ("tomorrow", (today + timedelta(days=1)).isoformat()),
        ("friday", _next_weekday(today, 4).isoformat()),
        ("week", (today + timedelta(days=7)).isoformat()),
        ("none", ""),
    ]


def _next_weekday(from_day: date, weekday: int) -> date:
    days_ahead = (weekday - from_day.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return from_day + timedelta(days=days_ahead)


def _deadline_label(iso: str) -> str:
    if not iso:
        return "Bez termínu"
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return iso
    return d.strftime("%d.%m.%Y")


def _summary_blocks(draft: SlackTaskDraft, user: WebUser) -> list[dict]:
    data = _draft_data(draft)
    typ = data.get("typ", "osobni")
    lines = [
        f"*Typ:* {'Osobní' if typ == 'osobni' else 'Přiřazený'}",
        f"*Název / výsledek:* {_escape_slack(data.get('vysledek') or data.get('ukol') or '—')}",
    ]
    if typ == "prirazeny":
        store_id = data.get("id_prodejny")
        if store_id:
            store = Prodejna.objects.filter(pk=store_id).first()
            lines.append(f"*Prodejna:* {_escape_slack(_store_label(store) if store else str(store_id))}")
        else:
            lines.append("*Prodejna:* bez pobočky (centrální)")
        assignee_id = data.get("id_prodejce_ukol")
        assignee = WebUser.objects.filter(pk=assignee_id).first() if assignee_id else None
        name = f"{assignee.jmeno} {assignee.prijmeni}".strip() if assignee else str(assignee_id or "—")
        lines.append(f"*Přiřazeno:* {_escape_slack(name)}")
        dod = data.get("dod_polozky") or []
        if dod:
            dod_lines = "\n".join(f"• {_escape_slack(d.get('text', ''))}" for d in dod)
            lines.append(f"*Definition of Done:*\n{dod_lines}")
    lines.append(f"*Termín dokončení:* {_deadline_label(data.get('deadline') or '')}")
    lines.append(f"*Priorita:* {PRIORITY_LABELS.get(data.get('priorita', 'stredni'), 'Střední')}")
    return [
        _section("*:clipboard: Shrnutí úkolu*\n" + "\n".join(lines)),
        {
            "type": "actions",
            "elements": [
                _btn("Vytvořit úkol", "confirm", "create"),
                _btn("Zrušit", "confirm", "cancel"),
            ],
        },
    ]


def _step_blocks(draft: SlackTaskDraft, user: WebUser) -> tuple[str, list[dict]]:
    step = draft.step
    data = _draft_data(draft)

    if step == STEP_CHOOSE_TYP:
        return (
            "Vyber typ úkolu:",
            [
                _section("*:heavy_plus_sign: Nový úkol*\nJaký typ chceš založit?"),
                {
                    "type": "actions",
                    "elements": [
                        _btn("Osobní (pro mě)", "typ", "osobni"),
                        _btn("Přiřadit někomu", "typ", "prirazeny"),
                    ],
                },
            ],
        )

    if step == STEP_ENTER_TITLE:
        return (
            "Zadej text úkolu tlačítkem níže (nebo napiš zprávu).",
            [
                _section("*:pencil: Osobní úkol*\nCo je úkolem / jaký je cíl?"),
                {
                    "type": "actions",
                    "elements": [_btn("Napsat úkol…", "modal", "title")],
                },
            ],
        )

    if step == STEP_ENTER_VYSLEDEK:
        return (
            "Zadej výsledek tlačítkem níže (nebo napiš zprávu).",
            [
                _section("*:dart: Přiřazený úkol*\nJaký je požadovaný *výsledek* (Outcome)?"),
                {
                    "type": "actions",
                    "elements": [_btn("Napsat výsledek…", "modal", "vysledek")],
                },
            ],
        )

    if step == STEP_CHOOSE_STORE:
        stores = _available_stores(user)
        store_buttons = [
            _btn(_store_label(store)[:75], "store", str(store.id))
            for store in stores
        ]
        blocks = [_section("*:store: Prodejna*\nNa kterou pobočku úkol patří?")]
        if getattr(user, "role", None) == "ADMIN":
            blocks.append({
                "type": "actions",
                "elements": [_btn("Bez prodejny (centrální)", "store", "none")],
            })
        blocks.extend(_store_action_blocks(store_buttons))
        return ("Vyber prodejnu.", blocks)

    if step == STEP_CHOOSE_ASSIGNEE:
        store_id = data.get("id_prodejny")
        page = int(data.get("assignee_page") or 0)
        if store_id is None and getattr(user, "role", None) == "ADMIN":
            assignees = assignees_storeless(user)
        else:
            assignees = assignees_for_store(int(store_id), user) if store_id else []
        page_size = 5
        chunk = assignees[page * page_size:(page + 1) * page_size]
        elements = [
            _btn((a.get("jmeno_plne") or f"#{a.get('id')}")[:75], "assignee", str(a["id"]))
            for a in chunk
        ]
        nav = []
        if page > 0:
            nav.append(_btn("← Předchozí", "assignee_page", str(page - 1)))
        if (page + 1) * page_size < len(assignees):
            nav.append(_btn("Další →", "assignee_page", str(page + 1)))
        blocks = [_section("*:bust_in_silhouette: Komu přiřadit úkol?*")]
        if elements:
            blocks.append({"type": "actions", "elements": elements})
        if nav:
            blocks.append({"type": "actions", "elements": nav})
        if not assignees:
            blocks.append(_section("_Na této prodejně není nikdo k přiřazení._"))
        return ("Vyber uživatele.", blocks)

    if step == STEP_ENTER_DOD:
        dod = data.get("dod_polozky") or []
        vysledek = (data.get("vysledek") or data.get("ukol") or "").strip()
        extra = ""
        if dod:
            items = "\n".join(f"• {_escape_slack(d.get('text', ''))}" for d in dod)
            extra = f"\n\n*Zatím:*\n{items}"
        blocks = [
            _section(
                f"*:white_check_mark: Definition of Done*\n"
                f"Vyber jednu položku nebo přidej vlastní.{extra}"
            ),
        ]
        actions: list[dict] = []
        if vysledek:
            label = vysledek.replace("\n", " ")[:70]
            actions.append(_btn(f"✓ {label}", "dod", "default"))
        if not actions:
            actions.append(_btn("✓ Splněno podle popisu", "dod", "default"))
        actions.append(_btn("Vlastní položka…", "modal", "dod"))
        blocks.append({"type": "actions", "elements": actions[:5]})
        if dod:
            blocks.append({
                "type": "actions",
                "elements": [
                    _btn("Přidat další položku", "modal", "dod"),
                    _btn("Pokračovat na termín", "dod", "next"),
                ],
            })
        return ("Vyber nebo přidej DoD.", blocks)

    if step == STEP_CHOOSE_DEADLINE:
        typ = data.get("typ", "osobni")
        elements = [
            _btn("Dnes", "deadline", "today"),
            _btn("Zítra", "deadline", "tomorrow"),
            _btn("Příští pátek", "deadline", "friday"),
            _btn("Za týden", "deadline", "week"),
        ]
        if typ == "osobni":
            elements.append(_btn("Bez termínu", "deadline", "none"))
        blocks = [
            _section("*:calendar: Termín dokončení*"),
            {"type": "actions", "elements": elements},
        ]
        return ("Vyber termín dokončení.", blocks)

    if step == STEP_CHOOSE_PRIORITY:
        return (
            "Vyber prioritu.",
            [
                _section("*:traffic_light: Priorita*"),
                {
                    "type": "actions",
                    "elements": [
                        _btn("Nízká", "priority", "nizka"),
                        _btn("Střední", "priority", "stredni"),
                        _btn("Vysoká", "priority", "vysoka"),
                    ],
                },
            ],
        )

    if step == STEP_CONFIRM:
        return ("Zkontroluj shrnutí.", _summary_blocks(draft, user))

    return ("", [_section("_Neznámý krok._")])


def _modal_view(kind: str, slack_user_id: str) -> dict:
    specs = {
        "title": ("Osobní úkol", "Co je úkolem / jaký je cíl?", False),
        "vysledek": ("Výsledek", "Požadovaný outcome úkolu", True),
        "dod": ("DoD položka", "Co musí být splněno?", True),
    }
    title, placeholder, multiline = specs[kind]
    return {
        "type": "modal",
        "callback_id": f"{MODAL_PREFIX}:{kind}",
        "private_metadata": slack_user_id,
        "title": {"type": "plain_text", "text": title[:24]},
        "submit": {"type": "plain_text", "text": "Uložit"},
        "close": {"type": "plain_text", "text": "Zrušit"},
        "blocks": [{
            "type": "input",
            "block_id": "text_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "value",
                "multiline": multiline,
                "placeholder": {"type": "plain_text", "text": placeholder[:150]},
            },
            "label": {"type": "plain_text", "text": title},
        }],
    }


def _open_text_modal(payload: dict, slack_user_id: str, kind: str) -> None:
    trigger_id = payload.get("trigger_id") or ""
    if not open_slack_modal(trigger_id, _modal_view(kind, slack_user_id)):
        send_slack_dm(
            slack_user_id,
            "Nepodařilo se otevřít formulář. Zkus znovu kliknout na tlačítko.",
        )


def _post_step(draft: SlackTaskDraft, user: WebUser) -> None:
    text, blocks = _step_blocks(draft, user)
    send_slack_dm(draft.slack_user_id, text or "Úkoly MOBILMAJAK", blocks)


def _get_or_reset_draft(slack_user_id: str, web_user: WebUser, channel_id: str = "") -> SlackTaskDraft:
    draft, created = SlackTaskDraft.objects.get_or_create(
        slack_user_id=slack_user_id,
        defaults={
            "web_user_id": web_user.id,
            "channel_id": channel_id or "",
            "step": STEP_ENTER_TITLE if not is_task_manager(web_user) else STEP_CHOOSE_TYP,
            "data": {"priorita": "stredni"},
        },
    )
    if not created and draft.web_user_id != web_user.id:
        draft.web_user_id = web_user.id
        draft.channel_id = channel_id or draft.channel_id
        draft.step = STEP_ENTER_TITLE if not is_task_manager(web_user) else STEP_CHOOSE_TYP
        draft.data = {"priorita": "stredni"}
        draft.save()
    elif channel_id and draft.channel_id != channel_id:
        draft.channel_id = channel_id
        draft.save(update_fields=["channel_id", "upraveno"])
    return draft


def start_slack_task_wizard(
    slack_user_id: str,
    web_user: WebUser,
    *,
    channel_id: str = "",
    initial_text: str = "",
) -> tuple[str, bool]:
    """
    Zahájí wizard. Vrací (zpráva pro uživatele, zda OK).
    """
    draft = _get_or_reset_draft(slack_user_id, web_user, channel_id)
    text = (initial_text or "").strip()
    if text:
        if not is_task_manager(web_user):
            _save_draft(draft, step=STEP_CHOOSE_DEADLINE, typ="osobni", ukol=text[:255], vysledek=text)
        else:
            _save_draft(draft, step=STEP_CHOOSE_TYP, vysledek=text, ukol=text[:255])
    _post_step(draft, web_user)
    return "Poslal jsem ti průvodce zakládáním úkolu.", True


def handle_slack_text_message(
    slack_user_id: str,
    text: str,
    *,
    channel_id: str = "",
) -> bool:
    """Zpracuje text v DM. True = zpracováno."""
    from .slack_notify import web_user_for_slack_id

    web_user = web_user_for_slack_id(slack_user_id)
    if not web_user:
        send_slack_dm(
            slack_user_id,
            "Tvůj Slack účet není propojený s MOBILMAJAK. Vyplň stejný e-mail v profilu aplikace.",
        )
        return True

    cleaned = (text or "").strip()
    if not cleaned or cleaned.startswith("/"):
        return False

    draft = SlackTaskDraft.objects.filter(slack_user_id=slack_user_id).first()
    trigger = bool(re.match(r"^(úkol|ukol|založit úkol|zalozit ukol)\b", cleaned, re.I))

    if draft is None and trigger:
        initial = re.sub(r"^(úkol|ukol|založit úkol|zalozit ukol)[:\s]*", "", cleaned, flags=re.I).strip()
        start_slack_task_wizard(slack_user_id, web_user, channel_id=channel_id, initial_text=initial)
        return True

    if draft is None:
        return False

    if draft.step not in TEXT_STEPS:
        return False

    user = web_user
    data = _draft_data(draft)

    if draft.step == STEP_ENTER_TITLE:
        _save_draft(draft, ukol=cleaned[:255], vysledek=cleaned, typ="osobni", step=STEP_CHOOSE_DEADLINE)
    elif draft.step == STEP_ENTER_VYSLEDEK:
        _save_draft(draft, vysledek=cleaned, ukol=cleaned[:255], typ="prirazeny", step=STEP_CHOOSE_STORE)
    elif draft.step == STEP_ENTER_DOD:
        dod = list(data.get("dod_polozky") or [])
        dod.append({"text": cleaned[:500], "splneno": False})
        _save_draft(draft, dod_polozky=dod, step=STEP_ENTER_DOD)
    else:
        return False

    _post_step(draft, user)
    return True


def handle_slack_interaction(payload: dict) -> bool:
    """Zpracuje block action z tlačítka. True = zpracováno."""
    from .slack_notify import web_user_for_slack_id

    actions = payload.get("actions") or []
    if not actions:
        return False
    action = actions[0]
    action_id = action.get("action_id") or ""
    if not action_id.startswith(f"{ACTION_PREFIX}:"):
        return False

    slack_user_id = (payload.get("user") or {}).get("id") or ""
    web_user = web_user_for_slack_id(slack_user_id)
    if not web_user:
        return True

    draft = SlackTaskDraft.objects.filter(slack_user_id=slack_user_id).first()
    if draft is None:
        start_slack_task_wizard(slack_user_id, web_user)
        return True

    parts = action_id.split(":", 2)
    if len(parts) < 3:
        return False
    _, kind, value = parts[0], parts[1], parts[2]

    if kind == "confirm":
        if value == "cancel":
            _delete_draft(draft)
            send_slack_dm(slack_user_id, "Zakládání úkolu zrušeno.")
            return True
        if value == "create":
            return _finalize_draft(draft, web_user)

    if kind == "typ":
        if value == "osobni":
            data = _draft_data(draft)
            if data.get("vysledek"):
                _save_draft(draft, typ="osobni", step=STEP_CHOOSE_DEADLINE)
            else:
                _save_draft(draft, typ="osobni", step=STEP_ENTER_TITLE)
        elif value == "prirazeny":
            data = _draft_data(draft)
            if data.get("vysledek"):
                _save_draft(draft, typ="prirazeny", step=STEP_CHOOSE_STORE)
            else:
                _save_draft(draft, typ="prirazeny", step=STEP_ENTER_VYSLEDEK)
        _post_step(draft, web_user)
        return True

    if kind == "store":
        if value == "none" and getattr(web_user, "role", None) == "ADMIN":
            _save_draft(draft, id_prodejny=None, step=STEP_CHOOSE_ASSIGNEE, assignee_page=0)
        else:
            _save_draft(draft, id_prodejny=int(value), step=STEP_CHOOSE_ASSIGNEE, assignee_page=0)
        _post_step(draft, web_user)
        return True

    if kind == "assignee_page":
        _save_draft(draft, assignee_page=int(value), step=STEP_CHOOSE_ASSIGNEE)
        _post_step(draft, web_user)
        return True

    if kind == "assignee":
        _save_draft(draft, id_prodejce_ukol=int(value), step=STEP_ENTER_DOD, dod_polozky=[])
        _post_step(draft, web_user)
        return True

    if kind == "modal":
        if value in ("title", "vysledek", "dod"):
            _open_text_modal(payload, slack_user_id, value)
        return True

    if kind == "dod":
        data = _draft_data(draft)
        dod = data.get("dod_polozky") or []
        if value == "default":
            text = (data.get("vysledek") or data.get("ukol") or "Splněno podle popisu").strip()
            dod = [{"text": text[:500], "splneno": False}]
            _save_draft(draft, dod_polozky=dod, step=STEP_CHOOSE_DEADLINE)
        elif value == "next":
            if len(dod) < 1:
                send_slack_dm(slack_user_id, "U přiřazeného úkolu je povinná alespoň jedna položka DoD.")
                _post_step(draft, web_user)
                return True
            _save_draft(draft, step=STEP_CHOOSE_DEADLINE)
        else:
            _open_text_modal(payload, slack_user_id, "dod")
            return True
        _post_step(draft, web_user)
        return True

    if kind == "deadline":
        mapping = dict(_deadline_options())
        iso = mapping.get(value, "")
        data = _draft_data(draft)
        if data.get("typ") == "prirazeny" and not iso:
            send_slack_dm(slack_user_id, "U přiřazeného úkolu je termín dokončení povinný.")
            _post_step(draft, web_user)
            return True
        if iso:
            _save_draft(draft, deadline=iso, step=STEP_CHOOSE_PRIORITY)
        else:
            _save_draft(draft, deadline=None, step=STEP_CHOOSE_PRIORITY)
        _post_step(draft, web_user)
        return True

    if kind == "priority":
        if value not in PRIORITY_LABELS:
            value = "stredni"
        _save_draft(draft, priorita=value, step=STEP_CONFIRM)
        _post_step(draft, web_user)
        return True

    return False


def handle_slack_view_submission(payload: dict) -> bool:
    """Zpracuje odeslání modálního formuláře."""
    from .slack_notify import web_user_for_slack_id

    view = payload.get("view") or {}
    callback_id = view.get("callback_id") or ""
    if not callback_id.startswith(f"{MODAL_PREFIX}:"):
        return False

    kind = callback_id.split(":", 1)[1]
    slack_user_id = (view.get("private_metadata") or "").strip()
    if not slack_user_id:
        slack_user_id = (payload.get("user") or {}).get("id") or ""

    values = (view.get("state") or {}).get("values") or {}
    cleaned = (
        (values.get("text_input") or {}).get("value") or {}
    ).get("value") or ""
    cleaned = cleaned.strip()
    if not cleaned:
        return True

    web_user = web_user_for_slack_id(slack_user_id)
    draft = SlackTaskDraft.objects.filter(slack_user_id=slack_user_id).first()
    if not draft or not web_user:
        return True

    if kind == "title":
        _save_draft(
            draft,
            ukol=cleaned[:255],
            vysledek=cleaned,
            typ="osobni",
            step=STEP_CHOOSE_DEADLINE,
        )
    elif kind == "vysledek":
        _save_draft(
            draft,
            vysledek=cleaned,
            ukol=cleaned[:255],
            typ="prirazeny",
            step=STEP_CHOOSE_STORE,
        )
    elif kind == "dod":
        dod = list(_draft_data(draft).get("dod_polozky") or [])
        dod.append({"text": cleaned[:500], "splneno": False})
        _save_draft(draft, dod_polozky=dod, step=STEP_ENTER_DOD)
    else:
        return False

    _post_step(draft, web_user)
    return True


def _finalize_draft(draft: SlackTaskDraft, user: WebUser) -> bool:
    data = _draft_data(draft)
    payload = {
        "typ": data.get("typ", "osobni"),
        "ukol": data.get("ukol") or "",
        "vysledek": data.get("vysledek") or "",
        "popis": data.get("popis") or "",
        "priorita": data.get("priorita", "stredni"),
        "stav": "novy",
        "dod_polozky": data.get("dod_polozky") or [],
    }
    if data.get("deadline"):
        payload["deadline"] = data["deadline"]
    if data.get("id_prodejny") is not None:
        payload["id_prodejny"] = data["id_prodejny"]
    if data.get("id_prodejce_ukol"):
        payload["id_prodejce_ukol"] = data["id_prodejce_ukol"]

    task, err = create_ukol_for_user(user, payload)
    if err:
        send_slack_dm(draft.slack_user_id, f"Úkol se nepodařilo vytvořit: {err}")
        _post_step(draft, user)
        return True

    _delete_draft(draft)
    link = f"{_app_base_url()}/tasks/mine?id={task.id}"
    if task.typ == "prirazeny" and task.id_prodejce_ukol != user.id:
        link = f"{_app_base_url()}/tasks/manage?id={task.id}"
    title = (task.vysledek or task.ukol or f"Úkol #{task.id}").strip()
    send_slack_dm(
        draft.slack_user_id,
        f":white_check_mark: Úkol *{_escape_slack(title)}* (#{task.id}) byl vytvořen.\n<{link}|Otevřít v MOBILMAJAK>",
    )
    return True


def parse_interaction_payload(raw: str) -> dict:
    return json.loads(raw)
