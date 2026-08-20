"""Pracovní dny (Po–Pá) pro připomínky objednávek."""
from __future__ import annotations

from datetime import date, timedelta

from django.utils import timezone


def _to_local_date(dt) -> date:
    if timezone.is_aware(dt):
        return timezone.localtime(dt).date()
    return dt.date()


def business_days_elapsed(since, now=None) -> int:
    """
    Počet pracovních dní (Po–Pá) od ``since`` do ``now``.
    Víkendy se nepočítají. Stejný kalendářní den = 0.
    """
    if not since:
        return 0
    now = now or timezone.now()
    if since >= now:
        return 0

    start = _to_local_date(since)
    end = _to_local_date(now)
    if end <= start:
        return 0

    count = 0
    current = start
    while current < end:
        current += timedelta(days=1)
        if current.weekday() < 5:
            count += 1
    return count
