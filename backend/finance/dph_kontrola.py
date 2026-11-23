"""Kontrola před podáním DPH a tři interní doklady z výkupů."""
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from .vykupy import priprav_vykupy

_MONEY = Decimal('0.01')
_TOLERANCE = Decimal('1.00')


def posledni_den(rok: int, mesic: int) -> date:
    return date(rok, mesic, monthrange(rok, mesic)[1])


def termin_dph(rok: int, mesic: int) -> date:
    """25. dne následujícího měsíce. Sobota a neděle se posouvají na pondělí."""
    if mesic == 12:
        den = date(rok + 1, 1, 25)
    else:
        den = date(rok, mesic + 1, 25)
    if den.weekday() == 5:
        return den + timedelta(days=2)
    if den.weekday() == 6:
        return den + timedelta(days=1)
    return den


def _castka(value) -> Decimal | None:
    if value is None or value == '':
        return None
    try:
        return Decimal(str(value).replace(',', '.').replace(' ', ''))
    except (InvalidOperation, ValueError):
        return None


def interni_doklady(souhrn: dict, den: date) -> list[dict]:
    nakup = _castka(souhrn.get('nakupni_cena')) or Decimal('0')
    zisk = _castka(souhrn.get('zisk')) or Decimal('0')
    dph = _castka(souhrn.get('dph')) or Decimal('0')
    vystaveno = den.isoformat()
    return [
        {
            'radek': 1,
            'nazev': 'Nákupní cena bazarovek',
            'castka': f'{nakup.quantize(_MONEY, rounding=ROUND_HALF_UP):.2f}',
            'vystaveno': vystaveno,
        },
        {
            'radek': 2,
            'nazev': 'Provize – zisk z bazarovek',
            'castka': f'{zisk.quantize(_MONEY, rounding=ROUND_HALF_UP):.2f}',
            'vystaveno': vystaveno,
        },
        {
            'radek': 3,
            'nazev': 'Zaúčtování provize – DPH bazarovek',
            'castka': f'{(-dph).quantize(_MONEY, rounding=ROUND_HALF_UP):.2f}',
            'vystaveno': vystaveno,
        },
    ]


def porovnej_obrat(*, priznani=None, vynosy=None, cisty_zisk=None) -> dict:
    dan = _castka(priznani)
    obrat = _castka(vynosy)
    zisk = _castka(cisty_zisk)
    delta = None
    sedi = None
    if dan is not None and obrat is not None:
        delta = (dan - obrat).quantize(_MONEY, rounding=ROUND_HALF_UP)
        sedi = abs(delta) <= _TOLERANCE
    if dan is None or obrat is None:
        dalsi = 'Doplňte řádek 1 z přiznání a výnosy z výkazu hospodaření.'
    elif not sedi:
        dalsi = 'Nesedí. Hledat chybu v pohybech na účtu.'
    else:
        dalsi = 'Řádek přiznání a výnosy sedí.'
    return {
        'priznani': f'{dan:.2f}' if dan is not None else None,
        'vynosy': f'{obrat:.2f}' if obrat is not None else None,
        'cisty_zisk': f'{zisk:.2f}' if zisk is not None else None,
        'delta_priznani_vynosy': f'{delta:.2f}' if delta is not None else None,
        'sedi': sedi,
        'dalsi_krok': dalsi,
    }


def _polozka(kod: str, nazev: str, stav: str, detail: str) -> dict:
    return {'kod': kod, 'nazev': nazev, 'stav': stav, 'detail': detail}


def kontrola_pred_dph(
    *,
    rok: int,
    mesic: int,
    radky: list[dict],
    prijate_otevrene: int,
    pokladna_pohybu: int,
    vydane_flexi: int | None,
    prodejnich_dokladu: int,
    priznani=None,
    vynosy=None,
    cisty_zisk=None,
    allegro: str = '',
) -> dict:
    priprava = priprav_vykupy(radky)
    souhrn = priprava['souhrn']
    den = posledni_den(rok, mesic)
    nejistych = priprava['nejistych']
    polozky = [
        _polozka(
            'prijate',
            'Přijaté faktury',
            'ok' if prijate_otevrene == 0 else 'chybi',
            'Všechny přijaté v období jsou ve Flexi.' if prijate_otevrene == 0
            else f'{prijate_otevrene} přijatých ještě není ve Flexi.',
        ),
        _polozka(
            'pokladna',
            'Pokladna',
            'ok' if pokladna_pohybu else 'chybi',
            f'{pokladna_pohybu} pohybů z pokladny Symplio.' if pokladna_pohybu
            else 'Za měsíc není žádný pokladní pohyb.',
        ),
        _polozka(
            'vykupy',
            'Výkupy',
            'ok' if priprava['pocet_nula'] else 'chybi',
            f'{priprava["pocet_nula"]} řádků s DPH 0 %.' if priprava['pocet_nula']
            else 'Chybí řádky výkupů s DPH 0 %.',
        ),
        _polozka(
            'vydane',
            'Vydané faktury',
            'nezjisteno' if vydane_flexi is None else ('ok' if vydane_flexi else 'chybi'),
            'Flexi nevrátilo počet vydaných faktur. Podání zůstává na člověku.'
            if vydane_flexi is None else (
                f'{vydane_flexi} vydaných faktur ve Flexi.' if vydane_flexi
                else 'Ve Flexi není za měsíc žádná vydaná faktura.'
            ),
        ),
        _polozka(
            'symplio',
            'Prodejní doklady',
            'ok' if prodejnich_dokladu else 'chybi',
            f'{prodejnich_dokladu} dokladů v prodeji.' if prodejnich_dokladu
            else 'V prodeji za měsíc nejsou doklady.',
        ),
        _polozka(
            'bazar',
            'Účtování bazaru',
            'ok' if nejistych == 0 else 'chybi',
            'Předpisy 604200 a 604001 jsou jasné.' if nejistych == 0
            else f'{nejistych} účtenek zůstává ve frontě.',
        ),
    ]
    pripraveno = all(row['stav'] == 'ok' for row in polozky)
    return {
        'obdobi': f'{rok:04d}-{mesic:02d}',
        'termin': termin_dph(rok, mesic).isoformat(),
        'pripraveno': pripraveno,
        'podani': 'Přiznání, kontrolní hlášení a souhrnné hlášení podává člověk.',
        'polozky': polozky,
        'interni_doklady': interni_doklady(souhrn, den),
        'souhrn_bazaru': souhrn,
        'bazary': priprava['bazary'][:50],
        'bazaru_celkem': len(priprava['bazary']),
        'nejistych': nejistych,
        'vykupy_nula': priprava['pocet_nula'],
        'obrat': porovnej_obrat(priznani=priznani, vynosy=vynosy, cisty_zisk=cisty_zisk),
        'allegro': {
            'akce': 'Posunout řádek VF Allegro nahoru a pod něj dopsat novou fakturu.',
            'nova_fa': (allegro or '').strip(),
        },
    }
