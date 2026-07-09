import django.db.models.deletion
from django.db import migrations, models

import users.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0023_webuser_slack_daily_report'),
        ('shifts', '0020_smena_pozice_skoleni'),
    ]

    operations = [
        migrations.CreateModel(
            name='PrumerMzdyMesicOverrideLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('akce', models.CharField(choices=[('create', 'Vytvoření'), ('update', 'Úprava'), ('delete', 'Smazání')], max_length=20)),
                ('rok', models.PositiveSmallIntegerField()),
                ('mesic', models.PositiveSmallIntegerField()),
                ('odpracovano_h_pred', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ('odpracovano_h_po', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ('fixni_body_pred', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('fixni_body_po', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('poznamka', models.TextField(blank=True, default='')),
                ('vytvoreno', users.fields.SafeDateTimeField(auto_now_add=True)),
                ('override', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logy', to='shifts.prumermzdymesicoverride')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prumer_mzdy_override_logy', to='users.webuser')),
                ('zmenil', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='prumer_mzdy_override_logy_provedl', to='users.webuser')),
            ],
            options={
                'verbose_name': 'Log ručních hodin',
                'verbose_name_plural': 'Logy ručních hodin',
                'db_table': 'WEB_PRUMER_MZDY_OVERRIDE_LOG',
                'ordering': ['-vytvoreno'],
            },
        ),
    ]
