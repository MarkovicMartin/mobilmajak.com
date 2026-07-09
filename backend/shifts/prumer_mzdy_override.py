"""Ruční hodiny a fixní výplata pro průměr dovolené – DB s fallbackem na JSON."""
import json
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent / 'data' / 'prumer_mzdy_override.json'


def clear_prumer_mzdy_override_cache():
    load_prumer_mzdy_overrides.cache_clear()


@lru_cache(maxsize=1)
def load_prumer_mzdy_overrides():
    if not DATA_PATH.is_file():
        return {}
    with DATA_PATH.open(encoding='utf-8') as f:
        payload = json.load(f)
    return payload.get('uzivatele') or {}


def _override_rows_from_db(user_id):
    from .models import PrumerMzdyMesicOverride

    rows = PrumerMzdyMesicOverride.objects.filter(user_id=user_id).order_by('rok', 'mesic')
    if not rows.exists():
        return None
    out = []
    for row in rows:
        item = {
            'rok': row.rok,
            'mesic': row.mesic,
            'odpracovano_h': float(row.odpracovano_h),
        }
        if row.fixni_body is not None:
            item['fixni_body'] = float(row.fixni_body)
        out.append(item)
    return out


def _override_rows_from_json(user):
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


def prumer_override_for_user(user):
    """Vrátí seznam měsíců pro uživatele nebo None."""
    if not user:
        return None
    db_rows = _override_rows_from_db(user.id)
    if db_rows is not None:
        return db_rows
    return _override_rows_from_json(user)


def serialize_prumer_override(row):
    return {
        'id': row.id,
        'user_id': row.user_id,
        'rok': row.rok,
        'mesic': row.mesic,
        'odpracovano_h': float(row.odpracovano_h),
        'fixni_body': float(row.fixni_body) if row.fixni_body is not None else None,
        'poznamka': row.poznamka or '',
        'zmenil_jmeno': (
            f'{row.zmenil.jmeno} {row.zmenil.prijmeni}'.strip()
            if row.zmenil_id else None
        ),
        'upraveno': row.upraveno.isoformat() if row.upraveno else None,
    }
