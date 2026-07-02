"""Propojení prodejů (Z / číslo balíku) s Packeta provizemi."""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

from django.db.models import Q
from django.utils import timezone

from analytics.models import WebProdejeAll
from analytics.receipt_metrics import active_receipt_filter_q
from packeta.models import PacketaProvizePolozka
from packeta.packeta_parser import PACKETA_MAIN_VISIT_TYPES, normalize_zasilka

# Z123456789 nebo ZS: Z 236 9101 479 – ne ZZS (Zlínský kraj)
ZASILKA_NOTE_RE = re.compile(
    r'(?:^|(?<![A-Za-z0-9]))Z(?:\s*(\d[\d\s]{8,20}))',
    re.IGNORECASE | re.MULTILINE,
)
PLAIN_Z_MARKER_RE = re.compile(r'(?i)^\s*Z\s*$')
ZS_PLAIN_Z_RE = re.compile(r'(?i)^\s*ZS:\s*Z\s*$')

Z_NOTE_SOURCES = frozenset({'poznamka', 'poznamka_dokladu', 'poznamka_zakaznika'})

Z_NOTE_FILTER_Q = (
    Q(poznamka_dokladu__iregex=r'(?i)^\s*Z\s*$')
    | Q(poznamka_dokladu__iregex=r'ZS:\s*Z')
    | Q(poznamka_dokladu__iregex=r'Z[0-9]')
    | Q(poznamka__iregex=r'Z[0-9]')
    | Q(poznamka__iregex=r'ZS:\s*Z')
    | Q(poznamka__iregex=r'(?i)^\s*Z\s*$')
    | Q(poznamka_zakaznika__iregex=r'Z[0-9]')
    | Q(poznamka_zakaznika__iregex=r'ZS:\s*Z')
    | Q(poznamka_zakaznika__iregex=r'(?i)^\s*Z\s*$')
)

VYDANE_TYPY = frozenset({
    'Zpracování zásilky', 'Zpracování nadrozměrné zásilky',
})
PRIJATE_TYPY = frozenset({'Podání', 'Podání C2C'})

MATCH_WINDOW_HOURS = 24


@dataclass
class LinkedSale:
    zasilka: str
    zasilka_raw: str
    typ_provize: str | None
    typ_skupina: str | None
    id_prodejce: int | None
    id_prodejny: int | None
    doklad: str
    datum_prodeje: date
    cas_baliku: datetime | None
    match_source: str
    packeta_nalezeno: bool = True
    z_marker: bool = False


@dataclass
class PacketaVisit:
    zasilka: str
    typ_provize: str
    typ_skupina: str
    prodejna_id: int
    cas: datetime


def digits_from_z_match(raw: str) -> str:
    return re.sub(r'\s+', '', raw or '')


def parse_zasilka_from_note(text: str | None) -> str | None:
    if not text:
        return None
    m = ZASILKA_NOTE_RE.search(text)
    if not m:
        return None
    digits = digits_from_z_match(m.group(1))
    if len(digits) < 9:
        return None
    return normalize_zasilka(f'Z {digits}')


def is_plain_z_marker(text: str | None) -> bool:
    if not text:
        return False
    t = text.strip()
    return bool(PLAIN_Z_MARKER_RE.match(t) or ZS_PLAIN_Z_RE.match(t))


def parse_z_note_fields(
    poznamka_dokladu: str | None,
    poznamka: str | None,
    poznamka_zakaznika: str | None,
) -> tuple[str | None, str | None, bool]:
    """Vrátí (zasilka, match_source, z_marker). Priorita: doklad → položka → zákazník."""
    for source, text in (
        ('poznamka_dokladu', poznamka_dokladu),
        ('poznamka', poznamka),
        ('poznamka_zakaznika', poznamka_zakaznika),
    ):
        if not text:
            continue
        zasilka = parse_zasilka_from_note(text)
        if zasilka:
            return zasilka, source, False
        if is_plain_z_marker(text):
            return None, source, True
    return None, None, False


def is_z_oznaceno(item: LinkedSale) -> bool:
    return item.match_source in Z_NOTE_SOURCES and (bool(item.zasilka) or item.z_marker)


def typ_skupina(typ_provize: str | None) -> str | None:
    if not typ_provize:
        return None
    if typ_provize in VYDANE_TYPY:
        return 'vydane'
    if typ_provize in PRIJATE_TYPY:
        return 'prijate'
    return 'jine'


