from django.db import migrations, models


def enable_globus_servis_pozice(apps, schema_editor):
    Prodejna = apps.get_model('stores', 'Prodejna')
    Prodejna.objects.filter(nazev='Globus').update(povolena_pozice_servis=True)


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0002_prodejna_vedouci_oteviraci'),
    ]

    operations = [
        migrations.AddField(
            model_name='prodejna',
            name='povolena_pozice_servis',
            field=models.BooleanField(
                default=False,
                verbose_name='Povolena pozice servisní technik',
            ),
        ),
        migrations.RunPython(enable_globus_servis_pozice, migrations.RunPython.noop),
    ]
