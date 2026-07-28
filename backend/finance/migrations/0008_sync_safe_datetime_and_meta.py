# State-only: DateTimeField → SafeDateTimeField v Django state (bez DDL).
# DB typ zůstává datetime(6). SafeDateTimeField.get_internal_type() musí zůstat
# 'SafeDateTimeField' (ne 'DateTimeField') – jinak MySQL converter spadne na zero-date.

from django.db import migrations
import users.fields


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0007_doklad_ocr_kontrola'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='financedoklad',
                    name='schvaleno',
                    field=users.fields.SafeDateTimeField(blank=True, null=True),
                ),
            ],
        ),
    ]
