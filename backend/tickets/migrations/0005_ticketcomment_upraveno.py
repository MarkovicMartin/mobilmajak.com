from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0004_ticketuserreadstate'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticketcomment',
            name='upraveno',
            field=models.DateTimeField(blank=True, db_column='UPRAVENO', null=True),
        ),
    ]
