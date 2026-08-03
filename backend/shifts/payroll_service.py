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

from .labor_hours import fondu_hodin_mesic, prescas_hodin, svatky_v_mesici_set

POL_DOK_HRANI = Decimal('2')
POL_DOK_ODMENA_KC = Decimal('1000')


def _body_whole(val):
    return Decimal(str(val or 0)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def _body_float(val):
    return float(_body_whole(val))


def _sum_odmeny_from_map(rows):
    rows = list(rows or [])
    total = sum(Decimal(str(r.castka or 0)) for r in rows)
    return total, rows


def provize_po_penalizaci(provize_brutto, penalizace_rows):
    """
    Srážky z hrubé provize:
    - procenta: sčítají se (max 100 %), počítáno z brutto
    - fixni: odečtou se z výsledku po procentech (min. 0)
    """
    brutto = _body_whole(provize_brutto)
    rows = list(penalizace_rows or [])
    if not rows:
        return brutto, Decimal('0'), Decimal('0'), []

    total_procent = Decimal('0')
    fixed_sum = Decimal('0')
    detail = []

    for row in rows:
        typ = getattr(row, 'typ', None) or 'procenta'
        hodnota = Decimal(str(getattr(row, 'hodnota', None) or 10))
        if typ == 'fixni':
            fixed_sum += _body_whole(hodnota)
            detail.append({
                'typ': typ,
                'hodnota': float(hodnota),
                'duvod': (getattr(row, 'duvod', None) or '').strip(),
                'srazka_body': float(_body_whole(hodnota)),
            })
        else:
            pct = min(Decimal('100'), max(Decimal('0'), hodnota))
            total_procent += pct
            detail.append({
                'typ': typ,
                'hodnota': float(pct),
                'duvod': (getattr(row, 'duvod', None) or '').strip(),
                'srazka_body': float(_body_whole(brutto * pct / Decimal('100'))),
            })

    total_procent = min(total_procent, Decimal('100'))
    netto = _body_whole(brutto * (Decimal('100') - total_procent) / Decimal('100'))
    netto = max(Decimal('0'), netto - fixed_sum)
    srazka = brutto - netto
    return netto, srazka, total_procent, detail


from .models import MzdovaOdmenaMesic, MzdovaPenalizaceMesic, Smena
from .payroll_points_batch import (
    _empty_metrics,
    batch_dyska_for_month,
    batch_pol_dok_for_month,
    batch_sales_metrics_for_month,
    batch_servis_points_for_month,
    build_points_payload_for_user,
)
from .prumer_mzdy_override import prumer_override_for_user
from .vacation_service import (
    _mesic_pocita_deficit,
    dovolena_hodin_ze_smeny,
    is_dovolena_eligible,
    pocita_deficit_z_fondu,
)


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
    odpracovano_efekt = min(odpracovano, float(fondu_h))
    return round(max(0.0, float(fondu_h) - odpracovano_efekt), 2)


def _provize_detail_mesic(user, rok, mesic_cislo, prumer_cache=None):
    """
    Provize za měsíc pro průměr dovolené – netto po penalizaci (procenta i fixní srážky).
    prumer_cache: volitelně {(rok, mesic): {user_id: {provize_net, provize_brutto, penalizace_srazka}}}.
    """
    zero = {
        'provize_net': Decimal('0'),
        'provize_brutto': Decimal('0'),
        'penalizace_srazka': Decimal('0'),
    }
    if prumer_cache is not None:
        row = prumer_cache.get((rok, mesic_cislo), {}).get(user.id)
        if row is not None:
            return {
                'provize_net': Decimal(str(row.get('provize_net') or 0)),
                'provize_brutto': Decimal(str(row.get('provize_brutto') or 0)),
                'penalizace_srazka': Decimal(str(row.get('penalizace_srazka') or 0)),
            }
        return zero
    ym = f'{rok}-{mesic_cislo:02d}'
    mesic_date = date(rok, mesic_cislo, 1)
    metrics_map = batch_sales_metrics_for_month(rok, mesic_cislo, [user.id])
    servis_map = batch_servis_points_for_month([user], ym)
    penalizace_rows = list(
        MzdovaPenalizaceMesic.objects.filter(mesic=mesic_date, user_id=user.id).order_by('vytvoreno')
    )
    metrics = metrics_map.get(user.id) or _empty_metrics()
    servis_points, servis_data = servis_map.get(user.id, (0, None))
    points_payload = build_points_payload_for_user(
        user.id, metrics, servis_points, servis_data, f'{ym}-01',
    )
    provize_brutto = _body_whole(points_payload.get('total_points') or 0)
    provize_net, srazka, _, _ = provize_po_penalizaci(provize_brutto, penalizace_rows)
    return {
        'provize_net': provize_net,
        'provize_brutto': provize_brutto,
        'penalizace_srazka': srazka,
    }


def _provize_body_mesic(user, rok, mesic_cislo, provize_cache=None, prumer_cache=None):
    """Netto provize za měsíc – zpětná kompatibilita s provize_cache."""
    if provize_cache is not None and prumer_cache is None:
        cached = provize_cache.get((rok, mesic_cislo), {}).get(user.id)
        if cached is not None:
            return Decimal(str(cached or 0))
        return Decimal('0')
    return _provize_detail_mesic(user, rok, mesic_cislo, prumer_cache=prumer_cache)['provize_net']


def _odmena_mesic_pro_prumer(user, rok, mesic_cislo, prumer_cache=None):
    """Manuální měsíční odměna – započítává se celá (kladná i záporná)."""
    if prumer_cache is not None:
        row = prumer_cache.get((rok, mesic_cislo), {}).get(user.id)
        if row is not None:
            return Decimal(str(row.get('odmena_mesic') or 0))
        return Decimal('0')
    mesic_date = date(rok, mesic_cislo, 1)
    rows = MzdovaOdmenaMesic.objects.filter(mesic=mesic_date, user_id=user.id)
    return sum(Decimal(str(r.castka or 0)) for r in rows)


def _pol_dok_odmena_mesic(user, rok, mesic_cislo, prumer_cache=None):
    """Bonus/penalizace za průměr položek/účtenku – stejně jako ve výplatě."""
    if is_brigadnik(user):
        return Decimal('0')
    if prumer_cache is not None:
        row = prumer_cache.get((rok, mesic_cislo), {}).get(user.id)
        if row is not None:
            return Decimal(str(row.get('pol_dok_odmena') or 0))
        return Decimal('0')
    pol_map = batch_pol_dok_for_month(rok, mesic_cislo, [user.id])
    info = pol_map.get(user.id) or {'pol_dok': 0.0, 'unikatni_doklady': 0}
    return pol_dok_odmena_body(info.get('pol_dok'), info.get('unikatni_doklady'))


def _zaklad_pro_prumer_dovolene(user, h, override_row=None, rok=None, mesic_cislo=None):
    """Základ + doplňky poměrně za odpracované hodiny (bez cestovného)."""
    return _fixni_pro_prumer_mesic(user, h, override_row, rok=rok, mesic_cislo=mesic_cislo)


def _mzda_mesic_pro_prumer_dovolene(user, rok, mesic_cislo, h, override_row=None,
                                    provize_cache=None, prumer_cache=None):
    """
    Měsíční mzda pro průměr dovolené – stejné složky jako výplata kromě
    cestovného, dýška/víceprací (P63615), dovolené a přesčasu.
    """
    zaklad = _zaklad_pro_prumer_dovolene(user, h, override_row, rok=rok, mesic_cislo=mesic_cislo)
    provize = _provize_detail_mesic(user, rok, mesic_cislo, prumer_cache=prumer_cache)
    if prumer_cache is None and provize_cache is not None:
        provize_net = _provize_body_mesic(user, rok, mesic_cislo, provize_cache=provize_cache)
    else:
        provize_net = provize['provize_net']
    odmena = _odmena_mesic_pro_prumer(user, rok, mesic_cislo, prumer_cache=prumer_cache)
    pol_dok = _pol_dok_odmena_mesic(user, rok, mesic_cislo, prumer_cache=prumer_cache)
    mzda = zaklad + provize_net + odmena + pol_dok
    return {
        'mzda': mzda,
        'zaklad': zaklad,
        'provize': provize,
        'provize_net': provize_net,
        'odmena_mesic': odmena,
        'pol_dok_odmena': pol_dok,
    }


def build_provize_cache_for_prumer(user_ids, rok, ref_mesic):
    """{(rok, mesic): {user_id: provize_net}} – zpětná kompatibilita."""
    full = build_prumer_mzdy_cache_for_prumer(user_ids, rok, ref_mesic)
    return {
        key: {uid: row['provize_net'] for uid, row in month.items()}
        for key, month in full.items()
    }


def build_prumer_mzdy_cache_for_prumer(user_ids, rok, ref_mesic):
    """
    {(rok, mesic): {user_id: {provize_net, provize_brutto, penalizace_srazka,
    odmena_mesic, pol_dok_odmena}}} pro průměr dovolené za 3 měsíce před referencí.
    """
    cache = {}
    user_ids = list(user_ids)
    if not user_ids:
        return cache
    from users.models import WebUser
    users_by_id = {u.id: u for u in WebUser.objects.filter(id__in=user_ids)}
    for i in range(1, 4):
        y, m = _subtract_months(rok, ref_mesic, i)
        ym = f'{y}-{m:02d}'
        mesic_date = date(y, m, 1)
        users_list = [users_by_id[uid] for uid in user_ids if uid in users_by_id]
        metrics_map = batch_sales_metrics_for_month(y, m, user_ids)
        servis_map = batch_servis_points_for_month(users_list, ym)
        pol_dok_map = batch_pol_dok_for_month(y, m, user_ids)
        penalizace_map = {}
        for p in MzdovaPenalizaceMesic.objects.filter(mesic=mesic_date, user_id__in=user_ids).order_by('vytvoreno'):
            penalizace_map.setdefault(p.user_id, []).append(p)
        odmeny_map = {}
        for o in MzdovaOdmenaMesic.objects.filter(mesic=mesic_date, user_id__in=user_ids):
            odmeny_map.setdefault(o.user_id, []).append(o)
        month_data = {}
        for uid in user_ids:
            user = users_by_id.get(uid)
            if not user:
                continue
            metrics = metrics_map.get(uid) or _empty_metrics()
            servis_points, servis_data = servis_map.get(uid, (0, None))
            points_payload = build_points_payload_for_user(
                uid, metrics, servis_points, servis_data, f'{ym}-01',
            )
            provize_brutto = _body_whole(points_payload.get('total_points') or 0)
            provize_net, srazka, _, _ = provize_po_penalizaci(
                provize_brutto, penalizace_map.get(uid) or [],
            )
            odmena_mesic, _ = _sum_odmeny_from_map(odmeny_map.get(uid))
            pol_info = pol_dok_map.get(uid) or {'pol_dok': 0.0, 'unikatni_doklady': 0}
            if is_brigadnik(user):
                pol_dok_odmena = Decimal('0')
            else:
                pol_dok_odmena = pol_dok_odmena_body(
                    pol_info.get('pol_dok'), pol_info.get('unikatni_doklady'),
                )
            month_data[uid] = {
                'provize_net': provize_net,
                'provize_brutto': provize_brutto,
                'penalizace_srazka': srazka,
                'odmena_mesic': odmena_mesic,
                'pol_dok_odmena': pol_dok_odmena,
            }
        cache[(y, m)] = month_data
    return cache


def _fixni_pro_prumer_mesic(user, h, override_row=None, rok=None, mesic_cislo=None):
    """Fixní část pro průměr – poměrně za odpracované hodiny do fondu."""
    if override_row is not None and override_row.get('fixni_body') is not None:
        return Decimal(str(override_row['fixni_body']))
    if not is_brigadnik(user) and rok and mesic_cislo:
        fond = fondu_hodin_mesic(rok, mesic_cislo)
        return zaklad_pomerovy_body(user, h, fond)
    return mzda_fixni_bez_cestovneho(user, float(h))


def prumer_fixni_hodinove_body(user, rok, mesic_cislo, hours_cache=None, override_mesice=None):
    """
    Průměr fixní části (základ + doplňky) / odpracované hodiny za 3 předchozí měsíce.
    hours_cache: volitelně {(rok, mesic): hours_map} – vyhne se N× dotazům na směny.
    override_mesice: volitelně [{'rok', 'mesic', 'odpracovano_h', 'fixni_body'?}, ...].
    Bez fixni_body v override se fixní část bere z profilu uživatele.
    """
    return _prumer_hodinove_body(
        user, rok, mesic_cislo, hours_cache=hours_cache, override_mesice=override_mesice,
        vcetne_provize=False, provize_cache=None,
    )


def prumer_dovolena_hodinove_body(
    user, rok, mesic_cislo, hours_cache=None, provize_cache=None, prumer_cache=None,
    override_mesice=None,
):
    """
    Průměr výplaty/h za dovolenou: složky běžné výplaty / odpracované hodiny.
    Zahrnuje základ, provize vč. servisu (po penalizaci), odměny a položky/účtenku.
    Mimo: cestovné, dýško/vícepráce (P63615), dovolená, přesčas.
    """
    return _prumer_hodinove_body(
        user, rok, mesic_cislo, hours_cache=hours_cache, override_mesice=override_mesice,
        vcetne_provize=True, provize_cache=provize_cache, prumer_cache=prumer_cache,
    )


def _prumer_hodinove_body(
    user, rok, mesic_cislo, hours_cache=None, override_mesice=None,
    vcetne_provize=False, provize_cache=None, prumer_cache=None,
):
    if is_brigadnik(user) or not is_dovolena_eligible(user):
        return Decimal('0')

    total_mzda = Decimal('0')
    total_h = Decimal('0')
    if override_mesice:
        for row in override_mesice:
            y = int(row['rok'])
            m = int(row['mesic'])
            h = Decimal(str(row.get('odpracovano_h', 0)))
            if vcetne_provize:
                parts = _mzda_mesic_pro_prumer_dovolene(
                    user, y, m, h, row, provize_cache=provize_cache, prumer_cache=prumer_cache,
                )
                mzda = parts['mzda']
            else:
                mzda = _fixni_pro_prumer_mesic(user, h, row, rok=y, mesic_cislo=m)
            total_mzda += mzda
            total_h += h
    else:
        for i in range(1, 4):
            y, m = _subtract_months(rok, mesic_cislo, i)
            if hours_cache is not None:
                hm = hours_cache.get((y, m), {})
                h = Decimal(str(hm.get(user.id, {}).get('odpracovano_h', 0)))
            else:
                h = _odpracovano_h_mesic(user.id, y, m)
            if vcetne_provize:
                parts = _mzda_mesic_pro_prumer_dovolene(
                    user, y, m, h, None, provize_cache=provize_cache, prumer_cache=prumer_cache,
                )
                mzda = parts['mzda']
            else:
                mzda = _fixni_pro_prumer_mesic(user, h, None, rok=y, mesic_cislo=m)
            total_mzda += mzda
            total_h += h

    if total_h > 0:
        return _body_whole(total_mzda / total_h)

    fond = Decimal(str(fondu_hodin_mesic(rok, mesic_cislo) or 0))
    zaklad_vp = mzda_zaklad_pro_vicepraci(user)
    if fond > 0 and zaklad_vp > 0:
        return _body_whole(zaklad_vp / fond)
    return Decimal('0')


def prumer_fixni_hodinove_detail(user, rok, mesic_cislo, hours_cache=None, override_mesice=None):
    """Rozpad průměru za 3 předchozí měsíce – hodiny, fixní body, sazba/h."""
    return _prumer_hodinove_detail(
        user, rok, mesic_cislo, hours_cache=hours_cache, override_mesice=override_mesice,
        vcetne_provize=False, provize_cache=None,
    )


def prumer_dovolena_hodinove_detail(
    user, rok, mesic_cislo, hours_cache=None, provize_cache=None, prumer_cache=None,
    override_mesice=None,
):
    """Rozpad průměru dovolené – složky běžné výplaty bez cestovného a dýška."""
    return _prumer_hodinove_detail(
        user, rok, mesic_cislo, hours_cache=hours_cache, override_mesice=override_mesice,
        vcetne_provize=True, provize_cache=provize_cache, prumer_cache=prumer_cache,
    )


def _prumer_hodinove_detail(
    user, rok, mesic_cislo, hours_cache=None, override_mesice=None,
    vcetne_provize=False, provize_cache=None, prumer_cache=None,
):
    if is_brigadnik(user) or not is_dovolena_eligible(user):
        return {
            'mesice': [], 'celkem_h': 0.0, 'celkem_fixni': 0.0,
            'celkem_provize': 0.0, 'celkem_penalizace': 0.0,
            'celkem_odmena': 0.0, 'celkem_pol_dok': 0.0,
            'celkem_ponizeni': 0.0, 'celkem_mzda': 0.0, 'prumer_fixni_h': 0.0,
        }

    mesice = []
    total_zaklad = Decimal('0')
    total_provize = Decimal('0')
    total_penalizace = Decimal('0')
    total_odmena = Decimal('0')
    total_pol_dok = Decimal('0')
    total_h = Decimal('0')

    if override_mesice:
        rows = [(int(r['rok']), int(r['mesic']), r) for r in override_mesice]
    else:
        rows = []
        for i in range(1, 4):
            y, m = _subtract_months(rok, mesic_cislo, i)
            rows.append((y, m, None))

    for y, m, override_row in rows:
        if override_row is not None:
            h = Decimal(str(override_row.get('odpracovano_h', 0)))
            if hours_cache is not None:
                hm = hours_cache.get((y, m), {})
                h_smeny = Decimal(str(hm.get(user.id, {}).get('odpracovano_h', 0)))
            else:
                h_smeny = _odpracovano_h_mesic(user.id, y, m)
        else:
            if hours_cache is not None:
                hm = hours_cache.get((y, m), {})
                h = Decimal(str(hm.get(user.id, {}).get('odpracovano_h', 0)))
            else:
                h = _odpracovano_h_mesic(user.id, y, m)
            h_smeny = h
        if vcetne_provize:
            parts = _mzda_mesic_pro_prumer_dovolene(
                user, y, m, h, override_row, provize_cache=provize_cache, prumer_cache=prumer_cache,
            )
            mzda = parts['mzda']
            zaklad = parts['zaklad']
            provize_detail = parts['provize']
            provize_net = parts['provize_net']
            odmena = parts['odmena_mesic']
            pol_dok = parts['pol_dok_odmena']
            penalizace = provize_detail['penalizace_srazka']
            provize_brutto = provize_detail['provize_brutto']
        else:
            zaklad = _fixni_pro_prumer_mesic(user, h, override_row, rok=y, mesic_cislo=m)
            provize_net = Decimal('0')
            penalizace = Decimal('0')
            odmena = Decimal('0')
            pol_dok = Decimal('0')
            mzda = zaklad
            provize_brutto = Decimal('0')
        sazba = _body_whole(mzda / h) if h > 0 else Decimal('0')
        total_zaklad += zaklad
        total_provize += provize_net
        total_penalizace += penalizace
        total_odmena += odmena
        total_pol_dok += pol_dok
        total_h += h
        row_out = {
            'rok': y,
            'mesic': m,
            'odpracovano_h': float(h),
            'fixni_body': float(zaklad),
            'zaklad_body': float(zaklad),
            'provize_body': float(provize_net),
            'provize_brutto_body': float(provize_brutto),
            'penalizace_srazka_body': float(penalizace),
            'odmena_mesic_body': float(odmena),
            'pol_dok_odmena_body': float(pol_dok),
            'ponizeni_manual_body': float(min(Decimal('0'), odmena)),
            'mzda_body': float(mzda),
            'sazba_h': float(sazba),
        }
        if override_row is not None:
            row_out['odpracovano_h_smeny'] = float(h_smeny)
            row_out['hodiny_rozdil_h'] = round(float(h - h_smeny), 2)
        mesice.append(row_out)

    prumer_fn = prumer_dovolena_hodinove_body if vcetne_provize else prumer_fixni_hodinove_body
    prumer_kwargs = {'provize_cache': provize_cache, 'prumer_cache': prumer_cache} if vcetne_provize else {}
    prumer = prumer_fn(
        user, rok, mesic_cislo, hours_cache=hours_cache, override_mesice=override_mesice,
        **prumer_kwargs,
    )
    zdroj = 'prumer_3m'
    fallback_zaklad = None
    fallback_fond = None
    if override_mesice:
        zdroj = 'override_excel'
    elif total_h <= 0:
        fond_fb = Decimal(str(fondu_hodin_mesic(rok, mesic_cislo) or 0))
        zaklad_fb = mzda_zaklad_pro_vicepraci(user)
        if fond_fb > 0 and zaklad_fb > 0:
            zdroj = 'fallback_zaklad_fond'
            fallback_zaklad = float(zaklad_fb)
            fallback_fond = float(fond_fb)
    return {
        'mesice': mesice,
        'celkem_h': float(total_h),
        'celkem_fixni': float(total_zaklad),
        'celkem_provize': float(total_provize),
        'celkem_penalizace': float(total_penalizace),
        'celkem_odmena': float(total_odmena),
        'celkem_pol_dok': float(total_pol_dok),
        'celkem_ponizeni': float(min(Decimal('0'), total_odmena)),
        'celkem_mzda': float(total_zaklad + total_provize + total_odmena + total_pol_dok),
        'prumer_fixni_h': float(prumer),
        'prumer_h': float(prumer),
        'zdroj': zdroj,
        'fallback_zaklad_body': fallback_zaklad,
        'fallback_fond_h': fallback_fond,
    }


def zaklad_pomerovy_body(user, odpracovano_h, fondu_h):
    """
    Základ + doplňky poměrně za odpracované hodiny do fondu (Excel).
    Hodiny nad fond se počítají zvlášť jako přesčas.
    """
    if is_brigadnik(user):
        return mzda_fixni_bez_cestovneho(user, float(odpracovano_h or 0))
    zaklad_vp = mzda_zaklad_pro_vicepraci(user)
    h = Decimal(str(odpracovano_h or 0))
    fond = Decimal(str(fondu_h or 0))
    if fond <= 0 or h <= 0:
        return Decimal('0')
    h_do_fondu = min(h, fond)
    return _body_whole(zaklad_vp * h_do_fondu / fond)


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


def pol_dok_odmena_body(pol_dok, unikatni_doklady):
    """
    Bonus/penalizace za průměr položek/účtenku v měsíci.
    > 2 → +1000 Kč, < 2 → −1000 Kč, přesně 2 nebo bez účtenek → 0.
    """
    if not unikatni_doklady or int(unikatni_doklady) <= 0:
        return Decimal('0')
    avg = Decimal(str(pol_dok or 0))
    if avg > POL_DOK_HRANI:
        return POL_DOK_ODMENA_KC
    if avg < POL_DOK_HRANI:
        return -POL_DOK_ODMENA_KC
    return Decimal('0')


def aggregate_hours_by_user(rok, mesic_cislo, prodejna_id=None):
    """Agregace hodin ze směn – stejná logika jako export.

    Pracovní směny ve státní svátek se do odpracovaných (i brigádnických)
    hodin počítají 2×. Sloupec svatek_h drží reálné hodiny na svátku (1×).
    """
    svatky_v_mesici = svatky_v_mesici_set(rok, mesic_cislo)

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
            je_svatek = smena.datum in svatky_v_mesici
            hodiny_ucetni = hodiny * 2 if je_svatek else hodiny
            result[uid]['odpracovano_h'] += hodiny_ucetni
            if is_brigadnik(smena.user):
                rezim = (smena.brigadnik_rezim or 'prodejce').strip()
                if rezim == 'vypomoc':
                    result[uid]['vypomoc_h'] += hodiny_ucetni
                else:
                    result[uid]['prodejce_h'] += hodiny_ucetni
            if je_svatek:
                result[uid]['svatek_h'] += hodiny
    for uid in result:
        for key in result[uid]:
            result[uid][key] = round(result[uid][key], 2)
    return result


def build_payroll_row(user, rok, mesic_cislo, hours_map, mesic_date, prodejny_cache,
                      fondu_h, metrics_map, servis_map, odmeny_map, dyska_map=None,
                      penalizace_map=None, hours_cache=None, pol_dok_map=None,
                      provize_cache=None, prumer_cache=None):
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
    dovolena_smeny_h = hours.get('dovolena_h', 0)
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
        mzda_fixni = zaklad_pomerovy_body(user, odpracovano, fondu_h)

    odmena_mesic, odmeny_rows = _sum_odmeny_from_map(odmeny_map.get(uid))
    odmena_poznamka = '; '.join(
        (o.poznamka or '').strip() for o in odmeny_rows if (o.poznamka or '').strip()
    )

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
    provize_body, penalizace_srazka, penalizace_procent, penalizace_detail = provize_po_penalizaci(
        provize_brutto, penalizace_rows,
    )
    penalizace_fixni = sum(
        float(d.get('srazka_body') or 0)
        for d in penalizace_detail
        if d.get('typ') == 'fixni'
    )

    prescas_h = prescas_hodin(odpracovano, fondu_h)
    deficit_h = _deficit_h_from_hours(uid, rok, mesic_cislo, hours_map, fondu_h) if is_dovolena_eligible(user) else 0.0
    if pocita_deficit_z_fondu(user) and _mesic_pocita_deficit(rok, mesic_cislo):
        dovolena_h = deficit_h
    else:
        dovolena_h = dovolena_smeny_h
    override_mesice = prumer_override_for_user(user)
    prumer_dovolena_detail = prumer_dovolena_hodinove_detail(
        user, rok, mesic_cislo, hours_cache=hours_cache, prumer_cache=prumer_cache,
        override_mesice=override_mesice,
    )
    prumer_dovolena_h = Decimal(str(prumer_dovolena_detail.get('prumer_h', 0)))
    dovolena_body = dovolena_body_vypocet(user, dovolena_h, prumer_dovolena_h)
    prescas_body, prescas_sazba_h, zaklad_pro_vicepraci = prescas_body_vypocet(user, prescas_h, fondu_h)

    dyska_info = (dyska_map or {}).get(uid) or {'obrat': 0, 'kusy': 0}
    dyska_body = _body_whole(dyska_info.get('obrat') or 0)

    pol_dok_info = (pol_dok_map or {}).get(uid) or {'pol_dok': 0.0, 'unikatni_doklady': 0}
    pol_dok = float(pol_dok_info.get('pol_dok') or 0)
    pol_dok_unikatni = int(pol_dok_info.get('unikatni_doklady') or 0)
    if is_brigadnik(user):
        pol_dok_odmena = Decimal('0')
    else:
        pol_dok_odmena = pol_dok_odmena_body(pol_dok, pol_dok_unikatni)

    celkem_body = _body_whole(
        mzda_fixni + provize_body + odmena_mesic
        + dovolena_body + prescas_body + cestovne + dyska_body + pol_dok_odmena
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
        **{k: v for k, v in hours.items() if k != 'dovolena_h'},
        'dovolena_smeny_h': dovolena_smeny_h,
        'dovolena_h': dovolena_h,
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
        'prumer_fixni_h': _body_float(prumer_dovolena_h),
        'prumer_dovolena_h': _body_float(prumer_dovolena_h),
        'prumer_dovolena_detail': prumer_dovolena_detail,
        'dovolena_body': _body_float(dovolena_body),
        'prescas_body': _body_float(prescas_body),
        'prescas_sazba_h': _body_float(prescas_sazba_h),
        'zaklad_pro_vicepraci_body': _body_float(zaklad_pro_vicepraci),
        'dyska_body': _body_float(dyska_body),
        'dyska_kusy': int(dyska_info.get('kusy') or 0),
        'dyska_obrat': float(dyska_info.get('obrat') or 0),
        'pol_dok': pol_dok,
        'pol_dok_unikatni_doklady': pol_dok_unikatni,
        'pol_dok_odmena_body': _body_float(pol_dok_odmena),
        'provize_body_brutto': _body_float(provize_brutto),
        'provize_body': _body_float(provize_body),
        'penalizace_pocet': len(penalizace_rows),
        'penalizace_procent': float(penalizace_procent),
        'penalizace_fixni_body': penalizace_fixni,
        'penalizace_srazka_body': _body_float(penalizace_srazka),
        'penalizace_popis': '; '.join((p.duvod or '').strip() for p in penalizace_rows if (p.duvod or '').strip()),
        'penalizace': [
            {
                'id': p.id,
                'duvod': p.duvod or '',
                'typ': p.typ or MzdovaPenalizaceMesic.TYP_PROCENTA,
                'hodnota': float(p.hodnota or 0),
                'srazka_body': float((penalizace_detail[i] or {}).get('srazka_body') or 0),
                'vytvoreno': p.vytvoreno.isoformat() if p.vytvoreno else None,
                'vytvoril_jmeno': (
                    f'{p.vytvoril.jmeno} {p.vytvoril.prijmeni}'.strip()
                    if p.vytvoril_id else None
                ),
            }
            for i, p in enumerate(penalizace_rows)
        ],
        'provize_breakdown': breakdown,
        'odmena_mesic_body': _body_float(odmena_mesic),
        'odmena_mesic_poznamka': odmena_poznamka,
        'odmeny': [
            {
                'id': o.id,
                'castka': float(o.castka or 0),
                'poznamka': o.poznamka or '',
                'vytvoreno': o.vytvoreno.isoformat() if o.vytvoreno else None,
                'vytvoril_jmeno': (
                    f'{o.vytvoril.jmeno} {o.vytvoril.prijmeni}'.strip()
                    if getattr(o, 'vytvoril_id', None) else None
                ),
            }
            for o in odmeny_rows
        ],
        'celkem_body': _body_float(celkem_body),
    }


def build_payroll_preview(mesic_str, prodejna_id=None, base_only=False):
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
    pol_dok_map = batch_pol_dok_for_month(rok, mesic_cislo, user_ids)
    odmeny_map = {}
    for o in MzdovaOdmenaMesic.objects.filter(
        mesic=mesic_date, user_id__in=user_ids,
    ).select_related('vytvoril').order_by('vytvoreno'):
        odmeny_map.setdefault(o.user_id, []).append(o)
    penalizace_map = {}
    for p in MzdovaPenalizaceMesic.objects.filter(
        mesic=mesic_date, user_id__in=user_ids,
    ).select_related('vytvoril').order_by('vytvoreno'):
        penalizace_map.setdefault(p.user_id, []).append(p)

    provize_cache = build_prumer_mzdy_cache_for_prumer(user_ids, rok, mesic_cislo)

    rows = []
    for user in users_list:
        rows.append(build_payroll_row(
            user, rok, mesic_cislo, hours_map, mesic_date, prodejny_cache,
            fondu_h, metrics_map, servis_map, odmeny_map, dyska_map, penalizace_map,
            hours_cache=hours_cache, pol_dok_map=pol_dok_map, prumer_cache=provize_cache,
        ))

    from .payroll_manual import manual_payroll_revision, strip_manual_adjustments_from_row

    manual_revision = manual_payroll_revision(mesic_date, odmeny_map, penalizace_map)
    if base_only:
        rows = [strip_manual_adjustments_from_row(r) for r in rows]

    celkem_bodu = int(round(sum(r.get('celkem_body', 0) for r in rows)))
    return {
        'mesic': mesic_str,
        'fondu_h': fondu_h,
        'celkem_bodu': celkem_bodu,
        'celkem_vyplata': celkem_bodu,
        'manual_revision': manual_revision,
        'base_only': bool(base_only),
        'rows': rows,
    }
