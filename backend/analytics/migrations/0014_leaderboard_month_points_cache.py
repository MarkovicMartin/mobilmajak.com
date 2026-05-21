from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0013_add_cas_prodeje_to_webprodejeall'),
    ]

    operations = [
        migrations.CreateModel(
            name='LeaderboardMonthPointsCache',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('month_ym', models.CharField(max_length=7, unique=True, verbose_name='Měsíc (YYYY-MM)')),
                ('points_by_prodejce', models.JSONField(
                    default=dict,
                    help_text='Mapa {"123": 450, ...} – klíče jako řetězce kvůli JSON.',
                    verbose_name='Body podle id_prodejce',
                )),
                ('computed_at', models.DateTimeField(auto_now=True, verbose_name='Naposledy spočítáno')),
            ],
            options={
                'verbose_name': 'Cache bodů žebříčku (měsíc)',
                'verbose_name_plural': 'Cache bodů žebříčku (měsíce)',
                'ordering': ['-month_ym'],
            },
        ),
    ]
