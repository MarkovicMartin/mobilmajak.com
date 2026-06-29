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
