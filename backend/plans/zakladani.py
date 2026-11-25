"""Starší zápis nedostatků. Ukládá do stejné tabulky jako Automatizace karet."""
from .automatizace_karet import (
    NeplatnyProblem,
    oznac_vyreseno as _oznac,
    radky,
    zapis_problem,
)

NeplatnyNedostatek = NeplatnyProblem


def zapis_nedostatek(*, kod, typ, text, nazev='', zbozi_id=None):
    """Stejné místo jako automatizace karet. Otevřený kód a typ se nepřidává znovu."""
    try:
        return zapis_problem(kod=kod, typ=typ, text=text, nazev=nazev, zbozi_id=zbozi_id)
    except NeplatnyProblem as exc:
        raise NeplatnyNedostatek(str(exc)) from exc


def oznac_vyreseno(pk, user):
    return _oznac(pk, user)
