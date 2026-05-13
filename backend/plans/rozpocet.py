"""Čistý přepočet plánu s dvouúrovňovými zámky (none / pct / kc).

Modul nekomunikuje s databází. Dostává dict payload, vrací dict s finálními
hodnotami a seznamem warnings. Používá se jak v dry-runu (endpoint /prepocet/),
tak před zápisem do DB ve view plan_ulozit.
"""

from decimal import Decimal, ROUND_HALF_UP


Q_MONEY = Decimal('0.01')
Q_PCT = Decimal('0.001')
ZERO = Decimal('0')
HUNDRED = Decimal('100')

LOCK_NONE = 'none'
LOCK_PCT = 'pct'
LOCK_KC = 'kc'
VALID_LOCK_MODES = {LOCK_NONE, LOCK_PCT, LOCK_KC}


def _D(value, default=ZERO):
    """Bezpečný převod na Decimal."""
    if value is None or value == '':
        return default
    try:
        return Decimal(str(value))
    except Exception:
        return default


def _normalize_lock(value):
    """Vrátí validní lock_mode nebo 'none'."""
    if value in VALID_LOCK_MODES:
        return value
    return LOCK_NONE


def _qmoney(v):
    return Decimal(v).quantize(Q_MONEY, rounding=ROUND_HALF_UP)


def _qpct(v):
    return Decimal(v).quantize(Q_PCT, rounding=ROUND_HALF_UP)


def _format_kc(v):
    """Pro warning hlášky (3 000 000 Kč)."""
    try:
        return f"{int(round(float(v))):,}".replace(',', ' ')
    except Exception:
        return str(v)


