"""Výkupy 0 % a návrh účtování bazaru. Zápis jde na samostatný list, původní se nemaže."""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from .secrets import _resolve_secret_file, get_ucetni_config
from .ucetni_pravidla import bez_diakritiky

logger = logging.getLogger(__name__)

_MONEY = Decimal('0.01')
_DPH_MARZE = Decimal('21') / Decimal('121')
_TOLERANCE = Decimal('0.02')
_DOPRAVA = ('doprava', 'dopravn', 'postov', 'postovne', 'zasilk', 'shipping')

HLAVICKA = [
    'datum', 'doklad', 'nazev', 'kategorie', 'pocet',
    'cena_bez_dph', 'nakupni_cena', 'zisk', 'stredisko', 'dph',
]


def _dec(value) -> Decimal | None:
    if value is None or value == '':
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _money(value: Decimal) -> str:
    return f'{value.quantize(_MONEY, rounding=ROUND_HALF_UP):.2f}'


def _pocet(value) -> Decimal:
    parsed = _dec(value)
    if parsed is None:
        return Decimal('1')
    return parsed


def je_nulove_dph(bez, s_dph) -> bool | None:
    base = _dec(bez)
    gross = _dec(s_dph)
    if base is None or gross is None:
        return None
    return abs(base - gross) <= _TOLERANCE


def druh_radku(*, nazev: str = '', kategorie: str = '', bez=None, s_dph=None) -> str:
    nulove = je_nulove_dph(bez, s_dph)
    if nulove is None:
        return 'nejisty'
    text = bez_diakritiky(f'{nazev} {kategorie}')
    if any(word in text for word in _DOPRAVA):
        return 'doprava'
    if nulove:
        return 'bazar'
    return 'prislusenstvi'


def radek_prodeje(raw: dict) -> dict:
    pocet = _pocet(raw.get('pocet'))
    bez_ks = _dec(raw.get('cena_bez_dph'))
    s_ks = _dec(raw.get('cena_s_dph'))
    nakup_ks = _dec(raw.get('nakupni'))
    zisk_ks = _dec(raw.get('zisk'))
    nulove = je_nulove_dph(bez_ks, s_ks)
    druh = druh_radku(
        nazev=str(raw.get('nazev') or ''),
        kategorie=str(raw.get('kategorie') or ''),
        bez=bez_ks,
        s_dph=s_ks,
    )
    cena = (bez_ks or Decimal('0')) * pocet
    nakup = (nakup_ks or Decimal('0')) * pocet if nakup_ks is not None else None
    if zisk_ks is not None:
        zisk = zisk_ks * pocet
    elif nakup is not None and bez_ks is not None:
        zisk = cena - nakup
    else:
        zisk = None
    datum = raw.get('datum') or ''
    if hasattr(datum, 'isoformat'):
        datum = datum.isoformat()
    if pocet == pocet.to_integral_value():
        pocet_text = str(int(pocet))
    else:
        pocet_text = _money(pocet)
    return {
        'datum': str(datum)[:10],
        'doklad': str(raw.get('doklad') or '').strip(),
        'nazev': str(raw.get('nazev') or '').strip(),
        'kategorie': str(raw.get('kategorie') or '').strip(),
        'pocet': pocet_text,
        'cena_bez_dph': _money(cena) if bez_ks is not None else None,
        'nakupni_cena': _money(nakup) if nakup is not None else None,
        'zisk': _money(zisk) if zisk is not None else None,
        'stredisko': str(raw.get('stredisko') or '').strip(),
        'druh': druh,
        'dph_nula': nulove,
    }


def _dph_znacka(radek: dict) -> str:
    if radek.get('dph_nula') is None:
        return 'nejisto'
    return '0' if radek['dph_nula'] else '21'


def normalizuj_radky(raw_rows: list[dict]) -> list[dict]:
    rows = []
    for raw in raw_rows:
        row = radek_prodeje(raw)
        row['dph'] = _dph_znacka(row)
        rows.append(row)
    return rows


def radky_nula(radky: list[dict]) -> list[dict]:
    return [row for row in radky if row.get('dph') == '0']


def souhrn_bazaru(radky: list[dict]) -> dict:
    nakup = Decimal('0')
    zisk = Decimal('0')
    pocet = 0
    for row in radky:
        if row.get('druh') != 'bazar':
            continue
        pocet += 1
        if row.get('nakupni_cena') is not None:
            nakup += Decimal(row['nakupni_cena'])
        if row.get('zisk') is not None:
            zisk += Decimal(row['zisk'])
    dph = (zisk * _DPH_MARZE).quantize(_MONEY, rounding=ROUND_HALF_UP) if zisk > 0 else Decimal('0.00')
    return {
        'radku': pocet,
        'nakupni_cena': _money(nakup),
        'zisk': _money(zisk),
        'dph': _money(dph),
        'vzorec_dph': 'zisk × 21 / 121',
    }


