"""Návrh dvou směn měsíčně na jiné prodejně."""

from __future__ import annotations

import random
import unicodedata
from calendar import monthrange
from datetime import date, datetime, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from shifts.mall_closure import closure_kind_for_date
from shifts.models import Smena, VyjezdNavrh, VyjezdNotifikace
from shifts.shift_helpers import shift_store_role_slot
from stores.models import Prodejna
from stores.oteviraci_doba_utils import DNY_KLICE, resolve_den_hours
from users.exclusions import is_excluded_report_user
from users.models import WebUser

# Technici na prodejně, ne prodejci u pultu. Testovací účty řeší is_excluded_report_user.
TECHNICI_BEZ_VYJEZDU = frozenset({'vychodil', 'dolak'})

# Domácí prodejna → automatické cíle (bez vlastní).
AUTOMATICKE_CILE = {
    'vsetin': ('prerov', 'zlin'),
    'zlin': ('vsetin', 'prerov'),
    'globus': ('senimo', 'sternberk', 'prerov'),
    'senimo': ('globus', 'sternberk', 'prerov'),
    'sternberk': ('globus', 'senimo', 'prerov'),
    'prerov': ('globus', 'senimo', 'sternberk'),
}

NAZVY_MESICU = (
    '',
    'Leden',
    'Únor',
    'Březen',
    'Duben',
    'Květen',
    'Červen',
    'Červenec',
    'Srpen',
    'Září',
    'Říjen',
    'Listopad',
    'Prosinec',
)

GRACE_DAYS = 7
POCET_VYJEZDU = 2


class VyjezdChyba(Exception):
    pass


def store_key(name: str | None) -> str:
    raw = (name or '').strip().lower()
    raw = unicodedata.normalize('NFD', raw)
    return ''.join(ch for ch in raw if unicodedata.category(ch) != 'Mn')


