# Cleanup legacy MySQL zero-datetimes na WEB_USERS (bez změny schématu).

from django.db import migrations, connection


def _cleanup_zero_datetimes(apps, schema_editor):
    # datum_upravy je NOT NULL – zero-date nahradíme datum_vytvoreni, jinak NOW.
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE `WEB_USERS` "
            "SET `datum_upravy` = IF( "
            "  CAST(`datum_vytvoreni` AS CHAR) LIKE '0000-00-00%', "
            "  NOW(6), "
            "  `datum_vytvoreni` "
            ") "
            "WHERE CAST(`datum_upravy` AS CHAR) LIKE '0000-00-00%'"
        )


def _noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0024_sync_safe_datetime_and_meta'),
    ]

    operations = [
        migrations.RunPython(_cleanup_zero_datetimes, _noop_reverse),
    ]
