"""Výpočet payroll dat – hodiny, provize, mzda (body)."""
from datetime import date, datetime, timedelta
from decimal import Decimal

from stores.models import Prodejna
from users.exclusions import real_sales_staff_queryset
from users.mzda_utils import (
    is_brigadnik,
    mzda_body_za_hodinu,
    mzda_fixni_body,
    mzda_fixni_mesicni_body,
    mzda_z_hodin_body,
    sum_mzda_doplnky,
)

from .labor_hours import fondu_hodin_mesic, prescas_hodin
from .models import MzdovaOdmenaMesic, Smena
from .payroll_points_batch import (
    _empty_metrics,
    batch_sales_metrics_for_month,
    batch_servis_points_for_month,
    build_points_payload_for_user,
)
from .views import get_ceske_svatky


def _shift_hours(smena):
    cas_od_dt = datetime.combine(smena.datum, smena.cas_od)
    cas_do_dt = datetime.combine(smena.datum, smena.cas_do)
    if cas_do_dt < cas_od_dt:
        cas_do_dt += timedelta(days=1)
    return round((cas_do_dt - cas_od_dt).total_seconds() / 3600, 2)


def aggregate_hours_by_user(rok, mesic_cislo, prodejna_id=None):
    """Agregace hodin ze směn – stejná logika jako export."""
    ceske_svatky = get_ceske_svatky(rok)
    svatky_v_mesici = set()
    for rok_s, mesic_s, den_s in ceske_svatky:
        if mesic_s == mesic_cislo:
            svatky_v_mesici.add(date(rok_s, mesic_s, den_s))

    smeny_qs = Smena.objects.filter(
        datum__year=rok,
        datum__month=mesic_cislo,
        aktivni=True,
    ).select_related('user', 'prodejna')
    if prodejna_id:
        try:
            pid = int(prodejna_id)
            smeny_qs = smeny_qs.filter(prodejna_id=pid)
        except (TypeError, ValueError):
            pass

    result = {}
    for smena in smeny_qs:
        uid = smena.user_id
        if uid not in result:
            result[uid] = {
                'odpracovano_h': 0,
                'dovolena_h': 0,
                'nemoc_h': 0,
                'svatek_h': 0,
            }
        hodiny = _shift_hours(smena)
        if smena.typ_smeny == 'dovolena':
            result[uid]['dovolena_h'] += hodiny
        elif smena.typ_smeny == 'nemoc':
            result[uid]['nemoc_h'] += hodiny
        elif smena.typ_smeny == 'prace':
            result[uid]['odpracovano_h'] += hodiny
            if smena.datum in svatky_v_mesici:
                result[uid]['svatek_h'] += hodiny
    for uid in result:
        for key in result[uid]:
            result[uid][key] = round(result[uid][key], 2)
    return result


def build_payroll_row(user, rok, mesic_cislo, hours_map, mesic_date, prodejny_cache,
                      fondu_h, metrics_map, servis_map, odmeny_map):
    uid = user.id
    hours = hours_map.get(uid, {
        'odpracovano_h': 0,
        'dovolena_h': 0,
        'nemoc_h': 0,
        'svatek_h': 0,
    })
    odpracovano = hours.get('odpracovano_h', 0)
    doplnky_sum, doplnky = sum_mzda_doplnky(user)
    if is_brigadnik(user):
        zaklad = mzda_z_hodin_body(user, odpracovano)
        sazba_h = float(mzda_body_za_hodinu(user))
    else:
        zaklad = mzda_fixni_mesicni_body(user)
        sazba_h = None
    mzda_fixni = mzda_fixni_body(user, odpracovano)

    odmena_row = odmeny_map.get(uid)
    if odmena_row:
        odmena_mesic = Decimal(str(odmena_row.castka))
        odmena_poznamka = odmena_row.poznamka or ''
    else:
        odmena_mesic = Decimal('0')
        odmena_poznamka = ''

    ym = f'{rok}-{mesic_cislo:02d}'
    metrics = metrics_map.get(uid) or _empty_metrics()
    servis_points, servis_data = servis_map.get(uid, (0, None))
    points_payload = build_points_payload_for_user(
        uid, metrics, servis_points, servis_data, f'{ym}-01',
    )
    provize_body = Decimal(str(points_payload.get('total_points') or 0))
    celkem_body = mzda_fixni + provize_body + odmena_mesic

    breakdown = points_payload.get('breakdown') or {}
    ct300_item = breakdown.get('ct300') or {}
    ct300_count = int(ct300_item.get('count') or 0)

    prescas_h = prescas_hodin(odpracovano, fondu_h)

    stredisko = ''
    if user.prodejna_id:
        stredisko = prodejny_cache.get(user.prodejna_id, '')

    return {
        'user_id': uid,
        'jmeno': f'{user.jmeno} {user.prijmeni}'.strip(),
        'stredisko': stredisko,
        **hours,
        'prescas_h': prescas_h,
        'ct300_count': ct300_count,
        'role': user.role,
        'is_brigadnik': is_brigadnik(user),
        'body_za_hodinu': sazba_h,
        'zaklad_body': float(zaklad),
        'doplnky': doplnky,
        'doplnky_body': float(doplnky_sum),
        'mzda_fixni_body': float(mzda_fixni),
        'provize_body': float(provize_body),
        'provize_breakdown': breakdown,
        'odmena_mesic_body': float(odmena_mesic),
        'odmena_mesic_poznamka': odmena_poznamka,
        'celkem_body': float(celkem_body),
    }


def build_payroll_preview(mesic_str, prodejna_id=None):
    rok, mesic_cislo = map(int, mesic_str.split('-'))
    mesic_date = date(rok, mesic_cislo, 1)
    ym = f'{rok}-{mesic_cislo:02d}'
    fondu_h = fondu_hodin_mesic(rok, mesic_cislo)

    prodejny_cache = {p.id: p.nazev for p in Prodejna.objects.all()}
    hours_map = aggregate_hours_by_user(rok, mesic_cislo, prodejna_id)

    users_qs = real_sales_staff_queryset().order_by('jmeno', 'prijmeni')
    users_list = []
    for user in users_qs:
        if prodejna_id:
            try:
                pid = int(prodejna_id)
                if user.prodejna_id != pid and user.id not in hours_map:
                    continue
            except (TypeError, ValueError):
                pass
        users_list.append(user)

    user_ids = [u.id for u in users_list]
    metrics_map = batch_sales_metrics_for_month(rok, mesic_cislo, user_ids)
    servis_map = batch_servis_points_for_month(users_list, ym)
    odmeny_map = {
        o.user_id: o
        for o in MzdovaOdmenaMesic.objects.filter(mesic=mesic_date, user_id__in=user_ids)
    }

    rows = []
    for user in users_list:
        rows.append(build_payroll_row(
            user, rok, mesic_cislo, hours_map, mesic_date, prodejny_cache,
            fondu_h, metrics_map, servis_map, odmeny_map,
        ))

    celkem_bodu = round(sum(r.get('celkem_body', 0) for r in rows), 2)
    return {
        'mesic': mesic_str,
        'fondu_h': fondu_h,
        'celkem_bodu': celkem_bodu,
        'celkem_vyplata': celkem_bodu,
        'rows': rows,
    }
