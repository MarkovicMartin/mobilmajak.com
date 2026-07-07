from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('shifts', '0016_smena_pozice_home_office'),
    ]

    operations = [
        migrations.AddField(
            model_name='mzdovapenalizacemesic',
            name='vytvoril',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='vytvorene_mzda_penalizace',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Zadal',
            ),
        ),
    ]
