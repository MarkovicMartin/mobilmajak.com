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
    if val is None:
        return default
    return str(val).strip()


def fetch_transactions(token: str, date_from: date, date_to: date) -> list[dict]:
    ensure_fio_available()
    url = f'{FIO_BASE}/periods/{token}/{date_from.isoformat()}/{date_to.isoformat()}/transactions.json'
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    txs = (
        data.get('accountStatement', {})
        .get('transactionList', {})
        .get('transaction', [])
    )
    if isinstance(txs, dict):
        txs = [txs]
    rows = []
    for tx in txs:
        amount_raw = _col(tx, 'column1', '0').replace(',', '.')
        try:
            amount = Decimal(amount_raw)
        except Exception:
            amount = Decimal('0')
        datum = _parse_fio_date(_col(tx, 'column0'))
        rows.append({
            'fio_id': _col(tx, 'column22') or _col(tx, 'column17'),
            'datum': datum,
            'castka': amount,
            'protiucet': _col(tx, 'column5'),
            'vs': _col(tx, 'column10'),
            'zprava': _col(tx, 'column16') or _col(tx, 'column25') or _col(tx, 'column7'),
            'popis': _col(tx, 'column7'),
        })
    return [r for r in rows if r['fio_id']]


def fetch_all_accounts(date_from: date, date_to: date) -> list[dict]:
    ensure_fio_available()
    all_rows = []
    for account in get_fio_accounts():
        token = account['token']
        label = account.get('label', 'fio')
        try:
            rows = fetch_transactions(token, date_from, date_to)
            for row in rows:
                row['account_label'] = label
            all_rows.extend(rows)
        except Exception as exc:
            logger.warning('Fio import selhal pro účet %s: %s', label, exc)
    return all_rows
