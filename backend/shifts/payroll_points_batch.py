"""Dávkový výpočet prodejních metrik a servisu pro payroll (místo N× dotazů na uživatele)."""
from datetime import date

from django.db.models import Count, Q, Sum

from analytics.models import WebProdejeAll
from analytics.points_config import POINTS_METRIC_KEYS, calculate_product_points
from analytics.viceprace_config import polozky_nad_100_q
from analytics.views import (
    _build_points_payload,
    _empty_servisni_prace_data,
    _salesperson_month_filter,
    _servis_points_for_user_id,
)

# Počet řádků (jako v _aggregate_web_prodeje_all_salesperson)
_SERVICE_COUNT_FILTERS = [
    ('ct300', Q(kod='P114194')),
    ('ct600', Q(kod='CT600')),
    ('ct1200', Q(kod='CT1200')),
    ('akt', Q(kod='AKT')),
    ('zah250', Q(kod='ZAH250')),
    ('nap', Q(kod__in=['NAP', 'NAN'])),
    ('zah500', Q(kod='ZAH500')),
    ('kop250', Q(kod='KOP250')),
    ('kop500', Q(kod='KOP500')),
    ('pz1', Q(kod='PZ1')),
    ('knz', Q(kod='KNZ')),
]


def _empty_metrics():
    return {k: 0 for k in POINTS_METRIC_KEYS}


def batch_sales_metrics_for_month(rok, mesic_cislo, user_ids):
    """~12 agregací pro celý měsíc místo desítek na každého uživatele."""
    if not user_ids:
        return {}
    target = date(rok, mesic_cislo, 1)
    uid_set = set(int(u) for u in user_ids)
    metrics = {uid: _empty_metrics() for uid in uid_set}

    base = WebProdejeAll.objects.filter(
        _salesperson_month_filter(target),
        id_prodejce__in=uid_set,
    )

    pol_rows = (
        base.filter(polozky_nad_100_q())
        .values('id_prodejce')
        .annotate(v=Sum('pocet_kusu'))
    )
    for row in pol_rows:
        uid = row['id_prodejce']
        if uid in metrics:
            metrics[uid]['polozky_nad_100'] = int(row['v'] or 0)

    for key, filt in _SERVICE_COUNT_FILTERS:
        for row in base.filter(filt).values('id_prodejce').annotate(v=Count('id')):
            uid = row['id_prodejce']
            if uid in metrics:
                metrics[uid][key] = row['v'] or 0

    return metrics


def batch_servis_points_for_month(users, ym_prefix):
    """Servis po uživatelích – stále 1 dotaz / technika, ale bez prodejních agregací."""
    from users.exclusions import is_excluded_report_user

    out = {}
    for user in users:
        if is_excluded_report_user(user=user):
            continue
        uid = user.id
        if not getattr(user, 'technik_id', None):
            out[uid] = (0, None)
            continue
        points, data = _servis_points_for_user_id(uid, typ_month_prefix=ym_prefix)
        if data is None and getattr(user, 'technik_id', None):
            data = _empty_servisni_prace_data()
        out[uid] = (points, data)
    return out


def build_points_payload_for_user(user_id, metrics, servis_points, servis_data, iso_date):
    """Stejný tvar jako get_salesperson_monthly_points, bez DB pro prodej."""
    product_points = calculate_product_points(metrics)
    total_points = product_points + (servis_points or 0)
    if servis_data is None and servis_points:
        servis_data = _empty_servisni_prace_data()
    base = {
        'date': iso_date,
        'prodejna': 'Prodejna',
        'prodejce': f'Prodejce {user_id}',
        'id_prodejce': int(user_id),
        **metrics,
    }
    return _build_points_payload(
        base, total_points, 'database',
        servis_data=servis_data, servis_points=servis_points or 0,
    )
