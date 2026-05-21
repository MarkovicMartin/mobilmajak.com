"""Výpočet fondu pracovní doby a přesčasu (plný úvazek 40 h/týden)."""
from calendar import monthrange
from datetime import date

from .views import get_ceske_svatky

HODINY_NA_PRACOVNI_DEN = 8


def svatky_v_mesici_set(rok, mesic_cislo):
    ceske = get_ceske_svatky(rok)
    return {
        date(rok_s, mesic_s, den_s)
        for rok_s, mesic_s, den_s in ceske
        if mesic_s == mesic_cislo
    }


def fondu_hodin_mesic(rok, mesic_cislo):
    """
    Fond hodin pro plný úvazek: Po–Pá v měsíci × 8 h,
    mínus 8 h za každý státní svátek padnoucí na pracovní den.
    """
    _, days_in_month = monthrange(rok, mesic_cislo)
    svatky = svatky_v_mesici_set(rok, mesic_cislo)
    pracovni_dny = 0
    svatky_na_pracovni_den = 0

    for day in range(1, days_in_month + 1):
        d = date(rok, mesic_cislo, day)
        if d.weekday() >= 5:
            continue
        pracovni_dny += 1
        if d in svatky:
            svatky_na_pracovni_den += 1

    fondu = pracovni_dny * HODINY_NA_PRACOVNI_DEN - svatky_na_pracovni_den * HODINY_NA_PRACOVNI_DEN
    return round(max(0, fondu), 2)


def prescas_hodin(odpracovano_h, fondu_h):
    return round(max(0, float(odpracovano_h or 0) - float(fondu_h or 0)), 2)
