from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0019_alter_webuser_mzda_zaklad'),
        ('plans', '0011_zakladani_nedostatek'),
    ]

    operations = [
        migrations.CreateModel(
            name='AutomatizaceKaretProblem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kod', models.CharField(db_index=True, max_length=100, verbose_name='P kód')),
                ('zbozi_id', models.PositiveIntegerField(blank=True, null=True, verbose_name='ID zboží')),
                ('nazev', models.CharField(blank=True, default='', max_length=255, verbose_name='Název')),
                ('typ', models.CharField(choices=[
                    ('chybejici_kategorie', 'Chybějící kategorie'),
                    ('nezname_ceny', 'Neznámé ceny'),
                    ('chybejici_fotka', 'Chybějící fotka'),
                    ('nejasna_rada', 'Nejasná řada'),
                    ('jine', 'Jiné'),
                ], max_length=32, verbose_name='Typ')),
                ('text', models.TextField(verbose_name='Problém')),
                ('stav', models.CharField(choices=[
                    ('otevreno', 'Otevřeno'),
                    ('vyreseno', 'Vyřešeno'),
                ], db_index=True, default='otevreno', max_length=16)),
                ('vytvoreno', models.DateTimeField(auto_now_add=True)),
                ('vyreseno', models.DateTimeField(blank=True, null=True)),
                ('vyresil', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='automatizace_karet_problemy', to='users.webuser',
                )),
            ],
            options={
                'verbose_name': 'Problém automatizace karet',
                'verbose_name_plural': 'Problémy automatizace karet',
                'db_table': 'WEB_AUTOMATIZACE_KARET',
                'ordering': ['-vytvoreno'],
            },
        ),
    ]
