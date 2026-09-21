"""Rozpad čisté výplaty na HPP a DPP (doporučení pro admina).

Cílová částka (`celkem_body`) je to, co má zaměstnanec dostat čistého.
HPP drží minimální mzdu + příplatky z 134,40 Kč/h (víkend 10 %, svátek 100 %,
přesčas 25 %, zaokrouhlení nahoru). Zbytek na DPP do 11 999 Kč hrubého.

Odvody podle výplatního lístku: SP/ZP jen z HPP (na celé Kč nahoru),
zálohová daň z úhrnu HPP+DPP (základ na celé 100 Kč nahoru) − sleva 2 570.
Bodový výpočet výplaty se nemění.
"""
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

HPP_SOC_RATE = Decimal('0.071')
HPP_HEALTH_RATE = Decimal('0.045')
HPP_TAX_RATE = Decimal('0.15')
TAX_CREDIT = Decimal('2570')
DPP_GROSS_MAX = Decimal('11999')
HPP_GROSS_MIN = Decimal('22400')
PRIPLATEK_SAZBA_H = Decimal('134.4')
WEEKEND_SURCHARGE_RATE = Decimal('0.10')
HOLIDAY_SURCHARGE_RATE = Decimal('1.00')
OVERTIME_SURCHARGE_RATE = Decimal('0.25')

REZIM_POD_MINIMEM = 'pod_minimem'
REZIM_MIN_HPP = 'min_hpp'
REZIM_MAX_DPP = 'max_dpp'

_FIND_WINDOW = 1500


