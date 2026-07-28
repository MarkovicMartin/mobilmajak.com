from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0019_sklad_vydejky'),
    ]

    operations = [
        migrations.CreateModel(
            name='ZasilkovnaLeaderboardCache',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('period_key', models.CharField(max_length=48, unique=True, verbose_name='Klíč období')),
                ('date_from', models.DateField(verbose_name='Od')),
                ('date_to', models.DateField(verbose_name='Do')),
                ('by_prodejce', models.JSONField(
                    default=dict,
                    help_text='Mapa {"4": {...}, ...} – klíče jako řetězce kvůli JSON.',
                    verbose_name='Metriky podle id_prodejce',
                )),
                ('by_prodejna', models.JSONField(
                    blank=True,
                    default=dict,
                    verbose_name='Metriky podle id_prodejny',
                )),
                ('source', models.CharField(blank=True, default='', max_length=32, verbose_name='Zdroj přepočtu')),
                ('computed_at', models.DateTimeField(auto_now=True, verbose_name='Naposledy spočítáno')),
            ],
            options={
                'verbose_name': 'Cache Zásilkovna žebříček',
                'verbose_name_plural': 'Cache Zásilkovna žebříček',
                'db_table': 'WEB_ZASILKOVNA_LEADERBOARD_CACHE',
                'ordering': ['-period_key'],
            },
        ),
    ]
