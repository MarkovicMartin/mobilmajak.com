from decimal import Decimal

from django.db import migrations, models


def set_legacy_penalizace_defaults(apps, schema_editor):
    MzdovaPenalizaceMesic = apps.get_model('shifts', 'MzdovaPenalizaceMesic')
    MzdovaPenalizaceMesic.objects.all().update(typ='procenta', hodnota=Decimal('10'))


class Migration(migrations.Migration):

    dependencies = [
        ('shifts', '0013_remove_smena_unique_user_datum_prodejna'),
    ]

    operations = [
        migrations.AddField(
            model_name='mzdovapenalizacemesic',
            name='hodnota',
            field=models.DecimalField(
                decimal_places=2,
                default=10,
                max_digits=10,
                verbose_name='Hodnota (%, nebo body)',
            ),
        ),
        migrations.AddField(
            model_name='mzdovapenalizacemesic',
            name='typ',
            field=models.CharField(
                choices=[('procenta', 'Procenta z provize'), ('fixni', 'Fixní body')],
                default='procenta',
                max_length=16,
                verbose_name='Typ srážky',
            ),
        ),
        migrations.RunPython(set_legacy_penalizace_defaults, migrations.RunPython.noop),
    ]
