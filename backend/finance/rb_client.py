"""Raiffeisen Premium API – výpisy pohybů a zůstatky (mTLS + client id)."""
from __future__ import annotations

import json
import logging
import os
import ssl
import subprocess
import tempfile
import uuid
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from .rb_status import get_rb_import_status
from .secrets import get_raiffeisen_config

logger = logging.getLogger(__name__)

RB_BASE = 'https://api.rb.cz'
PRAGUE = ZoneInfo('Europe/Prague')


class RbImportNotAvailable(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def ensure_rb_available():
    status = get_rb_import_status()
    if not status['available']:
        raise RbImportNotAvailable(status['message'])


def parse_rb_date(value: str) -> date:
    raw = (value or '').strip()
    if raw.endswith('Z'):
        raw = raw[:-1] + '+00:00'
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is not None:
        dt = dt.astimezone(PRAGUE)
    return dt.date()


def map_rb_transaction(tx: dict, account_number: str, account_label: str) -> dict | None:
    """Stejný tvar řádku jako Fio. Odchozí částka je záporná. Mimo CZK vrací None."""
    ref = str(tx.get('entryReference') or '').strip()
    if not ref:
        return None
    amount = (tx.get('amount') or {})
    currency = str(amount.get('currency') or 'CZK').upper()
    if currency != 'CZK':
        return None
    value = Decimal(str(amount.get('value') or '0'))
    indication = str(tx.get('creditDebitIndication') or '').upper()
    if indication == 'DBIT':
        value = -abs(value)
    elif indication == 'CRDT':
        value = abs(value)

    details = ((tx.get('entryDetails') or {}).get('transactionDetails') or {})
    parties = details.get('relatedParties') or {}
    party = parties.get('counterParty') or parties.get('debtor') or parties.get('creditor') or {}
    account = party.get('account') or {}
    org = party.get('organisationIdentification') or {}
    number = str(account.get('accountNumber') or '').strip()
    prefix = str(account.get('accountNumberPrefix') or '').strip()
    bank = str(org.get('bankCode') or '').strip()
    remittance = details.get('remittanceInformation') or {}
    cred = remittance.get('creditorReferenceInformation') or {}
    message = remittance.get('originatorMessage') or ''
    if isinstance(message, list):
        message = ' '.join(str(part) for part in message if part)
    name = str(party.get('name') or '').strip()
    if prefix and prefix.strip('0'):
        proti = f'{prefix}-{number}/{bank}' if bank else f'{prefix}-{number}'
    elif number and bank:
        proti = f'{number}/{bank}'
    else:
        proti = number

    booking = tx.get('bookingDate') or tx.get('valueDate') or ''
    external_id = f'rb:{account_number}:{ref}'
    if len(external_id) > 64:
        external_id = f'rb:{ref}'[:64]
    return {
        'fio_id': external_id,
        'datum': parse_rb_date(str(booking)),
        'castka': value,
        'protiucet': proti[:64],
        'protiucet_cislo': number,
        'protiucet_prefix': prefix,
        'protiucet_banka': bank,
        'vs': str(cred.get('variable') or '')[:32],
        'zprava': str(message or '')[:4000],
        'popis': name[:500],
        'account_label': account_label,
    }


@contextmanager
def _client_ssl(cert: dict):
    pem = tempfile.NamedTemporaryFile(prefix='rbcert-', suffix='.pem', delete=False)
    pem.close()
    try:
        proc = subprocess.run(
            ['openssl', 'pkcs12', '-in', cert['file'], '-out', pem.name, '-nodes', '-passin', 'stdin'],
            input=str(cert['password']).encode(),
            capture_output=True,
        )
        if proc.returncode != 0:
            logger.warning('Raiffeisen certifikát %s se nepodařilo otevřít', cert.get('label') or 'p12')
            raise RbImportNotAvailable('Certifikát Raiffeisen se nepodařilo otevřít.')
        os.chmod(pem.name, 0o600)
        ctx = ssl.create_default_context()
        ctx.load_cert_chain(pem.name)
        yield ctx
    finally:
        try:
            os.remove(pem.name)
        except OSError:
            pass


def _get_json(ctx: ssl.SSLContext, client_id: str, url: str):
    req = urllib.request.Request(url, method='GET')
    req.add_header('X-IBM-Client-Id', client_id)
    req.add_header('X-Request-Id', uuid.uuid4().hex)
    req.add_header('Accept', 'application/json')
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', 'replace')[:300]
        raise RbImportNotAvailable(f'Raiffeisen API HTTP {exc.code}: {body}') from exc
    if not raw:
        return None
    return json.loads(raw.decode('utf-8'), parse_float=Decimal)


def _account_allowed(account_number: str, allowed: list) -> bool:
    if not allowed:
        return True
    wanted = {str(item.get('account_number') or item.get('number') or item or '').strip() for item in allowed}
    wanted.discard('')
    return not wanted or account_number in wanted


def _list_accounts(ctx, client_id: str, allowed: list) -> list[dict]:
    accounts = []
    page = 1
    while page <= 20:
        payload = _get_json(
            ctx, client_id,
            f'{RB_BASE}/rbcz/premium/api/accounts?page={page}&size=50',
        ) or {}
        batch = payload.get('accounts') or []
        for raw in batch:
            number = str(raw.get('accountNumber') or '').strip()
            if not number or not _account_allowed(number, allowed):
                continue
            currency = str(raw.get('mainCurrency') or 'CZK').upper()
            accounts.append({
                'account_number': number,
                'prefix': str(raw.get('accountNumberPrefix') or '').strip(),
                'bank': str(raw.get('bankCode') or '5500').strip() or '5500',
                'currency': currency,
                'label': number[-4:],
                'name': str(raw.get('friendlyName') or raw.get('accountName') or '').strip(),
            })
        if payload.get('last') in (True, 'true') or payload.get('lastPage') in (True, 'true') or not batch:
            break
        page += 1
    return accounts


def fetch_rb_accounts() -> list[dict]:
    ensure_rb_available()
    config = get_raiffeisen_config()
    if not config:
        raise RbImportNotAvailable('Chybí konfigurace Raiffeisen.')
    found = []
    seen = set()
    for cert in config['certificates']:
        with _client_ssl(cert) as ctx:
            for account in _list_accounts(ctx, config['client_id'], config.get('accounts') or []):
                key = (account['prefix'], account['account_number'], account['bank'])
                if key in seen:
                    continue
                seen.add(key)
                found.append(account)
    return found


def _transactions(ctx, client_id: str, account_number: str, currency: str, date_from: date, date_to: date):
    page = 1
    rows = []
    while page <= 50:
        url = (
            f'{RB_BASE}/rbcz/premium/api/accounts/{account_number}/{currency}/transactions'
            f'?from={date_from.isoformat()}&to={date_to.isoformat()}&page={page}&size=100'
        )
        payload = _get_json(ctx, client_id, url) or {}
        batch = payload.get('transactions') or []
        rows.extend(batch)
        if payload.get('lastPage') in (True, 'true') or not batch:
            break
        page += 1
    return rows


def fetch_rb_transactions(date_from: date, date_to: date) -> tuple[list[dict], list[dict], int]:
    """Vrátí (řádky CZK, identity účtů, počet pohybů v jiné měně)."""
    ensure_rb_available()
    config = get_raiffeisen_config()
    if not config:
        raise RbImportNotAvailable('Chybí konfigurace Raiffeisen.')
    identities = []
    mapped = []
    other_currency = 0
    seen = set()
    seen_ids = set()
    for cert in config['certificates']:
        with _client_ssl(cert) as ctx:
            accounts = _list_accounts(ctx, config['client_id'], config.get('accounts') or [])
            for account in accounts:
                key = account['account_number']
                if key in seen:
                    continue
                seen.add(key)
                identities.append(account)
                currencies = []
                for currency in (account['currency'], 'CZK', 'EUR'):
                    if currency and currency not in currencies:
                        currencies.append(currency)
                for currency in currencies:
                    try:
                        txs = _transactions(
                            ctx, config['client_id'], key, currency, date_from, date_to,
                        )
                    except RbImportNotAvailable as exc:
                        if 'WRONG_ACCOUNT_CURRENCY' in exc.message:
                            logger.debug(
                                'Raiffeisen účet %s nemá měnu %s',
                                account['label'], currency,
                            )
                        else:
                            logger.warning(
                                'Raiffeisen pohyby selhaly pro účet %s %s: %s',
                                account['label'], currency, exc.message,
                            )
                        continue
                    for tx in txs:
                        tx_currency = str((tx.get('amount') or {}).get('currency') or currency).upper()
                        if tx_currency != 'CZK':
                            other_currency += 1
                            continue
                        row = map_rb_transaction(tx, key, account['label'])
                        if row and row['fio_id'] not in seen_ids:
                            seen_ids.add(row['fio_id'])
                            mapped.append(row)
    return mapped, identities, other_currency


def fetch_rb_balances() -> list[dict]:
    ensure_rb_available()
    config = get_raiffeisen_config()
    if not config:
        raise RbImportNotAvailable('Chybí konfigurace Raiffeisen.')
    results = []
    seen = set()
    for cert in config['certificates']:
        with _client_ssl(cert) as ctx:
            for account in _list_accounts(ctx, config['client_id'], config.get('accounts') or []):
                number = account['account_number']
                if number in seen:
                    continue
                seen.add(number)
                try:
                    payload = _get_json(
                        ctx, config['client_id'],
                        f'{RB_BASE}/rbcz/premium/api/accounts/{number}/balance',
                    ) or {}
                except RbImportNotAvailable as exc:
                    logger.warning('Raiffeisen zůstatek selhal pro %s: %s', account['label'], exc.message)
                    continue
                for folder in payload.get('currencyFolders') or []:
                    currency = str(folder.get('currency') or '').upper()
                    if currency != 'CZK':
                        continue
                    for bal in folder.get('balances') or []:
                        if bal.get('balanceType') != 'CLBD':
                            continue
                        raw_date = str(bal.get('balanceDate') or '')
                        try:
                            datum = parse_rb_date(raw_date) if raw_date else date.today()
                        except ValueError:
                            datum = date.today()
                        results.append({
                            'datum': datum,
                            'castka': Decimal(str(bal.get('value') or '0')),
                            'mena': 'CZK',
                            'account_label': account['label'],
                        })
    return results
