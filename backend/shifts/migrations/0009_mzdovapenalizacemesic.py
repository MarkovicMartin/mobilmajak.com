from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0017_webuser_dovolena_korekce'),
        ('shifts', '0008_smena_brigadnik_rezim'),
    ]

    operations = [
        migrations.CreateModel(
            name='MzdovaPenalizaceMesic',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mesic', models.DateField(verbose_name='Měsíc (první den)')),
                ('duvod', models.TextField(verbose_name='Důvod srážky')),
                ('vytvoreno', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='mzda_penalizace_mesic',
                    to='users.webuser',
                )),
            ],
            options={
                'verbose_name': 'Měsíční penalizace',
                'verbose_name_plural': 'Měsíční penalizace',
                'db_table': 'WEB_MZDOVA_PENALIZACE_MESIC',
                'ordering': ['mesic', 'vytvoreno'],
            },
        ),
    ]
