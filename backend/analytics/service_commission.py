"""
Provize za služby – příplatek nad základ 15 bodů jen při slevě pod 20 %.

Ceníková cena = číslo v kódu (CT600 → 600 Kč) nebo fixní sazba (AKT/NAP → 249).
Ceny typu 599 / 499 / 249 (x99) jsou v pořádku. Sleva ≥ 20 % → bez příplatku.
"""
from __future__ import annotations

import re
from decimal import Decimal

from django.db.models import Q

from .points_config import SERVICE_EXTRA_POINT_RATES, SERVICE_POINT_KEYS

MAX_SERVICE_DISCOUNT_RATIO = Decimal('0.20')

SERVICE_KOD_FILTERS: dict[str, Q] = {
    'ct600': Q(kod='CT600'),
    'ct1200': Q(kod='CT1200'),
    'akt': Q(kod='AKT'),
    'zah250': Q(kod='ZAH250'),
    'nap': Q(kod__in=['NAP', 'NAN']),
    'zah500': Q(kod='ZAH500'),
    'kop250': Q(kod='KOP250'),
    'kop500': Q(kod='KOP500'),
    'pz1': Q(kod='PZ1'),
}

# Služby bez čísla v kódu – referenční ceníková cena s DPH
SERVICE_CATALOG_PRICE_OVERRIDES: dict[str, Decimal] = {
    'akt': Decimal('249'),
    'nap': Decimal('249'),
}


def catalog_price_for_kod(kod: str | None) -> Decimal | None:
    k = (kod or '').strip().upper()
    if not k:
        return None
    if k in SERVICE_CATALOG_PRICE_OVERRIDES:
        return SERVICE_CATALOG_PRICE_OVERRIDES[k]
    if k == 'NAN':
        return SERVICE_CATALOG_PRICE_OVERRIDES.get('nap')
    match = re.search(r'(\d+)$', k)
    if match:
        return Decimal(match.group(1))
    return None


def catalog_price_for_metric(metric_key: str) -> Decimal | None:
    key = (metric_key or '').lower()
    if key in SERVICE_CATALOG_PRICE_OVERRIDES:
        return SERVICE_CATALOG_PRICE_OVERRIDES[key]
    kod_sample = {
        'ct600': 'CT600',
        'ct1200': 'CT1200',
        'zah250': 'ZAH250',
        'zah500': 'ZAH500',
        'kop250': 'KOP250',
        'kop500': 'KOP500',
        'pz1': 'PZ1',
    }.get(key)
    if kod_sample:
        return catalog_price_for_kod(kod_sample)
    return None


def min_commission_unit_price(catalog: Decimal) -> Decimal:
    """Minimální cena/ks pro příplatek – sleva musí být **pod** 20 % (≥20 % bez příplatku)."""
    threshold = catalog * (Decimal('1') - MAX_SERVICE_DISCOUNT_RATIO)
    return threshold.quantize(Decimal('0.01'))


def service_commission_qualified_q(metric_key: str) -> Q:
    """Řádky započtené do příplatku za službu."""
    key = (metric_key or '').lower()
    kod_q = SERVICE_KOD_FILTERS.get(key)
    if not kod_q:
        return Q(pk__in=[])
    catalog = catalog_price_for_metric(key)
    if catalog is None:
        return kod_q & Q(pocet_kusu__gt=0)
    min_price = min_commission_unit_price(catalog)
    return (
        kod_q
        & Q(cena_ks_vcl_dph__gt=min_price)
        & Q(cena_ks_vcl_dph__gt=0)
        & Q(pocet_kusu__gt=0)
    )


def service_commission_discounted_q(metric_key: str) -> Q:
    """Řádky se slevou ≥ 20 % – příplatek se nevyplácí."""
    key = (metric_key or '').lower()
    kod_q = SERVICE_KOD_FILTERS.get(key)
    catalog = catalog_price_for_metric(key)
    if not kod_q or catalog is None:
        return Q(pk__in=[])
    min_price = min_commission_unit_price(catalog)
    return (
        kod_q
        & Q(cena_ks_vcl_dph__lte=min_price)
        & Q(cena_ks_vcl_dph__gt=0)
        & Q(pocet_kusu__gt=0)
    )


