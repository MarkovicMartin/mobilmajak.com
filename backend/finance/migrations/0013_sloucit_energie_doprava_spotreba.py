from django.db import migrations


def sloucit_kategorie_forward(apps, schema_editor):
    from finance.kategorie_slouceni import sloucit_kategorie

    sloucit_kategorie(
        apps.get_model('finance', 'NakladKategorie'),
        apps.get_model('finance', 'NakladPolozka'),
        apps.get_model('finance', 'FioKategorizacniPravidlo'),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0012_pokladna_znacka_sloucit_kategorie'),
    ]

    operations = [
        migrations.RunPython(sloucit_kategorie_forward, migrations.RunPython.noop),
    ]
