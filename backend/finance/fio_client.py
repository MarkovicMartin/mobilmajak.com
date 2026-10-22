"""Fio REST API klient – volá se jen když je import povolen (FINANCE_FIO_ENABLED)."""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

import requests

from .fio_status import get_fio_import_status
from .secrets import get_fio_accounts

logger = logging.getLogger(__name__)

FIO_BASE = 'https://fioapi.fio.cz/v1/rest'


class FioImportNotAvailable(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def ensure_fio_available():
    status = get_fio_import_status()
    if not status['available']:
        raise FioImportNotAvailable(status['message'])


def _parse_fio_date(value: str) -> date:
    return date.fromisoformat(value.split('+')[0].split('T')[0])


def _col(tx: dict, key: str, default=''):
    val = tx.get(key)
    if isinstance(val, dict):
        val = val.get('value')
    if val is None:
        return default
    return str(val).strip()


def _parse_amount(value: str) -> Decimal:
    try:
        return Decimal(value.replace(',', '.'))
    except Exception:
        return Decimal('0')


def _parse_statement(data: dict) -> tuple[dict, list]:
    statement = data.get('accountStatement', {}) or {}
    txs = (
        statement.get('transactionList', {}) or {}
    ).get('transaction', [])
    if isinstance(txs, dict):
        txs = [txs]
    return statement, txs


def _download_period_http(token: str, date_from: date, date_to: date) -> tuple[list, dict]:
    url = f'{FIO_BASE}/periods/{token}/{date_from.isoformat()}/{date_to.isoformat()}/transactions.json'
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    statement, txs = _parse_statement(data)
    rows = []
    for tx in txs:
        amount = _parse_amount(_col(tx, 'column1', '0'))
        datum = _parse_fio_date(_col(tx, 'column0'))
        rows.append({
            'fio_id': _col(tx, 'column22') or _col(tx, 'column17'),
            'datum': datum,
            'castka': amount,
            # Oficiální mapování Fio JSON (viz API Bankovnictví):
            # column2 = protiúčet, column3 = kód banky, column5 = VS, column10 = název protiúčtu
            'protiucet': _col(tx, 'column2'),
            'protiucet_cislo': _col(tx, 'column2'),
            'protiucet_banka': _col(tx, 'column3'),
            'vs': _col(tx, 'column5'),
            'zprava': _col(tx, 'column16') or _col(tx, 'column25') or _col(tx, 'column7'),
            'popis': _col(tx, 'column7') or _col(tx, 'column10'),
        })
    info = dict(statement.get('info') or {})
    if not info.get('accountId') and statement.get('accountId'):
        info['accountId'] = statement.get('accountId')
    if not info.get('bankId') and statement.get('bankId'):
        info['bankId'] = statement.get('bankId')
    return [r for r in rows if r['fio_id']], info


def _download_period(token: str, date_from: date, date_to: date) -> tuple[list, dict]:
    ensure_fio_available()
    return _download_period_http(token, date_from, date_to)


def _identity_from_info(info: dict, label: str) -> dict | None:
    account_id = str(info.get('accountId') or '').strip()
    if not account_id:
        return None
    bank = str(info.get('bankId') or '2010').strip() or '2010'
    return {'label': label, 'account_number': account_id, 'bank': bank}


def fetch_fio_identities(date_from: date, date_to: date) -> list[dict]:
    """Čísla vlastních účtů i když je import pohybů Fio vypnutý."""
    identities = []
    for account in get_fio_accounts():
        label = account.get('label', 'fio')
        try:
            _rows, info = _download_period_http(account['token'], date_from, date_to)
        except Exception:
            logger.warning('Fio identity selhala pro účet %s', label)
            continue
        ident = _identity_from_info(info, label)
        if ident:
            identities.append(ident)
    return identities


def fetch_transactions(token: str, date_from: date, date_to: date) -> list[dict]:
    rows, _info = _download_period(token, date_from, date_to)
    return rows


def fetch_account_balance(token: str) -> dict:
    """Poslední pohyby včetně closing balance z Fio API."""
    ensure_fio_available()
    url = f'{FIO_BASE}/last/{token}/transactions.json'
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    statement, _ = _parse_statement(data)
    balance_raw = statement.get('closingBalance')
    if balance_raw is None:
        balance_raw = statement.get('closingbalance', '0')
    balance = _parse_amount(str(balance_raw))
    stmt_date = statement.get('dateEnd') or statement.get('dateStart') or ''
    datum = _parse_fio_date(stmt_date) if stmt_date else date.today()
    mena = str(statement.get('currency') or statement.get('idList') or 'CZK')[:8]
    return {
        'datum': datum,
        'castka': balance,
        'mena': mena if mena.isalpha() else 'CZK',
    }


def fetch_fio_periods(date_from: date, date_to: date) -> tuple[list[dict], list[dict]]:
    """Pohyby a identita účtů z jednoho stažení (kvůli limitu Fio API)."""
    ensure_fio_available()
    all_rows = []
    identities = []
    for account in get_fio_accounts():
        token = account['token']
        label = account.get('label', 'fio')
        try:
            rows, info = _download_period(token, date_from, date_to)
        except Exception as exc:
            logger.warning('Fio import selhal pro účet %s: %s', label, exc)
            continue
        ident = _identity_from_info(info, label)
        if ident:
            identities.append(ident)
        for row in rows:
            row['account_label'] = label
        all_rows.extend(rows)
    return all_rows, identities


def fetch_all_accounts(date_from: date, date_to: date) -> list[dict]:
    rows, _identities = fetch_fio_periods(date_from, date_to)
    return rows


def fetch_all_balances() -> list[dict]:
    ensure_fio_available()
    results = []
    for account in get_fio_accounts():
        token = account['token']
        label = account.get('label', 'fio')
        try:
            bal = fetch_account_balance(token)
            bal['account_label'] = label
            results.append(bal)
        except Exception as exc:
            logger.warning('Fio balance selhal pro účet %s: %s', label, exc)
    return results
