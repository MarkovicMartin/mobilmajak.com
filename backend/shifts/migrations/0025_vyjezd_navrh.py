from django.db import migrations, models
import django.db.models.deletion
import users.fields


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0006_enable_servis_all_stores'),
        ('users', '0028_app_activity_log'),
        ('shifts', '0024_smena_pozice_vypomoc'),
    ]

    operations = [
        migrations.CreateModel(
            name='VyjezdNavrh',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mesic', models.DateField(verbose_name='Měsíc (první den)')),
                ('datum', models.DateField()),
                ('stav', models.CharField(
                    choices=[
                        ('navrh', 'Návrh'),
                        ('potvrzeno', 'Potvrzeno'),
                        ('zruseno', 'Zrušeno'),
                    ],
                    default='navrh',
                    max_length=20,
                )),
                ('vytvoreno', users.fields.SafeDateTimeField(auto_now_add=True)),
                ('upraveno', users.fields.SafeDateTimeField(auto_now=True)),
                ('prodejna', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='vyjezd_navrhy',
                    to='stores.prodejna',
                )),
                ('smena', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='vyjezd_navrhy',
                    to='shifts.smena',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='vyjezd_navrhy',
                    to='users.webuser',
                )),
            ],
            options={
                'verbose_name': 'Návrh výjezdu',
                'verbose_name_plural': 'Návrhy výjezdů',
                'db_table': 'WEB_VYJEZD_NAVRH',
                'ordering': ['mesic', 'user_id', 'datum'],
            },
        ),
        migrations.CreateModel(
            name='VyjezdNotifikace',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mesic', models.DateField(verbose_name='Měsíc (první den)')),
                ('message', models.CharField(max_length=400)),
                ('created_at', users.fields.SafeDateTimeField(auto_now_add=True)),
                ('read_at', users.fields.SafeDateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='vyjezd_notifikace',
                    to='users.webuser',
                )),
            ],
            options={
                'verbose_name': 'Notifikace výjezdu',
                'verbose_name_plural': 'Notifikace výjezdů',
                'db_table': 'WEB_VYJEZD_NOTIFIKACE',
                'ordering': ['-created_at'],
            },
        ),
    ]
