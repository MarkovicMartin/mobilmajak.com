"""Rozpad čisté výplaty na HPP a DPP (doporučení pro admina).

Cílová částka (`celkem_body`) je to, co má zaměstnanec dostat čistého.
HPP drží minimální mzdu + zákonné příplatky (víkend 10 %, svátek 100 %),
zbytek jde na DPP do stropu 11 999 Kč hrubého. Nad stropem se DPP nechá
na maximu a navyšuje se HPP. Bodový výpočet výplaty se nemění.
"""
from decimal import Decimal, ROUND_HALF_UP

HPP_SOC_RATE = Decimal('0.071')
HPP_HEALTH_RATE = Decimal('0.045')
HPP_TAX_RATE = Decimal('0.15')
TAX_CREDIT = Decimal('2570')
DPP_TAX_RATE = Decimal('0.15')
DPP_GROSS_MAX = Decimal('11999')
HPP_GROSS_MIN = Decimal('22400')
WEEKEND_SURCHARGE_RATE = Decimal('0.10')
HOLIDAY_SURCHARGE_RATE = Decimal('1.00')

REZIM_POD_MINIMEM = 'pod_minimem'
REZIM_MIN_HPP = 'min_hpp'
REZIM_MAX_DPP = 'max_dpp'


def _kc(val):
    return Decimal(str(val or 0)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def _dec(val):
    return Decimal(str(val or 0))


def hpp_odvody(hruba):
    """Zaměstnanecké odvody HPP: 7,1 % SP + 4,5 % ZP + 15 % daň − sleva 2570."""
    g = _kc(hruba)
    if g <= 0:
        return {
            'hruba': Decimal('0'),
            'socialni': Decimal('0'),
            'zdravotni': Decimal('0'),
            'dan_pred_slevou': Decimal('0'),
            'sleva': TAX_CREDIT,
            'dan': Decimal('0'),
            'cista': Decimal('0'),
        }
    socialni = _kc(g * HPP_SOC_RATE)
    zdravotni = _kc(g * HPP_HEALTH_RATE)
    dan_pred_slevou = _kc(g * HPP_TAX_RATE)
    dan = max(Decimal('0'), dan_pred_slevou - TAX_CREDIT)
    cista = g - socialni - zdravotni - dan
    return {
        'hruba': g,
        'socialni': socialni,
        'zdravotni': zdravotni,
        'dan_pred_slevou': dan_pred_slevou,
        'sleva': TAX_CREDIT,
        'dan': dan,
        'cista': cista,
    }


def dpp_odvody(hruba):
    """DPP do stropu: jen 15 % daň z příjmů, bez sociálního a zdravotního."""
    g = min(_kc(hruba), DPP_GROSS_MAX)
    if g < 0:
        g = Decimal('0')
    dan = _kc(g * DPP_TAX_RATE)
    return {
        'hruba': g,
        'dan': dan,
        'cista': g - dan,
    }


def hpp_hruba_z_ciste(cista):
    """Inverze HPP: čistá → hrubá (celé Kč)."""
    n = _kc(cista)
    if n <= 0:
        return Decimal('0')
    koef_bez_dane = Decimal('1') - HPP_SOC_RATE - HPP_HEALTH_RATE
    koef_s_dani = koef_bez_dane - HPP_TAX_RATE
    odhad_bez = _kc(n / koef_bez_dane)
    if hpp_odvody(odhad_bez)['dan'] == 0:
        g = odhad_bez
    else:
        g = _kc((n - TAX_CREDIT) / koef_s_dani)
    for _ in range(30):
        got = hpp_odvody(g)['cista']
        if got == n:
            return g
        g += Decimal('1') if got < n else Decimal('-1')
        if g < 0:
            return Decimal('0')
    return max(Decimal('0'), g)


def dpp_hruba_z_ciste(cista):
    """Inverze DPP: čistá → hrubá, max 11 999 Kč."""
    n = _kc(cista)
    if n <= 0:
        return Decimal('0')
    max_cista = dpp_odvody(DPP_GROSS_MAX)['cista']
    if n >= max_cista:
        return DPP_GROSS_MAX
    g = _kc(n / (Decimal('1') - DPP_TAX_RATE))
    for _ in range(20):
        got = dpp_odvody(g)['cista']
        if got == n:
            return min(g, DPP_GROSS_MAX)
        g += Decimal('1') if got < n else Decimal('-1')
        if g < 0:
            return Decimal('0')
        if g > DPP_GROSS_MAX:
            return DPP_GROSS_MAX
    return min(max(Decimal('0'), g), DPP_GROSS_MAX)


def hodiny_sazba_hpp(odpracovano_h, svatek_h=0):
    """Kalendářní odpracované hodiny (svátek je ve výplatě v odpracovano_h 2×)."""
    odprac = _dec(odpracovano_h)
    svatek = _dec(svatek_h)
    kalendar = odprac - svatek
    if kalendar > 0:
        return kalendar
    return odprac


def _sazba_h(hpp_zaklad_hruba, hodiny_sazba):
    hours = _dec(hodiny_sazba)
    base = _kc(hpp_zaklad_hruba)
    if hours <= 0 or base <= 0:
        return Decimal('0')
    return base / hours


def vikend_priplatek_hruba(hpp_zaklad_hruba, odpracovano_h, vikend_h, svatek_h=0):
    """10 % průměrné hodinové mzdy HPP za hodiny so/ne."""
    sazba = _sazba_h(hpp_zaklad_hruba, hodiny_sazba_hpp(odpracovano_h, svatek_h))
    if sazba <= 0 or _dec(vikend_h) <= 0:
        return Decimal('0')
    return _kc(sazba * _dec(vikend_h) * WEEKEND_SURCHARGE_RATE)


def svatek_priplatek_hruba(hpp_zaklad_hruba, odpracovano_h, svatek_h):
    """100 % průměrné hodinové mzdy HPP za odpracovaný svátek."""
    sazba = _sazba_h(hpp_zaklad_hruba, hodiny_sazba_hpp(odpracovano_h, svatek_h))
    if sazba <= 0 or _dec(svatek_h) <= 0:
        return Decimal('0')
    return _kc(sazba * _dec(svatek_h) * HOLIDAY_SURCHARGE_RATE)


def hpp_minimum_hruba(odpracovano_h, vikend_h, svatek_h=0):
    """Minimální hrubá HPP: 22 400 + příplatky za víkend a svátek."""
    vikend = vikend_priplatek_hruba(HPP_GROSS_MIN, odpracovano_h, vikend_h, svatek_h)
    svatek = svatek_priplatek_hruba(HPP_GROSS_MIN, odpracovano_h, svatek_h)
    return HPP_GROSS_MIN + vikend + svatek, vikend, svatek


def _split_dict(hpp, dpp, vikend_priplatek, svatek_priplatek, vikend_h, svatek_h, rezim, target, warnings=None):
    hpp_cista = hpp['cista']
    dpp_cista = dpp['cista']
    return {
        'rezim': rezim,
        'cil_cista': int(target),
        'vikend_h': float(vikend_h or 0),
        'svatek_h': float(svatek_h or 0),
        'vikend_priplatek_hruba': int(vikend_priplatek),
        'svatek_priplatek_hruba': int(svatek_priplatek),
        'hpp_hruba_min': int(HPP_GROSS_MIN),
        'dpp_hruba_max': int(DPP_GROSS_MAX),
        'hpp_hruba': int(hpp['hruba']),
        'hpp_cista': int(hpp_cista),
        'hpp_socialni': int(hpp['socialni']),
        'hpp_zdravotni': int(hpp['zdravotni']),
        'hpp_dan_pred_slevou': int(hpp['dan_pred_slevou']),
        'hpp_sleva': int(hpp['sleva']),
        'hpp_dan': int(hpp['dan']),
        'dpp_hruba': int(dpp['hruba']),
        'dpp_cista': int(dpp_cista),
        'dpp_dan': int(dpp['dan']),
        'soucet_cista': int(hpp_cista + dpp_cista),
        'warning': (warnings or [])[0] if warnings else None,
        'warnings': warnings or [],
    }


def _priplatky(hpp_hruba, odpracovano_h, vikend_h, svatek_h):
    return (
        vikend_priplatek_hruba(hpp_hruba, odpracovano_h, vikend_h, svatek_h),
        svatek_priplatek_hruba(hpp_hruba, odpracovano_h, svatek_h),
    )


def recommend_hpp_dpp(target_net, odpracovano_h=0, vikend_h=0, svatek_h=0):
    """Nejefektivnější rozpad cílové čisté na HPP + DPP."""
    target = _kc(target_net)
    if target <= 0:
        empty_hpp = hpp_odvody(0)
        empty_dpp = dpp_odvody(0)
        return _split_dict(
            empty_hpp, empty_dpp, Decimal('0'), Decimal('0'),
            vikend_h, svatek_h, REZIM_POD_MINIMEM, target,
        )

    hpp_min_hruba, vikend_p, svatek_p = hpp_minimum_hruba(odpracovano_h, vikend_h, svatek_h)
    hpp_min = hpp_odvody(hpp_min_hruba)
    dpp_max = dpp_odvody(DPP_GROSS_MAX)
    hpp_min_cista = hpp_min['cista']
    dpp_max_cista = dpp_max['cista']

    if target <= hpp_min_cista:
        hpp = hpp_odvody(hpp_hruba_z_ciste(target))
        dpp = dpp_odvody(0)
        vikend_out, svatek_out = (
            _priplatky(hpp['hruba'], odpracovano_h, vikend_h, svatek_h)
            if hpp['hruba'] > 0 else (Decimal('0'), Decimal('0'))
        )
        warnings = ['Čistá je pod minimální HPP – vše na hlavní pracovní poměr.']
        return _split_dict(
            hpp, dpp, vikend_out, svatek_out, vikend_h, svatek_h,
            REZIM_POD_MINIMEM, target, warnings,
        )

    if target <= hpp_min_cista + dpp_max_cista:
        hpp = hpp_min
        dpp = dpp_odvody(dpp_hruba_z_ciste(target - hpp_min_cista))
        delta = target - (hpp['cista'] + dpp['cista'])
        if delta != 0:
            dpp_try = dpp_odvody(dpp_hruba_z_ciste(dpp['cista'] + delta))
            if dpp_try['hruba'] <= DPP_GROSS_MAX and dpp_try['cista'] == dpp['cista'] + delta:
                dpp = dpp_try
            else:
                hpp = hpp_odvody(hpp_hruba_z_ciste(hpp['cista'] + delta))
        return _split_dict(
            hpp, dpp, vikend_p, svatek_p, vikend_h, svatek_h, REZIM_MIN_HPP, target,
        )

    dpp = dpp_max
    hpp = hpp_odvody(hpp_hruba_z_ciste(target - dpp_max_cista))
    delta = target - (hpp['cista'] + dpp['cista'])
    if delta != 0:
        hpp = hpp_odvody(hpp_hruba_z_ciste(hpp['cista'] + delta))
    if hpp['hruba'] < hpp_min_hruba:
        hpp = hpp_odvody(hpp_min_hruba)
        rest = target - hpp['cista']
        dpp = dpp_odvody(dpp_hruba_z_ciste(max(Decimal('0'), rest)))
    return _split_dict(
        hpp, dpp, vikend_p, svatek_p, vikend_h, svatek_h, REZIM_MAX_DPP, target,
    )


def split_from_hpp_cista(target_net, hpp_cista, odpracovano_h=0, vikend_h=0, svatek_h=0):
    """Vzoreček: zadaná čistá HPP → dopočti DPP (strop 11 999 hrubého)."""
    target = _kc(target_net)
    hpp_n = _kc(hpp_cista)
    dpp_max_cista = dpp_odvody(DPP_GROSS_MAX)['cista']
    warnings = []
    if hpp_n < 0:
        hpp_n = Decimal('0')
    dpp_n = target - hpp_n
    if dpp_n > dpp_max_cista:
        dpp_n = dpp_max_cista
        hpp_n = target - dpp_n
        warnings.append(
            'DPP by překročila 11 999 Kč hrubého – DPP na maximu, zbytek na HPP.'
        )
    if dpp_n < 0:
        dpp_n = Decimal('0')
        hpp_n = target
        warnings.append('Zadaná HPP je vyšší než celková čistá – vše na HPP.')
    hpp = hpp_odvody(hpp_hruba_z_ciste(hpp_n))
    dpp = dpp_odvody(dpp_hruba_z_ciste(dpp_n))
    delta = target - (hpp['cista'] + dpp['cista'])
    if delta != 0:
        hpp = hpp_odvody(hpp_hruba_z_ciste(hpp['cista'] + delta))
    hpp_min_hruba, vikend_p, svatek_p = hpp_minimum_hruba(odpracovano_h, vikend_h, svatek_h)
    if hpp['hruba'] < hpp_min_hruba:
        warnings.append(
            f'HPP hrubá je pod minimem {int(hpp_min_hruba)} Kč (min. mzda + příplatky).'
        )
    rezim = REZIM_MAX_DPP if dpp['hruba'] >= DPP_GROSS_MAX else REZIM_MIN_HPP
    if hpp['hruba'] > 0:
        vikend_out, svatek_out = _priplatky(
            max(hpp['hruba'], HPP_GROSS_MIN), odpracovano_h, vikend_h, svatek_h,
        )
    else:
        vikend_out, svatek_out = vikend_p, svatek_p
    return _split_dict(
        hpp, dpp, vikend_out, svatek_out, vikend_h, svatek_h, rezim, target, warnings,
    )


def split_from_dpp_cista(target_net, dpp_cista, odpracovano_h=0, vikend_h=0, svatek_h=0):
    """Vzoreček: zadaná čistá DPP → dopočti HPP."""
    dpp_n = _kc(dpp_cista)
    dpp_max_cista = dpp_odvody(DPP_GROSS_MAX)['cista']
    extra = []
    if dpp_n > dpp_max_cista:
        dpp_n = dpp_max_cista
        extra.append('DPP zastropována na 11 999 Kč hrubého.')
    if dpp_n < 0:
        dpp_n = Decimal('0')
    hpp_n = _kc(target_net) - dpp_n
    result = split_from_hpp_cista(target_net, hpp_n, odpracovano_h, vikend_h, svatek_h)
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
    )
    return row
