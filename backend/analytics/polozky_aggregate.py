"""
Agregace pro analytiku Položky (výkony prodejců) z WEB_PRODEJE_ALL.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Callable, Iterable, Optional

from dateutil.parser import parse as parse_dateutil
from django.utils import timezone as dj_tz
from django.db.models import (
    Case,
    CharField,
    Count,
    F,
    Max,
    Q,
    Sum,
    Value,
    When,
)
from analytics.models import WebProdejeAll, WebVykupy
from analytics.points_config import POINTS_METRIC_KEYS
from analytics.query_helpers import count_active_receipts_from_queryset as count_active_receipts
from analytics.receipt_metrics import (
    prumer_hodnota_uctenky,
    prumer_polozek_uctu,
    qualifying_polozka_q,
    sum_obrat_s_dph,
)
from analytics.sunshine_config import sunshine_kusy_sum, sunshine_row_q
from analytics.viceprace_config import (
    polozky_nad_100_q,
    viceprace_obrat_sum,
)
from shifts.models import Smena
from stores.models import Prodejna
from tasks.models import Ukol
from users.models import WebUser

# Metriky ve výchozí odpovědi (zpětná kompatibilita)
DEFAULT_METRICS = (
    'polozky_nad_100',
    'sluzby_celkem',
    'sunshine',
    'pol_dok',
    'prumer_polozek_uctu',
    'prumer_hodnota_uctenky',
    'celkovy_obrat',
    'polozky_nad_29',
    'unikatni_doklady',
    'ct300',
    'ct600',
    'ct1200',
    'akt',
    'zah250',
    'nap',
    'zah500',
    'kop250',
    'kop500',
    'pz1',
    'knz',
    'sklicka',
    'lepeni',
    'vykupy',
    'servis_provize',
    'servisni_prace',
    'viceprace_obrat',
)

PLAN_CATEGORY_METRICS = (
    'NOVE_TELEFONY',
    'BAZAROVE_TELEFONY',
    'PRISLUSENSTVI_SKLA',
    'PRISLUSENSTVI_OBALY',
    'PRISLUSENSTVI_OSTATNI',
    'SLUZBY',
    'SERVIS',
    'OSTATNI',
)

ALL_METRIC_KEYS = frozenset(DEFAULT_METRICS) | frozenset(POINTS_METRIC_KEYS) | frozenset(PLAN_CATEGORY_METRICS)


def _aware_datetime(dt: datetime) -> datetime:
    if dj_tz.is_naive(dt):
        return dj_tz.make_aware(dt)
    return dt


def _task_deadline_datetime(task) -> datetime | None:
    if not task.deadline:
        return None
    if task.deadline_cas is None:
        dt = datetime.combine(task.deadline, datetime.max.time().replace(microsecond=0))
    else:
        dt = datetime.combine(task.deadline, task.deadline_cas)
    return _aware_datetime(dt)


@dataclass
class PolozkyParams:
    period: str = 'custom'
    selected_month: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    data_type: str = 'daily'
    target_date: Optional[str] = None
    kanal: str = 'all'
    prodejna_id: Optional[str] = None
    segment: str = 'vse'
    user_ids: Optional[list[int]] = None
    metrics: Optional[set[str]] = None
    include_hours: bool = False
    period_start: Optional[date] = None
    period_end: Optional[date] = None


def _web_prodeje_shipping_exclude_q():
    return (
        Q(nazev__icontains='Zásilkovna') | Q(nazev__icontains='ZASILKOVNA') |
        Q(nazev__icontains='Zásielkovňa') | Q(nazev__icontains='ZASIELKOVNA') |
        Q(nazev__icontains='Balíkovna') | Q(nazev__icontains='BALIKOVNA') |
        Q(nazev__icontains='Osobní odběr') | Q(nazev__icontains='OSOBNI ODBER') |
        Q(nazev__icontains='Česká pošta') | Q(nazev__icontains='Ceska posta') |
        Q(nazev__icontains='Allegro doručení') | Q(nazev__icontains='Allegro doruceni')
    )


def _resolve_period(period, selected_month, start_date, end_date, data_type, target_date):
    """Vrátí (start_date, end_date) jako date pro filtr typ."""
    today = date.today()
    if period == 'monthly_select' and selected_month:
        try:
            year, month = selected_month.split('-')
            y, m = int(year), int(month)
            sd = date(y, m, 1)
            if m == 12:
                ed = date(y + 1, 1, 1) - timedelta(days=1)
            else:
                ed = date(y, m + 1, 1) - timedelta(days=1)
            return sd, ed
        except Exception:
            pass
    if target_date:
        if data_type == 'daily':
            parsed = parse_dateutil(target_date).date()
            return parsed, parsed
        ym = target_date[:7]
        y, m = map(int, ym.split('-'))
        sd = date(y, m, 1)
        if m == 12:
            ed = date(y + 1, 1, 1) - timedelta(days=1)
        else:
            ed = date(y, m + 1, 1) - timedelta(days=1)
        return sd, ed
    if start_date and end_date:
        try:
            sd = parse_dateutil(start_date).date() if isinstance(start_date, str) else start_date
            ed = parse_dateutil(end_date).date() if isinstance(end_date, str) else end_date
            return sd, ed
        except Exception:
            pass
    return today, today


def _apply_typ_date_filter(queryset, sd: date, ed: date):
    if sd == ed:
        return queryset.filter(typ=sd.strftime('%Y-%m-%d'))
    end_upper = (ed + timedelta(days=1)).strftime('%Y-%m-%d')
    return queryset.filter(typ__gte=sd.strftime('%Y-%m-%d'), typ__lt=end_upper)


def _apply_kanal_filter(queryset, kanal: str):
    if kanal == 'eshop':
        return (
            queryset.filter(marketingovy_kanal='e-shop')
            .filter(Q(objednavku_zalozil__isnull=True) | Q(objednavku_zalozil=''))
            .filter(Q(poznamka__isnull=True) | Q(poznamka=''))
            .exclude(dropshipping='Baselinker')
            .exclude(kategorie_1__icontains='!Servis')
            .exclude(Q(kategorie__isnull=True) | Q(kategorie='') | Q(kategorie__iexact='Nezařazeno'))
            .exclude(_web_prodeje_shipping_exclude_q())
        )
    if kanal == 'allegro':
        return (
            queryset.filter(dropshipping='Baselinker')
            .exclude(Q(kategorie__isnull=True) | Q(kategorie='') | Q(kategorie__iexact='Nezařazeno'))
            .exclude(_web_prodeje_shipping_exclude_q())
        )
    if kanal == 'servis':
        return queryset.filter(objednavku_zalozil__icontains='servis eda', k_servisu='ANO')
    if kanal == 'prodejna':
        return queryset.exclude(marketingovy_kanal='e-shop').exclude(
            dropshipping='Baselinker'
        ).exclude(Q(objednavku_zalozil__icontains='servis eda') & Q(k_servisu='ANO'))
    return queryset


def _plan_category_case():
    from plans.category_mapping import plan_category_case_orm

    return plan_category_case_orm()


def _segment_row_filter(segment: str) -> Q:
    """
    Filtr řádků prodeje podle segmentu prodejce.

    - vse: bez omezení
    - domaci: řádek na domovské prodejně (id_prodejny = prodejna uživatele)
    - docasni: brigádník (role BRIGADNIK) nebo host (prodej mimo domovskou prodejnu); OR obou podmínek
    - host / brigadnik: zpětná kompatibilita API (stejné jako dříve)
    """
    if not segment or segment == 'vse':
        return Q()

    if segment == 'brigadnik':
        ids = list(WebUser.objects.filter(role='BRIGADNIK').values_list('id', flat=True))
        return Q(id_prodejce__in=ids) if ids else Q(pk__in=[])

    home_pairs = list(
        WebUser.objects.exclude(prodejna_id__isnull=True).values_list('id', 'prodejna_id')
    )
    host_q = Q()
    if home_pairs:
        for uid, pid in home_pairs:
            host_q |= Q(id_prodejce=uid) & (~Q(id_prodejny=pid) | Q(id_prodejny__isnull=True))

    if segment == 'docasni':
        brig_ids = list(WebUser.objects.filter(role='BRIGADNIK').values_list('id', flat=True))
        brig_q = Q(id_prodejce__in=brig_ids) if brig_ids else Q(pk__in=[])
        if not home_pairs:
            return brig_q
        return host_q | brig_q

    if not home_pairs:
        return Q(pk__in=[]) if segment in ('domaci', 'host') else Q()

    domaci_q = Q()
    for uid, pid in home_pairs:
        domaci_q |= Q(id_prodejce=uid, id_prodejny=pid)

    if segment == 'domaci':
        return domaci_q
    if segment == 'host':
        return host_q
    return Q()


def parse_polozky_params(get_params) -> PolozkyParams:
    period = get_params.get('period', 'custom')
    selected_month = get_params.get('selected_month')
    start_date = get_params.get('start_date')
    end_date = get_params.get('end_date')
    data_type = get_params.get('type', 'daily')
    target_date = get_params.get('date')
    kanal = get_params.get('kanal', 'all')
    prodejna_id = get_params.get('prodejna_id') or None
    segment = get_params.get('segment', 'vse') or 'vse'
    include_hours = get_params.get('include_hours') in ('1', 'true', 'True')

    user_ids = None
    raw_users = get_params.get('user_ids', '')
    if raw_users:
        try:
            user_ids = [int(x.strip()) for x in raw_users.split(',') if x.strip()]
        except ValueError:
            user_ids = []

    metrics = None
    raw_metrics = get_params.get('metrics', '')
    if raw_metrics:
        metrics = {m.strip() for m in raw_metrics.split(',') if m.strip()}

    sd, ed = _resolve_period(period, selected_month, start_date, end_date, data_type, target_date)

    return PolozkyParams(
        period=period,
        selected_month=selected_month,
        start_date=start_date,
        end_date=end_date,
        data_type=data_type,
        target_date=target_date,
        kanal=kanal,
        prodejna_id=prodejna_id,
        segment=segment,
        user_ids=user_ids,
        metrics=metrics,
        include_hours=include_hours,
        period_start=sd,
        period_end=ed,
    )


def build_polozky_queryset(params: PolozkyParams):
    qs = WebProdejeAll.objects.all()
    qs = _apply_typ_date_filter(qs, params.period_start, params.period_end)
    qs = _apply_kanal_filter(qs, params.kanal)
    if params.prodejna_id:
        try:
            qs = qs.filter(id_prodejny=int(params.prodejna_id))
        except (TypeError, ValueError):
            pass
    qs = qs.filter(_segment_row_filter(params.segment))
    if params.user_ids:
        qs = qs.filter(id_prodejce__in=params.user_ids)
    return qs


def _shift_hours_for_range(user_ids: Iterable[int], sd: date, ed: date, prodejna_id=None) -> dict[int, float]:
    smeny = Smena.objects.filter(
        user_id__in=user_ids,
        datum__gte=sd,
        datum__lte=ed,
        aktivni=True,
        typ_smeny='prace',
    )
    if prodejna_id:
        try:
            smeny = smeny.filter(prodejna_id=int(prodejna_id))
        except (TypeError, ValueError):
            pass
    hours = {}
    for smena in smeny:
        cas_od_dt = datetime.combine(smena.datum, smena.cas_od)
        cas_do_dt = datetime.combine(smena.datum, smena.cas_do)
        if cas_do_dt < cas_od_dt:
            cas_do_dt += timedelta(days=1)
        h = round((cas_do_dt - cas_od_dt).total_seconds() / 3600, 2)
        hours[smena.user_id] = hours.get(smena.user_id, 0) + h
    return {k: round(v, 2) for k, v in hours.items()}


def _wanted_metrics(params: PolozkyParams) -> set[str]:
    if params.metrics:
        return params.metrics & ALL_METRIC_KEYS
    return set(DEFAULT_METRICS)


def _vykupy_map(params: PolozkyParams) -> dict:
    sd, ed = params.period_start, params.period_end
    vykupy_qs = WebVykupy.objects.all()
    if sd == ed:
        vykupy_qs = vykupy_qs.filter(vystaveno=sd.strftime('%Y-%m-%d'))
    else:
        end_upper = (ed + timedelta(days=1)).strftime('%Y-%m-%d')
        vykupy_qs = vykupy_qs.filter(
            vystaveno__gte=sd.strftime('%Y-%m-%d'),
            vystaveno__lt=end_upper,
        )
    if params.prodejna_id:
        try:
            vykupy_qs = vykupy_qs.filter(id_prodejny=int(params.prodejna_id))
        except (TypeError, ValueError):
            pass
    ag = vykupy_qs.values('id_prodejce').annotate(pocet_vykupu=Sum('pocet_kusů', default=0))
    return {v['id_prodejce']: v['pocet_vykupu'] for v in ag if v['id_prodejce'] is not None}


def polozky_servis_period_kwargs(params: PolozkyParams) -> dict:
    if params.period == 'monthly_select' and params.selected_month:
        return {'typ_month_prefix': params.selected_month}
    if params.target_date:
        if params.data_type == 'daily':
            return {'typ_exact': params.target_date}
        return {'typ_month_prefix': params.target_date[:7]}
    if params.start_date and params.end_date:
        return {
            'start_date': params.start_date,
            'end_date': params.end_date,
            'period': 'custom',
        }
    today = date.today()
    return {'typ_exact': today.strftime('%Y-%m-%d')}


def aggregate_polozky_by_salesperson(
    params: PolozkyParams,
    *,
    servis_loader: Optional[Callable] = None,
    limit: int = 20,
) -> list[dict]:
    """Hlavní agregace pro endpoint polozky/."""
    queryset = build_polozky_queryset(params)
    wanted = _wanted_metrics(params)

    # Zjednodušená agregace – vždy počítáme core sloupce (jako dříve)
    agregace = queryset.filter(id_prodejce__isnull=False).values('id_prodejce').annotate(
        polozky_nad_100=Sum('pocet_kusu', filter=polozky_nad_100_q(), default=0),
        viceprace_obrat=viceprace_obrat_sum(),
        ct300=Count('id', filter=Q(kod='P114194')),
        ct600=Count('id', filter=Q(kod='CT600')),
        ct1200=Count('id', filter=Q(kod='CT1200')),
        akt=Count('id', filter=Q(kod='AKT')),
        zah250=Count('id', filter=Q(kod='ZAH250')),
        nap=Count('id', filter=Q(kod__in=['NAP', 'NAN'])),
        zah500=Count('id', filter=Q(kod='ZAH500')),
        kop250=Count('id', filter=Q(kod='KOP250')),
        kop500=Count('id', filter=Q(kod='KOP500')),
        pz1=Count('id', filter=Q(kod='PZ1')),
        knz=Count('id', filter=Q(kod='KNZ')),
        sunshine=sunshine_kusy_sum(),
        sklicka=Count('id', filter=Q(kategorie_1='Skla a fólie')),
        lepeni=Count('id', filter=Q(kod='LOS')),
        polozky_nad_29=Count('id', filter=qualifying_polozka_q()),
        prvni_stredisko=Max('stredisko'),
    ).order_by('-polozky_nad_100')[:limit]

    prodejci_ids = [p['id_prodejce'] for p in agregace]
    if not prodejci_ids:
        return []

    prodejny_map = {p.id: p.nazev for p in Prodejna.objects.all()}
    users_dict = {u.id: u for u in WebUser.objects.filter(id__in=prodejci_ids)}
    vykupy_map = _vykupy_map(params) if 'vykupy' in wanted or not params.metrics else {}

    hours_map = {}
    if params.include_hours:
        hours_map = _shift_hours_for_range(
            prodejci_ids, params.period_start, params.period_end, params.prodejna_id
        )

    servis_kwargs = polozky_servis_period_kwargs(params)
    doklady_cache = {}
    for prodejce_id in prodejci_ids:
        doklady_cache[prodejce_id] = count_active_receipts(
            queryset.filter(id_prodejce=prodejce_id)
        )

    data_list = []
    for agg_data in agregace:
        prodejce_id = agg_data['id_prodejce']
        user = users_dict.get(prodejce_id)
        if user:
            prodejce_jmeno = f"{user.jmeno} {user.prijmeni}".strip()
            p_id = getattr(user, 'prodejna_id', None)
            prodejna_nazev = prodejny_map.get(p_id, str(p_id)) if p_id else 'Neznámá'
        else:
            prodejce_jmeno = f"Prodejce {prodejce_id}"
            prodejna_nazev = agg_data.get('prvni_stredisko', 'Neznámá')

        sluzby_celkem = (
            agg_data['ct300'] + agg_data['ct600'] + agg_data['ct1200'] +
            agg_data['akt'] + agg_data['zah250'] + agg_data['nap'] +
            agg_data['zah500'] + agg_data['kop250'] + agg_data['kop500'] +
            agg_data['pz1'] + agg_data['knz']
        )
        unikatni_doklady = doklady_cache.get(prodejce_id, 0)
        prodejce_qs = queryset.filter(id_prodejce=prodejce_id)
        celkovy_obrat = float(sum_obrat_s_dph(prodejce_qs))
        prumer_polozek = prumer_polozek_uctu(agg_data['polozky_nad_29'], unikatni_doklady)
        prumer_hodnota = prumer_hodnota_uctenky(celkovy_obrat, unikatni_doklady)

        servisni_prace = None
        servis_provize = 0
        if servis_loader and user:
            servis_data, _reason = servis_loader(user, **servis_kwargs)
            if servis_data:
                servisni_prace = servis_data
                servis_provize = int(round(servis_data.get('odmena') or 0))

        row = {
            'id_prodejce': prodejce_id,
            'prodejce': prodejce_jmeno,
            'prodejna': str(prodejna_nazev),
            'polozky_nad_100': agg_data['polozky_nad_100'],
            'sluzby_celkem': sluzby_celkem,
            'sunshine': agg_data['sunshine'],
            'pol_dok': prumer_polozek,
            'prumer_polozek_uctu': prumer_polozek,
            'prumer_hodnota_uctenky': prumer_hodnota,
            'celkovy_obrat': celkovy_obrat,
            'polozky_nad_29': agg_data['polozky_nad_29'],
            'unikatni_doklady': unikatni_doklady,
            'ct300': agg_data['ct300'],
            'ct600': agg_data['ct600'],
            'ct1200': agg_data['ct1200'],
            'akt': agg_data['akt'],
            'zah250': agg_data['zah250'],
            'nap': agg_data['nap'],
            'zah500': agg_data['zah500'],
            'kop250': agg_data['kop250'],
            'kop500': agg_data['kop500'],
            'pz1': agg_data['pz1'],
            'knz': agg_data['knz'],
            'sklicka': agg_data['sklicka'],
            'lepeni': agg_data['lepeni'],
            'vykupy': vykupy_map.get(prodejce_id, 0),
            'servis_provize': servis_provize,
            'servisni_prace': servisni_prace,
            'viceprace_obrat': round(float(agg_data.get('viceprace_obrat') or 0), 2),
            'aligator': 0,
        }

        if params.include_hours:
            hod = hours_map.get(prodejce_id)
            row['odpracovane_hodiny'] = hod if hod else None
            if hod and hod > 0:
                for key in ('polozky_nad_100', 'celkovy_obrat', 'unikatni_doklady'):
                    if key in row and row[key] is not None:
                        row[f'{key}_za_hodinu'] = round(float(row[key]) / hod, 2)
            else:
                for key in ('polozky_nad_100', 'celkovy_obrat', 'unikatni_doklady'):
                    row[f'{key}_za_hodinu'] = None

        if params.metrics:
            keep = wanted | {
                'id_prodejce', 'prodejce', 'prodejna', 'servisni_prace', 'servis_provize',
                'marze_vytvorena', 'marze_prodej', 'marze_servis',
                'vyplata_body', 'vynos_firmy', 'profit_payroll_month',
            }
            row = {
                k: v for k, v in row.items()
                if k in keep or k.endswith('_za_hodinu') or k == 'odpracovane_hodiny'
            }

        data_list.append(row)

    data_list.sort(key=lambda x: x.get('polozky_nad_100', 0), reverse=True)

    from analytics.profit_by_salesperson import attach_profit_fields
    return attach_profit_fields(data_list, queryset, params)


_COMPARE_MONTH_SHIFT = {
    'prev_month': 1,
    'prev_quarter': 3,
    'prev_year': 12,
}


def shift_month_ym(ym: str, months_delta: int) -> str:
    y, m = (int(x) for x in ym.split('-'))
    m += months_delta
    while m < 1:
        m += 12
        y -= 1
    while m > 12:
        m -= 12
        y += 1
    return f'{y:04d}-{m:02d}'


def _timeline_month_value(month_qs, metric: str):
    if metric == 'polozky_nad_100':
        return month_qs.filter(polozky_nad_100_q()).aggregate(
            t=Sum('pocet_kusu', default=0)
        )['t'] or 0
    if metric == 'unikatni_doklady':
        return count_active_receipts(month_qs)
    if metric == 'celkovy_obrat':
        return round(float(sum_obrat_s_dph(month_qs)), 2)
    if metric == 'sluzby_celkem':
        return (
            month_qs.filter(kod='P114194').count()
            + month_qs.filter(kod='CT600').count()
            + month_qs.filter(kod='CT1200').count()
            + month_qs.filter(kod='AKT').count()
            + month_qs.filter(kod='ZAH250').count()
            + month_qs.filter(kod__in=['NAP', 'NAN']).count()
            + month_qs.filter(kod='ZAH500').count()
            + month_qs.filter(kod='KOP250').count()
            + month_qs.filter(kod='KOP500').count()
            + month_qs.filter(kod='PZ1').count()
            + month_qs.filter(kod='KNZ').count()
        )
    if metric in PLAN_CATEGORY_METRICS:
        return month_qs.annotate(_cat=_plan_category_case()).filter(
            _cat=metric
        ).aggregate(t=Sum('pocet_kusu', default=0))['t'] or 0
    return month_qs.filter(kod__iexact=metric).count() if metric else 0


def aggregate_polozky_timeline(
    user_id: int,
    metric: str,
    *,
    rok: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    kanal: str = 'all',
    prodejna_id: Optional[str] = None,
    segment: str = 'vse',
    compare_period: Optional[str] = None,
) -> list[dict]:
    """Měsíční body pro jednoho prodejce; volitelně compare_value pro srovnávací období."""
    if rok:
        start_date = date(rok, 1, 1)
        end_date = date(rok, 12, 31)
    if not start_date or not end_date:
        today = date.today()
        start_date = date(today.year, 1, 1)
        end_date = today

    display_start = start_date
    display_end = end_date
    query_start = start_date
    query_end = end_date
    if compare_period in _COMPARE_MONTH_SHIFT:
        shift = _COMPARE_MONTH_SHIFT[compare_period]
        query_start_ym = shift_month_ym(
            f'{display_start.year:04d}-{display_start.month:02d}',
            -shift,
        )
        y0, m0 = (int(x) for x in query_start_ym.split('-'))
        query_start = date(y0, m0, 1)

    params = PolozkyParams(
        period='custom',
        start_date=query_start.isoformat(),
        end_date=query_end.isoformat(),
        kanal=kanal,
        prodejna_id=prodejna_id,
        segment=segment,
        period_start=query_start,
        period_end=query_end,
    )
    qs = build_polozky_queryset(params).filter(id_prodejce=user_id)

    months = []
    y, m = display_start.year, display_start.month
    while (y, m) <= (display_end.year, display_end.month):
        months.append(f'{y:04d}-{m:02d}')
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1

    points = []
    for ym in months:
        month_qs = qs.filter(typ__startswith=ym)
        points.append({
            'month': ym,
            'value': _timeline_month_value(month_qs, metric),
        })

    if compare_period in _COMPARE_MONTH_SHIFT:
        shift = _COMPARE_MONTH_SHIFT[compare_period]
        compare_cache: dict[str, object] = {}
        for p in points:
            cm = shift_month_ym(p['month'], -shift)
            if cm not in compare_cache:
                compare_cache[cm] = _timeline_month_value(
                    qs.filter(typ__startswith=cm),
                    metric,
                )
            p['compare_month'] = cm
            p['compare_value'] = compare_cache[cm]

    return points


def _receipts_in_window(user_id: int, start_dt, end_dt, prodejna_id=None) -> int:
    qs = WebProdejeAll.objects.filter(
        id_prodejce=user_id,
        typ__gte=start_dt.date().isoformat(),
        typ__lte=end_dt.date().isoformat(),
    )
    if prodejna_id:
        qs = qs.filter(id_prodejny=prodejna_id)
    return count_active_receipts(qs)


def aggregate_tasks_workload(params: PolozkyParams) -> dict:
    """
    SLA úkolů + index vytížení (unikátní doklady během úkolu vs průměr na prodejně).
    """
    sd, ed = params.period_start, params.period_end
    start_dt = _aware_datetime(datetime.combine(sd, datetime.min.time()))
    end_dt = _aware_datetime(datetime.combine(ed, datetime.max.time()))

    tasks_qs = Ukol.objects.filter(
        vytvoreno__gte=start_dt,
        vytvoreno__lte=end_dt,
    )
    if params.prodejna_id:
        try:
            tasks_qs = tasks_qs.filter(id_prodejny=int(params.prodejna_id))
        except (TypeError, ValueError):
            pass

    store_receipt_avg = {}
    sellers = {}

    completed = tasks_qs.filter(stav='hotovo')
    sla_seconds = []
    on_time = 0
    sla_total = 0

    for task in completed:
        done_at = task.dokonceno_v or task.upraveno
        if not done_at:
            continue
        delta = (done_at - task.vytvoreno).total_seconds()
        sla_seconds.append(delta)
        sla_total += 1
        deadline_dt = _task_deadline_datetime(task)
        if deadline_dt and done_at <= deadline_dt:
            on_time += 1

        uid = task.id_prodejce_ukol
        if uid not in sellers:
            sellers[uid] = {'indices': [], 'doklady_pri_ukolech': 0, 'pocet_ukolu': 0}
        sellers[uid]['pocet_ukolu'] += 1

        receipts = _receipts_in_window(uid, task.vytvoreno, done_at, task.id_prodejny)
        sellers[uid]['doklady_pri_ukolech'] += receipts

        store_id = task.id_prodejny
        if store_id:
            if store_id not in store_receipt_avg:
                store_receipt_avg[store_id] = []
            store_receipt_avg[store_id].append(receipts)

    # Průměr dokladů na prodejně v období (proxy obsluhy)
    store_period_avg = {}
    for store_id in store_receipt_avg:
        staff_ids = list(
            WebUser.objects.filter(prodejna_id=store_id).values_list('id', flat=True)
        )
        if not staff_ids:
            continue
        total = 0
        for sid in staff_ids:
            qs = build_polozky_queryset(params).filter(id_prodejce=sid)
            if store_id:
                qs = qs.filter(id_prodejny=store_id)
            total += count_active_receipts(qs)
        store_period_avg[store_id] = total / max(len(staff_ids), 1)

    per_seller = []
    users = {u.id: u for u in WebUser.objects.filter(id__in=sellers.keys())}
    for uid, info in sellers.items():
        avg_store = None
        user = users.get(uid)
        store_id = user.prodejna_id if user else None
        if store_id and store_id in store_period_avg and store_period_avg[store_id] > 0:
            avg_during = info['doklady_pri_ukolech'] / max(info['pocet_ukolu'], 1)
            index = round(avg_during / store_period_avg[store_id], 2)
        else:
            index = None
        u = users.get(uid)
        name = f"{u.jmeno} {u.prijmeni}".strip() if u else f"Prodejce {uid}"
        per_seller.append({
            'id_prodejce': uid,
            'prodejce': name,
            'pocet_ukolu_hotovo': info['pocet_ukolu'],
            'doklady_pri_ukolech': info['doklady_pri_ukolech'],
            'index_vytizeni': index,
        })

    avg_sla_h = None
    if sla_seconds:
        avg_sla_h = round(sum(sla_seconds) / len(sla_seconds) / 3600, 2)

    return {
        'sla': {
            'prumer_hodin_do_hotovo': avg_sla_h,
            'podil_vcas': round(on_time / sla_total, 2) if sla_total else None,
            'pocet_hotovo': sla_total,
        },
        'prodejci': sorted(per_seller, key=lambda x: x.get('index_vytizeni') or 0, reverse=True),
        'poznamka_proxy': (
            'Index vytížení: průměr unikátních dokladů během úkolu (vytvořeno → dokončeno) '
            'vs průměr dokladů na prodejně v období. Nejde o skutečný počet zákazníků.'
        ),
    }
