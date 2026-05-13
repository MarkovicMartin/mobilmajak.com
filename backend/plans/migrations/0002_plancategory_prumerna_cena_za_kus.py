# Generated manually for Fáze 2

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='plancategory',
            name='prumerna_cena_za_kus',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Průměrná cena za kus (Kč)'),
        ),
    ]
