from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shifts', '0010_smena_prodejna_nullable_absence'),
    ]

    operations = [
        migrations.AddField(
            model_name='smena',
            name='pozice_smeny',
            field=models.CharField(
                blank=True,
                choices=[('prodej', 'Prodej'), ('servis', 'Servisní technik')],
                default='prodej',
                max_length=20,
                verbose_name='Pozice na směně',
            ),
        ),
    ]
