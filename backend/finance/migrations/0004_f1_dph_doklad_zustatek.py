# Generated manually for Finance F1

from django.db import migrations, models
import django.db.models.deletion
import users.fields


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0003_remove_packetaprovizepolozka'),
    ]

    operations = [
        migrations.AddField(
            model_name='nakladkategorie',
            name='parent',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='deti', to='finance.nakladkategorie',
            ),
        ),
        migrations.AddField(
            model_name='nakladkategorie',
            name='typ_dph',
            field=models.CharField(
                blank=True, choices=[('z_faktury', 'DPH z faktury'), ('bez', 'Bez DPH')],
                default='z_faktury', max_length=20,
            ),
        ),
        migrations.CreateModel(
            name='FinanceDoklad',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('soubor', models.CharField(blank=True, default='', max_length=500)),
                ('dodavatel_nazev', models.CharField(blank=True, default='', max_length=200)),
                ('dodavatel_ico', models.CharField(blank=True, default='', max_length=20)),
                ('cislo_faktury', models.CharField(blank=True, default='', max_length=64)),
                ('datum_vystaveni', models.DateField(blank=True, null=True)),
                ('datum_splatnosti', models.DateField(blank=True, null=True)),
                ('castka_celkem', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('castka_bez_dph', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('dph_castka', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('dph_sazba', models.IntegerField(blank=True, null=True)),
                ('stav', models.CharField(
                    choices=[('nova', 'Nová'), ('sparovana', 'Spárovaná')],
                    default='nova', max_length=20,
                )),
                ('ocr_raw', models.JSONField(blank=True, null=True)),
                ('vytvoreno', users.fields.SafeDateTimeField(auto_now_add=True)),
                ('upraveno', users.fields.SafeDateTimeField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Finance doklad',
                'verbose_name_plural': 'Finance doklady',
                'db_table': 'finance_doklad',
                'ordering': ['-vytvoreno'],
            },
        ),
        migrations.CreateModel(
            name='FinanceZustatek',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('datum', models.DateField()),
                ('typ', models.CharField(
                    choices=[('fio', 'Fio účet'), ('pokladna', 'Pokladna')], max_length=20,
                )),
                ('label', models.CharField(blank=True, default='', max_length=64)),
                ('prodejna_id', models.IntegerField(blank=True, null=True)),
                ('castka', models.DecimalField(decimal_places=2, max_digits=14)),
                ('mena', models.CharField(default='CZK', max_length=8)),
                ('vytvoreno', users.fields.SafeDateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Finance zůstatek',
                'verbose_name_plural': 'Finance zůstatky',
                'db_table': 'finance_zustatek',
                'ordering': ['-datum', '-id'],
            },
        ),
        migrations.AddField(
            model_name='nakladpolozka',
            name='castka_bez_dph',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='nakladpolozka',
            name='dph_castka',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='nakladpolozka',
            name='dph_sazba',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='nakladpolozka',
            name='dph_stav',
            field=models.CharField(
                choices=[
                    ('ceka_na_fakturu', 'Čeká na fakturu'),
                    ('sparovano', 'Spárováno'),
                    ('bez_dph', 'Bez DPH'),
                ],
                default='ceka_na_fakturu', max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='nakladpolozka',
            name='typ_platby',
            field=models.CharField(
                choices=[
                    ('odchozi', 'Odchozí'),
                    ('prichozi', 'Příchozí'),
                    ('interni', 'Interní'),
                ],
                default='odchozi', max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='nakladpolozka',
            name='symplio_doklad',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AlterField(
            model_name='nakladpolozka',
            name='zdroj',
            field=models.CharField(
                choices=[
                    ('fio', 'Fio'),
                    ('manual', 'Ruční'),
                    ('sheets_import', 'Sheets import'),
                    ('symplio_pokladna', 'Symplio pokladna'),
                ],
                default='manual', max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='nakladpolozka',
            name='doklad',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='naklady', to='finance.financedoklad',
            ),
        ),
        migrations.AddField(
            model_name='financedoklad',
            name='naklad_polozka',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='doklady', to='finance.nakladpolozka',
            ),
        ),
        migrations.AddIndex(
            model_name='nakladpolozka',
            index=models.Index(fields=['dph_stav'], name='finance_nak_dph_sta_idx'),
        ),
        migrations.AddIndex(
            model_name='financezustatek',
            index=models.Index(fields=['typ', 'datum'], name='finance_zus_typ_dat_idx'),
        ),
    ]
