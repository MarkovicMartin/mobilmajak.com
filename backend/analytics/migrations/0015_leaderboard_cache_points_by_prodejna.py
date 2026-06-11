from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0014_leaderboard_month_points_cache'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaderboardmonthpointscache',
            name='points_by_prodejna',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Mapa {"7": 12345, ...} – klíče jako řetězce kvůli JSON.',
                verbose_name='Body podle id_prodejny',
            ),
        ),
    ]
