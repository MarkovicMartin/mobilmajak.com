from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0002_ticket_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='opraveno_at',
            field=models.DateTimeField(blank=True, db_column='OPRAVENO_AT', null=True),
        ),
    ]
