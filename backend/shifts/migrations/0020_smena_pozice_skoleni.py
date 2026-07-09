from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shifts', '0019_prumer_override_dovolena_log'),
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
                    ('skoleni', 'Školení'),
                    ('backoffice', 'Backoffice'),
                    ('home_office', 'Home office'),
                ],
                default='prodej',
                max_length=20,
                verbose_name='Pozice na směně',
            ),
        ),
    ]
