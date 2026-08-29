from django.db import migrations, models


def codaruina_presna_shoda(apps, schema_editor):
    Pravidlo = apps.get_model('finance', 'FioKategorizacniPravidlo')
    Pravidlo.objects.filter(
        ignorovat=True,
        zprava_obsahuje__iexact='Codaruina s.r.o.',
    ).update(text_shoda='presne')


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0013_sloucit_energie_doprava_spotreba'),
    ]

    operations = [
        migrations.AddField(
            model_name='fiokategorizacnipravidlo',
            name='text_shoda',
            field=models.CharField(
                choices=[('obsahuje', 'Obsahuje text'), ('presne', 'Přesně (zpráva i popis)')],
                default='obsahuje',
                max_length=16,
            ),
        ),
        migrations.RunPython(codaruina_presna_shoda, migrations.RunPython.noop),
    ]
