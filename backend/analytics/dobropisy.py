"""
Dobropisy (vratky) z WEB_PRODEJE_ALL – záporná cena u reálné položky.

Nezapočítáváme slevové řádky (SLEVA, BODY) ani zaokrouhlení bez kódu.
Párování s původním prodejem: stejný kód + prodejce, heuristika (není vazba v Sympliu).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, F, Q, Sum

DOBROPIS_EXCLUDED_KODY = ('SLEVA', 'BODY')
MIRROR_MAX_MINUTES = 180
ORIGINAL_SALE_LOOKBACK_DAYS = 120

PAIRING_LABELS = {
    'zrcadlo': 'Zrcadlo',
    'par': 'Jiný prodej',
    'bez_paru': 'Bez páru',
}


def dobropis_polozka_q() -> Q:
    """Řádek dobropisu – záporná cena, skutečný kód položky."""
    return (
        Q(cena_ks_vcl_dph__lt=0)
        & ~Q(kod__in=DOBROPIS_EXCLUDED_KODY)
        & ~Q(nazev__icontains='zaokrouhl')
        & ~Q(nazev__icontains='zaokrúh')
        & Q(kod__isnull=False)
        & ~Q(kod='')
        & Q(pocet_kusu__gt=0)
    )


def original_sale_search_from(month_start: date) -> date:
    return month_start - timedelta(days=ORIGINAL_SALE_LOOKBACK_DAYS)


def _line_total(pocet_kusu, cena_ks_vcl_dph) -> float:
    try:
        kusy = int(pocet_kusu or 0)
        cena = float(cena_ks_vcl_dph or 0)
    except (TypeError, ValueError):
        return 0.0
    return round(kusy * cena, 2)


def _as_datetime(day: date | None, clock) -> datetime | None:
    if not day:
        return None
    if clock is None:
        return datetime.combine(day, time.min)
    return datetime.combine(day, clock)


def _minutes_between(earlier: datetime | None, later: datetime | None) -> float | None:
    if earlier is None or later is None:
        return None
    return (later - earlier).total_seconds() / 60.0


def _unit_prices_match(sale_price, return_price) -> bool:
    try:
        return abs(abs(float(return_price)) - float(sale_price)) < 0.01
    except (TypeError, ValueError):
        return False


def _batch_positive_sales(search_qs, pairs: set[tuple[str, int]]) -> dict[tuple[str, int], list[dict]]:
    if not pairs:
        return {}
    pair_q = Q(pk__in=[])
    for kod, pid in pairs:
        pair_q |= Q(kod=kod, id_prodejce=pid)
    positives = (
        search_qs.filter(pair_q, cena_ks_vcl_dph__gt=0, pocet_kusu__gt=0)
        .order_by('id_prodejce', 'kod', '-typ', '-cas_prodeje', '-id')
        .values(
            'typ', 'doklad', 'kod', 'cena_ks_vcl_dph', 'pocet_kusu',
            'id_prodejce', 'cas_prodeje', 'stredisko',
        )
    )
    idx: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in positives:
        idx[(row['kod'], row['id_prodejce'])].append(row)
    return idx


def classify_original_sale(dobropis: dict, candidates: dict[tuple[str, int], list[dict]]) -> tuple[dict | None, str]:
    key = (dobropis['kod'], dobropis['id_prodejce'])
    pool = [
        c for c in candidates.get(key, [])
        if c['typ'] and dobropis['typ'] and c['typ'] <= dobropis['typ']
    ]
    if not pool:
        return None, 'bez_paru'

    dob_dt = _as_datetime(dobropis['typ'], dobropis.get('cas_prodeje'))

    for sale in pool:
        if sale['typ'] != dobropis['typ']:
            continue
        if not _unit_prices_match(sale['cena_ks_vcl_dph'], dobropis['cena_ks_vcl_dph']):
            continue
        sale_dt = _as_datetime(sale['typ'], sale.get('cas_prodeje'))
        if sale_dt and dob_dt:
            mins = _minutes_between(sale_dt, dob_dt)
            if mins is not None and 0 <= mins <= MIRROR_MAX_MINUTES:
                return sale, 'zrcadlo'
        else:
            return sale, 'zrcadlo'

    return pool[0], 'par'


def _original_payload(sale: dict | None) -> dict:
    if not sale:
        return {
            'puvodni_doklad': None,
            'puvodni_datum': None,
            'puvodni_cas': None,
            'puvodni_cena': None,
            'puvodni_stredisko': None,
        }
    cas = sale.get('cas_prodeje')
    return {
        'puvodni_doklad': sale.get('doklad'),
        'puvodni_datum': sale['typ'].isoformat() if sale.get('typ') else None,
        'puvodni_cas': cas.isoformat() if cas else None,
        'puvodni_cena': float(sale['cena_ks_vcl_dph'] or 0),
        'puvodni_stredisko': sale.get('stredisko'),
    }


def pairing_totals_from_rows(rows: list[dict]) -> dict[str, int]:
    out = {'zrcadlo': 0, 'par': 0, 'bez_paru': 0}
    for row in rows:
        key = row.get('pairing') or 'bez_paru'
        if key in out:
            out[key] += 1
    return out


def dobropisy_summary_by_prodejce(queryset, *, users_map: dict | None = None) -> list[dict]:
    users_map = users_map or {}
    rows = (
        queryset.filter(dobropis_polozka_q(), id_prodejce__isnull=False)
        .values('id_prodejce')
        .annotate(
            polozky=Count('id'),
            doklady=Count('doklad', distinct=True),
            castka=Sum(F('pocet_kusu') * F('cena_ks_vcl_dph'), default=0),
        )
        .order_by('-polozky', 'id_prodejce')
    )
    out = []
    for row in rows:
        uid = row['id_prodejce']
        out.append({
            'id_prodejce': uid,
            'prodejce': users_map.get(uid, f'Prodejce {uid}'),
            'polozky': int(row['polozky'] or 0),
            'doklady': int(row['doklady'] or 0),
            'castka': float(row['castka'] or 0),
        })
    return out


def list_dobropisy(
    queryset,
    *,
    users_map: dict | None = None,
    search_qs=None,
) -> list[dict]:
    users_map = users_map or {}
    dobropis_qs = (
        queryset.filter(dobropis_polozka_q())
        .order_by('-typ', 'doklad', 'id')
        .values(
            'typ', 'doklad', 'kod', 'nazev', 'pocet_kusu', 'cena_ks_vcl_dph',
            'id_prodejce', 'stredisko', 'cas_prodeje',
        )
    )
    dobropis_list = list(dobropis_qs)
    pairs = {
        (row['kod'], row['id_prodejce'])
        for row in dobropis_list
        if row.get('kod') and row.get('id_prodejce') is not None
    }
    candidates = _batch_positive_sales(search_qs or queryset, pairs)

    rows = []
    for sale in dobropis_list:
        kusy = int(sale['pocet_kusu'] or 1)
        cena = float(sale['cena_ks_vcl_dph'] or 0)
        uid = sale['id_prodejce']
        typ = sale['typ']
        original, pairing = classify_original_sale(sale, candidates)
        orig_payload = _original_payload(original)
        mins_po = None
        if pairing == 'zrcadlo' and original:
            mins_po = _minutes_between(
                _as_datetime(original['typ'], original.get('cas_prodeje')),
                _as_datetime(typ, sale.get('cas_prodeje')),
            )
            if mins_po is not None:
                mins_po = round(mins_po, 1)

        rows.append({
            'datum': typ.isoformat() if typ else None,
            'cas': sale['cas_prodeje'].isoformat() if sale.get('cas_prodeje') else None,
            'doklad': sale['doklad'],
            'kod': sale['kod'],
            'nazev': (sale['nazev'] or '')[:100],
            'kusy': kusy,
            'cena_ks_vcl_dph': cena,
            'castka': _line_total(kusy, cena),
            'id_prodejce': uid,
            'prodejce': users_map.get(uid, uid),
            'stredisko': sale['stredisko'],
            'pairing': pairing,
            'pairing_label': PAIRING_LABELS[pairing],
            'minut_po_prodeji': mins_po,
            **orig_payload,
        })
    return rows


def dobropisy_totals(queryset) -> dict:
    agg = queryset.filter(dobropis_polozka_q()).aggregate(
        polozky=Count('id'),
        doklady=Count('doklad', distinct=True),
        castka=Sum(F('pocet_kusu') * F('cena_ks_vcl_dph'), default=Decimal('0')),
    )
    return {
        'polozky': int(agg['polozky'] or 0),
        'doklady': int(agg['doklady'] or 0),
        'castka': float(agg['castka'] or 0),
    }
