"""Ranní Slack recap úkolů ke začátku směny (+10 min)."""
from __future__ import annotations

import hashlib
from datetime import date, datetime, time, timedelta

from django.utils import timezone

from shifts.models import Smena
from users.models import WebUser

from .models import Ukol, UkolShiftRecapNotifikace
from .slack_notify import _app_base_url, _escape_slack, send_slack_dm, slack_user_id_for_web_user
from .urgency import OPEN_TASK_STATUSES, URGENCY_OVERDUE, urgency_for_task

RECAP_OFFSET_MINUTES = 10
RECAP_WINDOW_MINUTES = 12

MOTIVATIONAL_CLOSINGS = (
    "Čím dřív je máš hotové, tím dřív máš klid 🙂",
    "Klidná hlava na směně – úkoly postupně, bez stresu.",
    "Dneska to zvládneš – jeden krok po druhém.",
    "Až to bude hotové, můžeš se věnovat zákazníkům bez starostí v hlavě.",
)


def _local_now(now: datetime | None = None) -> datetime:
    return timezone.localtime(now or timezone.now())


def _motivational_line(user_id: int, datum: date) -> str:
    key = f"{user_id}:{datum.isoformat()}".encode()
    idx = int(hashlib.md5(key).hexdigest(), 16) % len(MOTIVATIONAL_CLOSINGS)
    return MOTIVATIONAL_CLOSINGS[idx]


def _format_deadline(task: Ukol) -> str:
    if not task.deadline:
        return "bez termínu"
    text = task.deadline.strftime("%d.%m.%Y")
    if task.deadline_cas:
        text += f" {task.deadline_cas.strftime('%H:%M')}"
    return text


def _task_title(task: Ukol) -> str:
    return (task.vysledek or task.ukol or f"Úkol #{task.id}").strip().split("\n")[0]


def open_tasks_for_user(user_id: int) -> list[Ukol]:
    return list(
        Ukol.objects.filter(
            typ="prirazeny",
            id_prodejce_ukol=user_id,
            stav__in=OPEN_TASK_STATUSES,
        ).order_by("deadline", "id")
    )


def last_completed_task(user_id: int) -> Ukol | None:
    return (
        Ukol.objects.filter(
            typ="prirazeny",
            id_prodejce_ukol=user_id,
            stav="hotovo",
            dokonceno_v__isnull=False,
        )
        .order_by("-dokonceno_v")
        .first()
    )


def build_shift_recap_message(
    user: WebUser,
    smena: Smena,
    tasks: list[Ukol],
    *,
    now: datetime | None = None,
) -> str:
    now = _local_now(now)
    today = now.date()
    jmeno = (user.jmeno or "").strip() or "ahoj"
    shift_from = smena.cas_od.strftime("%H:%M")

    lines = [
        f":sunrise: *Dobré ráno, {_escape_slack(jmeno)}!*",
        f"Dnes máš směnu od {shift_from}. Přehled tvých úkolů:",
        "",
    ]

    overdue: list[Ukol] = []
    due_today: list[Ukol] = []
    other: list[Ukol] = []

    for task in tasks:
        urgency = urgency_for_task(task, now)
        if urgency == URGENCY_OVERDUE:
            overdue.append(task)
        elif task.deadline == today:
            due_today.append(task)
        else:
            other.append(task)

    if overdue:
        lines.append(":warning: *Po termínu – řeš co nejdřív*")
        for task in overdue:
            lines.append(f"• {_escape_slack(_task_title(task))} (termín {_format_deadline(task)})")
        lines.append("")

    if due_today:
        lines.append(":rotating_light: *Dnes musí být hotovo!*")
        for task in due_today:
            lines.append(f"• {_escape_slack(_task_title(task))} (termín {_format_deadline(task)})")
        lines.append("")

    if other:
        lines.append(":clipboard: *Další aktivní úkoly*")
        for task in other:
            lines.append(f"• {_escape_slack(_task_title(task))} ({_format_deadline(task)})")
        lines.append("")

    if not tasks:
        lines.append("_Dnes nemáš otevřené přiřazené úkoly – přeji pohodovou směnu._")
        lines.append("")

    last_done = last_completed_task(user.id)
    if last_done:
        done_when = ""
        if last_done.dokonceno_v:
            done_when = timezone.localtime(last_done.dokonceno_v).strftime("%d.%m.%Y")
        lines.append(
            f":white_check_mark: Naposledy dokončeno: "
            f"*{_escape_slack(_task_title(last_done))}*"
            + (f" ({done_when})" if done_when else "")
        )
        lines.append("")

    lines.append(_motivational_line(user.id, today))
    link = f"{_app_base_url()}/tasks/mine"
    lines.append(f"<{link}|Otevřít moje úkoly v MOBILMAJAK>")

    return "\n".join(lines)


def shifts_due_for_recap(now: datetime | None = None) -> list[Smena]:
    """Směny typu práce, kde je čas pro odeslání recapu (start + 10 min)."""
    now = _local_now(now)
    today = now.date()
    window_start = now - timedelta(minutes=RECAP_WINDOW_MINUTES)
    window_end = now

    qs = (
        Smena.objects.filter(
            aktivni=True,
            typ_smeny="prace",
            datum=today,
            user__aktivni=True,
        )
        .select_related("user")
        .order_by("cas_od")
    )

    due: list[Smena] = []
    tz = timezone.get_current_timezone()
    already_sent = set(
        UkolShiftRecapNotifikace.objects.filter(datum=today).values_list("smena_id", flat=True)
    )

    for smena in qs:
        if smena.id in already_sent:
            continue
        start = timezone.make_aware(datetime.combine(smena.datum, smena.cas_od), tz)
        recap_at = start + timedelta(minutes=RECAP_OFFSET_MINUTES)
        if window_start <= recap_at <= window_end:
            due.append(smena)
    return due


def send_shift_recap(smena: Smena, *, now: datetime | None = None) -> bool:
    """Odešle recap uživateli směny. Vrací True pokud odesláno."""
    if UkolShiftRecapNotifikace.objects.filter(smena_id=smena.id).exists():
        return False

    user = smena.user
    slack_id = slack_user_id_for_web_user(user)
    if not slack_id:
        return False

    tasks = open_tasks_for_user(user.id)
    text = build_shift_recap_message(user, smena, tasks, now=now)
    if not send_slack_dm(slack_id, text):
        return False

    UkolShiftRecapNotifikace.objects.create(
        smena_id=smena.id,
        user_id=user.id,
        datum=_local_now(now).date(),
    )
    return True
