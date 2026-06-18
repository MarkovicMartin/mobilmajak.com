from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0016_webvykupy_alter_leaderboardmonthpointscache_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DobropisPairingCache',
            fields=[
                ('sale_id', models.PositiveIntegerField(
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID řádku WEB_PRODEJE_ALL (dobropis)',
                )),
                ('pairing', models.CharField(max_length=16, verbose_name='Typ párování')),
                ('puvodni_doklad', models.CharField(blank=True, max_length=100, null=True)),
                ('puvodni_datum', models.DateField(blank=True, null=True)),
                ('puvodni_cas', models.TimeField(blank=True, null=True)),
                ('puvodni_cena', models.DecimalField(
                    blank=True, decimal_places=2, max_digits=10, null=True,
                )),
                ('puvodni_stredisko', models.CharField(blank=True, max_length=100, null=True)),
                ('minut_po_prodeji', models.FloatField(blank=True, null=True)),
                ('pairing_version', models.PositiveSmallIntegerField(default=1)),
                ('computed_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Cache párování dobropisu',
                'verbose_name_plural': 'Cache párování dobropisů',
            },
        ),
    ]
