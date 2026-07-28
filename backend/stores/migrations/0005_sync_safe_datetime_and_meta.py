# State-only: DateTimeField → SafeDateTimeField v Django state (bez DDL).
# DB typ zůstává datetime(6). SafeDateTimeField.get_internal_type() musí zůstat
# 'SafeDateTimeField' (ne 'DateTimeField') – jinak MySQL converter spadne na zero-date.

from django.db import migrations
import users.fields


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0004_alter_prodejna_vedouci_prodejny'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='prodejna',
                    name='datum_upravy',
                    field=users.fields.SafeDateTimeField(auto_now=True, verbose_name='Datum úpravy'),
                ),
                migrations.AlterField(
                    model_name='prodejna',
                    name='datum_vytvoreni',
                    field=users.fields.SafeDateTimeField(auto_now_add=True, verbose_name='Datum vytvoření'),
                ),
            ],
        ),
    ]
