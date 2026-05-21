"""Pomocné funkce pro mzdové údaje uživatele (vše v bodech)."""
from decimal import Decimal


def normalize_mzda_doplnky(raw):
    """Validuje a normalizuje seznam doplňků z JSON."""
    if not raw:
        return []
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw[:10]:
        if not isinstance(item, dict):
            continue
        kod = str(item.get('kod') or '').strip()[:50]
        nazev = str(item.get('nazev') or '').strip()[:200]
        try:
            castka = Decimal(str(item.get('castka') or 0))
        except Exception:
            castka = Decimal('0')
        if castka < 0:
            castka = Decimal('0')
        if not nazev and not kod:
            continue
        out.append({
            'kod': kod or f'doplnek_{len(out) + 1}',
            'nazev': nazev or kod,
            'castka': float(castka),
        })
    return out


def sum_mzda_doplnky(user):
    doplnky = normalize_mzda_doplnky(getattr(user, 'mzda_doplnky', None))
    total = Decimal('0')
    for p in doplnky:
        total += Decimal(str(p.get('castka') or 0))
    return total, doplnky


def mzda_zaklad_body(user):
    val = getattr(user, 'mzda_zaklad', None)
    if val is None:
        return Decimal('0')
    return Decimal(str(val))


def mzda_fixni_body(user):
    return mzda_zaklad_body(user) + sum_mzda_doplnky(user)[0]
