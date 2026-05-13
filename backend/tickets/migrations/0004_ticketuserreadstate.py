# Generated manually for WEB_TICKET_USER_READ

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0003_ticket_opraveno_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='TicketUserReadState',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('user_id', models.IntegerField(db_column='USER_ID')),
                ('last_seen_at', models.DateTimeField(db_column='LAST_SEEN_AT')),
                (
                    'ticket',
                    models.ForeignKey(
                        db_column='TICKET_ID',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='read_states',
                        to='tickets.ticket',
                    ),
                ),
            ],
            options={
                'db_table': 'WEB_TICKET_USER_READ',
            },
        ),
        migrations.AddConstraint(
            model_name='ticketuserreadstate',
            constraint=models.UniqueConstraint(fields=('user_id', 'ticket'), name='uniq_ticket_user_read'),
        ),
    ]
