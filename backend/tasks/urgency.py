from __future__ import annotations

from datetime import datetime, time, timedelta

from django.utils import timezone

from .models import Ukol

URGENCY_NEUTRAL = "neutral"
URGENCY_WARN = "warn"
URGENCY_URGENT = "urgent"
URGENCY_OVERDUE = "overdue"

WIP_SOFT_LIMIT = 3
AT_RISK_INACTIVITY_HOURS = 48
AT_RISK_BLOCKED_HOURS = 24

OPEN_TASK_STATUSES = ("novy", "v_procesu", "blokovany", "ceka_schvaleni")


def task_deadline_dt(task: Ukol) -> datetime | None:
    if not task.deadline:
        return None
    cas = task.deadline_cas or time(23, 59, 59)
    naive = datetime.combine(task.deadline, cas)
    if timezone.is_aware(timezone.now()):
        return timezone.make_aware(naive, timezone.get_current_timezone())
    return naive


def urgency_for_task(task: Ukol, now: datetime | None = None) -> str:
    now = now or timezone.now()
    if task.stav in ("hotovo", "ceka_schvaleni"):
        return URGENCY_NEUTRAL
    deadline = task_deadline_dt(task)
    if not deadline:
        return URGENCY_NEUTRAL
    if now > deadline:
        return URGENCY_OVERDUE
    delta = deadline - now
    if delta <= timedelta(hours=24):
        return URGENCY_URGENT
    if delta <= timedelta(days=7):
        return URGENCY_WARN
    return URGENCY_NEUTRAL


def is_at_risk(task: Ukol, now: datetime | None = None) -> bool:
    """At risk: po termínu, bez aktivity 48h, nebo blokovaný bez komentáře 24h."""
    if task.stav in ("hotovo", "ceka_schvaleni"):
        return False
    now = now or timezone.now()

    deadline = task_deadline_dt(task)
    if deadline and now > deadline:
        return True

    if task.stav == "blokovany":
        ref = task.posledni_aktivita_v or task.upraveno or task.vytvoreno
        if ref and (now - ref) >= timedelta(hours=AT_RISK_BLOCKED_HOURS):
            return True
        return True

    if task.stav in ("v_procesu", "blokovany"):
        ref = task.posledni_aktivita_v or task.start_potvrzeno_v or task.upraveno
        if ref and (now - ref) >= timedelta(hours=AT_RISK_INACTIVITY_HOURS):
            return True

    return False


def is_task_unread(task: Ukol, user) -> bool:
    return (
        task.typ == "prirazeny"
        and task.id_prodejce_ukol == user.id
        and task.precteno_v is None
        and task.stav not in ("hotovo", "ceka_schvaleni")
    )


def active_task_count_for_assignee(assignee_id: int) -> int:
    return Ukol.objects.filter(
        typ="prirazeny",
        id_prodejce_ukol=assignee_id,
        stav__in=Ukol.ACTIVE_STAVY,
    ).count()


def wip_warning_for_assignee(assignee_id: int) -> str | None:
    count = active_task_count_for_assignee(assignee_id)
    if count >= WIP_SOFT_LIMIT:
        return (
            f"Zaměstnanec má {count} aktivních přiřazených úkolů "
            f"(doporučený limit {WIP_SOFT_LIMIT})."
        )
    return None


def notifications_counts_for_user(user) -> dict:
    now = timezone.now()
    qs = Ukol.objects.filter(id_prodejce_ukol=user.id, stav__in=OPEN_TASK_STATUSES)
    tasks_unread = 0
    overdue_count = 0
    due_soon_count = 0

    for task in qs.filter(typ="prirazeny"):
        if is_task_unread(task, user):
            tasks_unread += 1

    for task in qs:
        urgency = urgency_for_task(task, now)
        if urgency == URGENCY_OVERDUE:
            overdue_count += 1
        elif urgency in (URGENCY_URGENT, URGENCY_WARN):
            due_soon_count += 1

    result = {
        "tasks_unread": tasks_unread,
        "overdue_count": overdue_count,
        "due_soon_count": due_soon_count,
        "at_risk_count": 0,
        "cekajici_schvaleni_count": 0,
    }

    from users.vedouci_utils import is_task_manager, vedouci_store_ids

    role = getattr(user, "role", None)
    if role == "ADMIN":
        manager_qs = Ukol.objects.filter(typ="prirazeny").exclude(stav="hotovo")
    elif is_task_manager(user):
        store_ids = vedouci_store_ids(user)
        if not store_ids:
            return result
        manager_qs = Ukol.objects.filter(typ="prirazeny", id_prodejny__in=store_ids).exclude(
            stav="hotovo"
        )
    else:
        return result

    at_risk_count = 0
    for task in manager_qs:
        if is_at_risk(task, now):
            at_risk_count += 1

    cekajici_schvaleni_count = manager_qs.filter(stav="ceka_schvaleni").count()

    result["at_risk_count"] = at_risk_count
    result["cekajici_schvaleni_count"] = cekajici_schvaleni_count
    return result
