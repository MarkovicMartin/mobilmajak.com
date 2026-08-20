from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_order_prodejna_status_labels'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='stale_reminder_sent_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Připomínka bez pohybu odeslána',
            ),
        ),
    ]
