"""Pomocné funkce pro mzdové údaje uživatele (vše v bodech)."""
from decimal import Decimal

BRIGADNIK_DEFAULT_BODY_ZA_HODINU = Decimal('80')


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


def is_brigadnik(user):
    return getattr(user, 'role', None) == 'BRIGADNIK'


def mzda_zaklad_raw(user):
    val = getattr(user, 'mzda_zaklad', None)
    if val is None:
        return Decimal('0')
    return Decimal(str(val))


def mzda_body_za_hodinu(user):
    """Sazba bodů/h pro brigádníka (výchozí 80)."""
    if not is_brigadnik(user):
        return None
    rate = mzda_zaklad_raw(user)
    if rate <= 0:
        return BRIGADNIK_DEFAULT_BODY_ZA_HODINU
    return rate


def mzda_fixni_mesicni_body(user):
    """Fixní měsíční body (prodejce, vedoucí, admin v reportu)."""
    if is_brigadnik(user):
        return Decimal('0')
    return mzda_zaklad_raw(user)


def mzda_z_hodin_body(user, odpracovano_h):
    """Brigádník: odpracované hodiny × sazba bodů/h."""
    if not is_brigadnik(user):
        return Decimal('0')
    h = Decimal(str(odpracovano_h or 0))
    return (h * mzda_body_za_hodinu(user)).quantize(Decimal('0.01'))


def mzda_fixni_body(user, odpracovano_h=0):
    """Fixní část výplaty: měsíční fixní body nebo hodiny × sazba + doplňky."""
    doplnky_sum, _ = sum_mzda_doplnky(user)
    if is_brigadnik(user):
        return mzda_z_hodin_body(user, odpracovano_h) + doplnky_sum
    return mzda_fixni_mesicni_body(user) + doplnky_sum


# zpětná kompatibilita
def mzda_zaklad_body(user):
    return mzda_fixni_mesicni_body(user)
