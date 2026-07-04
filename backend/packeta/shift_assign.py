"""Přiřazení výdeje balíku prodejci podle nejbližší směny (pozice prodej)."""
from __future__ import annotations

from datetime import datetime, time, timedelta

from django.utils import timezone

from shifts.attendance_service import shift_window
from shifts.models import Smena
from users.prodejce_resolve import sales_id_keys_for_user

# Max. vzdálenost od směny – balík mimo okno se stejně přiřadí nejbližší směně v ±1 den
MAX_SHIFT_DISTANCE_MINUTES = 12 * 60
# Okno pro tie-break podle prodejů při překryvu směn
SALES_TIEBREAK_HOURS = 2


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


def _sale_datetime(row_date, cas_prodeje) -> datetime | None:
    if not row_date:
        return None
    if cas_prodeje is None:
        return datetime.combine(row_date, time.min)
    if hasattr(cas_prodeje, 'hour'):
        return datetime.combine(row_date, cas_prodeje)
    try:
        parts = str(cas_prodeje).split(':')
        return datetime.combine(row_date, time.min.replace(
            hour=int(parts[0]), minute=int(parts[1]) if len(parts) > 1 else 0,
        ))
    except (ValueError, IndexError):
        return datetime.combine(row_date, time.min)


def _count_sales_near(prodejna_id: int, user_id: int, cas_dt: datetime) -> int:
    """Počet unikátních dokladů prodejce v ±SALES_TIEBREAK_HOURS kolem výdeje balíku."""
    from analytics.models import WebProdejeAll
    from analytics.receipt_metrics import active_receipt_filter_q

    keys = sales_id_keys_for_user(user_id)
    if not keys:
        return 0

    day = cas_dt.date()
    window = timedelta(hours=SALES_TIEBREAK_HOURS)
    qs = (
        WebProdejeAll.objects.filter(
            id_prodejny=prodejna_id,
            typ__in=[day - timedelta(days=1), day, day + timedelta(days=1)],
            id_prodejce__in=list(keys),
        )
        .filter(active_receipt_filter_q())
        .values('typ', 'cas_prodeje', 'doklad')
        .distinct()
    )

    seen: set[str] = set()
    count = 0
    for row in qs:
        doklad = row.get('doklad')
        if not doklad or doklad in seen:
            continue
        sale_dt = _sale_datetime(row['typ'], row.get('cas_prodeje'))
        if sale_dt is None:
            continue
        sale_dt = _cas_to_aware(sale_dt)
        if abs((sale_dt - cas_dt).total_seconds()) <= window.total_seconds():
            seen.add(doklad)
            count += 1
    return count


def _pick_from_overlap(prodejna_id: int, cas_dt: datetime, overlapping: list[Smena]) -> int:
    """Při více prodejcích ve směně: nejvíc prodejů v okně, pak kratší směna."""
    if len(overlapping) == 1:
        return overlapping[0].user_id

    scored: list[tuple[int, float, Smena]] = []
    for smena in overlapping:
        sales = _count_sales_near(prodejna_id, smena.user_id, cas_dt)
        start, end = shift_window(smena)
        duration_h = max((end - start).total_seconds() / 3600.0, 0.01)
        scored.append((sales, duration_h, smena))

    scored.sort(key=lambda x: (-x[0], x[1], x[2].cas_od, x[2].user_id))
    best_sales = scored[0][0]
    top = [s for sales, _dur, s in scored if sales == best_sales]
    if len(top) == 1:
        return top[0].user_id

    top.sort(key=lambda s: (shift_window(s)[1] - shift_window(s)[0], s.cas_od, s.user_id))
    return top[0].user_id


def resolve_prodejce_for_packeta(prodejna_id: int, cas: datetime) -> int | None:
    """
    Vrátí WebUser.id prodejce s nejbližší směnou prodej na prodejně.
    Při překryvu směn rozhodne podle prodejů v ±2 h; jinak nejbližší interval směny.
    """
    if not prodejna_id or not cas:
        return None

    cas_dt = _cas_to_aware(cas)
    overlapping: list[Smena] = []
    best_user_id: int | None = None
    best_dist = float('inf')

    for smena in _candidate_smeny(prodejna_id, cas_dt):
        dist = _minutes_to_shift(cas_dt, smena)
        if dist == 0.0:
            overlapping.append(smena)
        elif dist < best_dist:
            best_dist = dist
            best_user_id = smena.user_id

    if overlapping:
        return _pick_from_overlap(prodejna_id, cas_dt, overlapping)

    if best_user_id is None or best_dist > MAX_SHIFT_DISTANCE_MINUTES:
        return None
    return best_user_id
