"""Parser CSV z admin.packeta.com/commission/."""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

EXPECTED_HEADERS_CZ = ['Datum a čas', 'Zásilka', 'Typ provize', 'Částka', 'Měna', 'Poznámka']
EXPECTED_HEADERS_EN = ['Date and time', 'Packet', 'Type of commission', 'Amount', 'Currency', 'Note']

PACKETA_MAIN_VISIT_TYPES = frozenset({
    'Zpracování zásilky',
    'Zpracování nadrozměrné zásilky',
    'Podání',
    'Podání C2C',
    # anglický export z admin.packeta.com
    'Consignment',
    'Oversized consignment',
    'Received package',
    'C2C consignment',
})

_TYPE_EN_TO_CZ = {
    'Consignment': 'Zpracování zásilky',
    'Oversized consignment': 'Zpracování nadrozměrné zásilky',
    'Received oversize package': 'Zpracování nadrozměrné zásilky',
    'Received package': 'Podání',
    'C2C consignment': 'Podání C2C',
    'C2C Consignment': 'Podání C2C',
}

# Hodnoty <select id="type"> v admin.packeta.com – jen typy určující počet balíků
PACKETA_TYPE_PODANI = ('1', '17')       # Podání, Podání C2C
PACKETA_TYPE_VYDANE = ('5', '11')       # Zpracování zásilky, nadrozměrná
PACKETA_TYPE_BALIKY = PACKETA_TYPE_PODANI + PACKETA_TYPE_VYDANE

PACKETA_TYPE_LABELS = {
    '1': 'Podání',
    '17': 'Podání C2C',
    '5': 'Zpracování zásilky',
    '11': 'Zpracování nadrozměrné zásilky',
}


def type_values_for_preset(preset: str) -> tuple[str, ...]:
    if preset == 'podani':
        return PACKETA_TYPE_PODANI
    if preset == 'vydane':
        return PACKETA_TYPE_VYDANE
    return PACKETA_TYPE_BALIKY


_DATE_RE = re.compile(
    r'^(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4}),\s*(\d{1,2}):(\d{2})$'
)
_DATE_EN_RE = re.compile(
    r'^(\d{1,2})-(\d{1,2})-(\d{4}),\s*(\d{1,2}):(\d{2})$'
)


def normalize_zasilka(raw: str) -> str:
    s = (raw or '').strip()
    s = re.sub(r'\s+', ' ', s)
    return s


def parse_packeta_datetime(value: str) -> datetime:
    raw = (value or '').strip().strip('"')
    m = _DATE_RE.match(raw) or _DATE_EN_RE.match(raw)
    if not m:
        raise ValueError(f'Neplatný formát data: {value!r}')
    day, month, year, hour, minute = map(int, m.groups())
    return datetime(year, month, day, hour, minute)


def normalize_typ_provize(raw: str) -> str:
    s = (raw or '').strip().strip('"')
    return _TYPE_EN_TO_CZ.get(s, s)


def parse_castka(value: str) -> Decimal:
    s = (value or '').strip().replace('\xa0', '').replace(' ', '')
    s = s.replace(',', '.')
    try:
        return Decimal(s)
    except InvalidOperation as exc:
        raise ValueError(f'Neplatná částka: {value!r}') from exc


def parse_packeta_csv(content: str | bytes) -> list[dict]:
    if isinstance(content, bytes):
        text = content.decode('utf-8-sig')
    else:
        text = content.lstrip('\ufeff')

    reader = csv.reader(io.StringIO(text), delimiter=';')
    rows = list(reader)
    if not rows:
        return []

    header = [h.strip().strip('"') for h in rows[0]]
    if header[:6] not in (EXPECTED_HEADERS_CZ, EXPECTED_HEADERS_EN):
        raise ValueError(
            f'Neočekávaná hlavička CSV. Očekáváno CZ nebo EN, nalezeno: {header}'
        )

    parsed = []
    for i, row in enumerate(rows[1:], start=2):
        if not row or all(not (c or '').strip().strip('"') for c in row):
            continue
        while len(row) < 6:
            row.append('')
        row = [c.strip().strip('"') for c in row]
        try:
            cas = parse_packeta_datetime(row[0])
            zasilka_raw = row[1].strip()
            parsed.append({
                'cas': cas,
                'zasilka': normalize_zasilka(zasilka_raw),
                'zasilka_raw': zasilka_raw,
                'typ_provize': normalize_typ_provize(row[2]),
                'castka': parse_castka(row[3]),
                'mena': row[4].strip() or 'Kč',
                'poznamka': row[5].strip(),
                'line': i,
            })
        except ValueError as exc:
            raise ValueError(f'Řádek {i}: {exc}') from exc
    return parsed


def count_distinct_visits(rows: list[dict]) -> dict:
    """Počet DISTINCT zásilek pro hlavní typy provize."""
    vydane_types = {'Zpracování zásilky', 'Zpracování nadrozměrné zásilky'}
    prijate_types = {'Podání', 'Podání C2C'}
    vydane = set()
    prijate = set()
    celkem = set()
    for row in rows:
        typ = row['typ_provize']
        if typ not in PACKETA_MAIN_VISIT_TYPES:
            continue
        z = row['zasilka']
        celkem.add(z)
        if typ in vydane_types:
            vydane.add(z)
        if typ in prijate_types:
            prijate.add(z)
    return {
        'navstevy_celkem': len(celkem),
        'vydane': len(vydane),
        'prijate': len(prijate),
        'radku_csv': len(rows),
    }
