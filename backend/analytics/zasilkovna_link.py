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
from users.prodejce_resolve import build_prodejce_key_to_user_id, resolve_web_user_id

# Z123456789 nebo ZS: Z 236 9101 479 – ne ZZS (Zlínský kraj)
ZASILKA_NOTE_RE = re.compile(
    r'(?:^|(?<![A-Za-z0-9]))Z(?:\s*(\d[\d\s]{8,20}))',
    re.IGNORECASE | re.MULTILINE,
)
PLAIN_Z_MARKER_RE = re.compile(r'(?i)^\s*Z\s*$')
ZS_PLAIN_Z_RE = re.compile(r'(?i)^\s*ZS:\s*Z\s*$')

Z_NOTE_SOURCES = frozenset({'poznamka', 'poznamka_dokladu', 'poznamka_zakaznika'})

# SQL prefiltr – detekci řeší parse_z_note_fields() (mezery, ZS:, jen Z, …)
Z_NOTE_PREFILTER_Q = (
    Q(poznamka_dokladu__iregex=r'(?i)Z')
    | Q(poznamka__iregex=r'(?i)Z')
    | Q(poznamka_zakaznika__iregex=r'(?i)Z')
)

VYDANE_TYPY = frozenset({
    'Zpracování zásilky', 'Zpracování nadrozměrné zásilky',
})
PRIJATE_TYPY = frozenset({'Podání'})
C2C_TYPY = frozenset({'Podání C2C'})
PRIJATE_ALL_TYPY = PRIJATE_TYPY | C2C_TYPY

# Výdej s dobírkou – v CSV někdy chybí řádek Zpracování zásilky, je jen Cash collection
VYDANE_DOBIRKA_TYPY = frozenset({'Cash collection'})
VYDANE_ALL_TYPY = VYDANE_TYPY | VYDANE_DOBIRKA_TYPY
PACKETA_SALE_MATCH_EXTRA = VYDANE_DOBIRKA_TYPY
PACKETA_SALE_MATCH_TYPES = PACKETA_MAIN_VISIT_TYPES | PACKETA_SALE_MATCH_EXTRA

TYP_KATEGORIE_LABELS = {
    'prijate': 'Příjem zásilky',
    'prijate_c2c': 'Příjem C2C',
    'vydane': 'Výdej zásilky',
    'vydane_dobirka': 'Výdej s dobírkou',
}

# Symplio sleva: kód SLEVA, název typicky „ZASILKOVNA ZASILKOVNA20“
ZASILKOVNA_SLEVA_KOD = 'zasilkovna20'


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
    typ_inferovano: bool = False


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
    return normalize_zasilka(f'Z{digits}')


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


def is_zasilkovna_prodej(item: LinkedSale) -> bool:
    """Prodejka Zásilkovna: Z+číslo v poznámce (sleva ani Packeta nejsou povinné)."""
    return bool(item.zasilka) and not item.z_marker and item.match_source in Z_NOTE_SOURCES


def typ_kategorie(typ_provize: str | None) -> str | None:
    if not typ_provize:
        return None
    if typ_provize in VYDANE_DOBIRKA_TYPY:
        return 'vydane_dobirka'
    if typ_provize in VYDANE_TYPY:
        return 'vydane'
    if typ_provize in PRIJATE_TYPY:
        return 'prijate'
    if typ_provize in C2C_TYPY:
        return 'prijate_c2c'
    return None


def typ_provize_label(typ_provize: str | None) -> str | None:
    if not typ_provize:
        return None
    if typ_provize in VYDANE_DOBIRKA_TYPY:
        return TYP_KATEGORIE_LABELS['vydane_dobirka']
    if typ_provize == 'Zpracování nadrozměrné zásilky':
        return 'Výdej zásilky (nadrozměrná)'
    if typ_provize in VYDANE_TYPY:
        return TYP_KATEGORIE_LABELS['vydane']
    if typ_provize == 'Podání C2C':
        return TYP_KATEGORIE_LABELS['prijate_c2c']
    if typ_provize in PRIJATE_TYPY:
        return TYP_KATEGORIE_LABELS['prijate']
    return typ_provize


