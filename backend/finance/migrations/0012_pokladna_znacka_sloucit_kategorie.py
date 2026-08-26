from django.db import migrations, models


def sloucit_kategorie_forward(apps, schema_editor):
    from finance.kategorie_slouceni import sloucit_kategorie

    sloucit_kategorie(
        apps.get_model('finance', 'NakladKategorie'),
        apps.get_model('finance', 'NakladPolozka'),
        apps.get_model('finance', 'FioKategorizacniPravidlo'),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0011_financedoklad_prirazeno_automaticky'),
    ]

    operations = [
        migrations.AddField(
            model_name='nakladpolozka',
            name='pokladna_key',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
        migrations.AddField(
            model_name='nakladpolozka',
            name='pokladna_label',
            field=models.CharField(blank=True, default='', max_length=80),
        ),
        migrations.RunPython(sloucit_kategorie_forward, migrations.RunPython.noop),
    ]
