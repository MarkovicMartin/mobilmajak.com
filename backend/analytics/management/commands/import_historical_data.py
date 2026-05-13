import csv
import logging
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from analytics.models import PolozkyMesicni

# Nastavení loggingu
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Importuje historická měsíční data z CSV souboru do tabulky PolozkyMesicni'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Cesta k CSV souboru s historickými daty'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Pouze testuje import bez uložení do databáze',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Detailní výstup',
        )

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        dry_run = options.get('dry_run', False)
        verbose = options.get('verbose', False)
        
        self.stdout.write(
            self.style.SUCCESS(f'🚀 Začínám import historických dat z: {csv_file_path}')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('⚠️  DRY RUN - data nebudou uložena do databáze')
            )
        
        try:
            imported_count = 0
            skipped_count = 0
            
            with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                # Kontrola požadovaných sloupců (podporuje i velká písmena)
                required_columns_lower = [
                    'prodejce', 'id prodejce', 'prodejna', 'id prodejna', 
                    'mesic_rok', 'nad_100', 'sluzby', 'pol_dok',
                    'ct300', 'ct600', 'ct1200', 'akt', 'zah250', 'nap', 
                    'zah500', 'kop250', 'kop500', 'pz1', 'knz'
                ]
                
                # Převedeme názvy sloupců na malá písmena pro porovnání
                fieldnames_lower = [col.lower().strip('"') for col in reader.fieldnames]
                missing_columns = set(required_columns_lower) - set(fieldnames_lower)
                if missing_columns:
                    raise CommandError(f'❌ Chybí sloupce v CSV: {", ".join(missing_columns)}')
                
                self.stdout.write(f'✅ CSV soubor obsahuje všechny požadované sloupce')
                
                # Vytvoříme mapování sloupců bez ohledu na velikost písmen
                def get_value(row, column_name):
                    """Získá hodnotu ze sloupce bez ohledu na velikost písmen nebo uvozovky"""
                    # Nejdřív zkusíme přesnou shodu
                    if column_name in row:
                        return row[column_name].strip().strip('"')
                    
                    # Pak zkusíme velká písmena
                    upper_name = column_name.upper()
                    if upper_name in row:
                        return row[upper_name].strip().strip('"')
                    
                    # Pak zkusíme s mezerami místo podtržítek
                    space_name = column_name.replace('_', ' ').upper()
                    if space_name in row:
                        return row[space_name].strip().strip('"')
                    
                    return ""
                
                with transaction.atomic():
                    for row_num, row in enumerate(reader, start=2):  # Start=2 kvůli header
                        try:
                            # Validace mesic_rok formátu
                            mesic_rok = get_value(row, 'mesic_rok')
                            if not mesic_rok or len(mesic_rok) != 7 or mesic_rok[4] != '-':
                                raise ValueError(f'Neplatný formát mesic_rok: {mesic_rok}. Očekává se formát YYYY-MM')
                            
                            # Kontrola, zda už záznam existuje
                            id_prodejce_val = get_value(row, 'id_prodejce')
                            existing = PolozkyMesicni.objects.filter(
                                id_prodejce=int(id_prodejce_val),
                                mesic_rok=mesic_rok
                            ).first()
                            
                            if existing:
                                if verbose:
                                    self.stdout.write(
                                        self.style.WARNING(f'⚠️  Řádek {row_num}: Záznam už existuje pro prodejce {get_value(row, "prodejce")} ({id_prodejce_val}) a měsíc {mesic_rok}')
                                    )
                                skipped_count += 1
                                continue
                            
                            if not dry_run:
                                # Vytvoření timestamp - první den měsíce v 12:00
                                year, month = mesic_rok.split('-')
                                timestamp = timezone.make_aware(datetime(int(year), int(month), 1, 12, 0, 0))
                                
                                # Vytvoření záznamu
                                prodejna_val = get_value(row, 'prodejna')
                                id_prodejna_val = get_value(row, 'id_prodejna')
                                
                                polozka = PolozkyMesicni.objects.create(
                                    prodejce=get_value(row, 'prodejce'),
                                    id_prodejce=int(id_prodejce_val),
                                    prodejna=prodejna_val if prodejna_val else None,
                                    id_prodejna=int(id_prodejna_val) if id_prodejna_val else None,
                                    mesic_rok=mesic_rok,
                                    timestamp=timestamp,
                                    nad_100=int(get_value(row, 'nad_100') or 0),
                                    sluzby=int(get_value(row, 'sluzby') or 0),
                                    pol_dok=float(get_value(row, 'pol_dok') or 0),
                                    ct300=int(get_value(row, 'ct300') or 0),
                                    ct600=int(get_value(row, 'ct600') or 0),
                                    ct1200=int(get_value(row, 'ct1200') or 0),
                                    akt=int(get_value(row, 'akt') or 0),
                                    zah250=int(get_value(row, 'zah250') or 0),
                                    nap=int(get_value(row, 'nap') or 0),
                                    zah500=int(get_value(row, 'zah500') or 0),
                                    kop250=int(get_value(row, 'kop250') or 0),
                                    kop500=int(get_value(row, 'kop500') or 0),
                                    pz1=int(get_value(row, 'pz1') or 0),
                                    knz=int(get_value(row, 'knz') or 0),
                                )
                                
                                if verbose:
                                    self.stdout.write(f'✅ Řádek {row_num}: Importován {get_value(row, "prodejce")} - {mesic_rok}')
                            
                            imported_count += 1
                            
                        except (ValueError, KeyError) as e:
                            self.stdout.write(
                                self.style.ERROR(f'❌ Chyba na řádku {row_num}: {str(e)}')
                            )
                            continue
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'❌ Neočekávaná chyba na řádku {row_num}: {str(e)}')
                            )
                            continue
            
            # Shrnutí
            self.stdout.write(
                self.style.SUCCESS(f'\n📊 SHRNUTÍ IMPORTU:')
            )
            self.stdout.write(f'   ✅ Úspěšně zpracováno: {imported_count} záznamů')
            self.stdout.write(f'   ⚠️  Přeskočeno (už existuje): {skipped_count} záznamů')
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f'\n⚠️  Toto byl pouze test - data nebyla uložena!')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'\n🎉 Import úspěšně dokončen!')
                )
                    
        except FileNotFoundError:
            raise CommandError(f'❌ Soubor nenalezen: {csv_file_path}')
        except Exception as e:
            raise CommandError(f'❌ Chyba při importu: {str(e)}') 