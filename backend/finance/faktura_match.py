"""Porovnání vyčtené faktury s očekáváním z pokladny."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from .models import FinanceDoklad, NakladPolozka
from .symplio_vydej_parse import faktura_hint_from_polozka


def _norm_fa(value: str) -> str:
    return re.sub(r'[\s\-_/]', '', (value or '').upper())


def _norm_name(value: str) -> str:
    return re.sub(r'\s+', ' ', (value or '').strip().lower())


def _to_decimal(value) -> Decimal | None:
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value).replace(',', '.').replace(' ', '')).copy_abs()
    except (InvalidOperation, ValueError):
        return None


def match_doklad_to_polozka(doklad: FinanceDoklad, polozka: NakladPolozka | None) -> dict:
    """
    Vrátí {stav: ok|warn|fail, checks: [...], hint: {...}}.
    Nikdy automaticky neschvaluje – jen scoring pro admina.
    """
    hint = faktura_hint_from_polozka(polozka) if polozka else None
    checks = []
    worst = FinanceDoklad.MATCH_OK

    def add_check(name: str, stav: str, ocekavano: str, nalezeno: str, detail: str = ''):
        nonlocal worst
        checks.append({
            'pole': name,
            'stav': stav,
            'ocekavano': ocekavano,
            'nalezeno': nalezeno,
            'detail': detail,
        })
        if stav == FinanceDoklad.MATCH_FAIL:
            worst = FinanceDoklad.MATCH_FAIL
        elif stav == FinanceDoklad.MATCH_WARN and worst != FinanceDoklad.MATCH_FAIL:
            worst = FinanceDoklad.MATCH_WARN

    if hint:
        o_fa = hint.get('cislo_faktury', '')
        n_fa = doklad.cislo_faktury or ''
        if o_fa and n_fa:
            if _norm_fa(o_fa) == _norm_fa(n_fa):
                add_check('cislo_faktury', FinanceDoklad.MATCH_OK, o_fa, n_fa)
            elif _norm_fa(o_fa) in _norm_fa(n_fa) or _norm_fa(n_fa) in _norm_fa(o_fa):
                add_check('cislo_faktury', FinanceDoklad.MATCH_WARN, o_fa, n_fa, 'Částečná shoda')
            else:
                add_check('cislo_faktury', FinanceDoklad.MATCH_FAIL, o_fa, n_fa)
        elif o_fa and not n_fa:
            add_check('cislo_faktury', FinanceDoklad.MATCH_WARN, o_fa, '–', 'OCR nenašlo číslo FA')

        o_dod = hint.get('dodavatel_nazev', '')
        n_dod = doklad.dodavatel_nazev or ''
        if o_dod and n_dod:
            on, nn = _norm_name(o_dod), _norm_name(n_dod)
            if on == nn or on in nn or nn in on:
                add_check('dodavatel', FinanceDoklad.MATCH_OK, o_dod, n_dod)
            else:
                add_check('dodavatel', FinanceDoklad.MATCH_WARN, o_dod, n_dod)
        elif o_dod and not n_dod:
            add_check('dodavatel', FinanceDoklad.MATCH_WARN, o_dod, '–', 'OCR nenašlo dodavatele')

        o_castka = _to_decimal(hint.get('castka_celkem'))
        n_castka = _to_decimal(doklad.castka_celkem)
        if (
            n_castka is None
            and doklad.castka_bez_dph is not None
            and doklad.dph_castka is not None
        ):
            n_castka = doklad.castka_bez_dph + doklad.dph_castka
        if polozka and o_castka is None:
            o_castka = _to_decimal(polozka.castka)
        if o_castka and n_castka:
            diff = abs(o_castka - n_castka)
            if diff <= Decimal('1'):
                add_check('castka_celkem', FinanceDoklad.MATCH_OK, str(o_castka), str(n_castka))
            elif diff <= Decimal('5'):
                add_check('castka_celkem', FinanceDoklad.MATCH_WARN, str(o_castka), str(n_castka), f'Rozdíl {diff} Kč')
            else:
                add_check('castka_celkem', FinanceDoklad.MATCH_FAIL, str(o_castka), str(n_castka), f'Rozdíl {diff} Kč')
        elif o_castka and not n_castka:
            add_check('castka_celkem', FinanceDoklad.MATCH_WARN, str(o_castka), '–', 'OCR nenašlo částku')

    if doklad.castka_bez_dph is not None and doklad.dph_castka is not None and doklad.castka_celkem is not None:
        soucet = doklad.castka_bez_dph + doklad.dph_castka
        if abs(soucet - doklad.castka_celkem) > Decimal('1'):
            add_check(
                'dph_soucet', FinanceDoklad.MATCH_FAIL,
                str(doklad.castka_celkem), str(soucet),
                'Základ + DPH ≠ celkem',
            )

    if not checks:
        worst = FinanceDoklad.MATCH_WARN
        checks.append({
            'pole': 'hint',
            'stav': FinanceDoklad.MATCH_WARN,
            'ocekavano': '–',
            'nalezeno': '–',
            'detail': 'Chybí očekávání z pokladny (Fio nebo jiný výdej)',
        })

    return {'stav': worst, 'checks': checks, 'hint': hint}