def _kc(val):
    return Decimal(str(val or 0)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def _dec(val):
    return Decimal(str(val or 0))


def _ceil_kc(val):
    d = _dec(val)
    if d <= 0:
        return Decimal('0')
    return d.to_integral_value(rounding=ROUND_CEILING)


def _ceil_hundreds(val):
    """Základ daně: celé stokoruny nahoru."""
    d = _kc(val)
    if d <= 0:
        return Decimal('0')
    return ((d + Decimal('99')) // Decimal('100')) * Decimal('100')


def odvody_kombinovane(hpp_hruba, dpp_hruba=0):
    """SP/ZP z HPP (ceil Kč) + zálohová daň z úhrnu (základ na 100 Kč nahoru)."""
    hpp = max(_kc(hpp_hruba), Decimal('0'))
    dpp = min(max(_kc(dpp_hruba), Decimal('0')), DPP_GROSS_MAX)
    socialni = _ceil_kc(hpp * HPP_SOC_RATE) if hpp > 0 else Decimal('0')
    zdravotni = _ceil_kc(hpp * HPP_HEALTH_RATE) if hpp > 0 else Decimal('0')
    zaklad = _ceil_hundreds(hpp + dpp)
    dan_pred = _kc(zaklad * HPP_TAX_RATE) if zaklad > 0 else Decimal('0')
    if hpp + dpp <= 0:
        dan = Decimal('0')
    else:
        dan = max(Decimal('0'), dan_pred - TAX_CREDIT)
    cista = hpp + dpp - socialni - zdravotni - dan
    return {
        'hpp_hruba': hpp,
        'dpp_hruba': dpp,
        'hruba': hpp,
        'socialni': socialni,
        'zdravotni': zdravotni,
        'zaklad_dane': zaklad,
        'dan_pred_slevou': dan_pred,
        'sleva': TAX_CREDIT,
        'dan': dan,
        'dpp_dan': Decimal('0'),
        'hpp_cista': hpp - socialni - zdravotni - dan,
        'dpp_cista': dpp,
        'cista': cista,
    }


def hpp_odvody(hruba):
    """Odvody při hrubé jen na HPP (DPP 0)."""
    return odvody_kombinovane(hruba, 0)


def dpp_odvody(hruba):
    """DPP složka: bez SP/ZP. Daň se počítá z úhrnu v odvody_kombinovane."""
    g = min(max(_kc(hruba), Decimal('0')), DPP_GROSS_MAX)
    return {
        'hruba': g,
        'dan': Decimal('0'),
        'cista': g,
    }


def hpp_hruba_z_ciste(cista):
    """Inverze: čistá (jen HPP) → hrubá."""
    return _find_hpp_for_net(cista, 0, 0)


def dpp_hruba_z_ciste(cista):
    """DPP bez vlastních odvodů: čistá = hrubá, strop 11 999."""
    n = _kc(cista)
    if n <= 0:
        return Decimal('0')
    return min(n, DPP_GROSS_MAX)


def priplatek_kc(hours, rate):
    """Příplatek v celých Kč nahoru: 134,40 Kč/h × hodiny × sazba."""
    if _dec(hours) <= 0:
        return Decimal('0')
    return _ceil_kc(PRIPLATEK_SAZBA_H * _dec(hours) * rate)


def vikend_priplatek_hruba(vikend_h):
    """10 % z 134,40 Kč/h za hodiny so/ne."""
    return priplatek_kc(vikend_h, WEEKEND_SURCHARGE_RATE)


def svatek_priplatek_hruba(svatek_h):
    """100 % z 134,40 Kč/h za odpracovaný svátek."""
    return priplatek_kc(svatek_h, HOLIDAY_SURCHARGE_RATE)


def prescas_priplatek_hruba(prescas_h):
    """25 % z 134,40 Kč/h za přesčas."""
    return priplatek_kc(prescas_h, OVERTIME_SURCHARGE_RATE)


def hpp_minimum_hruba(vikend_h=0, svatek_h=0, prescas_h=0):
    """Minimální hrubá HPP: 22 400 + příplatky z 134,40 Kč/h."""
    vikend = vikend_priplatek_hruba(vikend_h)
    svatek = svatek_priplatek_hruba(svatek_h)
    prescas = prescas_priplatek_hruba(prescas_h)
    return HPP_GROSS_MIN + vikend + svatek + prescas, vikend, svatek, prescas


def _find_hpp_for_net(target, dpp, hpp_floor=0):
    """Nejmenší HPP hrubá (Kč) tak, aby kombinovaná čistá = target."""
    target = _kc(target)
    dpp = min(max(_kc(dpp), Decimal('0')), DPP_GROSS_MAX)
    floor = max(int(_kc(hpp_floor)), 0)
    if target <= 0:
        return Decimal(floor)
    est = (target - Decimal('0.85') * dpp - TAX_CREDIT) / Decimal('0.734')
    est_i = max(int(_kc(est)), floor)
    lo = max(floor, est_i - _FIND_WINDOW)
    hi = max(est_i + _FIND_WINDOW, floor)
    best = floor
    best_err = None
    for g in range(lo, hi + 1):
        got = odvody_kombinovane(g, dpp)['cista']
        err = abs(got - target)
        if err == 0:
            return Decimal(g)
        if best_err is None or err < best_err:
            best = g
            best_err = err
    return Decimal(best)


def _find_dpp_for_net(target, hpp):
    """DPP hrubá (0–11 999) tak, aby kombinovaná čistá = target při dané HPP."""
    target = _kc(target)
    hpp = max(_kc(hpp), Decimal('0'))
    best = 0
    best_err = None
    for d in range(0, int(DPP_GROSS_MAX) + 1):
        got = odvody_kombinovane(hpp, d)['cista']
        err = abs(got - target)
        if err == 0:
            return Decimal(d)
        if best_err is None or err < best_err:
            best = d
            best_err = err
    return Decimal(best)


def _split_dict(
    combo, vikend_priplatek, svatek_priplatek, prescas_priplatek,
    vikend_h, svatek_h, prescas_h, rezim, target, warnings=None,
):
    return {
        'rezim': rezim,
        'cil_cista': int(target),
        'vikend_h': float(vikend_h or 0),
        'svatek_h': float(svatek_h or 0),
        'prescas_h': float(prescas_h or 0),
        'vikend_priplatek_hruba': int(vikend_priplatek),
        'svatek_priplatek_hruba': int(svatek_priplatek),
        'prescas_priplatek_hruba': int(prescas_priplatek),
        'priplatek_sazba_h': float(PRIPLATEK_SAZBA_H),
        'hpp_hruba_min': int(HPP_GROSS_MIN),
        'dpp_hruba_max': int(DPP_GROSS_MAX),
        'zaklad_dane': int(combo['zaklad_dane']),
        'hpp_hruba': int(combo['hpp_hruba']),
        'hpp_cista': int(combo['hpp_cista']),
        'hpp_socialni': int(combo['socialni']),
        'hpp_zdravotni': int(combo['zdravotni']),
        'hpp_dan_pred_slevou': int(combo['dan_pred_slevou']),
        'hpp_sleva': int(combo['sleva']),
        'hpp_dan': int(combo['dan']),
        'dpp_hruba': int(combo['dpp_hruba']),
        'dpp_cista': int(combo['dpp_cista']),
        'dpp_dan': int(combo['dpp_dan']),
        'soucet_cista': int(combo['cista']),
        'warning': (warnings or [])[0] if warnings else None,
        'warnings': warnings or [],
    }


def _priplatky(vikend_h, svatek_h, prescas_h):
    return (
        vikend_priplatek_hruba(vikend_h),
        svatek_priplatek_hruba(svatek_h),
        prescas_priplatek_hruba(prescas_h),
    )


def recommend_hpp_dpp(target_net, odpracovano_h=0, vikend_h=0, svatek_h=0, prescas_h=0):
    """Nejefektivnější rozpad cílové čisté na HPP + DPP (kombinovaná zálohová daň)."""
    target = _kc(target_net)
    vikend_p, svatek_p, prescas_p = _priplatky(vikend_h, svatek_h, prescas_h)
    if target <= 0:
        return _split_dict(
            odvody_kombinovane(0, 0), Decimal('0'), Decimal('0'), Decimal('0'),
            vikend_h, svatek_h, prescas_h, REZIM_POD_MINIMEM, target,
        )

    hpp_min_hruba, vikend_p, svatek_p, prescas_p = hpp_minimum_hruba(
        vikend_h, svatek_h, prescas_h,
    )
    net_min = odvody_kombinovane(hpp_min_hruba, 0)['cista']
    net_min_max_dpp = odvody_kombinovane(hpp_min_hruba, DPP_GROSS_MAX)['cista']

    if target < net_min:
        hpp_g = _find_hpp_for_net(target, 0, 0)
        combo = odvody_kombinovane(hpp_g, 0)
        warnings = ['Čistá je pod minimální HPP – vše na hlavní pracovní poměr.']
        return _split_dict(
            combo, vikend_p, svatek_p, prescas_p, vikend_h, svatek_h, prescas_h,
            REZIM_POD_MINIMEM, target, warnings,
        )

    if target <= net_min_max_dpp:
        dpp_g = _find_dpp_for_net(target, hpp_min_hruba)
        combo = odvody_kombinovane(hpp_min_hruba, dpp_g)
        if combo['cista'] != target:
            hpp_g = _find_hpp_for_net(target, dpp_g, hpp_min_hruba)
            combo = odvody_kombinovane(hpp_g, dpp_g)
        return _split_dict(
            combo, vikend_p, svatek_p, prescas_p, vikend_h, svatek_h, prescas_h,
            REZIM_MIN_HPP, target,
        )

    hpp_g = _find_hpp_for_net(target, DPP_GROSS_MAX, hpp_min_hruba)
    combo = odvody_kombinovane(max(hpp_g, hpp_min_hruba), DPP_GROSS_MAX)
    return _split_dict(
        combo, vikend_p, svatek_p, prescas_p, vikend_h, svatek_h, prescas_h,
        REZIM_MAX_DPP, target,
    )


def split_from_hpp_cista(target_net, hpp_cista, odpracovano_h=0, vikend_h=0, svatek_h=0, prescas_h=0):
    """Zadaná čistá HPP → dopočti DPP (strop 11 999 hrubého)."""
    target = _kc(target_net)
    hpp_n = _kc(hpp_cista)
    warnings = []
    if hpp_n < 0:
        hpp_n = Decimal('0')
    dpp_n = target - hpp_n
    if dpp_n > DPP_GROSS_MAX:
        dpp_n = DPP_GROSS_MAX
        warnings.append(
            'DPP by překročila 11 999 Kč hrubého – DPP na maximu, zbytek na HPP.'
        )
    if dpp_n < 0:
        dpp_n = Decimal('0')
        warnings.append('Zadaná HPP je vyšší než celková čistá – vše na HPP.')
    hpp_min_hruba, vikend_p, svatek_p, prescas_p = hpp_minimum_hruba(
        vikend_h, svatek_h, prescas_h,
    )
    hpp_g = _find_hpp_for_net(target, dpp_n, 0)
    combo = odvody_kombinovane(hpp_g, dpp_n)
    if combo['hpp_hruba'] < hpp_min_hruba:
        warnings.append(
            f'HPP hrubá je pod minimem {int(hpp_min_hruba)} Kč (min. mzda + příplatky).'
        )
    rezim = REZIM_MAX_DPP if combo['dpp_hruba'] >= DPP_GROSS_MAX else REZIM_MIN_HPP
    return _split_dict(
        combo, vikend_p, svatek_p, prescas_p, vikend_h, svatek_h, prescas_h,
        rezim, target, warnings,
    )


def split_from_dpp_cista(target_net, dpp_cista, odpracovano_h=0, vikend_h=0, svatek_h=0, prescas_h=0):
    """Zadaná čistá DPP → dopočti HPP."""
    dpp_n = _kc(dpp_cista)
    extra = []
    if dpp_n > DPP_GROSS_MAX:
        dpp_n = DPP_GROSS_MAX
        extra.append('DPP zastropována na 11 999 Kč hrubého.')
    if dpp_n < 0:
        dpp_n = Decimal('0')
    hpp_n = _kc(target_net) - dpp_n
    result = split_from_hpp_cista(
        target_net, hpp_n, odpracovano_h, vikend_h, svatek_h, prescas_h,
    )
    if extra:
        result['warnings'] = extra + list(result.get('warnings') or [])
        result['warning'] = result['warnings'][0]
    return result


def attach_hpp_dpp_to_row(row):
    """Doplní / přepočte doporučení HPP+DPP na řádku výplaty."""
    if row.get('is_brigadnik'):
        row['hpp_dpp'] = None
        return row
    row['hpp_dpp'] = recommend_hpp_dpp(
        row.get('celkem_body') or 0,
        odpracovano_h=row.get('odpracovano_h') or 0,
        vikend_h=row.get('vikend_h') or 0,
        svatek_h=row.get('svatek_h') or 0,
        prescas_h=row.get('prescas_h') or 0,
    )
    return row
