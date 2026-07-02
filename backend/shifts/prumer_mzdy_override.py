"""Volitelné ruční hodiny a fixní výplata pro průměr dovolené."""
import json
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent / 'data' / 'prumer_mzdy_override.json'


@lru_cache(maxsize=1)
def load_prumer_mzdy_overrides():
    if not DATA_PATH.is_file():
        return {}
    with DATA_PATH.open(encoding='utf-8') as f:
        payload = json.load(f)
    return payload.get('uzivatele') or {}


def prumer_override_for_user(user):
    """Vrátí seznam měsíců pro uživatele nebo None."""
    overrides = load_prumer_mzdy_overrides()
    if not overrides:
        return None
    prijmeni = (getattr(user, 'prijmeni', '') or '').strip().lower()
    aliases = {prijmeni}
    if prijmeni in ('smčková', 'smckova'):
        aliases.add('smrčková')
    if prijmeni in ('smrčková', 'smrckova'):
        aliases.add('smčková')
    for key in aliases:
        row = overrides.get(key)
        if row:
            mesice = row.get('mesice')
            return mesice if mesice else None
    return None
