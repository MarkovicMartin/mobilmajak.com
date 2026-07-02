from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shifts', '0015_smena_pozice_backoffice'),
    ]

    operations = [
        migrations.AlterField(
            model_name='smena',
            name='pozice_smeny',
            field=models.CharField(
                blank=True,
                choices=[
                    ('prodej', 'Prodej'),
                    ('servis', 'Servisní technik'),
                    ('backoffice', 'Backoffice'),
                    ('home_office', 'Home office'),
                ],
                default='prodej',
                max_length=20,
                verbose_name='Pozice na směně',
            ),
        ),
    ]
