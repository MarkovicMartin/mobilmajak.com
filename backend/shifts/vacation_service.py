"""Fond dovolené a výpočet hodin dovolené ze směn."""
from datetime import date

from users.mzda_utils import is_brigadnik

from .labor_hours import HODINY_NA_PRACOVNI_DEN, fondu_hodin_mesic
from .models import Smena
from .czech_holidays import get_ceske_svatky

DOVOLENA_ROCNI_FOND = 160
DOVOLENA_PREVOD_MAX = 40
DOVOLENA_HODINY_ZA_DEN = HODINY_NA_PRACOVNI_DEN
DOVOLENA_DEFICIT_OD_ROK = 2026
DOVOLENA_DEFICIT_OD_MESIC = 6


def _is_markovic_active_seller(user):
    """Martin Markovič – prodej na pultu při roli ADMIN."""
    return (
        (getattr(user, 'jmeno', '') or '').strip().lower() == 'martin'
        and (getattr(user, 'prijmeni', '') or '').strip().lower() == 'markovič'
    )


def is_dovolena_eligible(user):
    if not user or is_brigadnik(user):
        return False
    if getattr(user, 'role', None) in ('PRODEJCE', 'VEDOUCI'):
        return True
    return _is_markovic_active_seller(user)


def _svatky_set(rok):
    return {(y, m, d) for y, m, d in get_ceske_svatky(rok)}


def is_pracovni_den(datum, svatky_set=None):
    if datum.weekday() >= 5:
        return False
    if svatky_set is None:
        svatky_set = _svatky_set(datum.year)
    return (datum.year, datum.month, datum.day) not in svatky_set


def dovolena_hodin_ze_smeny(smena, svatky=None):
    if smena.typ_smeny != 'dovolena':
        return 0.0
    if svatky is not None and isinstance(next(iter(svatky), None), date):
        if not is_pracovni_den(smena.datum, {(d.year, d.month, d.day) for d in svatky}):
            return 0.0
    elif not is_pracovni_den(smena.datum):
        return 0.0
    return float(DOVOLENA_HODINY_ZA_DEN)


def mel_fond_v_roce(user_id, rok):
    """True pokud měl uživatel v roce alespoň jednu pracovní nebo dovolenou směnu."""
    return Smena.objects.filter(
        user_id=user_id,
        datum__year=rok,
        aktivni=True,
        typ_smeny__in=('prace', 'dovolena'),
    ).exists()


def cerpana_dovolena_rok(user_id, rok, ignorovat_smena_id=None):
    """Hodiny čerpané směnami typu dovolená (bez deficitu měsíčního fondu)."""
    smeny = Smena.objects.filter(
        user_id=user_id,
        typ_smeny='dovolena',
        aktivni=True,
        datum__year=rok,
    )
    if ignorovat_smena_id:
        smeny = smeny.exclude(id=ignorovat_smena_id)
    return round(sum(dovolena_hodin_ze_smeny(s) for s in smeny), 2)


def _mesic_pocita_deficit(rok, mesic_cislo):
    """True pokud se deficit z nesplněného fondu započítává do čerpání dovolené."""
    if rok < DOVOLENA_DEFICIT_OD_ROK:
        return False
    if rok == DOVOLENA_DEFICIT_OD_ROK:
        return mesic_cislo >= DOVOLENA_DEFICIT_OD_MESIC
    return True


def _mesic_ukoncen(rok, mesic_cislo, referencni_datum=None):
    """True pokud kalendářní měsíc již skončil (ne aktuální ani budoucí)."""
    if referencni_datum is None:
        referencni_datum = date.today()
    if rok < referencni_datum.year:
        return True
    if rok > referencni_datum.year:
        return False
    return mesic_cislo < referencni_datum.month


def deficit_mesic_hodin(user_id, rok, mesic_cislo, hours_cache=None):
    """
    Nesplněný měsíční pracovní fond: max(0, fondu - odpracováno - dovolená v měsíci).
    Dovolená v měsíci se odečte, aby se nepočítala dvakrát (směna + deficit).
    """
    fondu = fondu_hodin_mesic(rok, mesic_cislo)
    if fondu <= 0:
        return 0.0
    from .payroll_service import aggregate_hours_by_user

    if hours_cache is not None:
        hours = hours_cache.get((rok, mesic_cislo), {}).get(user_id, {})
    else:
        hours = aggregate_hours_by_user(rok, mesic_cislo).get(user_id, {})
    odpracovano = float(hours.get('odpracovano_h', 0) or 0)
    dovolena = float(hours.get('dovolena_h', 0) or 0)
    return round(max(0.0, fondu - odpracovano - dovolena), 2)


def deficit_mesic_pro_dovolenou(user_id, rok, mesic_cislo, hours_cache=None):
    """Deficit započítaný do dovolené – 0 před červnem 2026."""
    if not _mesic_pocita_deficit(rok, mesic_cislo):
        return 0.0
    return deficit_mesic_hodin(user_id, rok, mesic_cislo, hours_cache=hours_cache)


