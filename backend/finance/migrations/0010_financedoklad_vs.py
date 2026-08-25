from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0009_financedoklad_flexi_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='financedoklad',
            name='vs',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
    ]