def _rozpocet_uroven(
    total_input,
    polozky,
    get_lock,
    get_pct,
    get_kc,
    total_lock=False,
    warnings=None,
    warning_prefix='',
):
    """Univerzální dopočet jedné úrovně (firma→prodejny nebo prodejna→kategorie).

    polozky – list nějakých dictů (prodejna nebo kategorie)
    get_lock(polozka) → 'none'|'pct'|'kc'
    get_pct(polozka)  → Decimal (vstupní podíl %)
    get_kc(polozka)   → Decimal (vstupní Kč, když lock='kc')

    Vrací (total_final, [{'podil_procenta': Decimal, 'castka': Decimal}, ...]).
    Warnings dopisuje do předaného listu.
    """
    if warnings is None:
        warnings = []

    if not polozky:
        return total_input, []

    # Rozdělení podle režimu zámku
    idx_pct, idx_kc, idx_auto = [], [], []
    for i, p in enumerate(polozky):
        m = get_lock(p)
        if m == LOCK_PCT:
            idx_pct.append(i)
        elif m == LOCK_KC:
            idx_kc.append(i)
        else:
            idx_auto.append(i)

    # Zamčené podíly (v %) a částky (v Kč)
    sum_locked_pct = sum((get_pct(polozky[i]) for i in idx_pct), ZERO)
    sum_locked_kc = sum((get_kc(polozky[i]) for i in idx_kc), ZERO)

    # Sanity – zamčená % přes 100 → poměrové zkrácení
    pct_scale = Decimal('1')
    if sum_locked_pct > HUNDRED:
        pct_scale = HUNDRED / sum_locked_pct
        warnings.append(
            f"{warning_prefix}Součet zamčených procent je {sum_locked_pct:.1f} %, "
            f"poměrově zkráceno na 100 %. Zamčené Kč jdou nad rámec."
        )
        sum_locked_pct = HUNDRED

    # Minimální celek, aby zamčené Kč + zamčená % seděly
    # total * (1 - sum_pct/100) >= sum_kc  →  total >= sum_kc / (1 - sum_pct/100)
    remaining_ratio = (HUNDRED - sum_locked_pct) / HUNDRED  # 0..1
    if remaining_ratio <= ZERO:
        min_total = sum_locked_kc  # pct-locked dá 0 Kč, kc-locked zabírá celek
    else:
        min_total = sum_locked_kc / remaining_ratio if sum_locked_kc > 0 else ZERO

    total = total_input if total_input and total_input > 0 else ZERO

    if total < min_total:
        if total_lock:
            # Respektujeme pevný celek – warning, ale nedoskakujeme
            rozdil = min_total - total
            warnings.append(
                f"{warning_prefix}Zamčené hodnoty přesahují pevný celek o "
                f"{_format_kc(rozdil)} Kč. Některé položky dostanou méně."
            )
        else:
            warnings.append(
                f"{warning_prefix}Celková částka automaticky dorovnána na "
                f"{_format_kc(min_total)} Kč kvůli zamčeným hodnotám."
            )
            total = min_total

    if total <= ZERO:
        # Nemáme z čeho dopočítávat – vrátíme nuly
        return ZERO, [{'podil_procenta': ZERO, 'castka': ZERO} for _ in polozky]

    # Kč-locked Kč (s případným ořezem, když total_lock omezuje)
    # Pokud total_lock=True a min_total > total, budou kc-locked dostávat poměrově
    kc_values = [get_kc(polozky[i]) for i in idx_kc]
    if total_lock and sum_locked_kc > 0 and sum_locked_kc > total:
        # kc-locked zabírá vše úměrně, pct & auto dostanou nulu
        kc_scale = total / sum_locked_kc
    else:
        kc_scale = Decimal('1')

    # Výpočet Kč pro pct-locked (po případném zkrácení přes 100 %)
    pct_values = [get_pct(polozky[i]) * pct_scale for i in idx_pct]
    sum_pct_after = sum(pct_values, ZERO)  # <=100

    kc_locked_sum_final = sum((v * kc_scale for v in kc_values), ZERO)
    pct_locked_sum_kc = total * sum_pct_after / HUNDRED

    zbytek_kc = total - kc_locked_sum_final - pct_locked_sum_kc
    if zbytek_kc < 0:
        # V kombinaci total_lock=True + zamčené přesahy může zbýt záporné – clampni na 0
        zbytek_kc = ZERO

    # Auto rozdělení
    auto_pct_sum_input = sum((get_pct(polozky[i]) for i in idx_auto), ZERO)

    # Připravíme výstupy
    out = [None] * len(polozky)

    # 1) kc-locked
    for k, i in enumerate(idx_kc):
        castka = kc_values[k] * kc_scale
        pct = (castka / total * HUNDRED) if total > 0 else ZERO
        out[i] = {'podil_procenta': pct, 'castka': castka}

    # 2) pct-locked
    for k, i in enumerate(idx_pct):
        pct = pct_values[k]
        castka = total * pct / HUNDRED
        out[i] = {'podil_procenta': pct, 'castka': castka}

    # 3) auto
    if idx_auto:
        if auto_pct_sum_input > 0:
            # Proporcionálně podle vstupních %
            for i in idx_auto:
                p_in = get_pct(polozky[i])
                podil_auto = (p_in / auto_pct_sum_input) if auto_pct_sum_input > 0 else ZERO
                castka = zbytek_kc * podil_auto
                pct = (castka / total * HUNDRED) if total > 0 else ZERO
                out[i] = {'podil_procenta': pct, 'castka': castka}
        else:
            # Rovnoměrně
            n = len(idx_auto)
            castka_rovnomerna = zbytek_kc / n if n > 0 else ZERO
            for i in idx_auto:
                pct = (castka_rovnomerna / total * HUNDRED) if total > 0 else ZERO
                out[i] = {'podil_procenta': pct, 'castka': castka_rovnomerna}

    return total, out


def _rozpocet_servis(castka_prodejna, servis_lock_mode, castka_prodej_input, castka_servis_input):
    """Dopočet prodej/servis dle servis_lock_mode.

    - 'kc': drží absolutní castka_servis_input (clamp 0..castka_prodejna), prodej = zbytek.
    - 'pct': drží poměr servisu podle zadaných Kč (rel. k celkovému prodejna vstupu).
    - 'none': default 70/30.
    """
    total = castka_prodejna
    if total <= 0:
        return ZERO, ZERO

    mode = _normalize_lock(servis_lock_mode)

    if mode == LOCK_KC:
        servis = max(ZERO, min(total, castka_servis_input))
        prodej = total - servis
        return prodej, servis

    if mode == LOCK_PCT:
        soucet_vstup = castka_prodej_input + castka_servis_input
        if soucet_vstup > 0:
            ratio = castka_servis_input / soucet_vstup
        else:
            ratio = Decimal('0.3')
        servis = total * ratio
        prodej = total - servis
        return prodej, servis

    # none → default 70 % prodej / 30 % servis
    # Ale pokud má uživatel rozumné hodnoty, respektujeme jejich poměr.
    soucet_vstup = castka_prodej_input + castka_servis_input
    if soucet_vstup > 0:
        ratio = castka_servis_input / soucet_vstup
    else:
        ratio = Decimal('0.3')
    servis = total * ratio
    prodej = total - servis
    return prodej, servis