def typ_skupina(typ_provize: str | None) -> str | None:
    kat = typ_kategorie(typ_provize)
    if kat in ('vydane', 'vydane_dobirka'):
        return 'vydane'
    if kat in ('prijate', 'prijate_c2c'):
        return kat
    return 'jine' if typ_provize else None


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
        typ_provize__in=PACKETA_SALE_MATCH_TYPES,
    )
    if prodejna_id:
        qs = qs.filter(prodejna_id=prodejna_id)

    visits: list[PacketaVisit] = []
    seen: set[tuple[int, str, str]] = set()
    for row in qs.iterator():
        z_key = normalize_zasilka(row.zasilka)
        key = (row.prodejna_id, z_key, row.typ_provize)
        if key in seen:
            continue
        seen.add(key)
        skupina = typ_skupina(row.typ_provize) or 'jine'
        visits.append(PacketaVisit(
            zasilka=z_key,
            typ_provize=row.typ_provize,
            typ_skupina=skupina,
            prodejna_id=row.prodejna_id,
            cas=row.cas,
        ))
    return visits


def _zasilka_key(zasilka: str) -> str:
    return normalize_zasilka(zasilka)


def _merge_note_fields_from_rows(rows: Iterable[dict]) -> tuple[str | None, str | None, str | None]:
    poznamka_dokladu = poznamka = poznamka_zakaznika = None
    for row in rows:
        if not poznamka_dokladu and (row.get('poznamka_dokladu') or '').strip():
            poznamka_dokladu = row['poznamka_dokladu']
        if not poznamka and (row.get('poznamka') or '').strip():
            poznamka = row['poznamka']
        if not poznamka_zakaznika and (row.get('poznamka_zakaznika') or '').strip():
            poznamka_zakaznika = row['poznamka_zakaznika']
    return poznamka_dokladu, poznamka, poznamka_zakaznika


def _doklad_has_z_note(
    doklad: str,
    date_from: date,
    date_to: date,
    prodejna_id: int | None,
) -> bool:
    qs = WebProdejeAll.objects.filter(
        doklad=doklad,
        typ__gte=date_from,
        typ__lte=date_to,
    )
    if prodejna_id:
        qs = qs.filter(id_prodejny=prodejna_id)
    pd, p, pz = _merge_note_fields_from_rows(qs.values(
        'poznamka_dokladu', 'poznamka', 'poznamka_zakaznika',
    ))
    zasilka, _, z_marker = parse_z_note_fields(pd, p, pz)
    return bool(zasilka or z_marker)


def _scan_z_marked_doklady(
    date_from: date,
    date_to: date,
    prodejna_id: int | None,
) -> list[dict]:
    qs = WebProdejeAll.objects.filter(
        typ__gte=date_from,
        typ__lte=date_to,
    ).filter(Z_NOTE_PREFILTER_Q)
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
        for field in ('poznamka_dokladu', 'poznamka', 'poznamka_zakaznika'):
            if not (existing.get(field) or '').strip() and (row.get(field) or '').strip():
                existing[field] = row[field]

    rows = []
    for row in by_doklad.values():
        pd, p, pz = _merge_note_fields_from_rows([row])
        zasilka, source, z_marker = parse_z_note_fields(pd, p, pz)
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
    ).filter(nazev__icontains=ZASILKOVNA_SLEVA_KOD)
    if prodejna_id:
        qs = qs.filter(id_prodejny=prodejna_id)

    rows = []
    for row in qs.values(
        'typ', 'doklad', 'id_prodejce', 'id_prodejny', 'cas_prodeje', 'nazev',
    ).iterator():
        doklad = row.get('doklad')
        if not doklad or doklad in known_doklady:
            continue
        if _doklad_has_z_note(doklad, date_from, date_to, prodejna_id):
            continue
        rows.append({
            **row,
            'zasilka': None,
            'match_source': 'sleva_fallback',
            'z_marker': False,
        })
    return rows


def _sale_local_date(sale_dt: datetime | None) -> date | None:
    if sale_dt is None:
        return None
    if timezone.is_naive(sale_dt):
        return sale_dt.date()
    return timezone.localtime(sale_dt).date()


def _visit_local_date(visit_cas: datetime) -> date:
    if timezone.is_naive(visit_cas):
        return visit_cas.date()
    return timezone.localtime(visit_cas).date()


