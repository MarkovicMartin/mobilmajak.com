from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0019_sklad_vydejky'),
    ]

    operations = [
        migrations.AddField(
            model_name='webprodejeall',
            name='poznamka_dokladu',
            field=models.TextField(
                blank=True,
                db_column='Poznamka_dokladu',
                null=True,
                verbose_name='Poznámka k dokladu',
            ),
        ),
    ]
