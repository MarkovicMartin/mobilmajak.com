"""Pomocné funkce pro směny – absence (dovolená, nemoc) bez prodejny."""

from __future__ import annotations

from datetime import date, datetime, timedelta, time

from django.db.models import Q

from stores.models import Prodejna

ABSENCE_SHIFT_TYPES = ('dovolena', 'nemoc')

BACKOFFICE_SURNAME_KEYS = frozenset({
    'smčková', 'smckova', 'smrčková', 'smrckova',
})

BACKOFFICE_CALENDAR_KEY = 'backoffice'
BACKOFFICE_BARVA = '#A8B4E8'


def is_admin_user(user) -> bool:
    return getattr(user, 'role', None) == 'ADMIN'


def is_home_office_pozice(pozice) -> bool:
    return (pozice or '').strip() == 'home_office'


def is_backoffice_pozice(pozice) -> bool:
    return (pozice or '').strip() == 'backoffice'


def is_skoleni_pozice(pozice) -> bool:
    return (pozice or '').strip() == 'skoleni'


def is_senimo_prodejna(prodejna) -> bool:
    return bool(prodejna) and (getattr(prodejna, 'nazev', None) or '').strip() == 'Senimo'


def backoffice_poznamka_chyba(typ_smeny, pozice, poznamka) -> str | None:
    """Backoffice směna vyžaduje neprázdnou poznámku – co ten den dělal."""
    if typ_smeny != 'prace' or not is_backoffice_pozice(pozice):
        return None
    if not (poznamka or '').strip():
        return 'U směny Backoffice je povinná poznámka – popište, co jste ten den dělali.'
    return None


def smena_bez_prodejny(pozice) -> bool:
    return is_home_office_pozice(pozice) or is_backoffice_pozice(pozice)


def backoffice_surname_keys():
    """Všechny varianty příjmení pro mapování (Excel, JSON override)."""
    return BACKOFFICE_SURNAME_KEYS


def is_backoffice_user(user) -> bool:
    """
    Backoffice – bez domovské prodejny, ve směnách jako Backoffice (ne Prodejce).
    Michaela Smčková je výslovně backoffice i při chybně nastavené prodejně.
    """
    if not user:
        return False
    prijmeni = (getattr(user, 'prijmeni', '') or '').strip().lower()
    if prijmeni in BACKOFFICE_SURNAME_KEYS:
        return True
    if getattr(user, 'role', None) == 'ADMIN':
        return False
    return (
        getattr(user, 'prodejna_id', None) is None
        and getattr(user, 'role', None) in ('PRODEJCE', 'VEDOUCI')
    )


def is_plans_eligible_user(user) -> bool:
    """Smí mít plán / výkon – ne backoffice, admin. Brigádník ano (výpomoc se filtruje po směnách)."""
    return user_muze_dostat_plan(user)


def user_muze_dostat_plan(user) -> bool:
    """Uživatel smí mít záznam PlanProdejce (auto nebo ruční přiřazení)."""
    if not user or not getattr(user, 'aktivni', False):
        return False
    if is_backoffice_user(user):
        return False
    return getattr(user, 'role', None) != 'ADMIN'


def smena_pocita_do_planovych_hodin(smena) -> bool:
    """
    Započítat směnu do hodin pro rozdělení plánu.
    Brigádník jen v režimu „jako prodejce“, ne výpomoc.
  """
    user = smena.user
    if not user_muze_dostat_plan(user):
        return False
    if getattr(user, 'role', None) == 'BRIGADNIK':
        if (getattr(smena, 'brigadnik_rezim', None) or 'prodejce') != 'prodejce':
            return False
    pozice = getattr(smena, 'pozice_smeny', None) or 'prodej'
    if pozice in ('backoffice', 'home_office'):
        return False
    return True

def earliest_editable_shift_date(today: date | None = None) -> date:
    """Nejdřívější datum směny, které smí upravovat prodejce (aktuální měsíc, ne minulost)."""
    today = today or date.today()
    return today.replace(day=1)


def seller_may_edit_shift_on_date(datum: date, today: date | None = None) -> bool:
    """Prodejce: aktuální a budoucí měsíce, ne minulé."""
    today = today or date.today()
    return datum >= earliest_editable_shift_date(today)


def user_may_edit_shift_on_date(user, datum: date, today: date | None = None) -> bool:
    if getattr(user, 'role', None) in ('ADMIN', 'VEDOUCI'):
        return True
    return seller_may_edit_shift_on_date(datum, today)


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


def is_backoffice_calendar_key(value) -> bool:
    return str(value or '').strip().lower() == BACKOFFICE_CALENDAR_KEY


def apply_backoffice_calendar_filter(qs):
    """Virtuální pobočka Backoffice – směny bez fyzické prodejny + absence backoffice lidí."""
    return qs.filter(
        Q(pozice_smeny='backoffice', prodejna__isnull=True, typ_smeny='prace')
        | Q(
            typ_smeny__in=ABSENCE_SHIFT_TYPES,
            prodejna__isnull=True,
            user__prodejna_id__isnull=True,
        )
    )
