from django.db import migrations, models
import django.db.models.deletion
import users.fields


class Migration(migrations.Migration):

    dependencies = [
        ('shifts', '0025_vyjezd_navrh'),
        ('users', '0028_app_activity_log'),
    ]

    operations = [
        migrations.CreateModel(
            name='MzdovyStit',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vytvoreno', users.fields.SafeDateTimeField(auto_now_add=True)),
                ('penalizace', models.OneToOneField(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='stit',
                    to='shifts.mzdovapenalizacemesic',
                    verbose_name='Spotřebováno na srážku',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='mzda_stity',
                    to='users.webuser',
                )),
                ('vytvoril', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='vytvorene_mzda_stity',
                    to='users.webuser',
                    verbose_name='Zadal',
                )),
            ],
            options={
                'verbose_name': 'Štít proti srážce 10 %',
                'verbose_name_plural': 'Štíty proti srážce 10 %',
                'db_table': 'WEB_MZDOVY_STIT',
                'ordering': ['vytvoreno'],
            },
        ),
    ]
