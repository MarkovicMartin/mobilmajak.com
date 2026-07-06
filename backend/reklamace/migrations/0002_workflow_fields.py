from django.db import migrations, models


def set_initial_status(apps, schema_editor):
    ReklamacePolozka = apps.get_model('reklamace', 'ReklamacePolozka')
    ReklamacePolozka.objects.filter(datum_odeslani__isnull=False).update(status='odeslane')


class Migration(migrations.Migration):

    dependencies = [
        ('reklamace', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='reklamacepolozka',
            name='datum_vyrizeni',
            field=models.DateField(blank=True, null=True, verbose_name='Datum vyřízení'),
        ),
        migrations.AddField(
            model_name='reklamacepolozka',
            name='odeslano_dodavateli_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Odesláno dodavateli'),
        ),
        migrations.AddField(
            model_name='reklamacepolozka',
            name='sklad_naskladneno',
            field=models.BooleanField(default=False, verbose_name='Naskladněno'),
        ),
        migrations.AddField(
            model_name='reklamacepolozka',
            name='sklad_vyskladneno',
            field=models.BooleanField(default=False, verbose_name='Vyskladněno'),
        ),
        migrations.AddField(
            model_name='reklamacepolozka',
            name='status',
            field=models.CharField(
                choices=[
                    ('nezpracovane', 'Nezpracované'),
                    ('odeslane', 'Odeslané'),
                    ('vyrizene', 'Vyřízené'),
                ],
                default='nezpracovane',
                max_length=20,
                verbose_name='Stav',
            ),
        ),
        migrations.AddField(
            model_name='reklamacepolozka',
            name='zpusob_vyrizeni',
            field=models.CharField(
                blank=True,
                choices=[
                    ('vymena', 'Výměna'),
                    ('dobropis', 'Dobropis'),
                    ('oprava', 'Oprava'),
                    ('zamitnuto', 'Zamítnuto'),
                    ('jine', 'Jiné'),
                ],
                default='',
                max_length=20,
                verbose_name='Způsob vyřízení',
            ),
        ),
        migrations.RunPython(set_initial_status, migrations.RunPython.noop),
    ]
