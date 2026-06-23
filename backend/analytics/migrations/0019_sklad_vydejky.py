from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0018_dobropis_pairing_bez_paru_hint'),
    ]

    operations = [
        migrations.CreateModel(
            name='SkladVydejka',
            fields=[
                ('doklad', models.CharField(max_length=100, primary_key=True, serialize=False, verbose_name='Číslo dokladu')),
                ('vystaveno', models.DateField(db_index=True, verbose_name='Datum vystavení')),
                ('symplio_subtype', models.PositiveSmallIntegerField(verbose_name='Symplio subtype')),
                ('duvod_vyskladneni', models.CharField(max_length=255, verbose_name='Důvod vyskladnění')),
                ('sklad_typ', models.CharField(max_length=16, verbose_name='Typ skladu')),
                ('duvod_kategorie', models.CharField(max_length=16, verbose_name='Kategorie důvodu')),
                ('spravce', models.CharField(blank=True, max_length=100, null=True, verbose_name='Správce')),
                ('vazba', models.CharField(blank=True, max_length=255, null=True, verbose_name='Vazba')),
                ('castka_s_dph', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('castka_bez_dph', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('imported_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Skladová výdejka',
                'verbose_name_plural': 'Skladové výdejky',
                'db_table': 'WEB_SKLAD_VYDEJKY',
                'ordering': ['-vystaveno', 'doklad'],
            },
        ),
        migrations.CreateModel(
            name='SkladVydejkaPolozka',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kod', models.CharField(blank=True, max_length=100, null=True, verbose_name='Kód')),
                ('nazev', models.TextField(blank=True, null=True, verbose_name='Název')),
                ('pocet_kusu', models.IntegerField(default=0, verbose_name='Počet kusů')),
                ('cena_ks_bez_dph', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('cena_celkem_bez_dph', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('stredisko', models.CharField(blank=True, max_length=100, null=True)),
                ('spravce', models.CharField(blank=True, max_length=100, null=True)),
                ('vystaveno', models.DateField(blank=True, db_index=True, null=True)),
                ('cas_prodeje', models.TimeField(blank=True, null=True)),
                ('doklad', models.ForeignKey(db_column='doklad', on_delete=django.db.models.deletion.CASCADE, related_name='polozky', to='analytics.skladvydejka')),
            ],
            options={
                'verbose_name': 'Položka skladové výdejky',
                'verbose_name_plural': 'Položky skladových výdejek',
                'db_table': 'WEB_SKLAD_VYDEJKA_POLOZKY',
                'ordering': ['doklad_id', 'id'],
            },
        ),
    ]
