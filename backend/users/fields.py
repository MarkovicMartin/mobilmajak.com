from django.db import models
from django.conf import settings
from django.utils import timezone


class SafeDateTimeField(models.DateTimeField):
    """
    Ošetří legacy MySQL "zero-datetime" hodnoty typu `0000-00-00 00:00:00...`.

    U některých instalací je toto vraceno jako string a následná timezone konverze
    pak padá (např. `'str' object has no attribute 'utcoffset'`).
    """

    def _normalize_zero_datetime(self, value):
        if isinstance(value, str):
            v = value.strip()
            if v.startswith('0000-00-00'):
                return None
        return value

    def get_internal_type(self):
        return 'SafeDateTimeField'

    def db_type(self, connection):
        return models.DateTimeField().db_type(connection)

    def from_db_value(self, value, expression, connection):
        # DateTimeField u některých MySQL driverů může vracet invalidní hodnoty
        # jako raw string. Použijeme stejnou logiku jako to_python.
        return self.to_python(value)

    def to_python(self, value):
        value = self._normalize_zero_datetime(value)
        if value is None:
            return None
        parsed = super().to_python(value)
        # If Django can't parse it, it may come back as raw string.
        if isinstance(parsed, str):
            return None
        if settings.USE_TZ and timezone.is_naive(parsed):
            return timezone.make_aware(parsed, timezone.get_default_timezone())
        return parsed
