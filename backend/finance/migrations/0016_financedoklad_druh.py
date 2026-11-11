from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0015_raiffeisen_zdroj'),
    ]

    operations = [
        migrations.AddField(
            model_name='financedoklad',
            name='druh',
            field=models.CharField(
                choices=[('faktura', 'Faktura'), ('dobropis', 'Dobropis')],
                db_index=True,
                default='faktura',
                max_length=16,
            ),
        ),
    ]
