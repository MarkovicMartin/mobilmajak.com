from __future__ import annotations

from datetime import datetime, time, timedelta

from django.utils import timezone

from .models import Ukol

URGENCY_NEUTRAL = "neutral"
URGENCY_WARN = "warn"
URGENCY_URGENT = "urgent"
URGENCY_OVERDUE = "overdue"


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


def is_task_unread(task: Ukol, user) -> bool:
    return (
        task.typ == "prirazeny"
        and task.id_prodejce_ukol == user.id
        and task.precteno_v is None
        and task.stav != "hotovo"
    )


def notifications_counts_for_user(user) -> dict:
    qs = Ukol.objects.filter(id_prodejce_ukol=user.id, stav__in=("novy", "v_procesu"))
    now = timezone.now()
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

    return {
        "tasks_unread": tasks_unread,
        "overdue_count": overdue_count,
        "due_soon_count": due_soon_count,
    }
