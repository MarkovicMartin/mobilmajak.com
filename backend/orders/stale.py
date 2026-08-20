"""Připomínky objednávek bez pohybu ≥1 pracovní den (Po–Pá)."""
from __future__ import annotations

import logging

from django.utils import timezone

from .business_days import business_days_elapsed
from .models import Order
from .slack_notify import notify_order_stale

logger = logging.getLogger(__name__)

STALE_EXCLUDED_STATUSES = frozenset({"hotovo", "storno"})
STALE_BUSINESS_DAYS_THRESHOLD = 1


def orders_stale_candidates(now=None):
    """Objednávky ≥1 pracovní den ve stejném stavu (mimo hotovo/storno)."""
    now = now or timezone.now()
    qs = (
        Order.objects.exclude(status__in=STALE_EXCLUDED_STATUSES)
        .select_related("prodejna", "zalozil")
        .prefetch_related("historie_stavu")
    )
    stale = []
    for order in qs:
        since = order.status_since
        if not since:
            continue
        days = business_days_elapsed(since, now)
        if days < STALE_BUSINESS_DAYS_THRESHOLD:
            continue
        if order.stale_reminder_sent_at and order.stale_reminder_sent_at >= since:
            continue
        stale.append(order)
    return stale


def run_orders_stale_reminders(*, now=None, dry_run: bool = False) -> dict:
    now = now or timezone.now()
    candidates = orders_stale_candidates(now=now)
    sent = 0
    for order in candidates:
        days = business_days_elapsed(order.status_since, now)
        if dry_run:
            sent += 1
            continue
        status_before = order.status
        n = notify_order_stale(order, business_days=days)
        order.stale_reminder_sent_at = now
        order.save(update_fields=["stale_reminder_sent_at"])
        order.refresh_from_db(fields=["status"])
        if order.status != status_before:
            logger.error(
                "Stale reminder omylem změnil status objednávky #%s (%s → %s)",
                order.id,
                status_before,
                order.status,
            )
        sent += n if n else 1
    return {
        "candidates": len(candidates),
        "reminded": sent,
        "threshold_business_days": STALE_BUSINESS_DAYS_THRESHOLD,
        "dry_run": dry_run,
    }
