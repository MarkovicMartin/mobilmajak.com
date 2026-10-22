"""Stav importu Raiffeisen Premium API."""
import os


def is_rb_import_enabled() -> bool:
    return os.getenv('FINANCE_RB_ENABLED', '1').strip().lower() in ('1', 'true', 'yes')


def get_rb_import_status() -> dict:
    if not is_rb_import_enabled():
        return {
            'available': False,
            'enabled': False,
            'message': 'Import Raiffeisen je vypnutý (FINANCE_RB_ENABLED=0).',
        }
    try:
        from .secrets import get_raiffeisen_config
        config = get_raiffeisen_config()
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
    if not config:
        return {
            'available': False,
            'enabled': True,
            'message': 'V secrets chybí Raiffeisen client_id nebo heslo k certifikátu.',
        }
    return {
        'available': True,
        'enabled': True,
        'message': '',
        'account_count': len(config.get('accounts') or []),
        'certificate_count': len(config.get('certificates') or []),
    }
