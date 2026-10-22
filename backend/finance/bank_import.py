"""Import pohybů z Fio a Raiffeisen do nákladů."""
from __future__ import annotations

import logging

from .bank_accounts import OwnAccount, mark_internal_transfers, own_account
from .fio_client import (
    FioImportNotAvailable,
    fetch_all_balances,
    fetch_fio_identities,
    fetch_fio_periods,
)
from .fio_status import get_fio_import_status
from .models import FinanceZustatek, NakladPolozka
from .rb_client import (
    RbImportNotAvailable,
    fetch_rb_accounts,
    fetch_rb_balances,
    fetch_rb_transactions,
)
from .rb_status import get_rb_import_status
from .services import log_finance_system, upsert_fio_row

logger = logging.getLogger(__name__)


def _own_from_fio(identities: list[dict]) -> list[OwnAccount]:
    owned = []
    for item in identities:
        account = own_account(item.get('account_number') or '', item.get('bank') or '2010')
        if account:
            owned.append(account)
    return owned


def _own_from_rb(accounts: list[dict]) -> list[OwnAccount]:
    owned = []
    for item in accounts:
        account = own_account(
            item.get('account_number') or '',
            item.get('bank') or '5500',
            item.get('prefix') or '',
        )
        if account:
            owned.append(account)
    return owned


def _upsert_rows(rows: list[dict], zdroj: str, dry_run: bool) -> dict:
    created = incoming = internal = skipped = 0
    for row in rows:
        result = upsert_fio_row(row, dry_run=dry_run, zdroj=zdroj)
        if result == 'created':
            created += 1
        elif result == 'incoming':
            incoming += 1
        elif result == 'internal':
            internal += 1
        else:
            skipped += 1
    return {
        'downloaded': len(rows),
        'created': created,
        'incoming': incoming,
        'internal': internal,
        'skipped': skipped,
    }


def _save_balances(balances: list[dict], typ: str) -> int:
    saved = 0
    for bal in balances:
        FinanceZustatek.objects.create(
            datum=bal['datum'],
            typ=typ,
            label=bal.get('account_label', ''),
            castka=bal['castka'],
            mena=bal.get('mena', 'CZK'),
        )
        saved += 1
    return saved


def run_bank_import(
    date_from,
    date_to,
    *,
    dry_run: bool = False,
    skip_balance: bool = False,
    banks: str = 'both',
) -> dict:
    """banks: 'fio' | 'rb' | 'both'. Převody mezi vlastními účty se ukládají jako interní."""
    want_fio = banks in ('fio', 'both')
    want_rb = banks in ('rb', 'both')
    result = {
        'fio': None,
        'rb': None,
        'fio_error': '',
        'rb_error': '',
        'fio_skipped': '',
        'rb_skipped': '',
    }

    fio_rows: list[dict] = []
    fio_ids: list[dict] = []
    if want_fio or want_rb:
        fio_status = get_fio_import_status()
        if not fio_status['available']:
            if want_fio:
                result['fio_skipped'] = fio_status['message']
            if want_rb:
                try:
                    fio_ids = fetch_fio_identities(date_from, date_to)
                except Exception:
                    logger.warning('Fio identity pro filtr převodů selhala')
        else:
            try:
                fio_rows, fio_ids = fetch_fio_periods(date_from, date_to)
            except FioImportNotAvailable as exc:
                if want_fio:
                    result['fio_error'] = exc.message
                else:
                    logger.warning('Fio identity pro filtr převodů: %s', exc.message)
            except Exception as exc:
                logger.exception('Fio import selhal')
                if want_fio:
                    result['fio_error'] = str(exc)

    rb_rows: list[dict] = []
    rb_accounts: list[dict] = []
    other_currency = 0
    rb_status = get_rb_import_status()
    if not rb_status['available']:
        if want_rb:
            result['rb_skipped'] = rb_status['message']
    elif want_rb:
        try:
            rb_rows, rb_accounts, other_currency = fetch_rb_transactions(date_from, date_to)
        except RbImportNotAvailable as exc:
            result['rb_error'] = exc.message
        except Exception as exc:
            logger.exception('Raiffeisen import selhal')
            result['rb_error'] = str(exc)
    elif want_fio and not result['fio_error']:
        try:
            rb_accounts = fetch_rb_accounts()
        except Exception as exc:
            logger.warning('Nelze načíst účty Raiffeisen pro filtr převodů: %s', exc)

    own = _own_from_fio(fio_ids) + _own_from_rb(rb_accounts)

    if want_fio and not result['fio_error'] and not result['fio_skipped']:
        mark_internal_transfers(fio_rows, own)
        stats = _upsert_rows(fio_rows, NakladPolozka.ZDROJ_FIO, dry_run)
        stats['balances'] = 0
        if not dry_run and not skip_balance:
            try:
                stats['balances'] = _save_balances(fetch_all_balances(), FinanceZustatek.TYP_FIO)
            except Exception as exc:
                stats['balance_error'] = str(exc)
        result['fio'] = stats
        if not dry_run:
            log_finance_system('fio_import', _summary('Fio', stats))

    if want_rb and not result['rb_error'] and not result['rb_skipped']:
        mark_internal_transfers(rb_rows, own)
        stats = _upsert_rows(rb_rows, NakladPolozka.ZDROJ_RAIFFEISEN, dry_run)
        stats['other_currency'] = other_currency
        stats['balances'] = 0
        if not dry_run and not skip_balance:
            try:
                stats['balances'] = _save_balances(fetch_rb_balances(), FinanceZustatek.TYP_RAIFFEISEN)
            except Exception as exc:
                stats['balance_error'] = str(exc)
        result['rb'] = stats
        if not dry_run:
            log_finance_system('rb_import', _summary('Raiffeisen', stats))

    return result


def _summary(label: str, stats: dict) -> str:
    text = (
        f'{label}: staženo {stats["downloaded"]}, nových nákladů {stats["created"]}, '
        f'příchozích {stats["incoming"]}, interních převodů {stats["internal"]}, '
        f'přeskočeno {stats["skipped"]}, zůstatků {stats.get("balances", 0)}'
    )
    if stats.get('other_currency'):
        text += f', jiná měna {stats["other_currency"]}'
    if stats.get('balance_error'):
        text += f', zůstatek selhal: {stats["balance_error"]}'
    return text
