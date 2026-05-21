from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_webuser_mzda_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='webuser',
            name='role',
            field=models.CharField(
                choices=[
                    ('ADMIN', 'Administrátor'),
                    ('VEDOUCI', 'Vedoucí'),
                    ('PRODEJCE', 'Prodejce'),
                    ('BRIGADNIK', 'Brigádník'),
                ],
                default='PRODEJCE',
                max_length=20,
                verbose_name='Role',
            ),
        ),
        migrations.AlterField(
            model_name='webuser',
            name='mzda_zaklad',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                verbose_name='Fixní body / body za hodinu (brigádník)',
            ),
        ),
    ]