def month_add(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = year * 12 + (month - 1) + delta
    return idx // 12, idx % 12 + 1


def last_day(year: int, month: int) -> date:
    return date(year, month, monthrange(year, month)[1])


def first_day(year: int, month: int) -> date:
    return date(year, month, 1)


def generation_date(rok: int, mesic: int) -> date:
    """Poslední den měsíce o dva zpět. Listopad → 30. 9."""
    year, month = month_add(rok, mesic, -2)
    return last_day(year, month)


def due_months(today: date, grace_days: int = GRACE_DAYS) -> list[tuple[int, int]]:
    """Cílové měsíce, jejichž den návrhu už nastal a ještě běží týdenní dohon."""
    found = []
    for delta in range(0, 4):
        rok, mesic = month_add(today.year, today.month, delta)
        gen = generation_date(rok, mesic)
        if gen <= today <= gen + timedelta(days=grace_days):
            found.append((rok, mesic))
    return found


def mesic_nazev(rok: int, mesic: int) -> str:
    return f'{NAZVY_MESICU[mesic]} {rok}'


def _opening_times(store, day: date):
    den_key = DNY_KLICE[day.weekday()]
    pair = resolve_den_hours(store.oteviraci_doba, den_key)
    if not pair or not pair[0] or not pair[1]:
        return None
    cas_od = datetime.strptime(pair[0], '%H:%M').time()
    cas_do = datetime.strptime(pair[1], '%H:%M').time()
    if cas_do <= cas_od:
        return None
    return cas_od, cas_do


def store_open_on(store, day: date) -> bool:
    kind = closure_kind_for_date(day)
    if kind == 'always_closed':
        return False
    if kind == 'nc_verify_closed' and store_key(store.nazev) != 'globus':
        return False
    return _opening_times(store, day) is not None


def je_senimo_sobota(store, day: date) -> bool:
    return store_key(store.nazev) == 'senimo' and day.weekday() == 5


def pool_key_for_store(store) -> str | None:
    """Zlín - Čepkov i krátký název Zlín spadnou do skupiny zlin."""
    labels = (
        store_key(getattr(store, 'nazev', None)),
        store_key(getattr(store, 'nazev_kratkiy', None)),
    )
    for key in AUTOMATICKE_CILE:
        for label in labels:
            if not label:
                continue
            if label == key or label.startswith(key + ' ') or label.startswith(key + '-'):
                return key
    return None


def _stores_by_key():
    by_key = {}
    for store in Prodejna.objects.filter(aktivni=True):
        key = pool_key_for_store(store)
        if key and key not in by_key:
            by_key[key] = store
    return by_key


def je_prodejce_vyjezdu(user) -> bool:
    if getattr(user, 'role', None) not in ('PRODEJCE', 'VEDOUCI'):
        return False
    if is_excluded_report_user(user=user):
        return False
    if store_key(getattr(user, 'prijmeni', '')) in TECHNICI_BEZ_VYJEZDU:
        return False
    return True


def eligible_sellers(stores_by_key=None):
    stores_by_key = stores_by_key if stores_by_key is not None else _stores_by_key()
    sellers = []
    qs = WebUser.objects.filter(
        role__in=('PRODEJCE', 'VEDOUCI'),
        aktivni=True,
        prodejna_id__isnull=False,
    )
    id_to_key = {store.id: key for key, store in stores_by_key.items()}
    for user in qs:
        if not je_prodejce_vyjezdu(user):
            continue
        key = id_to_key.get(user.prodejna_id)
        if not key:
            continue
        sellers.append(user)
    return sellers


def zrus_navrhy_mimo_prodejce(rok: int, mesic: int) -> int:
    """Zruší nepotvrzené návrhy u techniků a testovacích účtů."""
    mesic_den = first_day(rok, mesic)
    rows = list(
        VyjezdNavrh.objects.filter(
            mesic=mesic_den,
            stav=VyjezdNavrh.STAV_NAVRH,
        ).select_related('user')
    )
    zrusit = [row for row in rows if not je_prodejce_vyjezdu(row.user)]
    if not zrusit:
        return 0
    user_ids = {row.user_id for row in zrusit}
    VyjezdNavrh.objects.filter(id__in=[row.id for row in zrusit]).update(
        stav=VyjezdNavrh.STAV_ZRUSENO,
    )
    VyjezdNotifikace.objects.filter(
        user_id__in=user_ids,
        mesic=mesic_den,
        read_at__isnull=True,
    ).update(read_at=timezone.now())
    return len(zrusit)


def _days_in_month(rok: int, mesic: int):
    count = monthrange(rok, mesic)[1]
    return [date(rok, mesic, day) for day in range(1, count + 1)]


def _prodej_occupancy(rok: int, mesic: int) -> dict[tuple[int, date], int]:
    occ: dict[tuple[int, date], int] = {}
    qs = Smena.objects.filter(
        datum__year=rok,
        datum__month=mesic,
        aktivni=True,
        typ_smeny='prace',
    ).only('datum', 'prodejna_id', 'pozice_smeny', 'brigadnik_rezim')
    for smena in qs:
        if not smena.prodejna_id:
            continue
        if shift_store_role_slot(smena.pozice_smeny, smena.brigadnik_rezim) != 'prodej':
            continue
        key = (smena.prodejna_id, smena.datum)
        occ[key] = occ.get(key, 0) + 1
    navrh_qs = VyjezdNavrh.objects.filter(
        mesic=first_day(rok, mesic),
        stav=VyjezdNavrh.STAV_NAVRH,
    ).only('prodejna_id', 'datum')
    for navrh in navrh_qs:
        key = (navrh.prodejna_id, navrh.datum)
        occ[key] = occ.get(key, 0) + 1
    return occ


def _covered_days(user, rok: int, mesic: int) -> set[date]:
    days = set(
        VyjezdNavrh.objects.filter(
            user=user,
            mesic=first_day(rok, mesic),
            stav__in=(VyjezdNavrh.STAV_NAVRH, VyjezdNavrh.STAV_POTVRZENO),
        ).values_list('datum', flat=True)
    )
    home_id = user.prodejna_id
    shifts = Smena.objects.filter(
        user=user,
        datum__year=rok,
        datum__month=mesic,
        aktivni=True,
        typ_smeny='prace',
    ).only('datum', 'prodejna_id')
    for smena in shifts:
        if smena.prodejna_id and smena.prodejna_id != home_id:
            days.add(smena.datum)
    return days


def _absence_days(user, rok: int, mesic: int) -> set[date]:
    return set(
        Smena.objects.filter(
            user=user,
            datum__year=rok,
            datum__month=mesic,
            aktivni=True,
            typ_smeny__in=('dovolena', 'nemoc'),
        ).values_list('datum', flat=True)
    )


def _home_shift_days(user, rok: int, mesic: int) -> set[date]:
    return set(
        Smena.objects.filter(
            user=user,
            datum__year=rok,
            datum__month=mesic,
            aktivni=True,
            typ_smeny='prace',
            prodejna_id=user.prodejna_id,
            pozice_smeny='prodej',
        ).values_list('datum', flat=True)
    )


def _blocked_around(days: set[date]) -> set[date]:
    blocked = set(days)
    for day in days:
        blocked.add(day - timedelta(days=1))
        blocked.add(day + timedelta(days=1))
    return blocked


def _pick_for_seller(user, rok, mesic, stores_by_key, occupancy, rng: random.Random):
    home_key = next(
        (key for key, store in stores_by_key.items() if store.id == user.prodejna_id),
        None,
    )
    if not home_key:
        return []
    targets = [stores_by_key[key] for key in AUTOMATICKE_CILE[home_key] if key in stores_by_key]
    if not targets:
        return []

    covered = _covered_days(user, rok, mesic)
    need = POCET_VYJEZDU - len(covered)
    if need <= 0:
        return []

    absence = _absence_days(user, rok, mesic)
    home_days = _home_shift_days(user, rok, mesic)
    blocked = _blocked_around(covered)
    chosen = []

    for _ in range(need):
        options = []
        for day in _days_in_month(rok, mesic):
            if day in blocked or day in absence:
                continue
            if any(abs((day - prev).days) < 2 for prev, _store in chosen):
                continue
            for store in targets:
                if je_senimo_sobota(store, day) or not store_open_on(store, day):
                    continue
                occ = occupancy.get((store.id, day), 0)
                home_penalty = 0
                if day in home_days and occupancy.get((user.prodejna_id, day), 0) <= 1:
                    home_penalty = 1
                options.append((occ, home_penalty, rng.random(), store, day))
        if not options:
            break
        options.sort(key=lambda row: (row[0], row[1], row[2]))
        best_occ, best_penalty = options[0][0], options[0][1]
        top = [row for row in options if row[0] == best_occ and row[1] == best_penalty]
        _occ, _penalty, _tie, store, day = rng.choice(top)
        chosen.append((day, store))
        occupancy[(store.id, day)] = occupancy.get((store.id, day), 0) + 1
        if day in home_days:
            home_key_occ = (user.prodejna_id, day)
            occupancy[home_key_occ] = max(0, occupancy.get(home_key_occ, 0) - 1)
        blocked.add(day)
        blocked.add(day - timedelta(days=1))
        blocked.add(day + timedelta(days=1))
    return chosen


def dopln_vyjezdy(rok: int, mesic: int, rng: random.Random | None = None) -> dict:
    """Doplní chybějící návrhy. Hotové řádky nepřepisuje."""
    rng = rng or random.Random()
    zrus_navrhy_mimo_prodejce(rok, mesic)
    mesic_den = first_day(rok, mesic)
    stores_by_key = _stores_by_key()
    sellers = eligible_sellers(stores_by_key)
    rng.shuffle(sellers)
    occupancy = _prodej_occupancy(rok, mesic)
    created_rows = []
    notified_users = []

    with transaction.atomic():
        for user in sellers:
            picks = _pick_for_seller(user, rok, mesic, stores_by_key, occupancy, rng)
            if not picks:
                continue
            for day, store in picks:
                created_rows.append(VyjezdNavrh.objects.create(
                    user=user,
                    mesic=mesic_den,
                    datum=day,
                    prodejna=store,
                    stav=VyjezdNavrh.STAV_NAVRH,
                ))
            _notifikuj(user, mesic_den)
            notified_users.append(user.id)

    return {
        'rok': rok,
        'mesic': mesic,
        'vytvoreno': len(created_rows),
        'uzivatele': notified_users,
    }


def _format_polozky(rows) -> str:
    parts = []
    for row in rows:
        nazev = row.prodejna.nazev if row.prodejna_id else ''
        parts.append(f'{row.datum.day}. {row.datum.month}. {nazev}')
    return ', '.join(parts)


def text_upozorneni(rows) -> str:
    if not rows:
        return ''
    prvni = rows[0]
    nazev = NAZVY_MESICU[prvni.mesic.month]
    return (
        f'{nazev}: {_format_polozky(rows)}. '
        'Počítej s nimi. Jiný den nebo prodejnu domluv s vedoucím.'
    )


def text_banner(rows) -> str:
    if not rows:
        return ''
    prvni = rows[0]
    nazev = NAZVY_MESICU[prvni.mesic.month]
    return f'{nazev}: {_format_polozky(rows)}. Ještě to není v rozpisu.'


def _notifikuj(user, mesic_den: date):
    rows = list(
        VyjezdNavrh.objects.filter(
            user=user,
            mesic=mesic_den,
            stav=VyjezdNavrh.STAV_NAVRH,
        ).select_related('prodejna').order_by('datum')
    )
    if not rows:
        return
    VyjezdNotifikace.objects.filter(
        user=user,
        mesic=mesic_den,
        read_at__isnull=True,
    ).update(read_at=timezone.now())
    VyjezdNotifikace.objects.create(
        user=user,
        mesic=mesic_den,
        message=text_upozorneni(rows),
    )


def notifikuj_zmenu(navrh: VyjezdNavrh):
    _notifikuj(navrh.user, navrh.mesic)


def over_manualni_zmenu(navrh: VyjezdNavrh, datum: date, prodejna: Prodejna):
    if navrh.stav != VyjezdNavrh.STAV_NAVRH:
        raise VyjezdChyba('Potvrzený návrh už nejde měnit.')
    if datum.year != navrh.mesic.year or datum.month != navrh.mesic.month:
        raise VyjezdChyba('Den musí zůstat ve stejném měsíci.')
    if prodejna.id == navrh.user.prodejna_id:
        raise VyjezdChyba('Cíl nemůže být domácí prodejna.')
    if not prodejna.aktivni:
        raise VyjezdChyba('Prodejna není aktivní.')
    if je_senimo_sobota(prodejna, datum):
        raise VyjezdChyba('Senimo v sobotu nelze vybrat.')
    if not store_open_on(prodejna, datum):
        raise VyjezdChyba('Prodejna má ten den zavřeno.')
    if Smena.objects.filter(
        user=navrh.user,
        datum=datum,
        aktivni=True,
        typ_smeny__in=('dovolena', 'nemoc'),
    ).exists():
        raise VyjezdChyba('Prodejce má ten den dovolenou nebo nemoc.')
    ostatni = VyjezdNavrh.objects.filter(
        user=navrh.user,
        mesic=navrh.mesic,
        stav__in=(VyjezdNavrh.STAV_NAVRH, VyjezdNavrh.STAV_POTVRZENO),
    ).exclude(pk=navrh.pk)
    for other in ostatni:
        if other.datum == datum:
            raise VyjezdChyba('Oba výjezdy nemohou být ve stejný den.')
        if abs((other.datum - datum).days) < 2:
            raise VyjezdChyba('Dvě směny nesmí být hned po sobě.')


def _jmeno(user) -> str:
    return f'{(user.prijmeni or "").strip()} {(user.jmeno or "").strip()}'.strip()


def _obsazeno(navrh: VyjezdNavrh) -> bool:
    qs = Smena.objects.filter(
        datum=navrh.datum,
        prodejna_id=navrh.prodejna_id,
        aktivni=True,
        typ_smeny='prace',
    ).exclude(user_id=navrh.user_id)
    for smena in qs:
        if shift_store_role_slot(smena.pozice_smeny, smena.brigadnik_rezim) == 'prodej':
            return True
    return VyjezdNavrh.objects.filter(
        datum=navrh.datum,
        prodejna_id=navrh.prodejna_id,
        stav=VyjezdNavrh.STAV_NAVRH,
    ).exclude(pk=navrh.pk).exists()


def seznam_mesice(rok: int, mesic: int) -> dict:
    mesic_den = first_day(rok, mesic)
    rows = list(
        VyjezdNavrh.objects.filter(mesic=mesic_den)
        .exclude(stav=VyjezdNavrh.STAV_ZRUSENO)
        .select_related('user', 'prodejna')
        .order_by('user__prijmeni', 'user__jmeno', 'datum')
    )
    stores_by_key = _stores_by_key()
    home_names = {store.id: store.nazev for store in stores_by_key.values()}
    skupiny = {}
    for row in rows:
        bucket = skupiny.setdefault(row.user_id, {
            'user_id': row.user_id,
            'jmeno': _jmeno(row.user),
            'domaci_prodejna_id': row.user.prodejna_id,
            'domaci_prodejna': home_names.get(row.user.prodejna_id, ''),
            'polozky': [],
        })
        bucket['polozky'].append({
            'id': row.id,
            'datum': row.datum.isoformat(),
            'prodejna_id': row.prodejna_id,
            'prodejna_nazev': row.prodejna.nazev,
            'obsazeno': _obsazeno(row) if row.stav == VyjezdNavrh.STAV_NAVRH else False,
            'stav': row.stav,
        })
    ma_navrh = {item['user_id'] for item in skupiny.values() if len(item['polozky']) >= POCET_VYJEZDU}
    bez_navrhu = []
    for user in eligible_sellers(stores_by_key):
        if user.id in ma_navrh:
            continue
        bez_navrhu.append({
            'user_id': user.id,
            'jmeno': _jmeno(user),
            'domaci_prodejna': home_names.get(user.prodejna_id, ''),
            'pocet': len(skupiny.get(user.id, {}).get('polozky', [])),
        })
    return {
        'mesic': f'{rok:04d}-{mesic:02d}',
        'mesic_nazev': mesic_nazev(rok, mesic),
        'skupiny': list(skupiny.values()),
        'bez_navrhu': bez_navrhu,
    }


def moje_skupiny(user) -> list[dict]:
    start = date.today().replace(day=1)
    rows = list(
        VyjezdNavrh.objects.filter(
            user=user,
            stav=VyjezdNavrh.STAV_NAVRH,
            mesic__gte=start,
        ).select_related('prodejna').order_by('mesic', 'datum')
    )
    skupiny = []
    by_month: dict[date, list] = {}
    for row in rows:
        by_month.setdefault(row.mesic, []).append(row)
    for mesic_den, month_rows in by_month.items():
        skupiny.append({
            'mesic': f'{mesic_den.year:04d}-{mesic_den.month:02d}',
            'mesic_nazev': mesic_nazev(mesic_den.year, mesic_den.month),
            'text': text_banner(month_rows),
            'polozky': [
                {
                    'id': row.id,
                    'datum': row.datum.isoformat(),
                    'prodejna_id': row.prodejna_id,
                    'prodejna_nazev': row.prodejna.nazev,
                    'prodejna': row.prodejna.nazev_kratkiy or row.prodejna.nazev,
                }
                for row in month_rows
            ],
        })
    return skupiny


def vyjezdy_pro_kalendar(rok: int, mesic: int, *, prodejna=None, person_user_id=None, backoffice=False):
    if backoffice:
        return {}
    qs = VyjezdNavrh.objects.filter(
        datum__year=rok,
        datum__month=mesic,
        stav=VyjezdNavrh.STAV_NAVRH,
    ).select_related('user', 'prodejna')
    if person_user_id:
        qs = qs.filter(user_id=person_user_id)
    elif prodejna is not None:
        home_ids = WebUser.objects.filter(prodejna_id=prodejna.id).values_list('id', flat=True)
        qs = qs.filter(Q(prodejna=prodejna) | Q(user_id__in=list(home_ids)))
    data = {}
    for row in qs:
        key = row.datum.isoformat()
        data.setdefault(key, []).append({
            'id': row.id,
            'navrh': True,
            'user_id': row.user_id,
            'user_jmeno': _jmeno(row.user),
            'prodejna_id': row.prodejna_id,
            'prodejna_nazev': row.prodejna.nazev,
            'prodejna': row.prodejna.nazev_kratkiy or row.prodejna.nazev,
            'datum': key,
            'stav': row.stav,
        })
    return data


def potvrdit_navrh(navrh: VyjezdNavrh) -> Smena:
    if navrh.stav != VyjezdNavrh.STAV_NAVRH:
        raise VyjezdChyba('Návrh už je vyřízený.')
    store = navrh.prodejna
    if je_senimo_sobota(store, navrh.datum):
        raise VyjezdChyba('Senimo v sobotu nelze potvrdit.')
    times = _opening_times(store, navrh.datum)
    if not times or not store_open_on(store, navrh.datum):
        raise VyjezdChyba('Prodejna má ten den zavřeno.')
    cas_od, cas_do = times
    from shifts.shift_helpers import find_store_role_slot_conflict

    conflict = find_store_role_slot_conflict(
        navrh.datum,
        store,
        'prace',
        cas_od,
        cas_do,
        'prodej',
        'prodejce',
    )
    if conflict and conflict.user_id != navrh.user_id:
        raise VyjezdChyba(
            f'Na {store.nazev} už {navrh.datum.day}. {navrh.datum.month}. někdo prodává. '
            'Vyber jiný den.'
        )
    with transaction.atomic():
        Smena.objects.filter(
            user=navrh.user,
            datum=navrh.datum,
            aktivni=True,
            typ_smeny='prace',
        ).update(aktivni=False)
        smena = Smena.objects.create(
            user=navrh.user,
            prodejna=store,
            datum=navrh.datum,
            cas_od=cas_od,
            cas_do=cas_do,
            typ_smeny='prace',
            pozice_smeny='prodej',
            brigadnik_rezim='prodejce',
            poznamka='Výjezd na jinou prodejnu',
        )
        navrh.stav = VyjezdNavrh.STAV_POTVRZENO
        navrh.smena = smena
        navrh.save(update_fields=['stav', 'smena', 'upraveno'])
    from plans.shift_hooks import naplanuj_prepocet_po_smene
    naplanuj_prepocet_po_smene(smena, zdroj='single')
    return smena