def _sale_datetime(row_date: date, cas_prodeje) -> datetime | None:
    if not row_date:
        return None
    if cas_prodeje is None:
        return datetime.combine(row_date, datetime.min.time())
    if hasattr(cas_prodeje, 'hour'):
        return datetime.combine(row_date, cas_prodeje)
    try:
        parts = str(cas_prodeje).split(':')
        return datetime.combine(row_date, datetime.min.time().replace(
            hour=int(parts[0]), minute=int(parts[1]) if len(parts) > 1 else 0,
        ))
    except (ValueError, IndexError):
        return datetime.combine(row_date, datetime.min.time())


def _within_window(a: datetime | None, b: datetime | None, hours: int = MATCH_WINDOW_HOURS) -> bool:
    if a is None or b is None:
        return True
    if timezone.is_naive(a):
        a = timezone.make_aware(a)
    if timezone.is_naive(b):
        b = timezone.make_aware(b)
    return abs((a - b).total_seconds()) <= hours * 3600


def _qualifying_doklady(date_from: date, date_to: date, prodejna_id: int | None) -> set[str]:
    qs = WebProdejeAll.objects.filter(
        typ__gte=date_from,
        typ__lte=date_to,
    ).filter(active_receipt_filter_q())
    if prodejna_id:
        qs = qs.filter(id_prodejny=prodejna_id)
    return set(qs.values_list('doklad', flat=True).distinct())


def load_packeta_visits(
    date_from: date,
    date_to: date,
    prodejna_id: int | None = None,
) -> list[PacketaVisit]:
    end_exclusive = date_to + timedelta(days=1)
    qs = PacketaProvizePolozka.objects.filter(
        cas__gte=date_from,
        cas__lt=end_exclusive,
        typ_provize__in=PACKETA_MAIN_VISIT_TYPES,
    )
    if prodejna_id:
        qs = qs.filter(prodejna_id=prodejna_id)

    visits: list[PacketaVisit] = []
    seen: set[tuple[int, str, str]] = set()
    for row in qs.iterator():
        key = (row.prodejna_id, row.zasilka, row.typ_provize)
        if key in seen:
            continue
        seen.add(key)
        skupina = typ_skupina(row.typ_provize) or 'jine'
        visits.append(PacketaVisit(
            zasilka=row.zasilka,
            typ_provize=row.typ_provize,
            typ_skupina=skupina,
            prodejna_id=row.prodejna_id,
            cas=row.cas,
        ))
    return visits


def _packeta_index(visits: Iterable[PacketaVisit]) -> dict[tuple[int, str], list[PacketaVisit]]:
    idx: dict[tuple[int, str], list[PacketaVisit]] = defaultdict(list)
    for v in visits:
        idx[(v.prodejna_id, v.zasilka)].append(v)
    return idx


def _scan_z_marked_doklady(
    date_from: date,
    date_to: date,
    prodejna_id: int | None,
) -> list[dict]:
    qs = WebProdejeAll.objects.filter(
        typ__gte=date_from,
        typ__lte=date_to,
    ).filter(Z_NOTE_FILTER_Q)
    if prodejna_id:
        qs = qs.filter(id_prodejny=prodejna_id)

    by_doklad: dict[str, dict] = {}
    for row in qs.values(
        'typ', 'doklad', 'poznamka', 'poznamka_dokladu', 'poznamka_zakaznika',
        'id_prodejce', 'id_prodejny', 'cas_prodeje',
    ).iterator():
        doklad = row.get('doklad')
        if not doklad:
            continue
        existing = by_doklad.get(doklad)
        if not existing:
            by_doklad[doklad] = dict(row)
            continue
        if not (existing.get('poznamka_dokladu') or '').strip() and (row.get('poznamka_dokladu') or '').strip():
            existing['poznamka_dokladu'] = row['poznamka_dokladu']

    rows = []
    for row in by_doklad.values():
        zasilka, source, z_marker = parse_z_note_fields(
            row.get('poznamka_dokladu'),
            row.get('poznamka'),
            row.get('poznamka_zakaznika'),
        )
        if not zasilka and not z_marker:
            continue
        rows.append({
            **row,
            'zasilka': zasilka,
            'match_source': source,
            'z_marker': z_marker,
        })
    return rows


