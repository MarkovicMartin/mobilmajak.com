"""Slack notifikace k termínům úkolů."""
from __future__ import annotations

import logging

import requests
from django.conf import settings
from django.utils import timezone

from users.models import WebUser

from .models import Ukol, UkolSlackNotifikace
from .urgency import URGENCY_OVERDUE, URGENCY_URGENT, urgency_for_task

logger = logging.getLogger(__name__)

NOTIFY_TYPES = ("due_soon", "overdue")


def _webhook_url() -> str:
    return (getattr(settings, "SLACK_TASKS_WEBHOOK_URL", None) or "").strip()


def _app_base_url() -> str:
    return (getattr(settings, "MOBILMAJAK_APP_URL", None) or "https://mobilmajak.com").rstrip("/")


def _assignee_name(task: Ukol) -> str:
    try:
        u = WebUser.objects.get(pk=task.id_prodejce_ukol)
        return f"{u.jmeno} {u.prijmeni}".strip() or str(u.id)
    except WebUser.DoesNotExist:
        return str(task.id_prodejce_ukol)


def _task_title(task: Ukol) -> str:
    return (task.vysledek or task.ukol or f"Úkol #{task.id}").strip().split("\n")[0]


def _task_link(task: Ukol) -> str:
    return f"{_app_base_url()}/profile?tab=tasks&task={task.id}"


def _format_deadline(task: Ukol) -> str:
    if not task.deadline:
        return "—"
    text = task.deadline.strftime("%d.%m.%Y")
    if task.deadline_cas:
        text += f" {task.deadline_cas.strftime('%H:%M')}"
    return text


def build_slack_payload(task: Ukol, notify_typ: str) -> dict:
    title = _task_title(task)
    assignee = _assignee_name(task)
    deadline = _format_deadline(task)
    link = _task_link(task)

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
        f"Termín: {deadline}\n"
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


def _escape_slack(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def send_slack_message(task: Ukol, notify_typ: str) -> bool:
    """Odešle Slack zprávu; vrací True pokud odesláno (nebo webhook není nastaven – no-op)."""
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
        UkolSlackNotifikace.objects.create(ukol=task, typ=notify_typ)
        logger.info("Slack %s odesláno pro úkol #%s", notify_typ, task.id)
        return True
    except Exception:
        logger.exception("Slack notifikace selhala pro úkol #%s typ=%s", task.id, notify_typ)
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


def tasks_needing_slack_notify(now=None):
    """Vrátí (task, notify_typ) pro otevřené přiřazené úkoly s termínem."""
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
        if task.slack_notifikace.filter(typ=notify_typ).exists():
            continue
        out.append((task, notify_typ))
    return out
