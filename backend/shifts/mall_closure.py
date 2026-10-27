"""Dny, kdy zákon č. 223/2016 Sb. zakazuje prodej v maloobchodě nad 200 m².

Úplný zákaz: 1. leden, Velikonoční pondělí, 8. květen, 28. září, 28. říjen,
25. a 26. prosinec. Štědrý den (24. 12.) jen do 12:00.

Senimo má stejný zákaz směn i limit 24. 12. do 12:00. Navíc u něj
v kalendáři zůstává upozornění u státních svátků, které nejsou zavřené natvrdo.
"""
from datetime import date, time, timedelta

# Fixní dny úplného zákazu. Velikonoční pondělí se počítá zvlášť.
FIXED_RETAIL_BAN = frozenset({(1, 1), (5, 8), (9, 28), (10, 28), (12, 25), (12, 26)})

RETAIL_CLOSED_SHIFT_ERROR = (
    'V tento den mají nákupní centra podle zákona o prodejní době zavřeno. '
    'Směnu může přidat jen administrátor.'
)
CHRISTMAS_EVE_SHIFT_ERROR = (
    '24. 12. může být prodejna otevřená jen do 12:00. '
    'Směna musí skončit nejpozději v poledne.'
)
NOON = time(12, 0)


def easter_sunday(year: int) -> date:
    """Velikonoční neděle (anonymní gregoriánský algoritmus)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def easter_monday(year: int) -> date:
    return easter_sunday(year) + timedelta(days=1)


def is_retail_ban_day(d: date) -> bool:
    if (d.month, d.day) in FIXED_RETAIL_BAN:
        return True
    return d == easter_monday(d.year)


def closure_kind_for_date(d: date) -> str | None:
    """Vrátí always_closed v den úplného zákazu prodeje, jinak None."""
    if is_retail_ban_day(d):
        return 'always_closed'
    return None


def is_christmas_eve(d: date) -> bool:
    return d.month == 12 and d.day == 24


def retail_closed_shift_error(user, datum: date, prodejna=None) -> str | None:
    """Ne-admin nesmí na zákonně zavřený den směnu, včetně Senima."""
    del prodejna  # stejné pravidlo pro všechny prodejny
    if getattr(user, 'role', None) == 'ADMIN':
        return None
    if is_retail_ban_day(datum):
        return RETAIL_CLOSED_SHIFT_ERROR
    return None


def christmas_eve_shift_error(datum: date, prodejna, typ_smeny, cas_od, cas_do) -> str | None:
    """Pracovní směna na prodejně 24. 12. končí nejpozději v poledne, včetně Senima."""
    if not is_christmas_eve(datum):
        return None
    if typ_smeny != 'prace' or prodejna is None:
        return None
    if cas_od >= NOON or cas_do > NOON:
        return CHRISTMAS_EVE_SHIFT_ERROR
    return None


def cap_christmas_eve_hours(store, day: date, cas_od: time, cas_do: time):
    """Vrátí časy směny, nebo None když by 24. 12. celá spadla až po poledni."""
    del store
    if not is_christmas_eve(day):
        return cas_od, cas_do
    if cas_od >= NOON:
        return None
    if cas_do > NOON:
        return cas_od, NOON
    return cas_od, cas_do
