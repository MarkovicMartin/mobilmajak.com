from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='url',
            field=models.CharField(blank=True, db_column='URL', default='', max_length=500),
        ),
    ]
