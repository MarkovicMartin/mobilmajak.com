from django.db import migrations, models
import tickets.models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Ticket',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('nazev', models.CharField(db_column='NAZEV', max_length=200)),
                ('popis', models.TextField(db_column='POPIS')),
                ('stav', models.CharField(
                    choices=[('novy', 'Nový'), ('makam', 'Makám na tom'), ('opraveno', 'Opraveno')],
                    db_column='STAV', default='novy', max_length=20)),
                ('autor_id', models.IntegerField(db_column='AUTOR_ID')),
                ('autor_jmeno', models.CharField(blank=True, db_column='AUTOR_JMENO', default='', max_length=100)),
                ('vytvoreno', models.DateTimeField(auto_now_add=True, db_column='VYTVORENO')),
                ('upraveno', models.DateTimeField(auto_now=True, db_column='UPRAVENO')),
            ],
            options={
                'db_table': 'WEB_TICKETS',
                'ordering': ['-vytvoreno'],
            },
        ),
        migrations.CreateModel(
            name='TicketImage',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('ticket', models.ForeignKey(
                    db_column='TICKET_ID', on_delete=models.deletion.CASCADE,
                    related_name='images', to='tickets.ticket')),
                ('obrazek', models.ImageField(db_column='OBRAZEK', upload_to=tickets.models.get_ticket_image_path)),
                ('nahrano', models.DateTimeField(auto_now_add=True, db_column='NAHRANO')),
            ],
            options={
                'db_table': 'WEB_TICKET_IMAGES',
            },
        ),
        migrations.CreateModel(
            name='TicketComment',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('ticket', models.ForeignKey(
                    db_column='TICKET_ID', on_delete=models.deletion.CASCADE,
                    related_name='comments', to='tickets.ticket')),
                ('autor_id', models.IntegerField(db_column='AUTOR_ID')),
                ('autor_jmeno', models.CharField(blank=True, db_column='AUTOR_JMENO', default='', max_length=100)),
                ('text', models.TextField(db_column='TEXT')),
                ('vytvoreno', models.DateTimeField(auto_now_add=True, db_column='VYTVORENO')),
            ],
            options={
                'db_table': 'WEB_TICKET_COMMENTS',
                'ordering': ['vytvoreno'],
            },
        ),
    ]
