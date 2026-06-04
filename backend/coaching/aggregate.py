"""
Agregace pro modul Coaching – sjednocuje prodej, plán, úkoly a benchmarky.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db import connection
from django.db.models import Count, Q
from django.utils import timezone as dj_tz

from analytics.polozky_aggregate import (
    PolozkyParams,
    aggregate_polozky_by_salesperson,
    aggregate_polozky_timeline,
    aggregate_tasks_workload,
)
from coaching.models import CoachingGoal
from plans.historie import KATEGORIE_PLANU
from plans.plneni import (
    _base_where_params,
    _kategorie_case_sql,
    kategorie_case_params,
    mesice_pred_planem,
)
from plans.servis_plneni import batch_servis_plneni_by_month
from plans.plneni_kontext import NAZVY_MESICU
from plans.models import KATEGORIE_CHOICES, PlanProdejceKategorie
from stores.models import Prodejna
from tasks.models import Ukol
from users.exclusions import real_sales_staff_queryset
from users.models import WebUser

KATEGORIE_NAZVY = dict(KATEGORIE_CHOICES)
# Plánovací kategorie bez nadřazeného PRISLUSENSTVI – prodej jde do podkategorií (Skla/Obaly/Ostatní)
COACHING_KATEGORIE_KODY = KATEGORIE_PLANU
PRISLUSENSTVI_PODKATEGORIE = (
    'PRISLUSENSTVI_SKLA', 'PRISLUSENSTVI_OBALY', 'PRISLUSENSTVI_OSTATNI',
)
CORE_BENCHMARK_METRICS = ('polozky_nad_100', 'sluzby_celkem', 'celkovy_obrat', 'unikatni_doklady')


def _parse_month(rok_mesic: str | None) -> tuple[int, int]:
    today = date.today()
    if not rok_mesic:
        return today.year, today.month
    try:
        y, m = rok_mesic.split('-')
        return int(y), int(m)
    except (ValueError, AttributeError):
        return today.year, today.month


def _iter_months(start: date, end: date):
    """Yield (rok, mesic) od start do end včetně (po měsících)."""
    y, m = start.year, start.month
    end_y, end_m = end.year, end.month
    while (y, m) <= (end_y, end_m):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def _build_kategorie_rows(skut: dict, plan_kat: dict) -> list[dict]:
    """Řádky kategorií – stejná logika jako modul Plány (bez prázdného rodiče Příslušenství)."""
    rows = []
    for kod in COACHING_KATEGORIE_KODY:
        sk = skut.get('kategorie', {}).get(kod, {})
        pk = plan_kat.get(kod, 0)
        kusy = sk.get('kusy', 0)
        rows.append({
            'kategorie_kod': kod,
            'nazev': KATEGORIE_NAZVY.get(kod, kod),
            'skutecne_kusy': kusy,
            'plan_kusy': pk,
            'plneni_procent': round(kusy / pk * 100, 1) if pk > 0 else None,
            'obrat': float(sk.get('obrat', 0)),
        })
    # Souhrn příslušenství (podkategorie) – informativní, bez vlastního plánu na rodiči
    p_kusy = sum(skut.get('kategorie', {}).get(k, {}).get('kusy', 0) for k in PRISLUSENSTVI_PODKATEGORIE)
    p_plan = sum(plan_kat.get(k, 0) for k in PRISLUSENSTVI_PODKATEGORIE)
    p_obrat = sum(
        float(skut.get('kategorie', {}).get(k, {}).get('obrat', 0) or 0)
        for k in PRISLUSENSTVI_PODKATEGORIE
    )
    rows.insert(2, {
        'kategorie_kod': 'PRISLUSENSTVI_SOUBR',
        'nazev': 'Příslušenství celkem',
        'skutecne_kusy': p_kusy,
        'plan_kusy': p_plan,
        'plneni_procent': round(p_kusy / p_plan * 100, 1) if p_plan > 0 else None,
        'obrat': p_obrat,
        'je_souhrn': True,
    })
    return rows


def _empty_skut() -> dict:
    return {'obrat': Decimal('0'), 'kategorie': {}}


def _accumulate_skut_row(target: dict, kod: str | None, obrat, kusy) -> None:
    if not kod:
        return
    obrat_val = Decimal(str(obrat)) if obrat else Decimal('0')
    kusy_val = int(kusy) if kusy is not None else 0
    target['obrat'] += obrat_val
    target['kategorie'][kod] = {'obrat': obrat_val, 'kusy': kusy_val}


def _batch_plneni_map_months(
    months: list[tuple[int, int]],
    user_ids: list[int],
) -> dict[tuple[int, int, int], dict]:
    """{(user_id, rok, mesic): skut} – jeden SQL dotaz pro všechny měsíce a prodejce."""
    if not user_ids or not months:
        return {}

    bounds = [_base_where_params(r, m) for r, m in months]
    start_d = min(b[0] for b in bounds)
    end_d = max(b[1] for b in bounds)
    month_set = set(months)
    case_sql = _kategorie_case_sql()
    placeholders = ','.join(['%s'] * len(user_ids))
    params = kategorie_case_params() + [start_d, end_d, *user_ids]
    sql = f"""
        SELECT ID_PRODEJCE, YEAR(Vystaveno) AS rok, MONTH(Vystaveno) AS mesic,
            {case_sql} AS kategorie_kod,
            SUM(COALESCE(NULLIF(Pocet_kusu, 0), 1) * COALESCE(Cena_ks_vcl_DPH, 0)) AS obrat,
            SUM(CASE WHEN COALESCE(Cena_ks_vcl_DPH, 0) >= 0
                THEN COALESCE(NULLIF(Pocet_kusu, 0), 1)
                ELSE -COALESCE(NULLIF(Pocet_kusu, 0), 1) END) AS kusy
        FROM WEB_PRODEJE_ALL
        WHERE Vystaveno >= %s AND Vystaveno < %s
        AND (Cena_ks_vcl_DPH > 14 OR Cena_ks_vcl_DPH < 0)
        AND KATEGORIE IS NOT NULL AND TRIM(COALESCE(KATEGORIE,'')) != ''
        AND COALESCE(KATEGORIE,'') != 'Nezařazeno'
        AND ID_PRODEJCE IN ({placeholders})
        GROUP BY ID_PRODEJCE, YEAR(Vystaveno), MONTH(Vystaveno), kategorie_kod
    """
    cache: dict[tuple[int, int, int], dict] = {}
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        for uid, rok, mesic, kod, obrat, kusy in cursor.fetchall():
            if (int(rok), int(mesic)) not in month_set:
                continue
            if kod == 'SERVIS':
                continue
            key = (int(uid), int(rok), int(mesic))
            if key not in cache:
                cache[key] = _empty_skut()
            _accumulate_skut_row(cache[key], kod, obrat, kusy)

    servis_map = batch_servis_plneni_by_month(start_d, end_d, user_ids=user_ids)
    for (uid, rok, mesic), servis_kusy in servis_map.items():
        if (rok, mesic) not in month_set:
            continue
        key = (uid, rok, mesic)
        if key not in cache:
            cache[key] = _empty_skut()
        _accumulate_skut_row(cache[key], 'SERVIS', 0, servis_kusy)
    return cache


def _batch_plan_map(
    months: list[tuple[int, int]],
    user_ids: list[int],
) -> dict[tuple[int, int, int], tuple[int, dict]]:
    """{(user_id, rok, mesic): (plan_kusy_celkem, plan_per_kat)} – jeden ORM dotaz."""
    if not user_ids or not months:
        return {}
    q = Q()
    for rok, mesic in months:
        q |= Q(
            plan_prodejce__plan_prodejna__plan_mesic__rok=rok,
            plan_prodejce__plan_prodejna__plan_mesic__mesic=mesic,
            plan_prodejce__plan_prodejna__plan_mesic__je_aktualni=True,
        )
    rows = PlanProdejceKategorie.objects.filter(
        q,
        plan_prodejce__uzivatel_id__in=user_ids,
    ).values(
        'plan_prodejce__uzivatel_id',
        'kategorie_kod',
        'pocet_kusu',
        'plan_prodejce__plan_prodejna__plan_mesic__rok',
        'plan_prodejce__plan_prodejna__plan_mesic__mesic',
    )
    per_key: dict[tuple[int, int, int], dict] = {}
    for row in rows:
        key = (
            row['plan_prodejce__uzivatel_id'],
            row['plan_prodejce__plan_prodejna__plan_mesic__rok'],
            row['plan_prodejce__plan_prodejna__plan_mesic__mesic'],
        )
        per_key.setdefault(key, {})
        kod = row['kategorie_kod']
        per_key[key][kod] = per_key[key].get(kod, 0) + (row['pocet_kusu'] or 0)
    result = {}
    for rok, mesic in months:
        for uid in user_ids:
            kat = per_key.get((uid, rok, mesic), {})
            result[(uid, rok, mesic)] = (sum(kat.values()), kat)
    return result


def _skut_kusy_celkem(skut: dict) -> int:
    return sum(k['kusy'] for k in skut.get('kategorie', {}).values())


def _category_kusy(skut: dict, kategorie_kod: str) -> int:
    if kategorie_kod == 'PRISLUSENSTVI_SOUBR':
        return sum(
            skut.get('kategorie', {}).get(k, {}).get('kusy', 0)
            for k in PRISLUSENSTVI_PODKATEGORIE
        )
    return skut.get('kategorie', {}).get(kategorie_kod, {}).get('kusy', 0)


def _compute_signaly(
    user_id: int,
    rok: int,
    mesic: int,
    skut_cache: dict,
    plan_cache: dict,
) -> dict:
    pcts = []
    kat_silne: dict[str, int] = {}
    kat_slabe: dict[str, int] = {}
    for r, m in mesice_pred_planem(rok, mesic, 3):
        skut = skut_cache.get((user_id, r, m), _empty_skut())
        plan_kusy, plan_kat = plan_cache.get((user_id, r, m), (0, {}))
        skut_kusy = _skut_kusy_celkem(skut)
        pct = round(skut_kusy / plan_kusy * 100, 1) if plan_kusy > 0 else None
        if pct is not None:
            pcts.append(pct)
        for kod, sk in skut.get('kategorie', {}).items():
            pk = plan_kat.get(kod, 0)
            pct_k = round(sk['kusy'] / pk * 100, 1) if pk > 0 else None
            if pct_k is not None:
                if pct_k >= 100:
                    kat_silne[kod] = kat_silne.get(kod, 0) + 1
                elif pct_k < 85:
                    kat_slabe[kod] = kat_slabe.get(kod, 0) + 1
    return {
        'systematicky_pod_planem': len(pcts) >= 3 and all(p < 85 for p in pcts),
        'silne_kategorie': [k for k, c in kat_silne.items() if c >= 2],
        'slabe_kategorie': [k for k, c in kat_slabe.items() if c >= 2],
    }


def _historie_from_cache(
    user_id: int,
    rok: int,
    mesic: int,
    skut_cache: dict,
    plan_cache: dict,
) -> dict:
    mesice = []
    pcts = []
    for r, m in mesice_pred_planem(rok, mesic, 3):
        skut = skut_cache.get((user_id, r, m), _empty_skut())
        plan_kusy, plan_kat = plan_cache.get((user_id, r, m), (0, {}))
        skut_kusy = _skut_kusy_celkem(skut)
        pct = round(skut_kusy / plan_kusy * 100, 1) if plan_kusy > 0 else None
        if pct is not None:
            pcts.append(pct)
        kat_detail = []
        for kod, sk in skut.get('kategorie', {}).items():
            pk = plan_kat.get(kod, 0)
            kat_detail.append({
                'kategorie_kod': kod,
                'plneni_procent': round(sk['kusy'] / pk * 100, 1) if pk > 0 else None,
                'skutecne_kusy': sk['kusy'],
                'plan_kusy': pk,
            })
        mesice.append({
            'rok': r,
            'mesic': m,
            'mesic_nazev': NAZVY_MESICU.get(m, ''),
            'plneni_procent_kusy': pct,
            'skutecne_kusy': skut_kusy,
            'plan_kusy': plan_kusy,
            'skutecny_obrat': round(float(skut.get('obrat', 0)), 2),
            'kategorie': kat_detail,
        })
    signaly = _compute_signaly(user_id, rok, mesic, skut_cache, plan_cache)
    return {
        'mesice': mesice,
        'signaly': signaly,
        'prumer_plneni_3m': round(sum(pcts) / len(pcts), 1) if pcts else None,
    }


def _benchmark_for_user(user_id: int, prodejna_id, rok: int, mesic: int, kanal: str) -> dict:
    if not prodejna_id:
        return {}
    params = _polozky_params_for_month(rok, mesic, prodejna_id, kanal)
    peer_sales = aggregate_polozky_by_salesperson(params, limit=500)
    bench_rows = [
        {
            'id': r['id_prodejce'],
            'prodejna_id': prodejna_id,
            'polozky_nad_100': r.get('polozky_nad_100', 0),
        }
        for r in peer_sales
    ]
    return _compute_benchmark(bench_rows, 'polozky_nad_100').get(user_id, {})


def _category_timeline_points(user_id: int, kategorie_kod: str, rok: int, mesic: int) -> list[dict]:
    """Měsíční kusy v kategorii – jeden batch dotaz místo N× plneni."""
    end_m = date(rok, mesic, 1)
    start_m = date(end_m.year - 1, end_m.month, 1)
    _, range_end = _month_date_range(rok, mesic)
    range_end = min(range_end, date.today())
    months = list(_iter_months(start_m, range_end))
    skut_cache = _batch_plneni_map_months(months, [user_id])
    return [
        {
            'month': f'{y:04d}-{m:02d}',
            'value': _category_kusy(skut_cache.get((user_id, y, m), _empty_skut()), kategorie_kod),
        }
        for y, m in months
    ]


def _month_date_range(rok: int, mesic: int) -> tuple[date, date]:
    start = date(rok, mesic, 1)
    if mesic == 12:
        end = date(rok + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(rok, mesic + 1, 1) - timedelta(days=1)
    return start, end


def _polozky_params_for_month(rok: int, mesic: int, prodejna_id=None, kanal='all') -> PolozkyParams:
    sd, ed = _month_date_range(rok, mesic)
    return PolozkyParams(
        period='custom',
        start_date=sd.isoformat(),
        end_date=ed.isoformat(),
        kanal=kanal,
        prodejna_id=str(prodejna_id) if prodejna_id else None,
        segment='vse',
        period_start=sd,
        period_end=ed,
    )


def _compute_benchmark(rows: list[dict], metric: str) -> dict[int, dict]:
    """Poradi, prumer, top per prodejna."""
    by_store: dict[int, list[tuple[int, float]]] = {}
    for row in rows:
        pid = row.get('prodejna_id')
        uid = row['id']
        val = float(row.get(metric) or 0)
        if pid:
            by_store.setdefault(pid, []).append((uid, val))

    result = {}
    for pid, items in by_store.items():
        if not items:
            continue
        sorted_items = sorted(items, key=lambda x: x[1], reverse=True)
        values = [v for _, v in sorted_items]
        avg = sum(values) / len(values) if values else 0
        top = max(values) if values else 0
        for rank, (uid, val) in enumerate(sorted_items, start=1):
            result[uid] = {
                'hodnota': val,
                'prumer_prodejny': round(avg, 2),
                'top_prodejce': top,
                'poradi': rank,
                'pocet_prodejcu': len(items),
                'vs_prumer_pct': round((val - avg) / avg * 100, 1) if avg else None,
                'vs_top_pct': round((val - top) / top * 100, 1) if top else None,
            }
    return result


def _staff_queryset(prodejna_id=None, store_ids=None):
    qs = real_sales_staff_queryset()
    if store_ids is not None:
        if not store_ids:
            return qs.none()
        qs = qs.filter(prodejna_id__in=store_ids)
    if prodejna_id:
        try:
            qs = qs.filter(prodejna_id=int(prodejna_id))
        except (TypeError, ValueError):
            pass
    return qs.order_by('prijmeni', 'jmeno')


def build_roster(rok: int, mesic: int, *, prodejna_id=None, kanal='all', store_ids=None) -> list[dict]:
    params = _polozky_params_for_month(rok, mesic, prodejna_id, kanal)
    sales_rows = aggregate_polozky_by_salesperson(params, limit=500)
    sales_by_id = {r['id_prodejce']: r for r in sales_rows}

    workload = aggregate_tasks_workload(params)
    workload_by_id = {p['id_prodejce']: p for p in workload.get('prodejci', [])}

    staff = list(_staff_queryset(prodejna_id, store_ids))
    user_ids = [u.id for u in staff]
    hist_months = mesice_pred_planem(rok, mesic, 3)
    all_months = hist_months + [(rok, mesic)]
    skut_cache = _batch_plneni_map_months(all_months, user_ids)
    plan_cache = _batch_plan_map(all_months, user_ids)

    prodejny_map = {p.id: p.nazev for p in Prodejna.objects.filter(aktivni=True)}
    goals_map = {
        g['prodejce_id']: g['cnt']
        for g in CoachingGoal.objects.filter(stav='otevreny').values('prodejce_id').annotate(cnt=Count('id'))
    }

    bench_rows = []
    roster = []
    for user in staff:
        uid = user.id
        sales = sales_by_id.get(uid, {})
        plan_kusy, _ = plan_cache.get((uid, rok, mesic), (0, {}))
        skut = skut_cache.get((uid, rok, mesic), _empty_skut())
        skut_kusy = _skut_kusy_celkem(skut)
        plneni_pct = round(skut_kusy / plan_kusy * 100, 1) if plan_kusy > 0 else None
        wl = workload_by_id.get(uid, {})

        bench_rows.append({
            'id': uid,
            'prodejna_id': user.prodejna_id,
            'polozky_nad_100': sales.get('polozky_nad_100', 0),
        })

        roster.append({
            'id': uid,
            'jmeno': user.jmeno,
            'prijmeni': user.prijmeni,
            'prodejce': f"{user.jmeno} {user.prijmeni}".strip(),
            'role': user.role,
            'prodejna_id': user.prodejna_id,
            'prodejna': prodejny_map.get(user.prodejna_id, ''),
            'polozky_nad_100': sales.get('polozky_nad_100', 0),
            'sluzby_celkem': sales.get('sluzby_celkem', 0),
            'celkovy_obrat': sales.get('celkovy_obrat', 0),
            'plneni_procent_kusy': plneni_pct,
            'plan_kusy': plan_kusy,
            'skutecne_kusy': skut_kusy,
            'signaly': _compute_signaly(uid, rok, mesic, skut_cache, plan_cache),
            'ukoly_hotovo': wl.get('pocet_ukolu_hotovo', 0),
            'index_vytizeni': wl.get('index_vytizeni'),
            'otevrene_cile': goals_map.get(uid, 0),
        })

    benchmark = _compute_benchmark(bench_rows, 'polozky_nad_100')
    for row in roster:
        row['benchmark'] = benchmark.get(row['id'], {})

    roster.sort(key=lambda r: r.get('polozky_nad_100', 0), reverse=True)
    return roster


def build_seller_profile(user_id: int, rok: int, mesic: int, *, kanal='all') -> dict:
    try:
        user = WebUser.objects.get(pk=user_id)
    except WebUser.DoesNotExist:
        return None

    params = _polozky_params_for_month(rok, mesic, user.prodejna_id, kanal)
    params.user_ids = [user_id]
    sales_rows = aggregate_polozky_by_salesperson(params, limit=1)
    sales = sales_rows[0] if sales_rows else {}

    hist_months = mesice_pred_planem(rok, mesic, 3)
    all_months = hist_months + [(rok, mesic)]
    skut_cache = _batch_plneni_map_months(all_months, [user_id])
    plan_cache = _batch_plan_map(all_months, [user_id])

    skut = skut_cache.get((user_id, rok, mesic), _empty_skut())
    plan_kusy, plan_kat = plan_cache.get((user_id, rok, mesic), (0, {}))
    skut_kusy = _skut_kusy_celkem(skut)
    historie = _historie_from_cache(user_id, rok, mesic, skut_cache, plan_cache)
    prodejny_map = {p.id: p.nazev for p in Prodejna.objects.filter(aktivni=True)}

    return {
        'prodejce': {
            'id': user.id,
            'jmeno': user.jmeno,
            'prijmeni': user.prijmeni,
            'role': user.role,
            'prodejna_id': user.prodejna_id,
            'prodejna': prodejny_map.get(user.prodejna_id, ''),
        },
        'obdobi': {'rok': rok, 'mesic': mesic},
        'prodej': sales,
        'plneni': {
            'plan_kusy': plan_kusy,
            'skutecne_kusy': skut_kusy,
            'plneni_procent_kusy': round(skut_kusy / plan_kusy * 100, 1) if plan_kusy > 0 else None,
            'obrat': float(skut.get('obrat', 0)),
        },
        'kategorie': _build_kategorie_rows(skut, plan_kat),
        'signaly': historie.get('signaly', {}),
        'historie_3m': historie.get('mesice', []),
        'benchmark': _benchmark_for_user(user_id, user.prodejna_id, rok, mesic, kanal),
    }


def build_seller_workload(user_id: int, rok: int, mesic: int, *, kanal='all') -> dict:
    try:
        user = WebUser.objects.get(pk=user_id)
    except WebUser.DoesNotExist:
        return {}
    params = _polozky_params_for_month(rok, mesic, user.prodejna_id, kanal)
    workload = aggregate_tasks_workload(params)
    wl = next((p for p in workload.get('prodejci', []) if p['id_prodejce'] == user_id), {})
    return {
        'sla': workload.get('sla', {}),
        'prodejce': wl,
        'poznamka_proxy': workload.get('poznamka_proxy'),
    }


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


def build_seller_tasks(user_id: int, rok: int, mesic: int) -> list[dict]:
    sd, ed = _month_date_range(rok, mesic)
    start_dt = _aware_datetime(datetime.combine(sd, datetime.min.time()))
    end_dt = _aware_datetime(datetime.combine(ed, datetime.max.time()))

    tasks = Ukol.objects.filter(
        id_prodejce_ukol=user_id,
        stav='hotovo',
        vytvoreno__gte=start_dt,
        vytvoreno__lte=end_dt,
    ).order_by('-dokonceno_v', '-upraveno')[:200]

    out = []
    for t in tasks:
        done_at = t.dokonceno_v or t.upraveno
        vcas = None
        deadline_dt = _task_deadline_datetime(t)
        if deadline_dt and done_at:
            vcas = done_at <= deadline_dt
        doba_h = None
        if done_at:
            doba_h = round((done_at - t.vytvoreno).total_seconds() / 3600, 2)
        out.append({
            'id': t.id,
            'ukol': t.ukol,
            'priorita': t.priorita,
            'deadline': t.deadline.isoformat() if t.deadline else None,
            'dokonceno_v': done_at.isoformat() if done_at else None,
            'vcas': vcas,
            'doba_hodin': doba_h,
        })
    return out


def build_timeline(
    user_id: int,
    metrics: list[str],
    rok: int,
    mesic: int,
    *,
    compare=None,
    prodejna_id=None,
    kanal='all',
) -> dict:
    end_m = date(rok, mesic, 1)
    start_m = date(end_m.year - 1, end_m.month, 1)
    _, range_end = _month_date_range(rok, mesic)
    range_end = min(range_end, date.today())

    compare_period = None
    if compare in ('prev_month', 'prev_quarter', 'prev_year'):
        compare_period = compare

    plan_kat_metrics = set(COACHING_KATEGORIE_KODY) | {'PRISLUSENSTVI_SOUBR'}
    series = {}
    for metric in metrics:
        if metric in plan_kat_metrics:
            series[metric] = _category_timeline_points(user_id, metric, rok, mesic)
        else:
            points = aggregate_polozky_timeline(
                user_id,
                metric,
                start_date=start_m,
                end_date=range_end,
                kanal=kanal,
                prodejna_id=str(prodejna_id) if prodejna_id else None,
                segment='vse',
                compare_period=compare_period,
            )
            series[metric] = points

    if compare in ('store_avg', 'store_top') and metrics:
        user = WebUser.objects.filter(pk=user_id).first()
        if user and user.prodejna_id:
            peer_params = PolozkyParams(
                period='custom',
                start_date=start_m.isoformat(),
                end_date=range_end.isoformat(),
                kanal=kanal,
                prodejna_id=str(user.prodejna_id),
                segment='vse',
                period_start=start_m,
                period_end=range_end,
            )
            peers = aggregate_polozky_by_salesperson(peer_params, limit=500)
            for metric in metrics:
                vals = [float(p.get(metric, 0) or 0) for p in peers if p.get('id_prodejce') != user_id]
                if not vals:
                    continue
                bench_val = sum(vals) / len(vals) if compare == 'store_avg' else max(vals)
                for pt in series.get(metric, []):
                    pt['compare_value'] = bench_val
                    pt['compare_month'] = 'prumer_prodejny' if compare == 'store_avg' else 'top_prodejce'

    return {'metrics': series, 'start_date': start_m.isoformat(), 'end_date': range_end.isoformat()}


def compare_sellers(user_a: int, user_b: int, rok: int, mesic: int, *, kanal='all') -> dict:
    users = {u.id: u for u in WebUser.objects.filter(pk__in=[user_a, user_b])}
    if user_a not in users or user_b not in users:
        return {'error': 'Prodejce nenalezen'}

    params = _polozky_params_for_month(rok, mesic, None, kanal)
    params.user_ids = [user_a, user_b]
    sales_rows = aggregate_polozky_by_salesperson(params, limit=2)
    sales_by_id = {r['id_prodejce']: r for r in sales_rows}

    skut_cache = _batch_plneni_map_months([(rok, mesic)], [user_a, user_b])
    plan_cache = _batch_plan_map([(rok, mesic)], [user_a, user_b])

    def _light_profile(uid):
        u = users[uid]
        skut = skut_cache.get((uid, rok, mesic), _empty_skut())
        plan_kusy, plan_kat = plan_cache.get((uid, rok, mesic), (0, {}))
        skut_kusy = _skut_kusy_celkem(skut)
        return {
            'prodejce': {
                'id': u.id,
                'jmeno': u.jmeno,
                'prijmeni': u.prijmeni,
            },
            'prodej': sales_by_id.get(uid, {}),
            'plneni': {
                'plan_kusy': plan_kusy,
                'skutecne_kusy': skut_kusy,
                'plneni_procent_kusy': round(skut_kusy / plan_kusy * 100, 1) if plan_kusy > 0 else None,
            },
            'kategorie': _build_kategorie_rows(skut, plan_kat),
        }

    pa = _light_profile(user_a)
    pb = _light_profile(user_b)

    metrics = [
        {'key': 'polozky_nad_100', 'label': 'Položky nad 100 Kč'},
        {'key': 'sluzby_celkem', 'label': 'Služby'},
        {'key': 'celkovy_obrat', 'label': 'Obrat'},
        {'key': 'unikatni_doklady', 'label': 'Účtenky'},
    ]
    rows = []
    for m in metrics:
        key = m['key']
        rows.append({
            'metric': key,
            'label': m['label'],
            'a': pa['prodej'].get(key, 0),
            'b': pb['prodej'].get(key, 0),
        })

    kat_rows = []
    kat_a = {k['kategorie_kod']: k for k in pa.get('kategorie', [])}
    kat_b = {k['kategorie_kod']: k for k in pb.get('kategorie', [])}
    for row in pa.get('kategorie', []):
        kod = row['kategorie_kod']
        kb = kat_b.get(kod, {})
        kat_rows.append({
            'kategorie_kod': kod,
            'nazev': row['nazev'],
            'a_kusy': row.get('skutecne_kusy', 0),
            'b_kusy': kb.get('skutecne_kusy', 0),
        })

    return {
        'prodejce_a': pa['prodejce'],
        'prodejce_b': pb['prodejce'],
        'metriky': rows,
        'kategorie': kat_rows,
        'plneni_a': pa.get('plneni'),
        'plneni_b': pb.get('plneni'),
    }
