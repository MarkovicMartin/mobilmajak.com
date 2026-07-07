from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0023_webuser_slack_daily_report'),
        ('shifts', '0017_mzdovapenalizacemesic_vytvoril'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mzdovapenalizacemesic',
            name='vytvoril',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='vytvorene_mzda_penalizace',
                to='users.webuser',
                verbose_name='Zadal',
            ),
        ),
    ]