def _scan_sleva_fallback(
    date_from: date,
    date_to: date,
    prodejna_id: int | None,
    known_doklady: set[str],
) -> list[dict]:
    qs = WebProdejeAll.objects.filter(
        typ__gte=date_from,
        typ__lte=date_to,
        kod='SLEVA',
    ).filter(
        Q(nazev__icontains='zasilkovna') | Q(nazev__icontains='ZASILKOVNA'),
    )
    if prodejna_id:
        qs = qs.filter(id_prodejny=prodejna_id)

    rows = []
    for row in qs.values(
        'typ', 'doklad', 'id_prodejce', 'id_prodejny', 'cas_prodeje', 'nazev',
    ).iterator():
        doklad = row.get('doklad')
        if not doklad or doklad in known_doklady:
            continue
        rows.append({
            **row,
            'zasilka': None,
            'match_source': 'sleva_fallback',
            'z_marker': False,
        })
    return rows


def _pick_packeta_match(
    zasilka: str | None,
    z_marker: bool,
    prodejna_id: int | None,
    sale_dt: datetime | None,
    packeta_idx: dict[tuple[int, str], list[PacketaVisit]],
    visits: list[PacketaVisit],
    used_visits: set[tuple[int, str]],
) -> PacketaVisit | None:
    if zasilka and prodejna_id:
        matches = packeta_idx.get((prodejna_id, zasilka), [])
        best: PacketaVisit | None = None
        for cand in matches:
            if _within_window(sale_dt, cand.cas):
                best = cand
                break
        if not best and matches:
            best = matches[0]
        if best:
            return best

    if not z_marker or not prodejna_id:
        return None

    best: PacketaVisit | None = None
    best_delta: float | None = None
    for cand in visits:
        if cand.prodejna_id != prodejna_id:
            continue
        if cand.typ_skupina != 'vydane':
            continue
        key = (cand.prodejna_id, cand.zasilka)
        if key in used_visits:
            continue
        if not _within_window(sale_dt, cand.cas):
            continue
        if sale_dt is None:
            return cand
        cdt = cand.cas
        sdt = sale_dt
        if timezone.is_naive(cdt):
            cdt = timezone.make_aware(cdt)
        if timezone.is_naive(sdt):
            sdt = timezone.make_aware(sdt)
        delta = abs((sdt - cdt).total_seconds())
        if best is None or (best_delta is not None and delta < best_delta):
            best = cand
            best_delta = delta
    return best


def link_sales_to_packeta(
    date_from: date,
    date_to: date,
    prodejna_id: int | None = None,
) -> tuple[list[LinkedSale], list[dict]]:
    qualifying = _qualifying_doklady(date_from, date_to, prodejna_id)
    visits = load_packeta_visits(date_from, date_to, prodejna_id)
    packeta_idx = _packeta_index(visits)

    linked: list[LinkedSale] = []
    invalid_z: list[dict] = []
    seen_doklad: set[str] = set()
    used_visits: set[tuple[int, str]] = set()

    for row in _scan_z_marked_doklady(date_from, date_to, prodejna_id):
        doklad = row.get('doklad')
        zasilka = row.get('zasilka')
        z_marker = bool(row.get('z_marker'))
        if not doklad or doklad not in qualifying or doklad in seen_doklad:
            continue
        seen_doklad.add(doklad)

        pid = row.get('id_prodejny')
        sale_dt = _sale_datetime(row['typ'], row.get('cas_prodeje'))
        best = _pick_packeta_match(
            zasilka, z_marker, pid, sale_dt, packeta_idx, visits, used_visits,
        )

        if zasilka and not best:
            invalid_z.append({
                'doklad': doklad,
                'zasilka': zasilka,
                'datum': row['typ'].isoformat() if row['typ'] else None,
                'id_prodejce': row.get('id_prodejce'),
                'id_prodejny': pid,
            })

        if best:
            used_visits.add((best.prodejna_id, best.zasilka))

        linked.append(LinkedSale(
            zasilka=best.zasilka if best else (zasilka or ''),
            zasilka_raw=best.zasilka if best else (zasilka or ''),
            typ_provize=best.typ_provize if best else None,
            typ_skupina=best.typ_skupina if best else None,
            id_prodejce=row.get('id_prodejce'),
            id_prodejny=pid,
            doklad=doklad,
            datum_prodeje=row['typ'],
            cas_baliku=best.cas if best else None,
            match_source=row['match_source'],
            packeta_nalezeno=best is not None,
            z_marker=z_marker,
        ))

    known_doklady = {l.doklad for l in linked}
    for row in _scan_sleva_fallback(date_from, date_to, prodejna_id, known_doklady):
        doklad = row.get('doklad')
        if not doklad or doklad not in qualifying:
            continue
        linked.append(LinkedSale(
            zasilka='',
            zasilka_raw='',
            typ_provize=None,
            typ_skupina=None,
            id_prodejce=row.get('id_prodejce'),
            id_prodejny=row.get('id_prodejny'),
            doklad=doklad,
            datum_prodeje=row['typ'],
            cas_baliku=None,
            match_source='sleva_fallback',
            packeta_nalezeno=False,
            z_marker=False,
        ))

    return linked, invalid_z


