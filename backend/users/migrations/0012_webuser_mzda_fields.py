from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_remove_webuser_datum_upravy_alter_webuser_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='webuser',
            name='mzda_zaklad',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True,
                verbose_name='Měsíční základ (body)',
            ),
        ),
        migrations.AddField(
            model_name='webuser',
            name='mzda_doplnky',
            field=models.JSONField(blank=True, default=list, verbose_name='Volitelné mzdové doplňky (body)'),
        ),
    ]
