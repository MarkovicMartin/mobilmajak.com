from django.db import migrations, models
import django.db.models.deletion


def clear_prodejna_for_absences(apps, schema_editor):
    Smena = apps.get_model('shifts', 'Smena')
    Smena.objects.filter(typ_smeny__in=('dovolena', 'nemoc')).update(prodejna_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ('shifts', '0009_mzdovapenalizacemesic'),
        ('stores', '0002_prodejna_vedouci_oteviraci'),
    ]

    operations = [
        migrations.AlterField(
            model_name='smena',
            name='prodejna',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='smeny',
                to='stores.prodejna',
                verbose_name='Prodejna',
            ),
        ),
        migrations.RunPython(clear_prodejna_for_absences, migrations.RunPython.noop),
    ]
