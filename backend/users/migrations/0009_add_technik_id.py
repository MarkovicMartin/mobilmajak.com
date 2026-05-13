# Generated manually - add technik_id to WEB_USERS (ID technika z EDA/Pohody)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_add_prodejna_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='webuser',
            name='technik_id',
            field=models.IntegerField(blank=True, null=True, verbose_name='ID technika (EDA/Pohoda)'),
        ),
    ]
