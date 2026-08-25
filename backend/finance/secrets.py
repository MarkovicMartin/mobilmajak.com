"""Načtení secrets/mobilmajak-finance.json – nikdy nelogovat tokeny."""
import json
import os
from pathlib import Path

from django.conf import settings

def finance_secrets_path() -> Path:
    env_path = os.getenv('FINANCE_SECRETS_FILE', '').strip()
    if env_path:
        p = Path(env_path)
        if not p.is_absolute():
            p = settings.BASE_DIR.parent / p
        return p
    return settings.BASE_DIR.parent / 'secrets' / 'mobilmajak-finance.json'


def load_finance_secrets() -> dict:
    path = finance_secrets_path()
    if not path.is_file():
        raise FileNotFoundError(f'Finance secrets soubor nenalezen: {path}')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def get_fio_accounts() -> list[dict]:
    data = load_finance_secrets()
    accounts = (data.get('fio') or {}).get('accounts') or []
    return [a for a in accounts if a.get('token')]


def get_flexi_config() -> dict | None:
    """
    Konfigurace ABRA Flexi REST API.
    Vrací None, pokud chybí údaje nebo je flexi.enabled=false.
    base_url bez koncového /c/.
    """
    try:
        data = load_finance_secrets()
    except FileNotFoundError:
        return None
    except Exception:
        return None

    flexi = data.get('flexi') or {}
    if flexi.get('enabled') is False:
        return None

    base = (flexi.get('base_url') or '').strip().rstrip('/')
    if base.endswith('/c'):
        base = base[:-2].rstrip('/')
    company = (flexi.get('company') or '').strip().strip('/')
    username = (flexi.get('username') or '').strip()
    password = flexi.get('password') or ''
    if not base or not company or not username or not password:
        return None

    return {
        'base_url': base,
        'company': company,
        'username': username,
        'password': password,
        'mode': (flexi.get('mode') or 'priloha').strip().lower() or 'priloha',
        'typ_dokl': (flexi.get('typ_dokl') or '').strip(),
    }


def is_flexi_sync_enabled() -> bool:
    if os.getenv('FINANCE_FLEXI_ENABLED', '1').strip().lower() in ('0', 'false', 'no'):
        return False
    return get_flexi_config() is not None
