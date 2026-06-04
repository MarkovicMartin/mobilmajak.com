from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0015_brigadnik_sazba_100'),
    ]

    operations = [
        migrations.AddField(
            model_name='webuser',
            name='mzda_cestovne',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True,
                verbose_name='Cestovné (body/měsíc)',
            ),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0015_brigadnik_sazba_100'),
    ]

    operations = [
        migrations.AddField(
            model_name='webuser',
            name='mzda_cestovne',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                verbose_name='Cestovné (body/měsíc)',
            ),
        ),
    ]
