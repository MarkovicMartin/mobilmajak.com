"""Načtení Packeta credentials – nikdy nelogovat hesla."""
import json
import os
from pathlib import Path

from django.conf import settings

PACKETA_ADMIN_KEY = '0'


def packeta_secrets_path() -> Path:
    env_path = os.getenv('PACKETA_SECRETS_FILE', '').strip()
    if env_path:
        p = Path(env_path)
        if not p.is_absolute():
            p = settings.BASE_DIR.parent / p
        return p
    finance_path = os.getenv('FINANCE_SECRETS_FILE', '').strip()
    if finance_path:
        p = Path(finance_path)
        if not p.is_absolute():
            p = settings.BASE_DIR.parent / p
        return p
    return settings.BASE_DIR.parent / 'secrets' / 'mobilmajak-finance.json'


def load_packeta_secrets() -> dict:
    path = packeta_secrets_path()
    if not path.is_file():
        raise FileNotFoundError(f'Packeta secrets soubor nenalezen: {path}')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


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
    try:
        data = load_packeta_secrets()
    except FileNotFoundError:
        return None
    entry = (data.get('packeta_admin') or {}).get(PACKETA_ADMIN_KEY)
    return _packeta_creds_from_entry(entry)


def get_packeta_admin_for_fetch() -> dict | None:
    return get_packeta_admin_credentials()
