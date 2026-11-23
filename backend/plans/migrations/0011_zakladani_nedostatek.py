from django.db import migrations, models
import django.db.models.deletion


def zaloz_chybejici_17c(apps, schema_editor):
    Nedostatek = apps.get_model('plans', 'ZakladaniNedostatek')
    Nedostatek.objects.get_or_create(
        kod='P153734',
        typ='chybejici_kategorie',
        stav='otevreno',
        defaults={
            'zbozi_id': 153429,
            'nazev': (
                'Tvrzené / ochranné sklo Xiaomi Redmi 14C / 17C černé'
                ' - Forcell Ultra Clear Glass'
            ),
            'text': (
                'Ve stromu Skla a fólie chybí list Xiaomi Redmi 17C. '
                'Karta je v Ke kontrole pod existujícím listem Xiaomi Redmi 14C.'
            ),
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0019_alter_webuser_mzda_zaklad'),
        ('plans', '0010_kategorie_zbozi_kategorie_2_po'),
    ]

    operations = [
        migrations.CreateModel(
            name='ZakladaniNedostatek',
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
                ('text', models.TextField(verbose_name='Co chybí')),
                ('stav', models.CharField(choices=[
                    ('otevreno', 'Otevřeno'),
                    ('vyreseno', 'Vyřešeno'),
                ], db_index=True, default='otevreno', max_length=16)),
                ('vytvoreno', models.DateTimeField(auto_now_add=True)),
                ('vyreseno', models.DateTimeField(blank=True, null=True)),
                ('vyresil', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='zakladani_nedostatky', to='users.webuser',
                )),
            ],
            options={
                'verbose_name': 'Nedostatek zakládání',
                'verbose_name_plural': 'Nedostatky zakládání',
                'db_table': 'WEB_ZAKLADANI_NEDOSTATEK',
                'ordering': ['-vytvoreno'],
            },
        ),
        migrations.RunPython(zaloz_chybejici_17c, migrations.RunPython.noop),
    ]
