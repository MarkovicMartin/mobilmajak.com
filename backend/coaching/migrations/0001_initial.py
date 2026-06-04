import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('users', '0017_webuser_dovolena_korekce'),
    ]

    operations = [
        migrations.CreateModel(
            name='CoachingNote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prodejna_id', models.IntegerField(blank=True, db_column='PRODEJNA_ID', null=True)),
                ('typ', models.CharField(
                    choices=[
                        ('poznamka', 'Poznámka'),
                        ('jedna_na_jednoho', '1:1'),
                        ('zpetna_vazba', 'Zpětná vazba'),
                    ],
                    db_column='TYP',
                    default='poznamka',
                    max_length=30,
                )),
                ('text', models.TextField(db_column='TEXT')),
                ('vytvoreno', models.DateTimeField(auto_now_add=True, db_column='VYTVORENO')),
                ('upraveno', models.DateTimeField(auto_now=True, db_column='UPRAVENO')),
                ('autor', models.ForeignKey(
                    db_column='AUTOR_ID',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='coaching_poznamky_autor',
                    to='users.webuser',
                )),
                ('prodejce', models.ForeignKey(
                    db_column='PRODEJCE_ID',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='coaching_poznamky',
                    to='users.webuser',
                )),
            ],
            options={
                'db_table': 'WEB_COACHING_NOTES',
                'ordering': ['-vytvoreno'],
            },
        ),
        migrations.CreateModel(
            name='CoachingGoal',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prodejna_id', models.IntegerField(blank=True, db_column='PRODEJNA_ID', null=True)),
                ('nazev', models.CharField(db_column='NAZEV', max_length=255)),
                ('popis', models.TextField(blank=True, db_column='POPIS', default='')),
                ('kategorie_metrika', models.CharField(blank=True, db_column='KATEGORIE_METRIKA', default='', max_length=60)),
                ('cil_hodnota', models.CharField(blank=True, db_column='CIL_HODNOTA', default='', max_length=64)),
                ('jednotka', models.CharField(blank=True, db_column='JEDNOTKA', default='', max_length=32)),
                ('termin', models.DateField(blank=True, db_column='TERMIN', null=True)),
                ('stav', models.CharField(
                    choices=[
                        ('otevreny', 'Otevřený'),
                        ('splneny', 'Splněný'),
                        ('zruseny', 'Zrušený'),
                    ],
                    db_column='STAV',
                    default='otevreny',
                    max_length=20,
                )),
                ('vytvoreno', models.DateTimeField(auto_now_add=True, db_column='VYTVORENO')),
                ('dokonceno_v', models.DateTimeField(blank=True, db_column='DOKONCENO_V', null=True)),
                ('autor', models.ForeignKey(
                    db_column='AUTOR_ID',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='coaching_cile_autor',
                    to='users.webuser',
                )),
                ('prodejce', models.ForeignKey(
                    db_column='PRODEJCE_ID',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='coaching_cile',
                    to='users.webuser',
                )),
            ],
            options={
                'db_table': 'WEB_COACHING_GOALS',
                'ordering': ['-vytvoreno'],
            },
        ),
    ]
