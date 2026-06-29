# Packeta app – stav modelu přesunut z finance; DB tabulka finance_packeta_provize už existuje.

import users.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    state_operations = [
        migrations.CreateModel(
            name='PacketaProvizePolozka',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prodejna_id', models.IntegerField()),
                ('cas', models.DateTimeField()),
                ('zasilka', models.CharField(max_length=64)),
                ('zasilka_raw', models.CharField(blank=True, default='', max_length=80)),
                ('typ_provize', models.CharField(max_length=120)),
                ('castka', models.DecimalField(decimal_places=2, max_digits=10)),
                ('mena', models.CharField(default='Kč', max_length=8)),
                ('poznamka', models.CharField(blank=True, default='', max_length=200)),
                ('import_batch', models.CharField(max_length=64)),
                ('vytvoreno', users.fields.SafeDateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Packeta provize',
                'verbose_name_plural': 'Packeta provize položky',
                'db_table': 'finance_packeta_provize',
                'ordering': ['-cas'],
                'indexes': [
                    models.Index(fields=['prodejna_id', 'cas'], name='finance_pac_prodejn_124458_idx'),
                    models.Index(fields=['zasilka'], name='finance_pac_zasilka_137992_idx'),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name='packetaprovizepolozka',
            constraint=models.UniqueConstraint(
                fields=('prodejna_id', 'zasilka', 'typ_provize', 'cas'),
                name='finance_packeta_uniq_row',
            ),
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=state_operations,
            database_operations=[],
        ),
    ]
