from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0005_seed_kategorie_excel'),
    ]

    operations = [
        migrations.AddField(
            model_name='nakladpolozka',
            name='auto_pravidlo',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
    ]
