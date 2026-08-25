from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0008_sync_safe_datetime_and_meta'),
    ]

    operations = [
        migrations.AddField(
            model_name='financedoklad',
            name='flexi_id',
            field=models.CharField(blank=True, db_index=True, default='', max_length=32),
        ),
    ]
