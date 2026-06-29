from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('packeta', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='packetaprovizepolozka',
            name='id_prodejce',
            field=models.IntegerField(blank=True, db_index=True, null=True),
        ),
    ]
