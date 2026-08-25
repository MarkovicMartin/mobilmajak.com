from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0010_financedoklad_vs'),
    ]

    operations = [
        migrations.AddField(
            model_name='financedoklad',
            name='prirazeno_automaticky',
            field=models.BooleanField(default=False),
        ),
    ]
