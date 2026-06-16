# Sloupec datum_upravy zůstal v MySQL po falešně zapsané migraci 0011.
from django.db import migrations, models


def ensure_datum_upravy_column(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SHOW COLUMNS FROM WEB_USERS LIKE 'datum_upravy'")
        if cursor.fetchone():
            return
        cursor.execute(
            "ALTER TABLE WEB_USERS ADD COLUMN datum_upravy datetime(6) NOT NULL "
            "DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)"
        )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0019_alter_webuser_mzda_zaklad'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='webuser',
                    name='datum_upravy',
                    field=models.DateTimeField(auto_now=True, verbose_name='Datum úpravy'),
                ),
            ],
            database_operations=[
                migrations.RunPython(ensure_datum_upravy_column, migrations.RunPython.noop),
            ],
        ),
    ]
