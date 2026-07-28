# State-only: SafeDateTimeField + Meta ordering (bez DDL – sloupce už jsou datetime(6)).
# SafeDateTimeField.get_internal_type() musí zůstat 'SafeDateTimeField' (ne 'DateTimeField').

from django.db import migrations
import users.fields


class Migration(migrations.Migration):

    dependencies = [
        ('shifts', '0022_odmena_vytvoril_multi'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterModelOptions(
                    name='mzdovaodmenamesic',
                    options={
                        'ordering': ['mesic', 'vytvoreno'],
                        'verbose_name': 'Měsíční odměna',
                        'verbose_name_plural': 'Měsíční odměny',
                    },
                ),
                migrations.AlterField(
                    model_name='mzdovaodmenamesic',
                    name='upraveno',
                    field=users.fields.SafeDateTimeField(auto_now=True),
                ),
                migrations.AlterField(
                    model_name='mzdovaodmenamesic',
                    name='vytvoreno',
                    field=users.fields.SafeDateTimeField(auto_now_add=True),
                ),
                migrations.AlterField(
                    model_name='mzdovapenalizacemesic',
                    name='vytvoreno',
                    field=users.fields.SafeDateTimeField(auto_now_add=True),
                ),
                migrations.AlterField(
                    model_name='prodejnapohybudalost',
                    name='cas',
                    field=users.fields.SafeDateTimeField(db_index=True),
                ),
                migrations.AlterField(
                    model_name='prodejnapohybudalost',
                    name='vytvoreno',
                    field=users.fields.SafeDateTimeField(auto_now_add=True),
                ),
                migrations.AlterField(
                    model_name='smena',
                    name='upraveno',
                    field=users.fields.SafeDateTimeField(auto_now=True),
                ),
                migrations.AlterField(
                    model_name='smena',
                    name='vytvoreno',
                    field=users.fields.SafeDateTimeField(auto_now_add=True),
                ),
                migrations.AlterField(
                    model_name='smenadochazka',
                    name='cas',
                    field=users.fields.SafeDateTimeField(),
                ),
                migrations.AlterField(
                    model_name='smenadochazka',
                    name='vytvoreno',
                    field=users.fields.SafeDateTimeField(auto_now_add=True),
                ),
                migrations.AlterField(
                    model_name='smenastatistiky',
                    name='posledni_aktualizace',
                    field=users.fields.SafeDateTimeField(auto_now=True),
                ),
            ],
        ),
    ]
