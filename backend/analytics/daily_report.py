"""Denní souhrn prodejů pro Slack – agregace z WEB_PRODEJE_ALL."""
from __future__ import annotations

from datetime import date, timedelta

from django.db import models
from django.db.models import Count, F, Sum
from django.utils import timezone

from analytics.models import WebProdejeAll


def _fmt_czk(value) -> str:
    if value is None:
        return '0 Kč'
    amount = float(value)
    return f"{amount:,.0f}".replace(',', ' ') + ' Kč'


def _fmt_pct(value) -> str:
    if value is None:
        return '0 %'
    return f"{float(value):.1f} %".replace('.', ',')


def _day_bounds(day: date) -> tuple[str, str]:
    start = day.isoformat()
    end = (day + timedelta(days=1)).isoformat()
    return start, end


def _day_queryset(day: date):
    start, end = _day_bounds(day)
    return WebProdejeAll.objects.filter(typ__gte=start, typ__lt=end)


def _top_sellers_by_leaderboard_points(day: date, limit: int = 3) -> list[dict]:
    """Top N prodejců podle denních bodů – stejná logika jako žebříček v appce."""
    from django.db.utils import OperationalError, ProgrammingError

    from analytics.views import (
        _leaderboard_day_queryset,
        _leaderboard_dominant_stredisko_map,
        _leaderboard_product_points,
        _leaderboard_seller_aggregation,
        _leaderboard_webuser_queryset,
        _servis_points_map_for_day,
    )
    from analytics.vykupy_config import vykupy_counts_map
    from users.exclusions import get_leaderboard_excluded_prodejce_ids

    day_queryset = _leaderboard_day_queryset(day)
    aggregation = list(_leaderboard_seller_aggregation(day_queryset))
    try:
        vykupy_map = vykupy_counts_map(typ_exact=day.strftime('%Y-%m-%d'))
    except (OperationalError, ProgrammingError):
        # Unmanaged WEB_VYKUPY chybí v test DB
        vykupy_map = {}
    servis_map = _servis_points_map_for_day(day) or {}
    excluded = get_leaderboard_excluded_prodejce_ids()

    points_map: dict[int, int] = {}
    for item in aggregation:
        pid = int(item['id_prodejce'])
        if pid in excluded:
            continue
        product_points, _ = _leaderboard_product_points(item, vykupy_map, pid)
        points_map[pid] = int(product_points) + int(servis_map.get(pid, 0) or 0)

    for uid, pts in servis_map.items():
        uid = int(uid)
        if uid in excluded or int(pts or 0) <= 0:
            continue
        points_map.setdefault(uid, int(pts))

    ranked = sorted(
        ((pid, pts) for pid, pts in points_map.items() if pts > 0),
        key=lambda x: -x[1],
    )[:limit]
    if not ranked:
        return []

    seller_ids = [pid for pid, _ in ranked]
    users = {
        u.id: u
        for u in _leaderboard_webuser_queryset().filter(id__in=seller_ids)
    }
    workplace = _leaderboard_dominant_stredisko_map(day_queryset, seller_ids)

    rows = []
    for pid, pts in ranked:
        user = users.get(pid)
        name = f'{user.jmeno} {user.prijmeni}'.strip() if user else f'#{pid}'
        rows.append({
            'id_prodejce': pid,
            'name': name,
            'points': pts,
            'prodejna': workplace.get(pid) or '',
        })
    return rows


def build_daily_report(report_day: date | None = None) -> dict:
    """Souhrn za jeden kalendářní den (výchozí: dnes v Europe/Prague)."""
    if report_day is None:
        report_day = timezone.localdate()

    qs = _day_queryset(report_day)
    agg = qs.aggregate(
        obrat_bez_dph=Sum(
            F('pocet_kusu') * F('cena_ks_bez_dph'),
            output_field=models.DecimalField(max_digits=15, decimal_places=2),
            default=0,
        ),
        obrat_s_dph=Sum(
            F('pocet_kusu') * F('cena_ks_vcl_dph'),
            default=0,
        ),
        zisk=Sum(
            F('pocet_kusu') * F('zisk'),
            output_field=models.DecimalField(max_digits=15, decimal_places=2),
            default=0,
        ),
        polozky=Count('id'),
        doklady=Count('doklad', distinct=True),
    )

    obrat_bez = float(agg['obrat_bez_dph'] or 0)
    zisk = float(agg['zisk'] or 0)
    marze_pct = round((zisk / obrat_bez) * 100, 1) if obrat_bez > 0 else 0.0

    stores = list(
        qs.exclude(stredisko__isnull=True)
        .exclude(stredisko='')
        .values('stredisko')
        .annotate(
            obrat=Sum(
                F('pocet_kusu') * F('cena_ks_bez_dph'),
                output_field=models.DecimalField(max_digits=15, decimal_places=2),
                default=0,
            ),
            doklady=Count('doklad', distinct=True),
        )
        .order_by('-obrat')[:6]
    )

    top_sellers = _top_sellers_by_leaderboard_points(report_day, limit=3)

    return {
        'day': report_day,
        'totals': {
            'obrat_bez_dph': obrat_bez,
            'obrat_s_dph': float(agg['obrat_s_dph'] or 0),
            'zisk': zisk,
            'polozky': int(agg['polozky'] or 0),
            'doklady': int(agg['doklady'] or 0),
            'marze_pct': marze_pct,
        },
        'stores': [
            {
                'name': row['stredisko'],
                'obrat': float(row['obrat'] or 0),
                'doklady': int(row['doklady'] or 0),
            }
            for row in stores
        ],
        'top_sellers': top_sellers,
    }


_CZ_WEEKDAYS = ('po', 'út', 'st', 'čt', 'pá', 'so', 'ne')


def format_daily_report_slack(report: dict) -> str:
    day: date = report['day']
    t = report['totals']
    day_label = f"{_CZ_WEEKDAYS[day.weekday()]} {day.day}. {day.month}. {day.year}"
    lines = [
        f"📊 *Denní report MOBILMAJAK* – {day_label}",
        '_Všechny částky bez DPH. Top prodejci = denní bodový žebříček (produkty + servis + výkupy)._',
        '',
        '*Celkem*',
        f"• Obrat: {_fmt_czk(t['obrat_bez_dph'])}",
        f"• Zisk: {_fmt_czk(t['zisk'])} (marže {_fmt_pct(t['marze_pct'])})",
        f"• Doklady: {t['doklady']} | Položky: {t['polozky']}",
    ]

    if report['stores']:
        lines.append('')
        lines.append('*Prodejny*')
        for store in report['stores']:
            lines.append(
                f"• {store['name']}: {_fmt_czk(store['obrat'])} ({store['doklady']} dokl.)"
            )

    if report['top_sellers']:
        lines.append('')
        lines.append('*Top prodejci* (denní body žebříčku)')
        for i, seller in enumerate(report['top_sellers'], 1):
            store = seller.get('prodejna') or ''
            store_bit = f" ({store})" if store else ''
            lines.append(
                f"{i}. {seller['name']}{store_bit} – {int(seller.get('points') or 0)} b"
            )

    if t['doklady'] == 0:
        lines.append('')
        lines.append('_Za tento den nejsou v datech žádné doklady._')

    return '\n'.join(lines)
