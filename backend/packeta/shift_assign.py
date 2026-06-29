"""Přiřazení výdeje balíku prodejci podle nejbližší směny (pozice prodej)."""
from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone

from shifts.attendance_service import shift_window
from shifts.models import Smena

# Max. vzdálenost od směny – balík mimo okno se stejně přiřadí nejbližší směně v ±1 den
MAX_SHIFT_DISTANCE_MINUTES = 12 * 60


def _cas_to_aware(cas: datetime) -> datetime:
    if timezone.is_aware(cas):
        return cas
    return timezone.make_aware(cas, timezone.get_current_timezone())


def _minutes_to_shift(cas_dt: datetime, smena: Smena) -> float:
    start, end = shift_window(smena)
    if start <= cas_dt <= end:
        return 0.0
    if cas_dt < start:
        return (start - cas_dt).total_seconds() / 60.0
    return (cas_dt - end).total_seconds() / 60.0


def _candidate_smeny(prodejna_id: int, cas_dt: datetime):
    day = cas_dt.date()
    dates = [day - timedelta(days=1), day, day + timedelta(days=1)]
    return (
        Smena.objects.filter(
            prodejna_id=prodejna_id,
            datum__in=dates,
            typ_smeny='prace',
            pozice_smeny='prodej',
            aktivni=True,
        )
        .select_related('user')
        .order_by('datum', 'cas_od')
    )


def resolve_prodejce_for_packeta(prodejna_id: int, cas: datetime) -> int | None:
    """
    Vrátí user_id prodejce s nejbližší směnou prodej na prodejně.
    Balík lehce před/po směně patří stejnému prodejci (min. vzdálenost k intervalu směny).
    """
    if not prodejna_id or not cas:
        return None

    cas_dt = _cas_to_aware(cas)
    best_user_id: int | None = None
    best_dist = float('inf')

    for smena in _candidate_smeny(prodejna_id, cas_dt):
        dist = _minutes_to_shift(cas_dt, smena)
        if dist < best_dist:
            best_dist = dist
            best_user_id = smena.user_id

    if best_user_id is None or best_dist > MAX_SHIFT_DISTANCE_MINUTES:
        return None
    return best_user_id
