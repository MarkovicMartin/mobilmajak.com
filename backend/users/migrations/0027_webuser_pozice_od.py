from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0026_created_confirm_default_off'),
    ]

    operations = [
        migrations.AddField(
            model_name='webuser',
            name='pozice_od',
            field=models.DateField(
                blank=True,
                help_text='Od tohoto data (včetně) platí aktuální role a odměna. Výplata měsíce podle 1. dne.',
                null=True,
                verbose_name='Aktuální pozice od',
            ),
        ),
        migrations.AddField(
            model_name='webuser',
            name='pozice_predchozi',
            field=models.JSONField(
                blank=True,
                help_text='Snímek role a odměny před datem pozice_od.',
                null=True,
                verbose_name='Předchozí pozice',
            ),
        ),
    ]
