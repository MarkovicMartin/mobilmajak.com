from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0021_safe_datetime_imported_at_and_cleanup'),
    ]

    operations = [
        migrations.CreateModel(
            name='VykupKartaStav',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('kod', models.CharField(max_length=50, unique=True)),
                ('hotovo', models.BooleanField(default=False)),
                ('skladem', models.BooleanField(default=False)),
                ('ukol_id', models.IntegerField(blank=True, null=True)),
                ('zbozi_id', models.CharField(blank=True, default='', max_length=20)),
                ('kategorie_id', models.CharField(blank=True, default='', max_length=20)),
                ('zkontrolovano', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Stav karty výkupu',
                'verbose_name_plural': 'Stavy karet výkupů',
                'db_table': 'WEB_VYKUP_KARTA_STAV',
            },
        ),
        migrations.CreateModel(
            name='VykupKartyHlaseni',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('mesic', models.CharField(max_length=7, unique=True)),
                ('odeslano_v', models.DateTimeField(auto_now_add=True)),
                ('pocet', models.IntegerField(default=0)),
                ('text', models.TextField(blank=True, default='')),
            ],
            options={
                'verbose_name': 'Hlášení karet výkupů',
                'verbose_name_plural': 'Hlášení karet výkupů',
                'db_table': 'WEB_VYKUP_KARTY_HLASENI',
            },
        ),
    ]
