"""Pomocné funkce pro mzdové údaje uživatele (vše v bodech)."""
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

BRIGADNIK_DEFAULT_BODY_ZA_HODINU = Decimal('100')
BRIGADNIK_VYPOMOC_BODY_ZA_HODINU = Decimal('150')
PRODEJCE_ZAKLAD_BODY = Decimal('14000')
VYCHODIL_ZAKLAD_BODY = Decimal('17000')
VYCHODIL_TECHNIK_ID = 121


def is_vychodil_user(user=None, *, jmeno=None, prijmeni=None, technik_id=None):
    """František Vychodil – vyšší měsíční základ."""
    if user is not None:
        prijmeni = getattr(user, 'prijmeni', None)
        technik_id = getattr(user, 'technik_id', None)
    if technik_id == VYCHODIL_TECHNIK_ID:
        return True
    return (prijmeni or '').strip().lower() == 'vychodil'


def default_mzda_zaklad_body(role, user=None, *, jmeno=None, prijmeni=None, technik_id=None):
    """Výchozí fixní měsíční body podle role (bez doplňků vedoucího)."""
    if role == 'BRIGADNIK':
        return BRIGADNIK_DEFAULT_BODY_ZA_HODINU
    if role in ('PRODEJCE', 'VEDOUCI'):
        if is_vychodil_user(user, jmeno=jmeno, prijmeni=prijmeni, technik_id=technik_id):
            return VYCHODIL_ZAKLAD_BODY
        return PRODEJCE_ZAKLAD_BODY
    return None


_STAFF_MONTHLY_DEFAULTS = frozenset({PRODEJCE_ZAKLAD_BODY, VYCHODIL_ZAKLAD_BODY})


def coerce_mzda_zaklad_for_role(role, mzda_zaklad, user=None, *, jmeno=None, prijmeni=None, technik_id=None):
    """Doplní prázdný základ a nahradí default z jiné role (14000 vs 100)."""
    default = default_mzda_zaklad_body(
        role, user, jmeno=jmeno, prijmeni=prijmeni, technik_id=technik_id,
    )
    if default is None:
        return mzda_zaklad
    if mzda_zaklad is None or mzda_zaklad == '':
        return default
    try:
        z = Decimal(str(mzda_zaklad))
    except Exception:
        return default
    if role == 'BRIGADNIK' and z in _STAFF_MONTHLY_DEFAULTS:
        return default
    if role in ('PRODEJCE', 'VEDOUCI') and z == BRIGADNIK_DEFAULT_BODY_ZA_HODINU:
        return default
    return z


def snapshot_pozice(user):
    """Uložitelný snímek role a odměny (JSON)."""
    zaklad = getattr(user, 'mzda_zaklad', None)
    cestovne = getattr(user, 'mzda_cestovne', None)
    return {
        'role': getattr(user, 'role', None),
        'mzda_zaklad': float(zaklad) if zaklad is not None else None,
        'mzda_doplnky': list(getattr(user, 'mzda_doplnky', None) or []),
        'mzda_cestovne': float(cestovne) if cestovne is not None else None,
    }


def _pozice_source_user(user):
    return getattr(user, '_mzda_source_user', user)


def _as_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and len(value) >= 10:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


class MzdaUserAsOf:
    """Uživatel s rolí a mzdou platnou k datu (před pozice_od = předchozí snímek)."""

    def __init__(self, user, snapshot):
        self._mzda_source_user = _pozice_source_user(user)
        self.role = snapshot.get('role') or getattr(self._mzda_source_user, 'role', None)
        zaklad = snapshot.get('mzda_zaklad')
        self.mzda_zaklad = Decimal(str(zaklad)) if zaklad is not None else None
        self.mzda_doplnky = list(snapshot.get('mzda_doplnky') or [])
        cestovne = snapshot.get('mzda_cestovne')
        self.mzda_cestovne = Decimal(str(cestovne)) if cestovne is not None else None

    def __getattr__(self, name):
        return getattr(self._mzda_source_user, name)


def mzda_user_as_of(user, on_date=None):
    """Role a mzda k datu. Výplata měsíce používá 1. den měsíce."""
    if user is None:
        return None
    source = _pozice_source_user(user)
    if on_date is None:
        return source
    od = getattr(source, 'pozice_od', None)
    pred = getattr(source, 'pozice_predchozi', None) or {}
    if not od or not pred.get('role'):
        return source
    on_date = _as_date(on_date)
    od = _as_date(od)
    if on_date is None or od is None or on_date >= od:
        return source
    return MzdaUserAsOf(source, pred)


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


def is_brigadnik(user, on_date=None):
    viewed = mzda_user_as_of(user, on_date) if on_date is not None else user
    return getattr(viewed, 'role', None) == 'BRIGADNIK'


def mzda_zaklad_raw(user):
    val = getattr(user, 'mzda_zaklad', None)
    if val is None:
        return Decimal('0')
    return Decimal(str(val))


def mzda_body_za_hodinu(user):
    """Sazba bodů/h pro brigádníka (výchozí 100)."""
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
    """Brigádník: odpracované hodiny × sazba bodů/h (zpětná kompatibilita – vše jako prodejce)."""
    if not is_brigadnik(user):
        return Decimal('0')
    h = Decimal(str(odpracovano_h or 0))
    return mzda_z_hodin_body_brigadnik(user, Decimal('0'), h)


def mzda_z_hodin_body_brigadnik(user, vypomoc_h, prodejce_h):
    """Brigádník: výpomoc × 150 + prodejce × sazba z profilu (výchozí 100)."""
    if not is_brigadnik(user):
        return Decimal('0')
    vh = Decimal(str(vypomoc_h or 0))
    ph = Decimal(str(prodejce_h or 0))
    sazba_prodejce = mzda_body_za_hodinu(user)
    return (
        vh * BRIGADNIK_VYPOMOC_BODY_ZA_HODINU + ph * sazba_prodejce
    ).quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def mzda_fixni_bez_cestovneho(user, odpracovano_h=0):
    """Fixní část bez cestovného – základ + doplňky (nebo hodiny × sazba)."""
    doplnky_sum, _ = sum_mzda_doplnky(user)
    if is_brigadnik(user):
        return mzda_z_hodin_body(user, odpracovano_h) + doplnky_sum
    return mzda_fixni_mesicni_body(user) + doplnky_sum


def mzda_cestovne_body(user):
    val = getattr(user, 'mzda_cestovne', None)
    if val is None:
        return Decimal('0')
    return Decimal(str(val))


def mzda_zaklad_pro_vicepraci(user):
    """Základ pro vícepráci: měsíční fix + doplňky z profilu (vedoucí…), bez cestovného."""
    if is_brigadnik(user):
        return Decimal('0')
    doplnky_sum, _ = sum_mzda_doplnky(user)
    return mzda_fixni_mesicni_body(user) + doplnky_sum


def mzda_fixni_body(user, odpracovano_h=0):
    """Fixní část výplaty: měsíční fixní body nebo hodiny × sazba + doplňky."""
    return mzda_fixni_bez_cestovneho(user, odpracovano_h)


# zpětná kompatibilita
def mzda_zaklad_body(user):
    return mzda_fixni_mesicni_body(user)
