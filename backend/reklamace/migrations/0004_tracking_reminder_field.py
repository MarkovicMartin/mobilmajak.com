from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reklamace', '0003_reminder_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='reklamacepolozka',
            name='reminder_tracking_2d_sent_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Odeslána 2d připomínka čísla balíčku',
            ),
        ),
    ]
