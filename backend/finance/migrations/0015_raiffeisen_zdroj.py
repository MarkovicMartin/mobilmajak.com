from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0014_pravidlo_text_shoda'),
    ]

    operations = [
        migrations.AlterField(
            model_name='nakladpolozka',
            name='zdroj',
            field=models.CharField(
                choices=[
                    ('fio', 'Fio'),
                    ('raiffeisen', 'Raiffeisen'),
                    ('manual', 'Ruční'),
                    ('sheets_import', 'Sheets import'),
                    ('symplio_pokladna', 'Symplio pokladna'),
                ],
                default='manual',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='financezustatek',
            name='typ',
            field=models.CharField(
                choices=[
                    ('fio', 'Fio účet'),
                    ('raiffeisen', 'Raiffeisen účet'),
                    ('pokladna', 'Pokladna'),
                ],
                max_length=20,
            ),
        ),
    ]
