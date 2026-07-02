"""Pomocné funkce pro směny – absence (dovolená, nemoc) bez prodejny."""

from __future__ import annotations

from datetime import date, datetime, timedelta, time

from django.db.models import Q

from stores.models import Prodejna

ABSENCE_SHIFT_TYPES = ('dovolena', 'nemoc')

# Dočasně: prodejci mohou opravit směny za červen 2026 do 1. 8. 2026.
JUNE_2026_SHIFT_EDIT_UNTIL = date(2026, 8, 1)
JUNE_2026_START = date(2026, 6, 1)


def earliest_editable_shift_date(today: date | None = None) -> date:
    """Nejdřívější datum směny, které může upravovat prodejce (ne admin/vedoucí)."""
    today = today or date.today()
    current_month_start = today.replace(day=1)
    if today < JUNE_2026_SHIFT_EDIT_UNTIL and JUNE_2026_START < current_month_start:
        return JUNE_2026_START
    return current_month_start


def seller_may_edit_shift_on_date(datum: date, today: date | None = None) -> bool:
    return datum >= earliest_editable_shift_date(today)


def is_absence_shift(typ_smeny: str | None) -> bool:
    return typ_smeny in ABSENCE_SHIFT_TYPES


def resolve_prodejna(prodejna_input, typ_smeny: str):
    """Pro dovolenou/nemoc vrací None; jinak Prodejna nebo vyvolá výjimku."""
    if is_absence_shift(typ_smeny):
        return None
    if prodejna_input is None:
        raise ValueError('Chybí parametr prodejna')
    try:
        return Prodejna.objects.get(id=int(prodejna_input))
    except (ValueError, TypeError):
        prodejna_obj = Prodejna.objects.filter(
            Q(nazev__iexact=prodejna_input)
            | Q(nazev_kratkiy__iexact=prodejna_input)
            | Q(nazev_google_sheets__iexact=prodejna_input)
        ).first()
        if not prodejna_obj:
            raise Prodejna.DoesNotExist
        return prodejna_obj


def parse_shift_time(value) -> time:
    """Parsuje čas směny z time objektu nebo řetězce HH:MM / HH:MM:SS."""
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        for fmt in ('%H:%M:%S', '%H:%M'):
            try:
                return datetime.strptime(value.strip(), fmt).time()
            except ValueError:
                continue
    raise ValueError(f'Neplatný čas směny: {value!r}')


def shift_interval_bounds(datum, cas_od, cas_do):
    """Vrátí (start, end) jako datetime; směna přes půlnoc má end na další den."""
    start = datetime.combine(datum, parse_shift_time(cas_od))
    end = datetime.combine(datum, parse_shift_time(cas_do))
    if end <= start:
        end += timedelta(days=1)
    return start, end


def shifts_time_overlap(datum, cas_od_a, cas_do_a, cas_od_b, cas_do_b) -> bool:
    a_start, a_end = shift_interval_bounds(datum, cas_od_a, cas_do_a)
    b_start, b_end = shift_interval_bounds(datum, cas_od_b, cas_do_b)
    return a_start < b_end and b_start < a_end


def find_overlapping_shift(
    user,
    datum,
    prodejna_obj,
    typ_smeny: str,
    cas_od,
    cas_do,
    *,
    exclude_id=None,
):
    """
    Vrátí konfliktní směnu, pokud existuje.
    Dovolená/nemoc: max. jeden záznam na den (bez ohledu na čas).
    Práce: konflikt jen při časovém překryvu na stejné prodejně.
    """
    from .models import Smena

    if is_absence_shift(typ_smeny):
        qs = Smena.objects.filter(
            user=user,
            datum=datum,
            aktivni=True,
            typ_smeny__in=ABSENCE_SHIFT_TYPES,
        )
        if exclude_id is not None:
            qs = qs.exclude(id=exclude_id)
        return qs.first()

    qs = Smena.objects.filter(
        user=user,
        datum=datum,
        prodejna=prodejna_obj,
        aktivni=True,
        typ_smeny='prace',
    )
    if exclude_id is not None:
        qs = qs.exclude(id=exclude_id)

    for smena in qs:
        if shifts_time_overlap(datum, cas_od, cas_do, smena.cas_od, smena.cas_do):
            return smena
    return None


def find_existing_shift(user, datum, prodejna_obj, typ_smeny: str, cas_od=None, cas_do=None, exclude_id=None):
    """Zpětná kompatibilita – bez časů u práce hledá libovolnou směnu ten den (staré volání)."""
    if cas_od is not None and cas_do is not None:
        return find_overlapping_shift(
            user, datum, prodejna_obj, typ_smeny, cas_od, cas_do, exclude_id=exclude_id,
        )
    from .models import Smena

    if is_absence_shift(typ_smeny):
        return Smena.objects.filter(
            user=user,
            datum=datum,
            aktivni=True,
            typ_smeny__in=ABSENCE_SHIFT_TYPES,
        ).first()
    return Smena.objects.filter(
        user=user,
        datum=datum,
        prodejna=prodejna_obj,
        aktivni=True,
    ).first()


def apply_calendar_prodejna_filter(qs, prodejna):
    """Pracovní směny na pobočce + absence zaměstnanců s domovskou pobočkou."""
    if prodejna is None:
        return qs
    return qs.filter(
        Q(prodejna=prodejna)
        | Q(
            prodejna__isnull=True,
            typ_smeny__in=ABSENCE_SHIFT_TYPES,
            user__prodejna_id=prodejna.id,
        )
    )
