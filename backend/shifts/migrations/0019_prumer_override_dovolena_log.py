import django.db.models.deletion
from django.db import migrations, models

import users.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0023_webuser_slack_daily_report'),
        ('shifts', '0018_fix_penalizace_vytvoril_webuser'),
    ]

    operations = [
        migrations.CreateModel(
            name='PrumerMzdyMesicOverride',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rok', models.PositiveSmallIntegerField()),
                ('mesic', models.PositiveSmallIntegerField()),
                ('odpracovano_h', models.DecimalField(decimal_places=2, max_digits=7)),
                ('fixni_body', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Fixní výplata za měsíc (body)')),
                ('poznamka', models.TextField(blank=True, default='')),
                ('vytvoreno', users.fields.SafeDateTimeField(auto_now_add=True)),
                ('upraveno', users.fields.SafeDateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prumer_mzdy_overrides', to='users.webuser')),
                ('zmenil', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='prumer_mzdy_overrides_zmenil', to='users.webuser')),
            ],
            options={
                'verbose_name': 'Ruční hodiny pro průměr mzdy',
                'verbose_name_plural': 'Ruční hodiny pro průměr mzdy',
                'db_table': 'WEB_PRUMER_MZDY_OVERRIDE',
                'ordering': ['-rok', '-mesic'],
                'unique_together': {('user', 'rok', 'mesic')},
            },
        ),
        migrations.CreateModel(
            name='DovolenaKorekceLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fond_extra_h_pred', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('fond_extra_h_po', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('korekce_cerpano_h_pred', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('korekce_cerpano_h_po', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('poznamka', models.TextField(blank=True, default='')),
                ('vytvoreno', users.fields.SafeDateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dovolena_korekce_logy', to='users.webuser')),
                ('zmenil', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dovolena_korekce_provedl', to='users.webuser')),
            ],
            options={
                'verbose_name': 'Log korekce dovolené',
                'verbose_name_plural': 'Logy korekcí dovolené',
                'db_table': 'WEB_DOVOLENA_KOREKCE_LOG',
                'ordering': ['-vytvoreno'],
            },
        ),
    ]
