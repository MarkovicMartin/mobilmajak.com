"""Fixní dny zavření prodejen – NC vs Globus (kalendář směn)."""
from datetime import date

ALWAYS_CLOSED = frozenset({(1, 1), (12, 25), (12, 26)})
NC_TYPICALLY_CLOSED = frozenset({(5, 8), (9, 28), (10, 28)})


def closure_kind_for_date(d: date) -> str | None:
    """Vrátí always_closed | nc_verify_closed nebo None."""
    key = (d.month, d.day)
    if key in ALWAYS_CLOSED:
        return 'always_closed'
    if key in NC_TYPICALLY_CLOSED:
        return 'nc_verify_closed'
    return None
