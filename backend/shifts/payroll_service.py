"""Výpočet payroll dat – hodiny, provize, mzda (body)."""
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from stores.models import Prodejna
from users.exclusions import real_sales_staff_queryset
from users.mzda_utils import (
    BRIGADNIK_VYPOMOC_BODY_ZA_HODINU,
    is_brigadnik,
    mzda_body_za_hodinu,
    mzda_cestovne_body,
    mzda_fixni_bez_cestovneho,
    mzda_fixni_body,
    mzda_fixni_mesicni_body,
    mzda_z_hodin_body_brigadnik,
    mzda_zaklad_pro_vicepraci,
    mzda_zaklad_raw,
    sum_mzda_doplnky,
)

from .labor_hours import fondu_hodin_mesic, prescas_hodin


def _body_whole(val):
    return Decimal(str(val or 0)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def _body_float(val):
    return float(_body_whole(val))


def provize_po_penalizaci(provize_brutto, pocet_penalizaci):
    """Každá penalizace = −10 % z hrubé provize (sčítá se)."""
    brutto = _body_whole(provize_brutto)
    if pocet_penalizaci <= 0:
        return brutto, Decimal('0'), 0
    procent = min(100, int(pocet_penalizaci) * 10)
    factor = (Decimal('100') - Decimal(str(procent))) / Decimal('100')
    netto = _body_whole(brutto * factor)
    return netto, brutto - netto, procent
from .models import MzdovaOdmenaMesic, MzdovaPenalizaceMesic, Smena
from .payroll_points_batch import (
    _empty_metrics,
    batch_dyska_for_month,
    batch_sales_metrics_for_month,
    batch_servis_points_for_month,
    build_points_payload_for_user,
)
from .vacation_service import (
    _mesic_pocita_deficit,
    dovolena_hodin_ze_smeny,
    is_dovolena_eligible,
)
from .czech_holidays import get_ceske_svatky


def _shift_hours(smena):
    if smena.typ_smeny == 'dovolena':
        return float(dovolena_hodin_ze_smeny(smena))
    cas_od_dt = datetime.combine(smena.datum, smena.cas_od)
    cas_do_dt = datetime.combine(smena.datum, smena.cas_do)
    if cas_do_dt < cas_od_dt:
        cas_do_dt += timedelta(days=1)
    return round((cas_do_dt - cas_od_dt).total_seconds() / 3600, 2)


def _subtract_months(rok, mesic, count):
    m = mesic - count
    y = rok
    while m <= 0:
        m += 12
        y -= 1
    return y, m


def _odpracovano_h_mesic(user_id, rok, mesic_cislo, prodejna_id=None):
    hours_map = aggregate_hours_by_user(rok, mesic_cislo, prodejna_id)
    return Decimal(str(hours_map.get(user_id, {}).get('odpracovano_h', 0)))


def _deficit_h_from_hours(uid, rok, mesic_cislo, hours_map, fondu_h):
    if not _mesic_pocita_deficit(rok, mesic_cislo) or fondu_h <= 0:
        return 0.0
    hours = hours_map.get(uid, {})
    odpracovano = float(hours.get('odpracovano_h', 0) or 0)
    dovolena = float(hours.get('dovolena_h', 0) or 0)
    return round(max(0.0, fondu_h - odpracovano - dovolena), 2)


def prumer_fixni_hodinove_body(user, rok, mesic_cislo, hours_cache=None):
    """
    Průměr fixní části (základ + doplňky) / odpracované hodiny za 3 předchozí měsíce.
    hours_cache: volitelně {(rok, mesic): hours_map} – vyhne se N× dotazům na směny.
    """
    if is_brigadnik(user) or not is_dovolena_eligible(user):
        return Decimal('0')

    total_fixni = Decimal('0')
    total_h = Decimal('0')
    for i in range(1, 4):
        y, m = _subtract_months(rok, mesic_cislo, i)
        if hours_cache is not None:
            hm = hours_cache.get((y, m), {})
            h = Decimal(str(hm.get(user.id, {}).get('odpracovano_h', 0)))
        else:
            h = _odpracovano_h_mesic(user.id, y, m)
        fixni = mzda_fixni_bez_cestovneho(user, float(h))
        total_fixni += fixni
        total_h += h

    if total_h > 0:
        return _body_whole(total_fixni / total_h)

    fond = Decimal(str(fondu_hodin_mesic(rok, mesic_cislo) or 0))
    zaklad = mzda_zaklad_raw(user)
    if fond > 0 and zaklad > 0:
        return _body_whole(zaklad / fond)
    return Decimal('0')


def prescas_body_vypocet(user, prescas_h, fondu_h):
    """Přesčas: (základ + variabilní doplňky z profilu) / fond × hodiny nad fondem. Bez cestovného."""
    if is_brigadnik(user) or not is_dovolena_eligible(user):
        return Decimal('0'), Decimal('0'), Decimal('0')
    h = Decimal(str(prescas_h or 0))
    if h <= 0:
        return Decimal('0'), Decimal('0'), Decimal('0')
    fond = Decimal(str(fondu_h or 0))
    if fond <= 0:
        return Decimal('0'), Decimal('0'), Decimal('0')
    zaklad_vp = mzda_zaklad_pro_vicepraci(user)
    sazba = _body_whole(zaklad_vp / fond)
    body = _body_whole(zaklad_vp * h / fond)
    return body, sazba, zaklad_vp


def dovolena_body_vypocet(user, dovolena_h, prumer_h):
    if is_brigadnik(user) or not is_dovolena_eligible(user):
        return Decimal('0')
    h = Decimal(str(dovolena_h or 0))
    if h <= 0 or prumer_h <= 0:
        return Decimal('0')
    return _body_whole(prumer_h * h)


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
                'vypomoc_h': 0,
                'prodejce_h': 0,
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
            if is_brigadnik(smena.user):
                rezim = (smena.brigadnik_rezim or 'prodejce').strip()
                if rezim == 'vypomoc':
                    result[uid]['vypomoc_h'] += hodiny
                else:
                    result[uid]['prodejce_h'] += hodiny
            if smena.datum in svatky_v_mesici:
                result[uid]['svatek_h'] += hodiny
    for uid in result:
        for key in result[uid]:
            result[uid][key] = round(result[uid][key], 2)
    return result


def build_payroll_row(user, rok, mesic_cislo, hours_map, mesic_date, prodejny_cache,
                      fondu_h, metrics_map, servis_map, odmeny_map, dyska_map=None,
                      penalizace_map=None, hours_cache=None):
    uid = user.id
    hours = hours_map.get(uid, {
        'odpracovano_h': 0,
        'vypomoc_h': 0,
        'prodejce_h': 0,
        'dovolena_h': 0,
        'nemoc_h': 0,
        'svatek_h': 0,
    })
    odpracovano = hours.get('odpracovano_h', 0)
    vypomoc_h = hours.get('vypomoc_h', 0)
    prodejce_h = hours.get('prodejce_h', 0)
    dovolena_h = hours.get('dovolena_h', 0)
    doplnky_sum, doplnky = sum_mzda_doplnky(user)
    cestovne = mzda_cestovne_body(user)
    if is_brigadnik(user):
        if vypomoc_h == 0 and prodejce_h == 0 and odpracovano > 0:
            prodejce_h = odpracovano
        zaklad = mzda_z_hodin_body_brigadnik(user, vypomoc_h, prodejce_h)
        sazba_h = float(mzda_body_za_hodinu(user))
        mzda_fixni = zaklad + doplnky_sum
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
    provize_raw = Decimal(str(points_payload.get('total_points') or 0))
    if is_brigadnik(user) and prodejce_h <= 0:
        provize_brutto = Decimal('0')
    else:
        provize_brutto = _body_whole(provize_raw)

    penalizace_rows = list((penalizace_map or {}).get(uid) or [])
    provize_body, penalizace_srazka, penalizace_procent = provize_po_penalizaci(
        provize_brutto, len(penalizace_rows),
    )

    prescas_h = prescas_hodin(odpracovano, fondu_h)
    deficit_h = _deficit_h_from_hours(uid, rok, mesic_cislo, hours_map, fondu_h) if is_dovolena_eligible(user) else 0.0
    prumer_fixni_h = prumer_fixni_hodinove_body(user, rok, mesic_cislo, hours_cache=hours_cache)
    dovolena_body = dovolena_body_vypocet(user, dovolena_h, prumer_fixni_h)
    prescas_body, prescas_sazba_h, zaklad_pro_vicepraci = prescas_body_vypocet(user, prescas_h, fondu_h)

    dyska_info = (dyska_map or {}).get(uid) or {'obrat': 0, 'kusy': 0}
    dyska_body = _body_whole(dyska_info.get('obrat') or 0)

    celkem_body = _body_whole(
        mzda_fixni + provize_body + odmena_mesic
        + dovolena_body + prescas_body + cestovne + dyska_body
    )

    breakdown = points_payload.get('breakdown') or {}
    ct300_item = breakdown.get('ct300') or {}
    ct300_count = int(ct300_item.get('count') or 0)

    stredisko = ''
    if user.prodejna_id:
        stredisko = prodejny_cache.get(user.prodejna_id, '')

    return {
        'user_id': uid,
        'jmeno': f'{user.jmeno} {user.prijmeni}'.strip(),
        'stredisko': stredisko,
        **hours,
        'fondu_h': fondu_h,
        'deficit_h': deficit_h,
        'prescas_h': prescas_h,
        'ct300_count': ct300_count,
        'role': user.role,
        'is_brigadnik': is_brigadnik(user),
        'vypomoc_h': vypomoc_h if is_brigadnik(user) else 0,
        'prodejce_h': prodejce_h if is_brigadnik(user) else 0,
        'body_za_hodinu': sazba_h,
        'body_vypomoc_za_hodinu': float(BRIGADNIK_VYPOMOC_BODY_ZA_HODINU) if is_brigadnik(user) else None,
        'zaklad_body': _body_float(zaklad),
        'doplnky': doplnky,
        'doplnky_body': _body_float(doplnky_sum),
        'cestovne_body': _body_float(cestovne),
        'mzda_fixni_body': _body_float(mzda_fixni),
        'prumer_fixni_h': _body_float(prumer_fixni_h),
        'dovolena_body': _body_float(dovolena_body),
        'prescas_body': _body_float(prescas_body),
        'prescas_sazba_h': _body_float(prescas_sazba_h),
        'zaklad_pro_vicepraci_body': _body_float(zaklad_pro_vicepraci),
        'dyska_body': _body_float(dyska_body),
        'dyska_kusy': int(dyska_info.get('kusy') or 0),
        'dyska_obrat': float(dyska_info.get('obrat') or 0),
        'provize_body_brutto': _body_float(provize_brutto),
        'provize_body': _body_float(provize_body),
        'penalizace_pocet': len(penalizace_rows),
        'penalizace_procent': penalizace_procent,
        'penalizace_srazka_body': _body_float(penalizace_srazka),
        'penalizace_popis': '; '.join((p.duvod or '').strip() for p in penalizace_rows if (p.duvod or '').strip()),
        'penalizace': [
            {'id': p.id, 'duvod': p.duvod or '', 'vytvoreno': p.vytvoreno.isoformat() if p.vytvoreno else None}
            for p in penalizace_rows
        ],
        'provize_breakdown': breakdown,
        'odmena_mesic_body': _body_float(odmena_mesic),
        'odmena_mesic_poznamka': odmena_poznamka,
        'celkem_body': _body_float(celkem_body),
    }


def build_payroll_preview(mesic_str, prodejna_id=None):
    rok, mesic_cislo = map(int, mesic_str.split('-'))
    mesic_date = date(rok, mesic_cislo, 1)
    ym = f'{rok}-{mesic_cislo:02d}'
    fondu_h = fondu_hodin_mesic(rok, mesic_cislo)

    prodejny_cache = {p.id: p.nazev for p in Prodejna.objects.all()}
    hours_map = aggregate_hours_by_user(rok, mesic_cislo, prodejna_id)
    hours_cache = {(rok, mesic_cislo): hours_map}
    for i in range(1, 4):
        y, m = _subtract_months(rok, mesic_cislo, i)
        hours_cache[(y, m)] = aggregate_hours_by_user(y, m, prodejna_id)

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
    dyska_map = batch_dyska_for_month(rok, mesic_cislo, user_ids)
    odmeny_map = {
        o.user_id: o
        for o in MzdovaOdmenaMesic.objects.filter(mesic=mesic_date, user_id__in=user_ids)
    }
    penalizace_map = {}
    for p in MzdovaPenalizaceMesic.objects.filter(mesic=mesic_date, user_id__in=user_ids).order_by('vytvoreno'):
        penalizace_map.setdefault(p.user_id, []).append(p)

    rows = []
    for user in users_list:
        rows.append(build_payroll_row(
            user, rok, mesic_cislo, hours_map, mesic_date, prodejny_cache,
            fondu_h, metrics_map, servis_map, odmeny_map, dyska_map, penalizace_map,
            hours_cache=hours_cache,
        ))

    celkem_bodu = int(round(sum(r.get('celkem_body', 0) for r in rows)))
    return {
        'mesic': mesic_str,
        'fondu_h': fondu_h,
        'celkem_bodu': celkem_bodu,
        'celkem_vyplata': celkem_bodu,
        'rows': rows,
    }