def _same_sale_day(sale_dt: datetime | None, visit_cas: datetime) -> bool:
    """Balík musí být v Packeta ve stejný den jako prodejka – jiná interakce (příjem vs. výdej)."""
    sday = _sale_local_date(sale_dt)
    if sday is None:
        return True
    return sday == _visit_local_date(visit_cas)


def _closest_by_time(visits: list[PacketaVisit], sale_dt: datetime) -> PacketaVisit:
    if timezone.is_naive(sale_dt):
        sale_dt = timezone.make_aware(sale_dt)
    best = visits[0]
    best_delta: float | None = None
    for cand in visits:
        cdt = cand.cas
        if timezone.is_naive(cdt):
            cdt = timezone.make_aware(cdt)
        delta = abs((sale_dt - cdt).total_seconds())
        if best_delta is None or delta < best_delta:
            best = cand
            best_delta = delta
    return best


def _closest_packeta_visit(
    visits: list[PacketaVisit],
    sale_dt: datetime | None,
) -> PacketaVisit | None:
    if not visits:
        return None
    if sale_dt is not None:
        same_day = [v for v in visits if _same_sale_day(sale_dt, v.cas)]
        if not same_day:
            return None
        visits = same_day
    if sale_dt is None:
        return visits[-1]
    return _closest_by_time(visits, sale_dt)


def _hint_vydany_visit(
    zasilka: str,
    prodejna_id: int,
    sale_dt: datetime | None,
) -> PacketaVisit | None:
    """Odhad typu výdeje z Packety – jen pro zobrazení, nepotvrzuje párování."""
    matches = _packeta_visits_for_zasilka(zasilka, prodejna_id)
    vydane = [v for v in matches if typ_kategorie(v.typ_provize) in ('vydane', 'vydane_dobirka')]
    if not vydane:
        return None
    if sale_dt is not None:
        same_day = [v for v in vydane if _same_sale_day(sale_dt, v.cas)]
        if same_day:
            return _closest_by_time(same_day, sale_dt)
        return _closest_by_time(vydane, sale_dt)
    return vydane[-1]


def _packeta_visits_for_zasilka(zasilka: str, prodejna_id: int) -> list[PacketaVisit]:
    """Hlavní návštěvy balíku na pobočce (vydané i přijaté – výběr podle dne prodeje)."""
    z_key = _zasilka_key(zasilka)
    visits: list[PacketaVisit] = []
    seen: set[tuple[int, str, str]] = set()
    qs = PacketaProvizePolozka.objects.filter(
        prodejna_id=prodejna_id,
        zasilka=z_key,
        typ_provize__in=PACKETA_SALE_MATCH_TYPES,
    ).order_by('cas')
    for row in qs.iterator():
        key = (row.prodejna_id, z_key, row.typ_provize)
        if key in seen:
            continue
        seen.add(key)
        visits.append(PacketaVisit(
            zasilka=z_key,
            typ_provize=row.typ_provize,
            typ_skupina=typ_skupina(row.typ_provize) or 'jine',
            prodejna_id=row.prodejna_id,
            cas=row.cas,
        ))
    return visits


def _pick_packeta_match(
    zasilka: str | None,
    prodejna_id: int | None,
    sale_dt: datetime | None,
) -> PacketaVisit | None:
    """Páruje Z+číslo na návštěvu ve stejný den jako prodejka (příjem nebo výdej)."""
    if not zasilka or not prodejna_id:
        return None
    matches = _packeta_visits_for_zasilka(zasilka, prodejna_id)
    return _closest_packeta_visit(matches, sale_dt)


