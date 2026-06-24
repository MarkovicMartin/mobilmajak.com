"""
Dobropisy (vratky) z WEB_PRODEJE_ALL – záporná cena u reálné položky.

Nezapočítáváme slevové řádky (SLEVA, BODY) ani zaokrouhlení bez kódu.
Párování s původním prodejem: stejný kód + prodejce, heuristika (není vazba v Sympliu).
Výsledek párování se ukládá kanonicky do DobropisPairingCache (jednou na sale_id).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, F, Q, Sum

from analytics.symplio_urls import symplio_doklad_pdf_url

DOBROPIS_EXCLUDED_KODY = ('SLEVA', 'BODY')
MIRROR_MAX_MINUTES = 180
ORIGINAL_SALE_LOOKBACK_DAYS = 30
PAIRING_VERSION = 2

PAIRING_LABELS = {
    'zrcadlo': 'Zrcadlo',
    'par': 'Jiný prodej',
    'bez_paru': 'Bez páru',
}

BEZ_PARU_DUVOD_LABELS = {
    'jiny_prodejce': 'Jiný prodejce',
    'mimo_okno': 'Mimo 30denní okno',
    'kod_nenalezen': 'Prodej nenalezen',
    'chybi_udaje': 'Chybí kód nebo prodejce',
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


def original_sale_search_from(anchor: date) -> date:
    return anchor - timedelta(days=ORIGINAL_SALE_LOOKBACK_DAYS)


def build_pairing_search_qs(
    dobropisy_month_qs,
    *,
    month_start: date,
    month_end: date,
    prodejna: str | None = None,
):
    """Kandidáti na původní prodej – zuženo podle filtru prodejny nebo poboček s vratkami."""
    from analytics.models import WebProdejeAll

    search_qs = WebProdejeAll.objects.filter(
        typ__gte=original_sale_search_from(month_start),
        typ__lte=month_end,
    )
    if prodejna:
        search_qs = search_qs.filter(stredisko=prodejna)
    else:
        strediska = list(
            dobropisy_month_qs.filter(dobropis_polozka_q())
            .exclude(stredisko__isnull=True)
            .exclude(stredisko='')
            .values_list('stredisko', flat=True)
            .distinct()
        )
        if strediska:
            search_qs = search_qs.filter(stredisko__in=strediska)
    return search_qs


def build_canonical_pairing_search_qs(dobropis_rows: list[dict], *, month_end: date):
    """Kanonické párování – celá firma, okno 30 dní před nejstarším dobropisem v dávce."""
    from analytics.models import WebProdejeAll

    if not dobropis_rows:
        return WebProdejeAll.objects.none()
    dates = [r['typ'] for r in dobropis_rows if r.get('typ')]
    if not dates:
        return WebProdejeAll.objects.none()
    earliest = min(dates)
    search_from = original_sale_search_from(earliest)
    end = max(month_end, max(dates))
    return WebProdejeAll.objects.filter(typ__gte=search_from, typ__lte=end)


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


_POSITIVE_SALE_VALUES = (
    'typ', 'doklad', 'kod', 'cena_ks_vcl_dph', 'pocet_kusu',
    'id_prodejce', 'cas_prodeje', 'stredisko',
)


def _positive_sales_queryset(search_qs, *, kod=None, id_prodejce=None, kody=None):
    qs = search_qs.filter(cena_ks_vcl_dph__gt=0, pocet_kusu__gt=0)
    if kod is not None:
        qs = qs.filter(kod=kod)
    if id_prodejce is not None:
        qs = qs.filter(id_prodejce=id_prodejce)
    if kody:
        qs = qs.filter(kod__in=kody)
    return qs.order_by('-typ', '-cas_prodeje', '-id').values(*_POSITIVE_SALE_VALUES)


def _batch_positive_sales(search_qs, pairs: set[tuple[str, int]]) -> dict[tuple[str, int], list[dict]]:
    if not pairs:
        return {}
    pair_q = Q(pk__in=[])
    for kod, pid in pairs:
        pair_q |= Q(kod=kod, id_prodejce=pid)
    positives = _positive_sales_queryset(search_qs).filter(pair_q).order_by(
        'id_prodejce', 'kod', '-typ', '-cas_prodeje', '-id',
    )
    idx: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in positives:
        idx[(row['kod'], row['id_prodejce'])].append(row)
    return idx


def _batch_positive_sales_by_kod(search_qs, kody: set[str]) -> dict[str, list[dict]]:
    if not kody:
        return {}
    idx: dict[str, list[dict]] = defaultdict(list)
    for row in _positive_sales_queryset(search_qs, kody=kody):
        idx[row['kod']].append(row)
    return idx


def _price_matching_candidates(dobropis: dict, pool: list[dict]) -> list[dict]:
    dob_typ = dobropis.get('typ')
    return [
        row for row in pool
        if row.get('typ') and dob_typ and row['typ'] <= dob_typ
        and _unit_prices_match(row['cena_ks_vcl_dph'], dobropis['cena_ks_vcl_dph'])
    ]


def _kandidat_payload(sale: dict | None) -> dict:
    if not sale:
        return {
            'kandidat_doklad': None,
            'kandidat_datum': None,
            'kandidat_cas': None,
            'kandidat_id_prodejce': None,
            'kandidat_cena': None,
        }
    cas = sale.get('cas_prodeje')
    return {
        'kandidat_doklad': sale.get('doklad'),
        'kandidat_datum': sale['typ'].isoformat() if sale.get('typ') else None,
        'kandidat_cas': cas.isoformat() if cas else None,
        'kandidat_id_prodejce': sale.get('id_prodejce'),
        'kandidat_cena': float(sale['cena_ks_vcl_dph'] or 0),
        'symplio_kandidat_url': symplio_doklad_pdf_url(sale.get('doklad')),
    }


def classify_bez_paru_hint(
    dobropis: dict,
    *,
    candidates_by_kod: dict[str, list[dict]],
    outside_window_by_kod: dict[str, list[dict]] | None = None,
) -> tuple[str, dict | None]:
    kod = dobropis.get('kod')
    pid = dobropis.get('id_prodejce')
    if not kod or pid is None:
        return 'chybi_udaje', None

    in_window = _price_matching_candidates(dobropis, candidates_by_kod.get(kod, []))
    same_prodejce = [row for row in in_window if row.get('id_prodejce') == pid]
    if in_window and not same_prodejce:
        return 'jiny_prodejce', in_window[0]

    outside = _price_matching_candidates(
        dobropis, (outside_window_by_kod or {}).get(kod, []),
    )
    if outside:
        same_outside = [row for row in outside if row.get('id_prodejce') == pid]
        if same_outside:
            return 'mimo_okno', same_outside[0]
        return 'mimo_okno', outside[0]

    return 'kod_nenalezen', None


def _batch_positive_sales_outside_window(kody: set[str], anchor_dates: list[date]):
    if not kody or not anchor_dates:
        return {}
    from analytics.models import WebProdejeAll

    earliest_anchor = min(anchor_dates)
    search_before = original_sale_search_from(earliest_anchor)
    latest_anchor = max(anchor_dates)
    idx: dict[str, list[dict]] = defaultdict(list)
    for row in WebProdejeAll.objects.filter(
        kod__in=kody,
        cena_ks_vcl_dph__gt=0,
        pocet_kusu__gt=0,
        typ__lt=search_before,
        typ__lte=latest_anchor,
    ).order_by('-typ', '-cas_prodeje', '-id').values(*_POSITIVE_SALE_VALUES):
        idx[row['kod']].append(row)
    return idx


def _bez_paru_hint_payload(
    dobropis: dict,
    *,
    candidates_by_kod: dict[str, list[dict]],
    outside_window_by_kod: dict[str, list[dict]] | None = None,
) -> dict:
    duvod, kandidat = classify_bez_paru_hint(
        dobropis,
        candidates_by_kod=candidates_by_kod,
        outside_window_by_kod=outside_window_by_kod,
    )
    return {
        'bez_paru_duvod': duvod,
        'bez_paru_duvod_label': BEZ_PARU_DUVOD_LABELS.get(duvod, duvod),
        **_kandidat_payload(kandidat),
    }


def _empty_bez_paru_hint() -> dict:
    return {
        'bez_paru_duvod': None,
        'bez_paru_duvod_label': None,
        'kandidat_doklad': None,
        'kandidat_datum': None,
        'kandidat_cas': None,
        'kandidat_id_prodejce': None,
        'kandidat_cena': None,
    }


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


def _pairing_minutes(dobropis: dict, pairing: str, original: dict | None) -> float | None:
    if pairing != 'zrcadlo' or not original:
        return None
    mins_po = _minutes_between(
        _as_datetime(original['typ'], original.get('cas_prodeje')),
        _as_datetime(dobropis['typ'], dobropis.get('cas_prodeje')),
    )
    if mins_po is None:
        return None
    return round(mins_po, 1)


def _load_pairing_cache(sale_ids: list[int]) -> dict[int, dict]:
    if not sale_ids:
        return {}
    from analytics.models import DobropisPairingCache

    out = {}
    stale_ids = []
    for row in DobropisPairingCache.objects.filter(sale_id__in=sale_ids):
        if row.pairing_version != PAIRING_VERSION:
            stale_ids.append(row.sale_id)
            continue
        puvodni_datum = row.puvodni_datum.isoformat() if row.puvodni_datum else None
        puvodni_cas = row.puvodni_cas.isoformat() if row.puvodni_cas else None
        kandidat_datum = row.kandidat_datum.isoformat() if row.kandidat_datum else None
        kandidat_cas = row.kandidat_cas.isoformat() if row.kandidat_cas else None
        hint = _empty_bez_paru_hint()
        if row.pairing == 'bez_paru' and row.bez_paru_duvod:
            hint = {
                'bez_paru_duvod': row.bez_paru_duvod,
                'bez_paru_duvod_label': BEZ_PARU_DUVOD_LABELS.get(row.bez_paru_duvod, row.bez_paru_duvod),
                'kandidat_doklad': row.kandidat_doklad,
                'kandidat_datum': kandidat_datum,
                'kandidat_cas': kandidat_cas,
                'kandidat_id_prodejce': row.kandidat_id_prodejce,
                'kandidat_cena': float(row.kandidat_cena) if row.kandidat_cena is not None else None,
            }
        out[row.sale_id] = {
            'pairing': row.pairing,
            'pairing_label': PAIRING_LABELS.get(row.pairing, row.pairing),
            'puvodni_doklad': row.puvodni_doklad,
            'puvodni_datum': puvodni_datum,
            'puvodni_cas': puvodni_cas,
            'puvodni_cena': float(row.puvodni_cena) if row.puvodni_cena is not None else None,
            'puvodni_stredisko': row.puvodni_stredisko,
            'minut_po_prodeji': row.minut_po_prodeji,
            **hint,
        }
    if stale_ids:
        DobropisPairingCache.objects.filter(sale_id__in=stale_ids).delete()
    return out


def _cache_entry_from_pairing(
    sale_id: int,
    dobropis: dict,
    original: dict | None,
    pairing: str,
    *,
    bez_paru_hint: dict | None = None,
):
    from analytics.models import DobropisPairingCache

    orig = _original_payload(original)
    puvodni_datum = None
    if orig['puvodni_datum']:
        puvodni_datum = date.fromisoformat(orig['puvodni_datum'])
    puvodni_cas = None
    if orig['puvodni_cas']:
        puvodni_cas = time.fromisoformat(orig['puvodni_cas'])
    hint = bez_paru_hint or _empty_bez_paru_hint()
    kandidat_datum = None
    if hint.get('kandidat_datum'):
        kandidat_datum = date.fromisoformat(hint['kandidat_datum'])
    kandidat_cas = None
    if hint.get('kandidat_cas'):
        kandidat_cas = time.fromisoformat(hint['kandidat_cas'])
    return DobropisPairingCache(
        sale_id=sale_id,
        pairing=pairing,
        puvodni_doklad=orig['puvodni_doklad'],
        puvodni_datum=puvodni_datum,
        puvodni_cas=puvodni_cas,
        puvodni_cena=orig['puvodni_cena'],
        puvodni_stredisko=orig['puvodni_stredisko'],
        minut_po_prodeji=_pairing_minutes(dobropis, pairing, original),
        bez_paru_duvod=hint.get('bez_paru_duvod'),
        kandidat_doklad=hint.get('kandidat_doklad'),
        kandidat_datum=kandidat_datum,
        kandidat_cas=kandidat_cas,
        kandidat_id_prodejce=hint.get('kandidat_id_prodejce'),
        kandidat_cena=hint.get('kandidat_cena'),
        pairing_version=PAIRING_VERSION,
    )


def _ensure_pairing_cached(
    dobropis_list: list[dict],
    cached: dict[int, dict],
    *,
    month_end: date,
) -> dict[int, dict]:
    uncached = [row for row in dobropis_list if row['id'] not in cached]
    if not uncached:
        return cached

    pairs = {
        (row['kod'], row['id_prodejce'])
        for row in uncached
        if row.get('kod') and row.get('id_prodejce') is not None
    }
    search_qs = build_canonical_pairing_search_qs(uncached, month_end=month_end)
    candidates = _batch_positive_sales(search_qs, pairs)

    classified = []
    bez_paru_rows = []
    for sale in uncached:
        original, pairing = classify_original_sale(sale, candidates)
        classified.append((sale, original, pairing))
        if pairing == 'bez_paru':
            bez_paru_rows.append(sale)

    bez_paru_hints: dict[int, dict] = {}
    if bez_paru_rows:
        kody = {row['kod'] for row in bez_paru_rows if row.get('kod')}
        candidates_by_kod = _batch_positive_sales_by_kod(search_qs, kody)
        outside_window_by_kod = _batch_positive_sales_outside_window(
            kody,
            [row['typ'] for row in bez_paru_rows if row.get('typ')],
        )
        for sale in bez_paru_rows:
            bez_paru_hints[sale['id']] = _bez_paru_hint_payload(
                sale,
                candidates_by_kod=candidates_by_kod,
                outside_window_by_kod=outside_window_by_kod,
            )

    to_store = []
    for sale, original, pairing in classified:
        hint = bez_paru_hints.get(sale['id']) if pairing == 'bez_paru' else None
        entry = _cache_entry_from_pairing(
            sale['id'], sale, original, pairing, bez_paru_hint=hint,
        )
        to_store.append(entry)
        orig = _original_payload(original)
        cached[sale['id']] = {
            'pairing': pairing,
            'pairing_label': PAIRING_LABELS[pairing],
            'minut_po_prodeji': entry.minut_po_prodeji,
            **orig,
            **(hint or _empty_bez_paru_hint()),
        }

    from analytics.models import DobropisPairingCache

    uncached_ids = [sale['id'] for sale in uncached]
    with transaction.atomic():
        if uncached_ids:
            DobropisPairingCache.objects.filter(sale_id__in=uncached_ids).delete()
        DobropisPairingCache.objects.bulk_create(to_store, ignore_conflicts=True)
    return cached


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


def _enrich_users_map(users_map: dict, pairing_by_id: dict[int, dict]) -> dict:
    missing = set()
    for data in pairing_by_id.values():
        kid = data.get('kandidat_id_prodejce')
        if kid is not None and kid not in users_map:
            missing.add(kid)
    if not missing:
        return users_map
    from users.models import WebUser

    out = dict(users_map)
    for user in WebUser.objects.filter(id__in=missing):
        out[user.id] = f'{user.jmeno} {user.prijmeni}'.strip()
    return out


def list_dobropisy(
    queryset,
    *,
    users_map: dict | None = None,
    month_end: date | None = None,
    search_qs=None,
) -> list[dict]:
    """
    Seznam dobropisů s kanonickým párováním (cache v DB).
    search_qs: jen pro testy – produkce používá build_canonical_pairing_search_qs.
    """
    users_map = users_map or {}
    dobropis_qs = (
        queryset.filter(dobropis_polozka_q())
        .order_by('-typ', 'doklad', 'id')
        .values(
            'id', 'typ', 'doklad', 'kod', 'nazev', 'pocet_kusu', 'cena_ks_vcl_dph',
            'id_prodejce', 'stredisko', 'cas_prodeje',
        )
    )
    dobropis_list = list(dobropis_qs)
    if not dobropis_list:
        return []

    if month_end is None:
        dates = [r['typ'] for r in dobropis_list if r.get('typ')]
        month_end = max(dates) if dates else date.today()

    sale_ids = [int(r['id']) for r in dobropis_list]
    pairing_by_id = _load_pairing_cache(sale_ids)

    uncached = [row for row in dobropis_list if row['id'] not in pairing_by_id]
    if uncached:
        if search_qs is not None:
            pairs = {
                (row['kod'], row['id_prodejce'])
                for row in uncached
                if row.get('kod') and row.get('id_prodejce') is not None
            }
            candidates = _batch_positive_sales(search_qs, pairs)
            classified = []
            bez_paru_rows = []
            for sale in uncached:
                original, pairing = classify_original_sale(sale, candidates)
                classified.append((sale, original, pairing))
                if pairing == 'bez_paru':
                    bez_paru_rows.append(sale)
            bez_paru_hints: dict[int, dict] = {}
            if bez_paru_rows:
                kody = {row['kod'] for row in bez_paru_rows if row.get('kod')}
                candidates_by_kod = _batch_positive_sales_by_kod(search_qs, kody)
                outside_window_by_kod = _batch_positive_sales_outside_window(
                    kody,
                    [row['typ'] for row in bez_paru_rows if row.get('typ')],
                )
                for sale in bez_paru_rows:
                    bez_paru_hints[sale['id']] = _bez_paru_hint_payload(
                        sale,
                        candidates_by_kod=candidates_by_kod,
                        outside_window_by_kod=outside_window_by_kod,
                    )
            to_store = []
            for sale, original, pairing in classified:
                hint = bez_paru_hints.get(sale['id']) if pairing == 'bez_paru' else None
                entry = _cache_entry_from_pairing(
                    sale['id'], sale, original, pairing, bez_paru_hint=hint,
                )
                to_store.append(entry)
                orig = _original_payload(original)
                pairing_by_id[sale['id']] = {
                    'pairing': pairing,
                    'pairing_label': PAIRING_LABELS[pairing],
                    'minut_po_prodeji': entry.minut_po_prodeji,
                    **orig,
                    **(hint or _empty_bez_paru_hint()),
                }
            from analytics.models import DobropisPairingCache

            uncached_ids = [sale['id'] for sale in uncached]
            if uncached_ids:
                DobropisPairingCache.objects.filter(sale_id__in=uncached_ids).delete()
            DobropisPairingCache.objects.bulk_create(to_store)
        else:
            pairing_by_id = _ensure_pairing_cached(
                dobropis_list, pairing_by_id, month_end=month_end,
            )

    users_map = _enrich_users_map(users_map, pairing_by_id)

    rows = []
    for sale in dobropis_list:
        kusy = int(sale['pocet_kusu'] or 1)
        cena = float(sale['cena_ks_vcl_dph'] or 0)
        uid = sale['id_prodejce']
        typ = sale['typ']
        pairing_data = pairing_by_id.get(sale['id'], {
            'pairing': 'bez_paru',
            'pairing_label': PAIRING_LABELS['bez_paru'],
            'minut_po_prodeji': None,
            **_original_payload(None),
            **_empty_bez_paru_hint(),
        })
        kandidat_uid = pairing_data.get('kandidat_id_prodejce')
        rows.append({
            'datum': typ.isoformat() if typ else None,
            'cas': sale['cas_prodeje'].isoformat() if sale.get('cas_prodeje') else None,
            'doklad': sale['doklad'],
            'symplio_doklad_url': symplio_doklad_pdf_url(sale['doklad']),
            'symplio_puvodni_doklad_url': symplio_doklad_pdf_url(pairing_data.get('puvodni_doklad')),
            'kod': sale['kod'],
            'nazev': (sale['nazev'] or '')[:100],
            'kusy': kusy,
            'cena_ks_vcl_dph': cena,
            'castka': _line_total(kusy, cena),
            'id_prodejce': uid,
            'prodejce': users_map.get(uid, uid),
            'stredisko': sale['stredisko'],
            'kandidat_prodejce': users_map.get(kandidat_uid, kandidat_uid) if kandidat_uid else None,
            **pairing_data,
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
