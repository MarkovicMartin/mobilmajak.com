# Generated manually for WEB_PRODEJE_ALL table

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0008_create_web_prodeje_all'),
    ]

    operations = [
        migrations.CreateModel(
            name='WebProdejeAll',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('typ', models.CharField(blank=True, db_column='Vystaveno', max_length=100, null=True, verbose_name='Datum prodeje')),
                ('kod', models.CharField(blank=True, db_column='Kod', max_length=100, null=True, verbose_name='Kód položky')),
                ('nazev', models.TextField(blank=True, db_column='Nazev', null=True, verbose_name='Název položky')),
                ('doklad', models.CharField(blank=True, db_column='Doklad', max_length=100, null=True, verbose_name='Číslo účtenky/faktury')),
                ('nazev_dokladu', models.CharField(blank=True, db_column='Nazev_dokladu', max_length=255, null=True, verbose_name='Název dokladu')),
                ('objednavka', models.CharField(blank=True, db_column='Objednavka', max_length=100, null=True, verbose_name='Číslo objednávky')),
                ('polozka', models.CharField(blank=True, db_column='Polozka', max_length=100, null=True, verbose_name='Položka dokladu')),
                ('stredisko', models.CharField(blank=True, db_column='Stredisko', max_length=100, null=True, verbose_name='Název prodejny')),
                ('spravce', models.CharField(blank=True, db_column='Spravce', max_length=100, null=True, verbose_name='Správce')),
                ('poznamka', models.TextField(blank=True, db_column='Poznamka', null=True, verbose_name='Poznámka k položce')),
                ('poznamka_dokladu', models.TextField(blank=True, db_column='Poznamka_dokladu', null=True, verbose_name='Poznámka k dokladu')),
                ('pocet_kusu', models.IntegerField(blank=True, db_column='Pocet_kusu', null=True, verbose_name='Počet kusů')),
                ('cena_ks_vcl_dph', models.DecimalField(blank=True, db_column='Cena_ks_vcl_DPH', decimal_places=2, max_digits=10, null=True, verbose_name='Prodejní cena s DPH')),
                ('skladova_cena_bez_dph', models.DecimalField(blank=True, db_column='Skladova_cena_bez_DPH', decimal_places=2, max_digits=10, null=True, verbose_name='Nákupní cena bez DPH')),
                ('skladova_cena_bez_dph_total', models.DecimalField(blank=True, db_column='Skladova_cena_bez_DPH_total', decimal_places=2, max_digits=10, null=True, verbose_name='Celková nákupní cena')),
                ('marketingovy_kanal', models.CharField(blank=True, db_column='Marketingovy_kanal', max_length=100, null=True, verbose_name='Marketing kanál')),
                ('dropshipping', models.CharField(blank=True, db_column='Dropshipping', max_length=10, null=True, verbose_name='Dropshipping')),
                ('id_prodejce', models.IntegerField(blank=True, db_column='ID_PRODEJCE', null=True, verbose_name='ID prodejce')),
                ('id_prodejny', models.IntegerField(blank=True, db_column='ID_PRODEJNY', null=True, verbose_name='ID prodejny')),
                ('zisk', models.DecimalField(blank=True, db_column='ZISK', decimal_places=2, max_digits=10, null=True, verbose_name='Zisk')),
                ('kategorie', models.CharField(blank=True, db_column='KATEGORIE', max_length=255, null=True, verbose_name='Hlavní kategorie')),
                ('kategorie_1', models.CharField(blank=True, db_column='KATEGORIE_1', max_length=255, null=True, verbose_name='Podkategorie 1')),
                ('kategorie_2', models.CharField(blank=True, db_column='KATEGORIE_2', max_length=255, null=True, verbose_name='Podkategorie 2')),
                
                # Rozšířená pole pro WEB_PRODEJE_ALL
                ('marze_procenta', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name='Marže v %')),
                ('je_nad_100_kc', models.BooleanField(default=False, verbose_name='Položka nad 100 Kč')),
                ('je_servisni_sluzba', models.BooleanField(default=False, verbose_name='Servisní služba')),
                ('je_eshop_prodej', models.BooleanField(default=False, verbose_name='E-shop prodej')),
                ('je_allegro_prodej', models.BooleanField(default=False, verbose_name='ALLEGRO prodej')),
                
                # Čas a období
                ('den_v_tydnu', models.IntegerField(blank=True, null=True, verbose_name='Den v týdnu (1-7)')),
                ('tyden_v_roce', models.IntegerField(blank=True, null=True, verbose_name='Týden v roce')),
                ('mesic', models.IntegerField(blank=True, null=True, verbose_name='Měsíc')),
                ('kvartal', models.IntegerField(blank=True, null=True, verbose_name='Kvartál')),
                ('rok', models.IntegerField(blank=True, null=True, verbose_name='Rok')),
                
                # Prodejní metriky
                ('pozice_v_dokladu', models.IntegerField(blank=True, null=True, verbose_name='Pozice položky v dokladu')),
                ('pocet_polozek_v_dokladu', models.IntegerField(blank=True, null=True, verbose_name='Celkový počet položek v dokladu')),
                ('celkova_hodnota_dokladu', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Celková hodnota dokladu')),
                
                # Prodejce informace
                ('nazev_prodejce', models.CharField(blank=True, max_length=100, null=True, verbose_name='Jméno prodejce')),
                ('je_hlavni_prodejce', models.BooleanField(default=False, verbose_name='Hlavní prodejce')),
                
                # Produktové kategorie pro analýzy
                ('je_accessory', models.BooleanField(default=False, verbose_name='Příslušenství')),
                ('je_telefon', models.BooleanField(default=False, verbose_name='Telefon')),
                ('je_tablet', models.BooleanField(default=False, verbose_name='Tablet')),
                ('je_smart_watch', models.BooleanField(default=False, verbose_name='Chytré hodinky')),
                
                # Import/sync informace
                ('importovano_z_web_prodeje', models.BooleanField(default=False, verbose_name='Importováno z WEB_PRODEJE')),
                ('datum_posledni_aktualizace', models.DateTimeField(blank=True, null=True, verbose_name='Datum poslední aktualizace')),
                
                # Metadata
                ('datum_vlozeni', models.DateTimeField(auto_now_add=True, db_column='datum_vlozeni', verbose_name='Datum vložení do DB')),
                ('datum_upravy', models.DateTimeField(auto_now=True, verbose_name='Datum úpravy')),
            ],
            options={
                'verbose_name': 'Prodejní položka (ALL)',
                'verbose_name_plural': 'Prodejní položky (ALL)',
                'db_table': 'WEB_PRODEJE_ALL',
                'ordering': ['-datum_vlozeni', '-id'],
            },
        ),
        
        # Přidání indexů pro optimalizaci výkonu
        migrations.RunSQL(
            sql=[
                "CREATE INDEX idx_prodeje_all_typ ON WEB_PRODEJE_ALL (Vystaveno);",
                "CREATE INDEX idx_prodeje_all_prodejce ON WEB_PRODEJE_ALL (ID_PRODEJCE);",
                "CREATE INDEX idx_prodeje_all_prodejny ON WEB_PRODEJE_ALL (ID_PRODEJNY);",
                "CREATE INDEX idx_prodeje_all_kanal ON WEB_PRODEJE_ALL (Marketingovy_kanal);",
                "CREATE INDEX idx_prodeje_all_kategorie ON WEB_PRODEJE_ALL (KATEGORIE);",
                "CREATE INDEX idx_prodeje_all_stredisko ON WEB_PRODEJE_ALL (Stredisko);",
                "CREATE INDEX idx_prodeje_all_nad_100 ON WEB_PRODEJE_ALL (je_nad_100_kc);",
                "CREATE INDEX idx_prodeje_all_servis ON WEB_PRODEJE_ALL (je_servisni_sluzba);",
                "CREATE INDEX idx_prodeje_all_eshop ON WEB_PRODEJE_ALL (je_eshop_prodej);",
                "CREATE INDEX idx_prodeje_all_mesic_rok ON WEB_PRODEJE_ALL (rok, mesic);",
                "CREATE INDEX idx_prodeje_all_import ON WEB_PRODEJE_ALL (importovano_z_web_prodeje);",
            ],
            reverse_sql=[
                "DROP INDEX idx_prodeje_all_typ ON WEB_PRODEJE_ALL;",
                "DROP INDEX idx_prodeje_all_prodejce ON WEB_PRODEJE_ALL;",
                "DROP INDEX idx_prodeje_all_prodejny ON WEB_PRODEJE_ALL;",
                "DROP INDEX idx_prodeje_all_kanal ON WEB_PRODEJE_ALL;",
                "DROP INDEX idx_prodeje_all_kategorie ON WEB_PRODEJE_ALL;",
                "DROP INDEX idx_prodeje_all_stredisko ON WEB_PRODEJE_ALL;",
                "DROP INDEX idx_prodeje_all_nad_100 ON WEB_PRODEJE_ALL;",
                "DROP INDEX idx_prodeje_all_servis ON WEB_PRODEJE_ALL;",
                "DROP INDEX idx_prodeje_all_eshop ON WEB_PRODEJE_ALL;",
                "DROP INDEX idx_prodeje_all_mesic_rok ON WEB_PRODEJE_ALL;",
                "DROP INDEX idx_prodeje_all_import ON WEB_PRODEJE_ALL;",
            ],
        ),
    ]