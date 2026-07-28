# State-only: imported_at → SafeDateTimeField + cleanup zero-datetimes na výdejkách.

from django.db import migrations, connection
import users.fields


def _cleanup_zero_imported_at(apps, schema_editor):
    # imported_at je NOT NULL – zero-date nahradíme timestampem z vystaveno.
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE `WEB_SKLAD_VYDEJKY` "
            "SET `imported_at` = TIMESTAMP(`vystaveno`) "
            "WHERE CAST(`imported_at` AS CHAR) LIKE '0000-00-00%'"
        )


def _noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0020_webprodejeall_poznamka_dokladu'),
        ('analytics', '0020_zasilkovna_leaderboard_cache'),
        ('users', '0024_sync_safe_datetime_and_meta'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(_cleanup_zero_imported_at, _noop_reverse),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name='skladvydejka',
                    name='imported_at',
                    field=users.fields.SafeDateTimeField(auto_now=True),
                ),
            ],
        ),
    ]