def link_sales_to_packeta(
    date_from: date,
    date_to: date,
    prodejna_id: int | None = None,
) -> tuple[list[LinkedSale], list[dict]]:
    qualifying = _qualifying_doklady(date_from, date_to, prodejna_id)
    prodejce_key_map = build_prodejce_key_to_user_id()

    linked: list[LinkedSale] = []
    invalid_z: list[dict] = []
    seen_doklad: set[str] = set()

    for row in _scan_z_marked_doklady(date_from, date_to, prodejna_id):
        doklad = row.get('doklad')
        zasilka = row.get('zasilka')
        z_marker = bool(row.get('z_marker'))
        if not doklad or doklad not in qualifying or doklad in seen_doklad:
            continue
        seen_doklad.add(doklad)

        pid = row.get('id_prodejny')
        sale_dt = _sale_datetime(row['typ'], row.get('cas_prodeje'))
        best = _pick_packeta_match(zasilka, pid, sale_dt)
        hint = None
        if zasilka and not best:
            hint = _hint_vydany_visit(zasilka, pid, sale_dt)

        if zasilka and not best:
            invalid_z.append({
                'doklad': doklad,
                'zasilka': zasilka,
                'datum': row['typ'].isoformat() if row['typ'] else None,
                'id_prodejce': row.get('id_prodejce'),
                'id_prodejny': pid,
            })

        visit = best or hint
        linked.append(LinkedSale(
            zasilka=visit.zasilka if visit else (zasilka or ''),
            zasilka_raw=visit.zasilka if visit else (zasilka or ''),
            typ_provize=visit.typ_provize if visit else None,
            typ_skupina=visit.typ_skupina if visit else None,
            id_prodejce=resolve_web_user_id(row.get('id_prodejce'), prodejce_key_map),
            id_prodejny=pid,
            doklad=doklad,
            datum_prodeje=row['typ'],
            cas_baliku=visit.cas if visit else None,
            match_source=row['match_source'],
            packeta_nalezeno=best is not None,
            z_marker=z_marker,
            typ_inferovano=best is None and hint is not None,
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
            id_prodejce=resolve_web_user_id(row.get('id_prodejce'), prodejce_key_map),
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
    podani: set[str] = set()
    c2c: set[str] = set()
    by_typ: dict[str, set[str]] = defaultdict(set)

    for v in visits:
        key = (v.prodejna_id, _zasilka_key(v.zasilka))
        celkem.add(key)
        by_typ[v.typ_provize].add(key)
        if v.typ_skupina == 'vydane':
            vydane.add(key)
        elif v.typ_skupina == 'prijate':
            podani.add(key)
        elif v.typ_skupina == 'prijate_c2c':
            c2c.add(key)

    return {
        'navstevy_celkem': len(celkem),
        'navstevy_vydane': len(vydane),
        'navstevy_podani': len(podani),
        'navstevy_c2c': len(c2c),
        'navstevy_prijate': len(podani | c2c),
        'po_typu': {typ: len(z) for typ, z in by_typ.items()},
    }


def prodeje_by_prodejce(linked: Iterable[LinkedSale]) -> dict[int, dict]:
    """Po prodejci (WebUser.id): prodeje = Z+číslo v poznámce (bez nutnosti slevy / Packety)."""
    key_map = build_prodejce_key_to_user_id()
    out: dict[int, dict] = defaultdict(lambda: {
        'prodeje_propojene': set(),
        'prodeje_oznacene': set(),
        'prodeje_z_cislem': set(),
        'z_bez_cisla': set(),
        'sleva_bez_baliku': set(),
        'zasilky': set(),
        'packeta_potvrzene': set(),
    })
    for item in linked:
        pid = resolve_web_user_id(item.id_prodejce, key_map)
        if not pid:
            continue
        if is_z_oznaceno(item):
            out[pid]['prodeje_oznacene'].add(item.doklad)
            if item.z_marker and not item.packeta_nalezeno:
                out[pid]['z_bez_cisla'].add(item.doklad)
            if item.zasilka and item.packeta_nalezeno:
                out[pid]['zasilky'].add(item.zasilka)
        if is_zasilkovna_prodej(item):
            out[pid]['prodeje_z_cislem'].add(item.doklad)
        if item.packeta_nalezeno and is_zasilkovna_prodej(item):
            out[pid]['prodeje_propojene'].add(item.doklad)
            out[pid]['packeta_potvrzene'].add(item.doklad)
        if item.match_source == 'sleva_fallback':
            out[pid]['sleva_bez_baliku'].add(item.doklad)

    result = {}
    for pid, data in out.items():
        oznacene = len(data['prodeje_oznacene'])
        z_cislem = len(data['prodeje_z_cislem'])
        packeta = len(data['packeta_potvrzene'])
        result[pid] = {
            'zasilkovna_prodeje': z_cislem,
            'zasilkovna_oznaceno': oznacene,
            'zasilkovna_z_bez_cisla': len(data['z_bez_cisla']),
            'zasilkovna_sleva_bez_baliku': len(data['sleva_bez_baliku']),
            'zasilkovna_packeta_potvrzene': packeta,
            'zasilkovna_konverze_z_pct': round(100 * packeta / z_cislem, 1) if z_cislem else None,
        }
    return result


def _baliky_distinct_by_prodejce(
    date_from: date,
    date_to: date,
    typy: frozenset[str],
    prodejna_id: int | None = None,
    *,
    require_prodejce: bool = True,
) -> dict[int, int]:
    """DISTINCT zásilka per prodejce pro zadané typy provize."""
    qs = PacketaProvizePolozka.objects.filter(
        cas__date__gte=date_from,
        cas__date__lte=date_to,
        typ_provize__in=typy,
    )
    if require_prodejce:
        qs = qs.filter(id_prodejce__isnull=False)
    if prodejna_id:
        qs = qs.filter(prodejna_id=prodejna_id)

    by_prodejce: dict[int, set[str]] = defaultdict(set)
    for row in qs.values('id_prodejce', 'zasilka'):
        if row['id_prodejce']:
            by_prodejce[row['id_prodejce']].add(_zasilka_key(row['zasilka']))
    return {pid: len(zasilky) for pid, zasilky in by_prodejce.items()}


def _baliky_distinct_by_prodejna(
    date_from: date,
    date_to: date,
    typy: frozenset[str],
) -> dict[int, int]:
    """DISTINCT zásilka per prodejna pro zadané typy provize."""
    qs = PacketaProvizePolozka.objects.filter(
        cas__date__gte=date_from,
        cas__date__lte=date_to,
        typ_provize__in=typy,
    )
    by_prodejna: dict[int, set[str]] = defaultdict(set)
    for row in qs.values('prodejna_id', 'zasilka'):
        if row['prodejna_id']:
            by_prodejna[row['prodejna_id']].add(_zasilka_key(row['zasilka']))
    return {sid: len(zasilky) for sid, zasilky in by_prodejna.items()}


def baliky_vydane_by_prodejce(
    date_from: date,
    date_to: date,
    prodejna_id: int | None = None,
) -> dict[int, int]:
    """Vydané balíky přiřazené prodejci ze směny (DISTINCT zásilka)."""
    return _baliky_distinct_by_prodejce(date_from, date_to, VYDANE_ALL_TYPY, prodejna_id)


def baliky_zpracovane_by_prodejce(
    date_from: date,
    date_to: date,
    prodejna_id: int | None = None,
) -> dict[int, int]:
    """Všechny zpracované balíky (vydané + přijaté) přiřazené prodejci ze směny."""
    return _baliky_distinct_by_prodejce(
        date_from, date_to, PACKETA_MAIN_VISIT_TYPES, prodejna_id,
    )


def baliky_vydane_by_prodejna(
    date_from: date,
    date_to: date,
) -> dict[int, int]:
    """Vydané balíky po prodejně (DISTINCT zásilka)."""
    return _baliky_distinct_by_prodejna(date_from, date_to, VYDANE_ALL_TYPY)


def baliky_zpracovane_by_prodejna(
    date_from: date,
    date_to: date,
) -> dict[int, int]:
    """Všechny zpracované balíky (vydané + přijaté) po prodejně."""
    return _baliky_distinct_by_prodejna(date_from, date_to, PACKETA_MAIN_VISIT_TYPES)


def prodeje_zasilkovna_by_prodejna(
    linked: Iterable[LinkedSale],
) -> dict[int, int]:
    """Prodeje Zásilkovna po prodejně (DISTINCT doklad se Z+číslem v poznámce)."""
    by_prodejna: dict[int, set[str]] = defaultdict(set)
    for item in linked:
        if not item.id_prodejny:
            continue
        if is_zasilkovna_prodej(item):
            by_prodejna[item.id_prodejny].add(item.doklad)
    return {sid: len(doklady) for sid, doklady in by_prodejna.items()}
