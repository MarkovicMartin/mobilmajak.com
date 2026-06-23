from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0017_dobropis_pairing_cache'),
    ]

    operations = [
        migrations.AddField(
            model_name='dobropispairingcache',
            name='bez_paru_duvod',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Důvod bez páru'),
        ),
        migrations.AddField(
            model_name='dobropispairingcache',
            name='kandidat_doklad',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Kandidát doklad'),
        ),
        migrations.AddField(
            model_name='dobropispairingcache',
            name='kandidat_datum',
            field=models.DateField(blank=True, null=True, verbose_name='Kandidát datum'),
        ),
        migrations.AddField(
            model_name='dobropispairingcache',
            name='kandidat_cas',
            field=models.TimeField(blank=True, null=True, verbose_name='Kandidát čas'),
        ),
        migrations.AddField(
            model_name='dobropispairingcache',
            name='kandidat_id_prodejce',
            field=models.IntegerField(blank=True, null=True, verbose_name='Kandidát ID prodejce'),
        ),
        migrations.AddField(
            model_name='dobropispairingcache',
            name='kandidat_cena',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Kandidát cena',
            ),
        ),
    ]
