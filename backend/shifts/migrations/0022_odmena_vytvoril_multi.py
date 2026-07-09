import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0023_webuser_slack_daily_report'),
        ('shifts', '0021_prumer_override_audit_log'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='mzdovaodmenamesic',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='mzdovaodmenamesic',
            name='vytvoril',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='vytvorene_mzda_odmeny',
                to='users.webuser',
                verbose_name='Zadal',
            ),
        ),
    ]
