"""Propojení prodejů (Z + číslo balíku) s Packeta provizemi."""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Iterable

from django.db.models import Q
from django.utils import timezone

from analytics.models import WebProdejeAll
from analytics.receipt_metrics import active_receipt_filter_q, leaderboard_doklad_q
from finance.models import PacketaProvizePolozka
from finance.packeta_parser import PACKETA_MAIN_VISIT_TYPES, normalize_zasilka

# Z123456789 nebo ZS: Z 236 9101 479 – ne ZZS (Zlínský kraj)
ZASILKA_NOTE_RE = re.compile(
    r'(?:^|(?<![A-Za-z0-9]))Z(?:\s*(\d[\d\s]{8,20}))',
    re.IGNORECASE | re.MULTILINE,
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


def _scan_z_note_rows(
    date_from: date,
    date_to: date,
    prodejna_id: int | None,
) -> list[dict]:
    qs = WebProdejeAll.objects.filter(
        typ__gte=date_from,
        typ__lte=date_to,
    ).filter(
        Q(poznamka__iregex=r'Z[0-9]') | Q(poznamka__iregex=r'ZS:\s*Z'),
    )
    if prodejna_id:
        qs = qs.filter(id_prodejny=prodejna_id)

    rows = []
    for row in qs.values(
        'id', 'typ', 'doklad', 'poznamka', 'id_prodejce', 'id_prodejny', 'cas_prodeje',
    ).iterator():
        zasilka = parse_zasilka_from_note(row.get('poznamka'))
        if not zasilka:
            continue
        rows.append({**row, 'zasilka': zasilka, 'match_source': 'poznamka'})
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
        })
    return rows


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
    seen_doklad_z: set[tuple[str, str | None]] = set()

    for row in _scan_z_note_rows(date_from, date_to, prodejna_id):
        doklad = row.get('doklad')
        zasilka = row['zasilka']
        if not doklad or doklad not in qualifying:
            continue
        dedupe_key = (doklad, zasilka)
        if dedupe_key in seen_doklad_z:
            continue
        seen_doklad_z.add(dedupe_key)

        pid = row.get('id_prodejny')
        matches = packeta_idx.get((pid, zasilka), []) if pid else []
        sale_dt = _sale_datetime(row['typ'], row.get('cas_prodeje'))

        best: PacketaVisit | None = None
        for cand in matches:
            if _within_window(sale_dt, cand.cas):
                best = cand
                break
        if not best and matches:
            best = matches[0]

        if not best:
            invalid_z.append({
                'doklad': doklad,
                'zasilka': zasilka,
                'datum': row['typ'].isoformat() if row['typ'] else None,
                'id_prodejce': row.get('id_prodejce'),
                'id_prodejny': pid,
            })
            linked.append(LinkedSale(
                zasilka=zasilka,
                zasilka_raw=zasilka,
                typ_provize=None,
                typ_skupina=None,
                id_prodejce=row.get('id_prodejce'),
                id_prodejny=pid,
                doklad=doklad,
                datum_prodeje=row['typ'],
                cas_baliku=None,
                match_source='poznamka',
                packeta_nalezeno=False,
            ))
            continue

        linked.append(LinkedSale(
            zasilka=zasilka,
            zasilka_raw=zasilka,
            typ_provize=best.typ_provize,
            typ_skupina=best.typ_skupina,
            id_prodejce=row.get('id_prodejce'),
            id_prodejny=pid,
            doklad=doklad,
            datum_prodeje=row['typ'],
            cas_baliku=best.cas,
            match_source='poznamka',
            packeta_nalezeno=True,
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
        if item.match_source == 'poznamka' and item.zasilka:
            out[pid]['prodeje_oznacene'].add(item.doklad)
            out[pid]['zasilky'].add(item.zasilka)
        if item.packeta_nalezeno or item.match_source == 'poznamka':
            out[pid]['prodeje_propojene'].add(item.doklad)

    result = {}
    for pid, data in out.items():
        oznacene = len(data['prodeje_oznacene'])
        propojene = len(data['prodeje_propojene'])
        result[pid] = {
            'zasilkovna_prodeje': propojene,
            'zasilkovna_oznaceno': oznacene,
            'zasilkovna_konverze_pct': round(100 * propojene / oznacene, 1) if oznacene else None,
        }
    return result
