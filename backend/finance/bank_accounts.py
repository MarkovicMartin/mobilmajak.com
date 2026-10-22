"""Vlastní účty Fio a Raiffeisen – převody mezi nimi nejsou náklad."""
from __future__ import annotations

import re
from typing import Iterable, NamedTuple


class OwnAccount(NamedTuple):
    prefix: str
    number: str
    bank: str


def norm_digits(value: str) -> str:
    return re.sub(r'\D', '', value or '').lstrip('0')


def parse_czech_account(raw: str, bank: str = '') -> tuple[str, str, str]:
    """Vrátí (předčíslí, číslo, kód banky) bez úvodních nul."""
    text = (raw or '').strip().replace(' ', '')
    bank_code = norm_digits(bank)
    compact = re.sub(r'\s', '', text).upper()
    if compact.startswith('CZ') and len(compact) >= 24:
        return norm_digits(compact[8:14]), norm_digits(compact[14:24]), compact[4:8]
    if '/' in text:
        text, bank_part = text.split('/', 1)
        bank_code = norm_digits(bank_part) or bank_code
    if '-' in text:
        prefix, number = text.split('-', 1)
    else:
        prefix, number = '', text
    return norm_digits(prefix), norm_digits(number), bank_code


def own_account(account_number: str, bank: str, prefix: str = '') -> OwnAccount | None:
    parsed_prefix, number, bank_code = parse_czech_account(account_number, bank)
    if prefix:
        parsed_prefix = norm_digits(prefix) or parsed_prefix
    if not number or not bank_code:
        return None
    return OwnAccount(parsed_prefix, number, bank_code)


def is_own_counterparty(prefix: str, number: str, bank: str, own: Iterable[OwnAccount]) -> bool:
    key = own_account(number, bank, prefix)
    if key is None:
        return False
    return key in set(own)


def counterparty_parts(row: dict) -> tuple[str, str, str]:
    raw = (row.get('protiucet_cislo') or row.get('protiucet') or '').strip()
    bank = (row.get('protiucet_banka') or '').strip()
    prefix = (row.get('protiucet_prefix') or '').strip()
    parsed_prefix, number, bank_code = parse_czech_account(raw, bank)
    if prefix:
        parsed_prefix = norm_digits(prefix) or parsed_prefix
    return parsed_prefix, number, bank_code


def mark_internal_transfers(rows: list[dict], own: Iterable[OwnAccount]) -> int:
    """Označí převod na vlastní účet Fio nebo Raiffeisen. Vrátí počet."""
    owned = list(own)
    marked = 0
    for row in rows:
        prefix, number, bank = counterparty_parts(row)
        if is_own_counterparty(prefix, number, bank, owned):
            row['interni'] = True
            marked += 1
    return marked
