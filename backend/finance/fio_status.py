"""Stav Fio importu – výchozí vypnuto do získání admin účtu."""
import os

FIO_DISABLED_MESSAGE = 'Fio token vyžaduje admin účet – zatím nedostupné'


def is_fio_import_enabled() -> bool:
    return os.getenv('FINANCE_FIO_ENABLED', '0').strip().lower() in ('1', 'true', 'yes')


def get_fio_import_status() -> dict:
    if not is_fio_import_enabled():
        return {
            'available': False,
            'enabled': False,
            'message': FIO_DISABLED_MESSAGE,
        }
    try:
        from .secrets import get_fio_accounts
        accounts = get_fio_accounts()
    except FileNotFoundError:
        return {
            'available': False,
            'enabled': True,
            'message': 'Chybí soubor finance secrets (FINANCE_SECRETS_FILE).',
        }
    except Exception:
        return {
            'available': False,
            'enabled': True,
            'message': 'Nelze načíst finance secrets.',
        }
    if not accounts:
        return {
            'available': False,
            'enabled': True,
            'message': 'V secrets chybí platný Fio token.',
        }
    return {
        'available': True,
        'enabled': True,
        'message': '',
        'account_count': len(accounts),
    }
