from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shifts', '0007_prodejnapohybudalost'),
    ]

    operations = [
        migrations.AddField(
            model_name='smena',
            name='brigadnik_rezim',
            field=models.CharField(
                blank=True,
                choices=[('prodejce', 'Jako prodejce'), ('vypomoc', 'Výpomoc')],
                default='prodejce',
                help_text='Výpomoc: 150 bodů/h bez provize. Jako prodejce: sazba z profilu + provize.',
                max_length=20,
                verbose_name='Režim brigádníka',
            ),
        ),
    ]
