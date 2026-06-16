"""Synchronizace skutečného stavu dovolené z externí tabulky (fond / čerpání)."""
from decimal import Decimal

from shifts.vacation_service import (
    DOVOLENA_ROCNI_FOND,
    cerpana_dovolena_rok,
    deficit_fondu_rok,
    dovolena_stav,
    prevod_z_predchoziho_roku,
)


def normalize_prijmeni(prijmeni):
    return (prijmeni or '').strip().lower()


def apply_dovolena_targets(user, rok, fond_h, cerpano_h, zbyva_h=None, dry_run=False):
    """
    Nastaví dovolena_fond_extra_h a dovolena_korekce_cerpano_h tak,
    aby fond a čerpání odpovídaly skutečnosti mimo evidenci směn.
    """
    fond_h = float(fond_h)
    cerpano_h = float(cerpano_h)
    if zbyva_h is not None:
        expected = round(fond_h - cerpano_h, 2)
        if abs(expected - float(zbyva_h)) > 0.5:
            raise ValueError(
                f'Nesoulad u {user.prijmeni}: fond {fond_h} - čerpáno {cerpano_h} != zbývá {zbyva_h}'
            )

    prevod = prevod_z_predchoziho_roku(user.id, rok)
    fond_zaklad = float(DOVOLENA_ROCNI_FOND) + prevod
    cerpano_sys = cerpana_dovolena_rok(user.id, rok) + deficit_fondu_rok(user.id, rok)
    fond_extra = round(fond_h - fond_zaklad, 2)
    korekce = round(cerpano_h - cerpano_sys, 2)

    before = dovolena_stav(user, rok) or {}
    changes = {
        'prijmeni': user.prijmeni,
        'fond_extra': fond_extra,
        'korekce_cerpano': korekce,
        'cerpano_sys': round(cerpano_sys, 2),
        'fond_zaklad': round(fond_zaklad, 2),
        'before': {
            'fond_h': before.get('fond_h'),
            'cerpano_h': before.get('cerpano_h'),
            'zbyva_h': before.get('zbyva_h'),
        },
        'after': {
            'fond_h': fond_h,
            'cerpano_h': cerpano_h,
            'zbyva_h': round(fond_h - cerpano_h, 2),
        },
    }

    if not dry_run:
        user.dovolena_fond_extra_h = Decimal(str(fond_extra))
        user.dovolena_korekce_cerpano_h = Decimal(str(korekce))
        user.save(update_fields=['dovolena_fond_extra_h', 'dovolena_korekce_cerpano_h'])

    return changes