def deficit_fondu_rok(user_id, rok, referencni_datum=None, hours_cache=None):
    """Součet deficitů z ukončených měsíců v daném roce."""
    if referencni_datum is None:
        referencni_datum = date.today()
    celkem = 0.0
    for mesic in range(1, 13):
        if not _mesic_ukoncen(rok, mesic, referencni_datum):
            continue
        if not _mesic_pocita_deficit(rok, mesic):
            continue
        celkem += deficit_mesic_hodin(user_id, rok, mesic, hours_cache=hours_cache)
    return round(celkem, 2)


def celkove_cerpano_rok(user_id, rok, ignorovat_smena_id=None, referencni_datum=None):
    """Čerpání fondu: směny dovolené + automatický deficit z nesplněného měsíčního fondu."""
    smeny_h = cerpana_dovolena_rok(user_id, rok, ignorovat_smena_id=ignorovat_smena_id)
    deficit_h = deficit_fondu_rok(user_id, rok, referencni_datum=referencni_datum)
    return round(smeny_h + deficit_h, 2)


def prevod_z_predchoziho_roku(user_id, rok):
    if rok <= 2000:
        return 0.0
    prev_rok = rok - 1
    if not mel_fond_v_roce(user_id, prev_rok):
        return 0.0
    fond_prev = DOVOLENA_ROCNI_FOND + prevod_z_predchoziho_roku(user_id, prev_rok)
    cerpano_prev = celkove_cerpano_rok(user_id, prev_rok)
    nevyuzito = max(0.0, fond_prev - cerpano_prev)
    return min(float(DOVOLENA_PREVOD_MAX), nevyuzito)


def fond_extra_h(user):
    val = getattr(user, 'dovolena_fond_extra_h', None)
    return float(val) if val is not None else 0.0


def korekce_cerpano_h(user):
    val = getattr(user, 'dovolena_korekce_cerpano_h', None)
    return float(val) if val is not None else 0.0


def dovolena_fond_rok(user_id, rok, fond_extra=0.0):
    return round(
        DOVOLENA_ROCNI_FOND + prevod_z_predchoziho_roku(user_id, rok) + float(fond_extra or 0),
        2,
    )


def dovolena_stav(user, rok=None, hours_cache=None, referencni_datum=None):
    if not is_dovolena_eligible(user):
        return None
    if rok is None:
        rok = date.today().year
    if referencni_datum is None:
        referencni_datum = date.today()
    extra = fond_extra_h(user)
    korekce = korekce_cerpano_h(user)
    prevod = prevod_z_predchoziho_roku(user.id, rok)
    fond = dovolena_fond_rok(user.id, rok, fond_extra=extra)
    cerpano_smeny = cerpana_dovolena_rok(user.id, rok)
    odeceno_deficit = deficit_fondu_rok(
        user.id, rok, referencni_datum=referencni_datum, hours_cache=hours_cache,
    )
    cerpano = round(cerpano_smeny + odeceno_deficit + korekce, 2)
    zbyva = fond - cerpano
    return {
        'rok': rok,
        'fond_h': fond,
        'rocni_narok_h': DOVOLENA_ROCNI_FOND,
        'prevod_h': prevod,
        'fond_extra_h': extra,
        'korekce_cerpano_h': korekce,
        'cerpano_smeny_h': cerpano_smeny,
        'odeceno_deficit_h': odeceno_deficit,
        'cerpano_h': cerpano,
        'zbyva_h': round(max(0.0, zbyva), 2),
        'propadne_h': round(max(0.0, zbyva - DOVOLENA_PREVOD_MAX), 2),
    }


def validate_dovolena_kapacita(user, datum, typ_smeny, ignorovat_smena_id=None):
    if typ_smeny != 'dovolena' or not is_dovolena_eligible(user):
        return None
    nove_h = DOVOLENA_HODINY_ZA_DEN if is_pracovni_den(datum) else 0.0
    if nove_h <= 0:
        return None
    rok = datum.year if isinstance(datum, date) else datum
    fond = dovolena_fond_rok(user.id, rok, fond_extra=fond_extra_h(user))
    cerpano = celkove_cerpano_rok(user.id, rok, ignorovat_smena_id=ignorovat_smena_id) + korekce_cerpano_h(user)
    if cerpano + nove_h > fond + 0.001:
        zbyva = max(0.0, fond - cerpano)
        return (
            f'Překročen fond dovolené pro rok {rok}. '
            f'Zbývá {zbyva:.0f} h (fond {fond:.0f} h, čerpáno {cerpano:.0f} h vč. deficitu fondu).'
        )
    return None


def normalize_dovolena_casy(datum, cas_od='08:00', cas_do='16:00'):
    """Pro dovolenou v pracovní den nastaví 8h; jinak ponechá vstup."""
    if is_pracovni_den(datum):
        return '08:00', '16:00'
    return cas_od, cas_do


