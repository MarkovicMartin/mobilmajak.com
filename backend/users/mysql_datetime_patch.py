"""
MySQL + USE_TZ: convert_datetimefield_value běží *před* Field.from_db_value.

Legacy `0000-00-00 …` (a občas jiné neparsovatelné hodnoty) přijdou jako str
→ `make_aware` volá `.utcoffset()` → AttributeError.

Tento patch ošetří stringy dřív, než Django spadne. Platí pro všechna DateTimeField.
SafeDateTimeField.internal_type zůstává 'SafeDateTimeField' (backend converter se
u něj nepoužije) – to je správný design; patch je záchranná síť pro obyčejná DT pole.
"""

from __future__ import annotations

_PATCH_ATTR = '_mobilmajak_safe_datetime_patched'


def _normalize_db_datetime(value):
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped.startswith('0000-00-00'):
            return None
        from django.core.exceptions import ValidationError
        from django.db.models.fields import DateTimeField

        try:
            parsed = DateTimeField().to_python(stripped)
        except (ValidationError, OverflowError, ValueError, TypeError):
            return None
        if isinstance(parsed, str):
            return None
        return parsed
    return value


def patch_mysql_datetime_conversion():
    from django.db.backends.mysql import operations as mysql_ops

    ops_cls = mysql_ops.DatabaseOperations
    if getattr(ops_cls, _PATCH_ATTR, False):
        return

    original = ops_cls.convert_datetimefield_value

    def convert_datetimefield_value(self, value, expression, connection):
        value = _normalize_db_datetime(value)
        if value is None:
            return None
        return original(self, value, expression, connection)

    ops_cls.convert_datetimefield_value = convert_datetimefield_value
    setattr(ops_cls, _PATCH_ATTR, True)