def navrh_uctovani(lines: list[dict]) -> dict | None:
    if not any(row.get('druh') == 'bazar' for row in lines):
        return None
    if any(row.get('druh') == 'nejisty' for row in lines):
        return {
            'predpis': '',
            'nejisty': True,
            'popis': 'Nejasná položka. Účtenka zůstává ve frontě.',
        }
    druhy = {row.get('druh') for row in lines}
    doklad = lines[0].get('doklad') or ''
    if druhy <= {'bazar', 'doprava'}:
        doprava = 'doprava' in druhy
        return {
            'doklad': doklad,
            'predpis': '604200',
            'nejisty': False,
            'md': '604200',
            'dph': '0',
            'kontrolni_hlaseni': '0',
            'doprava_dph': '0' if doprava else None,
            'popis': (
                'Jen bazar a doprava. Doprava je 0 % a předpis 604200.'
                if doprava else
                'Jen telefon. Předpis 604200, kontrolní hlášení 0, DPH 0.'
            ),
        }
    if druhy <= {'bazar', 'prislusenstvi'}:
        return {
            'doklad': doklad,
            'predpis': 'mix',
            'nejisty': False,
            'bazar': {'ucet': '604200', 'dph': '0', 'kontrolni_hlaseni': '0'},
            'prislusenstvi': {'ucet': '604001', 'dph': '1-2', 'kontrolni_hlaseni': 'A4-5.AUTO'},
            'popis': 'Příslušenství 604001, DPH 1-2, KH A4-5.AUTO. Pak znovu 604200 jen na bazar.',
        }
    return {
        'doklad': doklad,
        'predpis': '',
        'nejisty': True,
        'popis': 'Na účtence je bazar, příslušenství i doprava. Zůstává ve frontě.',
    }


def navrhy_bazaru(radky: list[dict]) -> list[dict]:
    skupiny: dict[str, list] = defaultdict(list)
    bez_dokladu = 0
    for row in radky:
        if not row.get('doklad'):
            if row.get('druh') == 'bazar':
                bez_dokladu += 1
            continue
        skupiny[row['doklad']].append(row)
    navrhy = []
    for lines in skupiny.values():
        navrh = navrh_uctovani(lines)
        if navrh:
            navrhy.append(navrh)
    if bez_dokladu:
        navrhy.append({
            'doklad': '',
            'predpis': '',
            'nejisty': True,
            'popis': f'{bez_dokladu} řádků bazaru bez čísla dokladu zůstává ve frontě.',
        })
    return navrhy


def tabulka_vykupu(radky: list[dict]) -> list[list]:
    telo = []
    for row in radky_nula(radky):
        telo.append([
            row.get('datum') or '',
            row.get('doklad') or '',
            row.get('nazev') or '',
            row.get('kategorie') or '',
            row.get('pocet') or '',
            row.get('cena_bez_dph') or '',
            row.get('nakupni_cena') or '',
            row.get('zisk') or '',
            row.get('stredisko') or '',
            '0',
        ])
    return telo


def priprav_vykupy(raw_rows: list[dict]) -> dict:
    radky = normalizuj_radky(raw_rows)
    nula = tabulka_vykupu(radky)
    navrhy = navrhy_bazaru(radky)
    return {
        'radky_nula': nula,
        'pocet_nula': len(nula),
        'souhrn': souhrn_bazaru(radky),
        'bazary': navrhy,
        'nejistych': sum(1 for row in navrhy if row.get('nejisty')),
    }


def nacti_radky_prodeje(rok: int, mesic: int) -> list[dict]:
    from calendar import monthrange

    from analytics.models import WebProdejeAll

    start = date(rok, mesic, 1)
    end = date(rok, mesic, monthrange(rok, mesic)[1])
    qs = WebProdejeAll.objects.filter(typ__gte=start, typ__lte=end).iterator(chunk_size=500)
    rows = []
    for item in qs:
        rows.append({
            'datum': item.typ,
            'doklad': item.doklad,
            'nazev': item.nazev,
            'kategorie': item.kategorie or item.kategorie_1 or '',
            'pocet': item.pocet_kusu,
            'cena_bez_dph': item.cena_ks_bez_dph,
            'cena_s_dph': item.cena_ks_vcl_dph,
            'nakupni': item.skladova_cena_bez_dph,
            'zisk': item.zisk,
            'stredisko': item.stredisko,
        })
    return rows


def _google_append(values: list[list], config: dict) -> dict:
    path = _resolve_secret_file(config.get('credentials_file') or '')
    if not path.is_file():
        return {'ok': False, 'skipped': True, 'reason': 'chybi_credentials'}
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_file(
        str(path),
        scopes=['https://www.googleapis.com/auth/spreadsheets'],
    )
    service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
    spreadsheet_id = config['spreadsheet_id']
    title = config['sheet_name']
    meta = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        fields='sheets.properties',
    ).execute()
    titles = [
        (sheet.get('properties') or {}).get('title')
        for sheet in meta.get('sheets') or []
    ]
    if title not in titles:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': [{'addSheet': {'properties': {'title': title}}}]},
        ).execute()
    existing = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{title}'!A1:A1",
    ).execute()
    payload = []
    if not existing.get('values'):
        payload.append(HLAVICKA)
    payload.extend(values)
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"'{title}'!A1",
        valueInputOption='USER_ENTERED',
        insertDataOption='INSERT_ROWS',
        body={'values': payload},
    ).execute()
    return {
        'ok': True,
        'spreadsheet_id': spreadsheet_id,
        'sheet': title,
        'pocet': len(values),
    }


def zapsat_vykupy(raw_rows: list[dict], *, writer=None) -> dict:
    priprava = priprav_vykupy(raw_rows)
    values = priprava['radky_nula']
    config = get_ucetni_config()
    if not values:
        return {**priprava, 'zapis': {'ok': False, 'skipped': True, 'reason': 'prazdne'}}
    try:
        zapis = (writer or _google_append)(values, config)
    except Exception as exc:
        logger.warning('Zápis výkupů do tabulky selhal: %s', exc)
        zapis = {'ok': False, 'error': str(exc)[:300]}
    return {**priprava, 'zapis': zapis}
