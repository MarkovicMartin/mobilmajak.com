"""Sdílená logika pro Mastersheet přihlášení (bez hesel v git/JSON)."""

import json
import re
from collections import defaultdict
from pathlib import Path

import openpyxl

DEFAULT_EXCEL = Path.home() / 'Downloads' / 'Mastersheet - prodejny.xlsx'
LOGINS_JSON = Path(__file__).resolve().parents[2] / 'docs' / 'mastersheet-prihlasovaci-loginy.json'

PLACEHOLDER_PASSWORD = 'DOPLNIT_RUCNE'

STORE_ALIASES = {
    'GLOBUS': 'Globus',
    'ZLÍN ČEPKOV': 'Čepkov',
    'ZLIN CEPKOV': 'Čepkov',
    'ČEPKOV': 'Čepkov',
    'ŠTERNBERK': 'Šternberk',
    'STERNBERK': 'Šternberk',
    'PŘEROV': 'Přerov',
    'PREROV': 'Přerov',
    'SENIMO': 'Senimo',
    'VSETÍN': 'Vsetín',
    'VSETIN': 'Vsetín',
    'LITOVELSKÁ': 'Litovelská',
    'LITOVELSKA': 'Litovelská',
}


def normalize_store(name: str) -> str:
    key = re.sub(r'\s+', ' ', (name or '').strip()).upper()
    return STORE_ALIASES.get(key, name.strip().title())


def normalize_key(store, service, username):
    return (
        normalize_store(store).lower(),
        re.sub(r'\s+', ' ', (service or '').strip()).lower(),
        (username or '').strip().lower(),
    )


def needs_password_update(password: str | None) -> bool:
    value = (password or '').strip()
    return not value or value == PLACEHOLDER_PASSWORD


def load_mastersheet_logins_from_json(json_path: Path):
    return json.loads(json_path.read_text(encoding='utf-8'))


def load_mastersheet_logins_from_excel(excel_path: Path, *, include_passwords: bool = False):
    wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    ws = wb['Přihl.údaje']
    logins = []
    current_store = None
    for row in ws.iter_rows(values_only=True):
        c0 = row[0] if row else None
        c1 = row[1] if len(row) > 1 else None
        c2 = row[2] if len(row) > 2 else None
        if c0 and str(c0).startswith('Prodejna'):
            current_store = str(c0).replace('Prodejna ', '').strip()
            continue
        if not current_store or not c1:
            continue
        service = str(c0).strip() if c0 else ''
        if 'příhlašovací' in service.lower():
            continue
        item = {
            'store': current_store,
            'service': service,
            'username': str(c1).strip(),
        }
        if include_passwords and c2 is not None:
            item['password'] = str(c2).strip()
        logins.append(item)
    wb.close()
    return logins


def load_mastersheet_logins(excel_path: Path, json_path: Path):
    if json_path.is_file():
        return load_mastersheet_logins_from_json(json_path)
    return load_mastersheet_logins_from_excel(excel_path, include_passwords=False)


def build_password_index(ms_logins):
    """normalize_key -> heslo z Mastersheet (poslední výskyt vyhrává)."""
    index = {}
    for item in ms_logins:
        password = (item.get('password') or '').strip()
        if not password:
            continue
        key = normalize_key(item['store'], item['service'], item['username'])
        index[key] = password
    return index


def plan_password_updates(db_rows, password_index):
    """
    Naplánuje aktualizace hesel pro DB záznamy s placeholderem nebo prázdným heslem.

    db_rows: iterable dictů s klíči store, company_name, username, password, id (volitelné)
    password_index: dict z build_password_index

    Vrací dict se seznamy updated, skipped_no_match, skipped_has_password, skipped_empty_excel.
    """
    updated = []
    skipped_no_match = []
    skipped_has_password = []
    skipped_empty_excel = []

    for row in db_rows:
        current = (row.get('password') or '').strip()
        if not needs_password_update(current):
            skipped_has_password.append(row)
            continue

        key = normalize_key(row['store'], row['company_name'], row['username'])
        new_password = password_index.get(key)
        if new_password is None:
            skipped_no_match.append(row)
            continue
        if not new_password.strip():
            skipped_empty_excel.append(row)
            continue

        updated.append({**row, 'new_password': new_password})

    return {
        'updated': updated,
        'skipped_no_match': skipped_no_match,
        'skipped_has_password': skipped_has_password,
        'skipped_empty_excel': skipped_empty_excel,
    }


def summarize_by_store(rows, store_field='store'):
    counts = defaultdict(int)
    for row in rows:
        store = normalize_store(row.get(store_field, ''))
        counts[store] += 1
    return dict(sorted(counts.items()))