def all_discounted_services_q() -> Q:
    combined = Q(pk__in=[])
    for key in SERVICE_POINT_KEYS:
        if key not in SERVICE_KOD_FILTERS:
            continue
        if catalog_price_for_metric(key) is None:
            continue
        combined |= service_commission_discounted_q(key)
    return combined


def metric_key_for_kod(kod: str | None) -> str | None:
    k = (kod or '').strip().upper()
    if k in ('NAP', 'NAN'):
        return 'nap'
    mapping = {
        'CT600': 'ct600', 'CT1200': 'ct1200', 'AKT': 'akt',
        'ZAH250': 'zah250', 'ZAH500': 'zah500',
        'KOP250': 'kop250', 'KOP500': 'kop500', 'PZ1': 'pz1',
    }
    return mapping.get(k)


def row_qualifies_for_service_extra(kod: str | None, cena_ks_vcl_dph) -> bool:
    metric = metric_key_for_kod(kod)
    if not metric:
        return True
    catalog = catalog_price_for_metric(metric)
    if catalog is None:
        return True
    try:
        cena = Decimal(str(cena_ks_vcl_dph or 0))
    except Exception:
        return False
    if cena <= 0:
        return False
    return cena > min_commission_unit_price(catalog)


def discount_percent(kod: str | None, cena_ks_vcl_dph) -> float | None:
    catalog = catalog_price_for_kod(kod) or catalog_price_for_metric(metric_key_for_kod(kod) or '')
    if not catalog:
        return None
    try:
        cena = float(cena_ks_vcl_dph or 0)
    except (TypeError, ValueError):
        return None
    if cena <= 0:
        return None
    return round((1 - cena / float(catalog)) * 100, 1)


def service_metrics_count_annotations():
    """Count filtry pro Django annotate – jen služby s povolenou slevou (< 20 %)."""
    from django.db.models import Count

    ann = {
        'ct300': Count('id', filter=Q(kod='P114194')),
        'knz': Count('id', filter=Q(kod='KNZ')),
    }
    for key in SERVICE_POINT_KEYS:
        if key in SERVICE_KOD_FILTERS:
            ann[key] = Count('id', filter=service_commission_qualified_q(key))
    return ann


def count_service_metrics_on_queryset(queryset) -> dict:
    """Počty služeb pro jeden queryset (profil / denní přehled)."""
    out = {
        'ct300': queryset.filter(kod='P114194').count(),
        'knz': queryset.filter(kod='KNZ').count(),
    }
    for key in SERVICE_POINT_KEYS:
        if key in SERVICE_KOD_FILTERS:
            out[key] = queryset.filter(service_commission_qualified_q(key)).count()
        else:
            out[key] = 0
    return out


def list_discounted_service_sales(queryset, *, users_map: dict | None = None):
    """Řádky se slevou ≥ 20 % v querysetu (seřazeno od nejnovějších)."""
    users_map = users_map or {}
    rows = []
    qs = queryset.filter(all_discounted_services_q()).order_by('-typ', 'doklad')
    for sale in qs.iterator():
        metric = metric_key_for_kod(sale.kod)
        catalog = catalog_price_for_kod(sale.kod)
        if catalog is None and metric:
            catalog = catalog_price_for_metric(metric)
        kusy = int(sale.pocet_kusu or 1)
        cena = float(sale.cena_ks_vcl_dph or 0)
        excluded_pts = 0
        if metric:
            excluded_pts = SERVICE_EXTRA_POINT_RATES.get(metric, 0) * kusy
        rows.append({
            'datum': sale.typ.isoformat() if sale.typ else None,
            'doklad': sale.doklad,
            'kod': sale.kod,
            'nazev': (sale.nazev or '')[:80],
            'cena_ks_vcl_dph': cena,
            'katalog_cena': float(catalog) if catalog else None,
            'sleva_procent': discount_percent(sale.kod, cena),
            'kusy': kusy,
            'vyloucene_body': excluded_pts,
            'id_prodejce': sale.id_prodejce,
            'prodejce': users_map.get(sale.id_prodejce, sale.id_prodejce),
            'stredisko': sale.stredisko,
            'metric_key': metric,
        })
    return rows
