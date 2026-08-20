"""7d eskalace objednávek – Bulandra + servis/prodejna, nikdy nemění status."""
from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import Order
from .slack_notify import notify_order_sla

logger = logging.getLogger(__name__)

SLA_EXCLUDED_STATUSES = frozenset({"hotovo", "storno"})


def sla_days_threshold() -> int:
    raw = getattr(settings, "ORDERS_SLA_DAYS", None)
    try:
        return max(1, int(raw if raw is not None else 7))
    except (TypeError, ValueError):
        return 7


def orders_past_sla(now=None):
    """Objednávky déle než práh ve stejném stavu (mimo hotovo/storno)."""
    now = now or timezone.now()
    threshold = sla_days_threshold()
    cutoff = now - timedelta(days=threshold)
    qs = (
        Order.objects.exclude(status__in=SLA_EXCLUDED_STATUSES)
        .select_related("zalozil")
        .prefetch_related("historie_stavu")
    )
    overdue = []
    for order in qs:
        since = order.status_since
        if since and since <= cutoff:
            if order.sla_reminder_sent_at and order.sla_reminder_sent_at >= since:
                continue
            overdue.append(order)
    return overdue


def run_orders_sla_reminders(*, now=None, dry_run: bool = False) -> dict:
    """
    Odešle Slack připomínky. Nikdy nemění status ani jiné business pole kromě
    sla_reminder_sent_at (marker dedupe).
    """
    now = now or timezone.now()
    candidates = orders_past_sla(now=now)
    sent = 0
    for order in candidates:
        days = order.days_in_current_status(now)
        if dry_run:
            sent += 1
            continue
        status_before = order.status
        n = notify_order_sla(order, days_in_status=days)
        # I při 0 DM (chybí Slack) označit, ať cron nesype logy každý den
        order.sla_reminder_sent_at = now
        order.save(update_fields=["sla_reminder_sent_at"])
        # Guard: status se nesmí změnit
        order.refresh_from_db(fields=["status"])
        if order.status != status_before:
            logger.error(
                "SLA reminder omylem změnil status objednávky #%s (%s → %s)",
                order.id,
                status_before,
                order.status,
            )
        sent += n if n else 1
    return {
        "candidates": len(candidates),
        "reminded": sent,
        "threshold_days": sla_days_threshold(),
        "dry_run": dry_run,
    }
