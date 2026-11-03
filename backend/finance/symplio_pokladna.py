"""Parser a deduplikace importu historie pokladny ze Symplio XLSX."""
from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .models import NakladPolozka

SYMPLIO_HEADERS = {
    'datum': 'Datum',
    'admin': 'Admin',
    'nazev': 'Název',
    'castka': 'Částka',
    'objednavka': 'Objednávka',
    'doklad': 'Doklad',
}

_DATUM_RE = re.compile(
    r'^(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})(?:\s+(\d{1,2}):(\d{2}))?$',
)


def parse_symplio_datum(value) -> date:
    s = str(value or '').strip()
    m = _DATUM_RE.match(s)
    if not m:
        raise ValueError(f'Neznámý formát data Symplio: {value!r}')
    day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return date(year, month, day)


def parse_symplio_castka(value) -> Decimal:
    if value is None or value == '':
        raise ValueError('Chybí částka')
    try:
        return Decimal(str(value).replace(',', '.').replace(' ', ''))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f'Neplatná částka: {value!r}') from exc


def _cell_str(value) -> str:
    if value is None:
        return ''
    return str(value).strip()


def _header_index(headers: list) -> dict[str, int]:
    normalized = {str(h).strip(): i for i, h in enumerate(headers) if h is not None}
    idx = {}
    for key, label in SYMPLIO_HEADERS.items():
        if label not in normalized:
            raise ValueError(f'V XLSX chybí sloupec {label!r}')
        idx[key] = normalized[label]
    return idx


def last_imported_datum(prodejna_id: int, pokladna_key: str = '') -> date | None:
    """Nejnovější den už uložený pro tuto pokladnu. Export jde od nejnovějšího."""
    qs = NakladPolozka.objects.filter(
        zdroj=NakladPolozka.ZDROJ_SYMPLIO_POKLADNA,
        prodejna_id=prodejna_id,
    )
    key = (pokladna_key or '').strip()
    if key:
        qs = qs.filter(pokladna_key=key)
    return qs.order_by('-datum').values_list('datum', flat=True).first()


def parse_symplio_pokladna_xlsx(
    path: str | Path,
    *,
    stop_before: date | None = None,
) -> list[dict]:
    """Řádky z exportu (včetně příjmů).

    Symplio vrací celou historii, seřazenou od nejnovějšího. `stop_before` je
    poslední uložený den: ten den se ještě přečte (nový výdej tentýž den),
    starší řádky se už nečtou.
    """
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb.active
        row_iter = ws.iter_rows(values_only=True)
        try:
            header = next(row_iter)
        except StopIteration:
            return []
        idx = _header_index(list(header))
        parsed = []
        seen_in_window = stop_before is None
        for row_num, row in enumerate(row_iter, start=2):
            if not row or all(v is None or str(v).strip() == '' for v in row):
                continue
            try:
                castka = parse_symplio_castka(row[idx['castka']])
                datum = parse_symplio_datum(row[idx['datum']])
            except (ValueError, IndexError, TypeError):
                continue
            if stop_before is not None and datum < stop_before:
                if seen_in_window:
                    break
                continue
            seen_in_window = True

            doklad = _cell_str(row[idx['doklad']]) if idx['doklad'] < len(row) else ''
            objednavka = _cell_str(row[idx['objednavka']]) if idx['objednavka'] < len(row) else ''
            nazev = _cell_str(row[idx['nazev']]) if idx['nazev'] < len(row) else ''
            admin = _cell_str(row[idx['admin']]) if idx['admin'] < len(row) else ''

            parsed.append({
                'datum': datum,
                'castka': castka,
                'popis': nazev,
                'admin': admin,
                'objednavka': objednavka,
                'symplio_doklad': doklad,
                'row_num': row_num,
            })
        return parsed
    finally:
        wb.close()


def is_symplio_vydej(row: dict) -> bool:
    """Výdej z pokladny = záporná částka v exportu."""
    return Decimal(str(row['castka'])) < 0


def symplio_pokladna_external_id(prodejna_id: int, row: dict) -> str:
    doklad = (row.get('symplio_doklad') or '').strip()
    if doklad:
        return f'symplio:{prodejna_id}:{doklad}'
    key = (
        f'{prodejna_id}|{row["datum"].isoformat()}|{row["castka"]}|'
        f'{row.get("popis", "")}|{row.get("objednavka", "")}'
    )
    digest = hashlib.sha256(key.encode('utf-8')).hexdigest()[:32]
    return f'symplio:{digest}'


def find_existing_symplio_polozka(prodejna_id: int, row: dict) -> NakladPolozka | None:
    external_id = symplio_pokladna_external_id(prodejna_id, row)
    existing = NakladPolozka.objects.filter(fio_id=external_id).first()
    if existing:
        return existing

    doklad = (row.get('symplio_doklad') or '').strip()
    if doklad:
        return NakladPolozka.objects.filter(
            zdroj=NakladPolozka.ZDROJ_SYMPLIO_POKLADNA,
            prodejna_id=prodejna_id,
            symplio_doklad=doklad,
        ).first()
    return None
