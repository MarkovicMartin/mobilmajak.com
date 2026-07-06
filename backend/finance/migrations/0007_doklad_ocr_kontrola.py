from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0006_nakladpolozka_auto_pravidlo'),
    ]

    operations = [
        migrations.AddField(
            model_name='financedoklad',
            name='match_detail',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='financedoklad',
            name='match_stav',
            field=models.CharField(
                blank=True,
                choices=[('ok', 'Sedí'), ('warn', 'Kontrola'), ('fail', 'Nesedí')],
                default='',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='financedoklad',
            name='schvaleno',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='financedoklad',
            name='schvalil_user_id',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='financedoklad',
            name='stav',
            field=models.CharField(
                choices=[
                    ('ceka_na_ocr', 'Čeká na OCR'),
                    ('ke_kontrole', 'Ke kontrole'),
                    ('schvaleno', 'Schváleno'),
                    ('zamitnuto', 'Zamítnuto'),
                    ('odeslano_flexi', 'Odesláno do Flexi'),
                    ('nova', 'Nová'),
                    ('sparovana', 'Spárovaná'),
                ],
                default='ceka_na_ocr',
                max_length=20,
            ),
        ),
    ]
