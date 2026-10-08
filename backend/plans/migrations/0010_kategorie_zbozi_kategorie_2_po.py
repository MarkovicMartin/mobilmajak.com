from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0009_kategorie_zbozi_bod_hned'),
    ]

    operations = [
        migrations.AddField(
            model_name='kategoriezboziclaim',
            name='kategorie_2_po',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]