def rozpoctij(castka_celkem_input, prodejny_input, total_lock=False):
    """Hlavní přepočet plánu.

    Args:
        castka_celkem_input: Decimal | number | str – celek zadaný uživatelem.
        prodejny_input: list[dict] s klíči:
            prodejna_id, podil_procenta, castka_prodejna,
            lock_mode, servis_lock_mode,
            castka_prodej, castka_servis,
            kategorie: list[dict{kategorie_kod, podil_procenta, castka_kategorie, lock_mode,
                                  prumerna_cena_za_kus?}].
        total_lock: bool – pokud True, celek se nedorovnává automaticky.

    Returns:
        dict viz docstring modulu.
    """
    warnings = []
    castka_celkem_input_d = _D(castka_celkem_input)

    # 1) Dopočet úrovně prodejen
    total_final, pd_out = _rozpocet_uroven(
        total_input=castka_celkem_input_d,
        polozky=prodejny_input,
        get_lock=lambda p: _normalize_lock(p.get('lock_mode')),
        get_pct=lambda p: _D(p.get('podil_procenta')),
        get_kc=lambda p: _D(p.get('castka_prodejna')),
        total_lock=total_lock,
        warnings=warnings,
        warning_prefix='',
    )

    prodejny_result = []
    soucet_zamk_pct = ZERO
    soucet_zamk_kc = ZERO
    soucet_auto_pct = ZERO

    for p_in, p_out in zip(prodejny_input, pd_out):
        lock = _normalize_lock(p_in.get('lock_mode'))
        servis_lock = _normalize_lock(p_in.get('servis_lock_mode'))

        castka_p = _qmoney(p_out['castka'])
        podil_p = _qpct(p_out['podil_procenta'])

        if lock == LOCK_PCT:
            soucet_zamk_pct += podil_p
        elif lock == LOCK_KC:
            soucet_zamk_kc += castka_p
        else:
            soucet_auto_pct += podil_p

        # 2) Dopočet kategorií v rámci prodejny
        kat_in = p_in.get('kategorie', []) or []
        prodejna_nazev = p_in.get('prodejna_nazev') or f"Prodejna {p_in.get('prodejna_id', '?')}"
        _, kat_out = _rozpocet_uroven(
            total_input=castka_p,
            polozky=kat_in,
            get_lock=lambda k: _normalize_lock(k.get('lock_mode')),
            get_pct=lambda k: _D(k.get('podil_procenta')),
            get_kc=lambda k: _D(k.get('castka_kategorie')),
            total_lock=True,  # částka prodejny je pevná, kategorie dorovnávají uvnitř
            warnings=warnings,
            warning_prefix=f"{prodejna_nazev}: ",
        )

        kategorie_result = []
        for k_in, k_out in zip(kat_in, kat_out):
            kategorie_result.append({
                'kategorie_kod': k_in.get('kategorie_kod'),
                'podil_procenta': _qpct(k_out['podil_procenta']),
                'castka_kategorie': _qmoney(k_out['castka']),
                'lock_mode': _normalize_lock(k_in.get('lock_mode')),
                'prumerna_cena_za_kus': k_in.get('prumerna_cena_za_kus'),
            })

        # 3) Dopočet prodej/servis
        castka_prodej_in = _D(p_in.get('castka_prodej'))
        castka_servis_in = _D(p_in.get('castka_servis'))
        prodej, servis = _rozpocet_servis(
            castka_p, servis_lock, castka_prodej_in, castka_servis_in
        )
        prodej = _qmoney(prodej)
        servis = _qmoney(servis)

        prodejny_result.append({
            'prodejna_id': p_in.get('prodejna_id'),
            'prodejna_nazev': p_in.get('prodejna_nazev'),
            'podil_procenta': podil_p,
            'castka_prodejna': castka_p,
            'castka_prodej': prodej,
            'castka_servis': servis,
            'lock_mode': lock,
            'servis_lock_mode': servis_lock,
            'kategorie': kategorie_result,
        })

    soucet_castek = sum((p['castka_prodejna'] for p in prodejny_result), ZERO)
    soucet_podilu = sum((p['podil_procenta'] for p in prodejny_result), ZERO)

    return {
        'castka_celkem': _qmoney(total_final),
        'castka_celkem_input': _qmoney(castka_celkem_input_d),
        'total_lock': bool(total_lock),
        'soucet_podilu': _qpct(soucet_podilu),
        'soucet_castek': _qmoney(soucet_castek),
        'soucet_zamk_pct': _qpct(soucet_zamk_pct),
        'soucet_zamk_kc': _qmoney(soucet_zamk_kc),
        'soucet_auto_pct': _qpct(soucet_auto_pct),
        'warnings': warnings,
        'prodejny': prodejny_result,
    }
