"""Načtení secrets/mobilmajak-finance.json – nikdy nelogovat tokeny."""
import json
import os
from pathlib import Path

from django.conf import settings

PACKETA_ADMIN_KEY = '0'


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


def _packeta_creds_from_entry(entry: dict | None) -> dict | None:
    if not entry:
        return None
    login = (entry.get('login') or '').strip()
    password = (entry.get('password') or '').strip()
    if not login or not password:
        return None
    return {'label': entry.get('label', ''), 'login': login, 'password': password}


def get_packeta_admin_credentials() -> dict | None:
    """Centrální Packeta admin účet (klíč „0" v packeta_admin)."""
    data = load_finance_secrets()
    entry = (data.get('packeta_admin') or {}).get(PACKETA_ADMIN_KEY)
    return _packeta_creds_from_entry(entry)


def get_packeta_admin_for_fetch() -> dict | None:
    """Alias pro automatické stahování provizí."""
    return get_packeta_admin_credentials()
