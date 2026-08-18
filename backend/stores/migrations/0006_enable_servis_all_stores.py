from django.db import migrations, models


def enable_all_servis_pozice(apps, schema_editor):
    Prodejna = apps.get_model('stores', 'Prodejna')
    Prodejna.objects.all().update(povolena_pozice_servis=True)


class Migration(migrations.Migration):
    dependencies = [
        ('stores', '0005_sync_safe_datetime_and_meta'),
    ]

    operations = [
        migrations.AlterField(
            model_name='prodejna',
            name='povolena_pozice_servis',
            field=models.BooleanField(
                default=True,
                verbose_name='Povolena pozice servisní technik',
            ),
        ),
        migrations.RunPython(enable_all_servis_pozice, migrations.RunPython.noop),
    ]
