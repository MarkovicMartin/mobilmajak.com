"""Denní souhrn prodejů pro Slack – agregace z WEB_PRODEJE_ALL."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db import models
from django.db.models import Count, F, Sum
from django.utils import timezone

from analytics.models import WebProdejeAll
from analytics.polozky_aggregate import PolozkyParams, aggregate_polozky_by_salesperson


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


def build_daily_report(report_day: date | None = None) -> dict:
    """Souhrn za jeden kalendářní den (výchozí: včera v Europe/Prague)."""
    if report_day is None:
        report_day = timezone.localdate() - timedelta(days=1)

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

    obrat_s = float(agg['obrat_s_dph'] or 0)
    zisk = float(agg['zisk'] or 0)
    marze_pct = round((zisk / obrat_s) * 100, 1) if obrat_s > 0 else 0.0

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

    params = PolozkyParams(
        start_date=report_day.isoformat(),
        end_date=report_day.isoformat(),
        period_start=report_day,
        period_end=report_day,
        metrics={'polozky_nad_100', 'celkovy_obrat'},
        include_profit=False,
    )
    sellers = aggregate_polozky_by_salesperson(params, limit=5)

    return {
        'day': report_day,
        'totals': {
            'obrat_bez_dph': float(agg['obrat_bez_dph'] or 0),
            'obrat_s_dph': obrat_s,
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
        'top_sellers': [
            {
                'name': row.get('prodejce') or f"#{row.get('id_prodejce')}",
                'polozky_nad_100': int(row.get('polozky_nad_100') or 0),
                'obrat': float(row.get('celkovy_obrat') or 0),
            }
            for row in sellers[:3]
        ],
    }


_CZ_WEEKDAYS = ('po', 'út', 'st', 'čt', 'pá', 'so', 'ne')


def format_daily_report_slack(report: dict) -> str:
    day: date = report['day']
    t = report['totals']
    day_label = f"{_CZ_WEEKDAYS[day.weekday()]} {day.day}. {day.month}. {day.year}"
    lines = [
        f"📊 *Denní report MOBILMAJAK* – {day_label}",
        '',
        '*Celkem*',
        f"• Obrat bez DPH: {_fmt_czk(t['obrat_bez_dph'])}",
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
        lines.append('*Top prodejci* (položky nad 100 Kč)')
        for i, seller in enumerate(report['top_sellers'], 1):
            lines.append(
                f"{i}. {seller['name']} – {seller['polozky_nad_100']} ks, "
                f"{_fmt_czk(seller['obrat'])}"
            )

    if t['doklady'] == 0:
        lines.append('')
        lines.append('_Za tento den nejsou v datech žádné doklady._')

    return '\n'.join(lines)
