from django.core import checks
from django.db import models
from django.conf import settings
from django.utils import timezone


class SafeDateTimeField(models.DateTimeField):
    """
    Ošetří legacy MySQL "zero-datetime" hodnoty typu `0000-00-00 00:00:00...`.

    U některých instalací je toto vraceno jako string a následná timezone konverze
    pak padá (např. `'str' object has no attribute 'utcoffset'`).

    Důležité: get_internal_type() MUSÍ vracet 'SafeDateTimeField', ne 'DateTimeField'.
    Jinak MySQL backend zaregistruje convert_datetimefield_value *před* from_db_value
    a zero-datetime string znovu shodí request (kalendář směn apod.).
    """

    def _normalize_zero_datetime(self, value):
        if isinstance(value, str):
            v = value.strip()
            if not v or v.startswith('0000-00-00'):
                return None
        return value

    def get_internal_type(self):
        # Nesmí být 'DateTimeField' – viz docstring / mysql_datetime_patch.
        return 'SafeDateTimeField'

    def db_type(self, connection):
        return models.DateTimeField().db_type(connection)

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        if self.get_internal_type() == 'DateTimeField':
            errors.append(
                checks.Error(
                    "SafeDateTimeField.get_internal_type() must not return 'DateTimeField'.",
                    hint=(
                        "MySQL convert_datetimefield_value runs before from_db_value and "
                        "crashes on legacy zero-datetime strings (utcoffset)."
                    ),
                    obj=self,
                    id='users.E001',
                )
            )
        return errors

    def from_db_value(self, value, expression, connection):
        # DateTimeField u některých MySQL driverů může vracet invalidní hodnoty
        # jako raw string. Validní DB hodnoty ale zůstávají v timezone DB spojení.
        return self._to_python(value, source_tz=getattr(connection, 'timezone', None))

    def to_python(self, value):
        return self._to_python(value)

    def _to_python(self, value, source_tz=None):
        value = self._normalize_zero_datetime(value)
        if value is None:
            return None
        parsed = super().to_python(value)
        # If Django can't parse it, it may come back as raw string.
        if isinstance(parsed, str):
            return None
        if settings.USE_TZ and timezone.is_naive(parsed):
            return timezone.make_aware(parsed, source_tz or timezone.get_default_timezone())
        return parsed
