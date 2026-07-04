"""Mapování id_prodejce z prodejních dat (technik_id nebo WebUser.id) na WebUser.id."""
from __future__ import annotations

from users.models import WebUser


def build_prodejce_key_to_user_id() -> dict[int, int]:
    """
    Vrátí mapu libovolného klíče prodejce -> kanonické WebUser.id.
    Klíče: WebUser.id i technik_id (EDA).
    """
    out: dict[int, int] = {}
    qs = WebUser.objects.exclude(technik_id__isnull=True).exclude(technik_id=0).only('id', 'technik_id')
    for user in qs:
        out[user.id] = user.id
        out[user.technik_id] = user.id
    return out


def resolve_web_user_id(raw_id: int | None, key_map: dict[int, int] | None = None) -> int | None:
    """Přeloží id_prodejce z účtenky na WebUser.id; neznámé ID vrátí beze změny."""
    if not raw_id:
        return None
    mapping = key_map if key_map is not None else build_prodejce_key_to_user_id()
    return mapping.get(int(raw_id), int(raw_id))


def sales_id_keys_for_user(user_id: int, key_map: dict[int, int] | None = None) -> set[int]:
    """Množina id_prodejce hodnot v WebProdejeAll patřících danému uživateli."""
    mapping = key_map if key_map is not None else build_prodejce_key_to_user_id()
    canonical = resolve_web_user_id(user_id, mapping)
    if not canonical:
        return set()
    keys = {canonical}
    for key, uid in mapping.items():
        if uid == canonical:
            keys.add(key)
    return keys