def _reference_month_for_prumer(rok, referencni_datum=None):
    """Měsíc pro výpočet průměru – aktuální v probíhajícím roce, jinak prosinec/leden."""
    if referencni_datum is None:
        referencni_datum = date.today()
    if rok < referencni_datum.year:
        return 12
    if rok > referencni_datum.year:
        return 1
    return referencni_datum.month


def cerpana_dovolena_mesic(user_id, rok, mesic_cislo, hours_cache=None):
    """Hodiny dovolené ze směn v kalendářním měsíci."""
    from .payroll_service import aggregate_hours_by_user

    if hours_cache is not None:
        hours = hours_cache.get((rok, mesic_cislo), {}).get(user_id, {})
    else:
        hours = aggregate_hours_by_user(rok, mesic_cislo).get(user_id, {})
    return round(float(hours.get('dovolena_h', 0) or 0), 2)


def mesicni_cerpani_dovolene(user_id, rok, mesic_cislo, referencni_datum=None, hours_cache=None):
    """
    Čerpání fondu v měsíci: směny dovolené + deficit (jen u ukončených měsíců).
    """
    smeny_h = cerpana_dovolena_mesic(user_id, rok, mesic_cislo, hours_cache=hours_cache)
    pocita_deficit = _mesic_pocita_deficit(rok, mesic_cislo)
    deficit_h = (
        deficit_mesic_hodin(user_id, rok, mesic_cislo, hours_cache=hours_cache)
        if pocita_deficit else 0.0
    )
    ukoncen = _mesic_ukoncen(rok, mesic_cislo, referencni_datum)
    deficit_odeceno = round(deficit_h, 2) if ukoncen and pocita_deficit else 0.0
    return {
        'mesic': mesic_cislo,
        'dovolena_smeny_h': smeny_h,
        'deficit_h': deficit_odeceno,
        'deficit_predikce_h': round(deficit_h, 2) if not ukoncen and pocita_deficit and deficit_h > 0 else 0.0,
        'cerpano_h': round(smeny_h + deficit_odeceno, 2),
        'mesic_ukoncen': ukoncen,
    }


def build_hours_cache_for_overview(rok, referencni_datum=None) -> dict:
    """
    Agregace hodin ze směn pro přehled dovolené – max. ~15 dotazů místo stovek.
    Klíč: (rok, měsíc) → {user_id: {odpracovano_h, dovolena_h, …}}.
    """
    from .payroll_service import aggregate_hours_by_user, _subtract_months

    if referencni_datum is None:
        referencni_datum = date.today()
    ref_mesic = _reference_month_for_prumer(rok, referencni_datum)
    month_keys = {(rok, m) for m in range(1, 13)}
    for i in range(1, 4):
        month_keys.add(_subtract_months(rok, ref_mesic, i))
    return {
        key: aggregate_hours_by_user(y, m)
        for (y, m) in month_keys
    }


def build_vacation_overview_user(user, rok=None, referencni_datum=None, hours_cache=None):
    """Přehled dovolené pro jednoho uživatele – roční tabulka měsíců a sazba výplaty."""
    if not is_dovolena_eligible(user):
        return None
    if rok is None:
        rok = date.today().year
    if referencni_datum is None:
        referencni_datum = date.today()

    from .payroll_service import prumer_fixni_hodinove_body, prumer_fixni_hodinove_detail
    from .prumer_mzdy_override import prumer_override_for_user

    ref_mesic = _reference_month_for_prumer(rok, referencni_datum)
    override_mesice = prumer_override_for_user(user)
    prumer_detail = prumer_fixni_hodinove_detail(
        user, rok, ref_mesic, hours_cache=hours_cache, override_mesice=override_mesice,
    )
    prumer_h = prumer_fixni_hodinove_body(
        user, rok, ref_mesic, hours_cache=hours_cache, override_mesice=override_mesice,
    )
    stav = dovolena_stav(
        user, rok, hours_cache=hours_cache, referencni_datum=referencni_datum,
    )
    mesice = [
        mesicni_cerpani_dovolene(
            user.id, rok, m, referencni_datum=referencni_datum, hours_cache=hours_cache,
        )
        for m in range(1, 13)
    ]
    cerpano_rok_z_mesicu = round(sum(m['cerpano_h'] for m in mesice), 2)

    return {
        'user_id': user.id,
        'jmeno': f'{user.jmeno} {user.prijmeni}'.strip(),
        'eligible': True,
        'prumer_fixni_h': float(prumer_h),
        'dovolena_sazba_h': float(prumer_h),
        'prumer_mesice': f'{rok}-{ref_mesic:02d}',
        'prumer_detail': prumer_detail,
        'mesice': mesice,
        'cerpano_rok_z_mesicu_h': cerpano_rok_z_mesicu,
        **stav,
    }
