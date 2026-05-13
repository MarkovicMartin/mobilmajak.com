# Generated manually - Add cas_prodeje column to WEB_PRODEJE_ALL

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0012_webzasilkovna_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='webprodejeall',
            name='cas_prodeje',
            field=models.TimeField(blank=True, db_column='cas_prodeje', null=True, verbose_name='Čas prodeje'),
        ),
    ]


