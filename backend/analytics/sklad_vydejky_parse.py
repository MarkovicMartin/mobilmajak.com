"""Parsování řádků skladových výdejek ze Symplia (XLSX doklady, HTML položky)."""
from __future__ import annotations

import re
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation

VYDEJKA_ALLOWED_SUBTYPES = frozenset({20, 25, 202, 252, 204, 254})

PODTYP_TO_SUBTYPE: dict[str, int] = {
    'Vyskladnění z hlavního skladu - ruční': 20,
    'Vyskladnění z komisního skladu - ruční': 25,
    'Vyskladnění z hlavního skladu - reklamace': 202,
    'Vyskladnění z komisního skladu - reklamace': 252,
    'Vyskladnění z hlavního skladu - spotřeba': 204,
    'Vyskladnění z komisního skladu - spotřeba': 254,
}

SUBTYPE_DUVOD_KATEGORIE: dict[int, str] = {
    20: 'rucni', 25: 'rucni',
    202: 'reklamace', 252: 'reklamace',
    204: 'spotreba', 254: 'spotreba',
}

SUBTYPE_SKLAD_TYP: dict[int, str] = {
    20: 'hlavni', 25: 'komisni',
    202: 'hlavni', 252: 'komisni',
    204: 'hlavni', 254: 'komisni',
}

DUVOD_KATEGORIE_LABELS = {
    'rucni': 'Ruční',
    'spotreba': 'Spotřeba',
    'reklamace': 'Reklamace',
}

SKLAD_TYP_LABELS = {
    'hlavni': 'Hlavní sklad',
    'komisni': 'Komisní sklad',
}

_DOKLAD_RE = re.compile(r'(S\d+)\s*$')


def parse_doklad_cislo(nazev: str | None) -> str | None:
    if not nazev:
        return None
    text = str(nazev).strip()
    m = _DOKLAD_RE.search(text.replace('\xa0', ' '))
    if m:
        return m.group(1)
    if text.startswith('S') and text[1:].isdigit():
        return text
    return None


def parse_czech_date(value) -> date | None:
    if value is None or value == '':
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip().replace('\xa0', ' ')
    for fmt in ('%d. %m. %Y', '%d.%m.%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_czech_time(value) -> time | None:
    if value is None or value == '':
        return None
    if isinstance(value, time):
        return value
    text = str(value).strip()
    for fmt in ('%H:%M:%S', '%H:%M'):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def parse_decimal(value) -> Decimal | None:
    if value is None or value == '':
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    text = str(value).strip().replace('\xa0', ' ').replace(' ', '').replace('Kč', '').replace(',', '.')
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def resolve_subtype(podtyp: str | None) -> int | None:
    if not podtyp:
        return None
    text = str(podtyp).strip()
    if text in PODTYP_TO_SUBTYPE:
        return PODTYP_TO_SUBTYPE[text]
    lowered = text.lower()
    is_komisni = 'komisní' in lowered or 'komisni' in lowered
    if 'ruční' in lowered or 'rucni' in lowered:
        return 25 if is_komisni else 20
    if 'spotřeba' in lowered or 'spotreba' in lowered:
        return 254 if is_komisni else 204
    if 'reklamace' in lowered:
        return 252 if is_komisni else 202
    return None


def parse_doklad_xlsx_row(row: list) -> dict | None:
    """Řádek z stock-document-list.xlsx."""
    if not row or len(row) < 5:
        return None
    nazev = row[0]
    doklad = parse_doklad_cislo(nazev if isinstance(nazev, str) else str(nazev or ''))
    if not doklad:
        return None
    podtyp = str(row[1] or '').strip()
    subtype = resolve_subtype(podtyp)
    if subtype is None or subtype not in VYDEJKA_ALLOWED_SUBTYPES:
        return None
    vystaveno = parse_czech_date(row[4])
    if not vystaveno:
        return None
    vazba_raw = row[2]
    vazba = str(vazba_raw).strip() if vazba_raw not in (None, '') else None
    spravce = str(row[3] or '').strip() or None
    castka_s = parse_decimal(row[7] if len(row) > 7 else None)
    castka_b = parse_decimal(row[8] if len(row) > 8 else None)
    return {
        'doklad': doklad,
        'vystaveno': vystaveno,
        'symplio_subtype': subtype,
        'duvod_vyskladneni': podtyp,
        'sklad_typ': SUBTYPE_SKLAD_TYP[subtype],
        'duvod_kategorie': SUBTYPE_DUVOD_KATEGORIE[subtype],
        'spravce': spravce,
        'vazba': vazba,
        'castka_s_dph': float(castka_s or 0),
        'castka_bez_dph': float(castka_b or castka_s or 0),
    }


def parse_polozka_html_cells(cells: list[str]) -> dict | None:
    """
    Buňky z HTML tabulky /sklady/doklady/polozky.
    [Vystaveno, Kód, Název, Doklad, Objednávka, Jméno, Počet kusů, DPH, Cena ks, Cena ks bez, Cena celkem]
    """
    if len(cells) < 7:
        return None
    doklad = str(cells[3] or '').strip()
    if not doklad.startswith('S'):
        return None
    kod = str(cells[1] or '').strip() or None
    vystaveno = parse_czech_date(cells[0])
    pocet_raw = str(cells[6] or '').replace('\xa0', '').replace(' ', '')
    try:
        pocet = int(pocet_raw)
    except ValueError:
        pocet = 0
    cena_ks = parse_decimal(cells[9] if len(cells) > 9 else None)
    cena_celkem = parse_decimal(cells[10] if len(cells) > 10 else None)
    return {
        'doklad': doklad,
        'kod': kod,
        'nazev': str(cells[2] or '').strip() or None,
        'pocet_kusu': pocet,
        'cena_ks_bez_dph': float(cena_ks) if cena_ks is not None else None,
        'cena_celkem_bez_dph': float(cena_celkem) if cena_celkem is not None else None,
        'stredisko': None,
        'spravce': None,
        'vystaveno': vystaveno.isoformat() if vystaveno else None,
        'cas_prodeje': None,
    }