def distinct_visit_counts(visits: Iterable[PacketaVisit]) -> dict:
    celkem: set[str] = set()
    vydane: set[str] = set()
    prijate: set[str] = set()
    by_typ: dict[str, set[str]] = defaultdict(set)

    for v in visits:
        celkem.add((v.prodejna_id, v.zasilka))
        by_typ[v.typ_provize].add((v.prodejna_id, v.zasilka))
        if v.typ_skupina == 'vydane':
            vydane.add((v.prodejna_id, v.zasilka))
        elif v.typ_skupina == 'prijate':
            prijate.add((v.prodejna_id, v.zasilka))

    return {
        'navstevy_celkem': len(celkem),
        'navstevy_vydane': len(vydane),
        'navstevy_prijate': len(prijate),
        'po_typu': {typ: len(z) for typ, z in by_typ.items()},
    }


def prodeje_by_prodejce(linked: Iterable[LinkedSale]) -> dict[int, dict]:
    """Po prodejci: propojené prodeje (DISTINCT doklad se Z match)."""
    out: dict[int, dict] = defaultdict(lambda: {
        'prodeje_propojene': set(),
        'prodeje_oznacene': set(),
        'zasilky': set(),
    })
    for item in linked:
        pid = item.id_prodejce
        if not pid:
            continue
        if is_z_oznaceno(item):
            out[pid]['prodeje_oznacene'].add(item.doklad)
            if item.zasilka:
                out[pid]['zasilky'].add(item.zasilka)
        if item.packeta_nalezeno or item.match_source in Z_NOTE_SOURCES:
            out[pid]['prodeje_propojene'].add(item.doklad)

    result = {}
    for pid, data in out.items():
        oznacene = len(data['prodeje_oznacene'])
        propojene = len(data['prodeje_propojene'])
        result[pid] = {
            'zasilkovna_prodeje': propojene,
            'zasilkovna_oznaceno': oznacene,
            'zasilkovna_konverze_z_pct': round(100 * propojene / oznacene, 1) if oznacene else None,
        }
    return result


def baliky_vydane_by_prodejce(
    date_from: date,
    date_to: date,
    prodejna_id: int | None = None,
) -> dict[int, int]:
    """Vydané balíky přiřazené prodejci ze směny (DISTINCT zásilka, typ vydání)."""
    qs = PacketaProvizePolozka.objects.filter(
        cas__date__gte=date_from,
        cas__date__lte=date_to,
        typ_provize__in=VYDANE_TYPY,
        id_prodejce__isnull=False,
    )
    if prodejna_id:
        qs = qs.filter(prodejna_id=prodejna_id)

    by_prodejce: dict[int, set[str]] = defaultdict(set)
    for row in qs.values('id_prodejce', 'zasilka'):
        by_prodejce[row['id_prodejce']].add(row['zasilka'])
    return {pid: len(zasilky) for pid, zasilky in by_prodejce.items()}


def baliky_vydane_by_prodejna(
    date_from: date,
    date_to: date,
) -> dict[int, int]:
    """Vydané balíky po prodejně (DISTINCT zásilka)."""
    qs = PacketaProvizePolozka.objects.filter(
        cas__date__gte=date_from,
        cas__date__lte=date_to,
        typ_provize__in=VYDANE_TYPY,
    )
    by_prodejna: dict[int, set[str]] = defaultdict(set)
    for row in qs.values('prodejna_id', 'zasilka'):
        if row['prodejna_id']:
            by_prodejna[row['prodejna_id']].add(row['zasilka'])
    return {sid: len(zasilky) for sid, zasilky in by_prodejna.items()}


def prodeje_zasilkovna_by_prodejna(
    linked: Iterable[LinkedSale],
) -> dict[int, int]:
    """Propojené prodeje Zásilkovna po prodejně (DISTINCT doklad)."""
    by_prodejna: dict[int, set[str]] = defaultdict(set)
    for item in linked:
        if not item.id_prodejny:
            continue
        if item.packeta_nalezeno or item.match_source in Z_NOTE_SOURCES:
            by_prodejna[item.id_prodejny].add(item.doklad)
    return {sid: len(doklady) for sid, doklady in by_prodejna.items()}
