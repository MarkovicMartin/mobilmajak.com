"""Preference Slack notifikací k úkolům – per uživatel."""
from __future__ import annotations

from users.models import WebUser

from .models import Ukol

# Klíče uložené v WebUser.slack_ukoly_prefs (JSON)
PREF_ASSIGNED_MINE = "assigned_mine"
PREF_CREATED_CONFIRM = "created_confirm"
PREF_CREATED_ALL = "created_all"
PREF_DUE_SOON_MINE = "due_soon_mine"
PREF_DUE_SOON_ALL = "due_soon_all"
PREF_OVERDUE_MINE = "overdue_mine"
PREF_OVERDUE_ALL = "overdue_all"
PREF_AWAITING_APPROVAL = "awaiting_approval"
PREF_STARTED_MINE = "started_mine"
PREF_COMPLETED_MINE = "completed_mine"
PREF_COMMENT_MINE = "comment_mine"
PREF_COMMENT_ALL = "comment_all"

SLACK_UKOLY_PREF_KEYS = (
    PREF_ASSIGNED_MINE,
    PREF_CREATED_CONFIRM,
    PREF_CREATED_ALL,
    PREF_DUE_SOON_MINE,
    PREF_DUE_SOON_ALL,
    PREF_OVERDUE_MINE,
    PREF_OVERDUE_ALL,
    PREF_AWAITING_APPROVAL,
    PREF_STARTED_MINE,
    PREF_COMPLETED_MINE,
    PREF_COMMENT_MINE,
    PREF_COMMENT_ALL,
)

DEFAULT_SLACK_UKOLY_PREFS: dict[str, bool] = {
    PREF_ASSIGNED_MINE: True,
    PREF_CREATED_CONFIRM: False,
    PREF_CREATED_ALL: False,
    PREF_DUE_SOON_MINE: True,
    PREF_DUE_SOON_ALL: False,
    PREF_OVERDUE_MINE: True,
    PREF_OVERDUE_ALL: False,
    PREF_AWAITING_APPROVAL: True,
    PREF_STARTED_MINE: True,
    PREF_COMPLETED_MINE: True,
    PREF_COMMENT_MINE: False,
    PREF_COMMENT_ALL: False,
}

# Výchozí presety pro konkrétní uživatele (data migrace)
USER_SLACK_UKOLY_PRESETS: dict[int, dict[str, bool]] = {
  # Radek Bulandra – supervizor všech úkolů
    888: {
        PREF_CREATED_ALL: True,
        PREF_DUE_SOON_ALL: True,
        PREF_OVERDUE_ALL: True,
        PREF_DUE_SOON_MINE: False,
        PREF_OVERDUE_MINE: False,
        PREF_COMMENT_ALL: True,
    },
    # Martin Markovič – jen vlastní + po termínu
    999: {
        PREF_CREATED_CONFIRM: False,
        PREF_DUE_SOON_MINE: False,
        PREF_CREATED_ALL: False,
        PREF_DUE_SOON_ALL: False,
        PREF_OVERDUE_ALL: False,
        PREF_COMMENT_MINE: True,
    },
}

_global_watcher_cache: dict[str, list[int]] = {}


def get_slack_ukoly_prefs(user: WebUser | int | None) -> dict[str, bool]:
    """Sloučí uložené preference s výchozími hodnotami."""
    prefs = dict(DEFAULT_SLACK_UKOLY_PREFS)
    if user is None:
        return prefs
    if isinstance(user, int):
        try:
            user = WebUser.objects.only("slack_ukoly_prefs").get(pk=user)
        except WebUser.DoesNotExist:
            return prefs

    stored = user.slack_ukoly_prefs or {}
    if isinstance(stored, dict):
        for key in SLACK_UKOLY_PREF_KEYS:
            if key in stored:
                prefs[key] = bool(stored[key])
    return prefs


def normalize_slack_ukoly_prefs(data: dict | None) -> dict[str, bool]:
    """Validuje a normalizuje vstup z API."""
    if not isinstance(data, dict):
        return dict(DEFAULT_SLACK_UKOLY_PREFS)
    out = get_slack_ukoly_prefs(None)
    for key in SLACK_UKOLY_PREF_KEYS:
        if key in data:
            out[key] = bool(data[key])
    return out


def invalidate_global_watcher_cache() -> None:
    _global_watcher_cache.clear()


def global_watcher_ids(pref_key: str) -> list[int]:
    """Aktivní uživatelé s danou globální volbou (created_all, due_soon_all, …)."""
    if pref_key in _global_watcher_cache:
        return list(_global_watcher_cache[pref_key])

    ids: list[int] = []
    for user in WebUser.objects.filter(aktivni=True).only("id", "slack_ukoly_prefs"):
        if get_slack_ukoly_prefs(user).get(pref_key):
            ids.append(user.id)
    _global_watcher_cache[pref_key] = ids
    return list(ids)


def is_task_mine_for_user(task: Ukol, user_id: int, *, vedouci_id: int | None = None) -> bool:
    """Úkol „můj“ = jsem řešitel, zadavatel, nebo vedoucí prodejny úkolu."""
    if user_id == task.id_prodejce_ukol or user_id == task.id_prodejce_zadal:
        return True
    if vedouci_id and user_id == vedouci_id:
        return True
    return False


def user_wants_slack_notification(
    user_id: int,
    task: Ukol,
    event_type: str,
    *,
    vedouci_id: int | None = None,
) -> bool:
    """Má uživatel dostat DM pro danou událost u tohoto úkolu?"""
    prefs = get_slack_ukoly_prefs(user_id)
    mine = is_task_mine_for_user(task, user_id, vedouci_id=vedouci_id)
    assignee = user_id == task.id_prodejce_ukol
    zadavatel = user_id == task.id_prodejce_zadal
    is_vedouci = vedouci_id is not None and user_id == vedouci_id

    if event_type == "assigned":
        return assignee and prefs[PREF_ASSIGNED_MINE]
    if event_type == "created":
        if zadavatel and prefs[PREF_CREATED_CONFIRM]:
            return True
        return prefs[PREF_CREATED_ALL]
    if event_type == "due_soon":
        if mine and prefs[PREF_DUE_SOON_MINE]:
            return True
        return prefs[PREF_DUE_SOON_ALL]
    if event_type == "overdue":
        if mine and prefs[PREF_OVERDUE_MINE]:
            return True
        return prefs[PREF_OVERDUE_ALL]
    if event_type == "awaiting_approval":
        return (zadavatel or is_vedouci) and prefs[PREF_AWAITING_APPROVAL]
    if event_type == "started":
        return zadavatel and prefs[PREF_STARTED_MINE]
    if event_type == "completed":
        return zadavatel and prefs[PREF_COMPLETED_MINE]
    return False
