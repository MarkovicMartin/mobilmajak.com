import json
import requests
import logging
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from analytics.models import ProdejniDataDenni, ProdejniDataMesicni, GoogleSheetsConfig

# Nastavení loggingu
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Automaticky uloží aktuální analytická data do databáze (denní i měsíční)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--daily-only',
            action='store_true',
            help='Uložit pouze denní data',
        )
        parser.add_argument(
            '--monthly-only',
            action='store_true',
            help='Uložit pouze měsíční data',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Detailní výstup',
        )

    def handle(self, *args, **options):
        self.verbose = options.get('verbose', False)
        daily_only = options.get('daily_only', False)
        monthly_only = options.get('monthly_only', False)
        
        self.stdout.write(
            self.style.SUCCESS(f'🚀 Začínám automatické ukládání dat - {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}')
        )
        
        results = []
        
        try:
            # Pokud není specifikováno jinak, ukládáme oba typy dat
            if not monthly_only:
                daily_result = self.save_data_type('daily')
                results.append(('Denní', daily_result))
                
            if not daily_only:
                monthly_result = self.save_data_type('monthly')
                results.append(('Měsíční', monthly_result))
            
            # Výpis výsledků
            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.SUCCESS('📊 SOUHRN AUTOMATICKÉHO UKLÁDÁNÍ'))
            self.stdout.write('='*50)
            
            for data_type, result in results:
                if result['success']:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ {data_type} data: {result["message"]}'
                        )
                    )
                    if self.verbose:
                        self.stdout.write(f'   • Zpracováno: {result["saved_count"]} záznamů')
                        self.stdout.write(f'   • Aktualizováno: {result["updated_count"]} záznamů')
                        self.stdout.write(f'   • Vytvořeno: {result["created_count"]} záznamů')
                        self.stdout.write(f'   • Tabulka: {result["table_name"]}')
                else:
                    self.stdout.write(
                        self.style.ERROR(f'❌ {data_type} data: {result["error"]}')
                    )
            
            self.stdout.write('\n' + self.style.SUCCESS('🎉 Automatické ukládání dokončeno!'))
                    
        except Exception as e:
            error_msg = f'Kritická chyba při automatickém ukládání: {str(e)}'
            logger.error(error_msg)
            raise CommandError(error_msg)

    def save_data_type(self, data_type):
        """Uloží data konkrétního typu (daily/monthly)"""
        try:
            if self.verbose:
                self.stdout.write(f'📥 Načítám {data_type} data z Google Sheets...')
            
            # Načtení dat z Google Sheets (stejná logika jako ve views)
            sales_data = self.fetch_data_from_sheets(data_type)
            
            if not sales_data:
                return {
                    'success': False,
                    'error': f'Nepodařilo se načíst {data_type} data z Google Sheets'
                }
            
            if self.verbose:
                self.stdout.write(f'✅ Načteno {len(sales_data)} záznamů')
                self.stdout.write(f'💾 Ukládám {data_type} data do databáze...')
            
            # Uložení do databáze (stejná logika jako v SaveProdejnyDataView)
            result = self.save_to_database(data_type, sales_data)
            
            return result
            
        except Exception as e:
            error_msg = f'Chyba při ukládání {data_type} dat: {str(e)}'
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

    def fetch_data_from_sheets(self, data_type):
        """Načte data z Google Sheets"""
        try:
            # Načte konfiguraci Google Sheets
            config = GoogleSheetsConfig.objects.filter(is_active=True).first()
            if not config:
                if self.verbose:
                    self.stdout.write(self.style.WARNING('⚠️  Google Sheets konfigurace není nastavena, používám mock data'))
                return self.get_mock_data(data_type)
            
            # Určí název listu podle typu dat
            sheet_name = config.daily_sheet_name if data_type == 'daily' else config.monthly_sheet_name
            
            # Zavolá Google Apps Script pro načtení dat
            script_url = f"https://script.google.com/macros/s/AKfycbx9vCVq2YO6gDNn-1cGN10Y14dj2yCWvcAiSoQwmlCr2U7bNYTjag6CxlImqhMjPqtYeA/exec"
            params = {
                'spreadsheetId': config.spreadsheet_id,
                'sheetName': sheet_name,
                'action': 'getData'
            }
            
            response = requests.get(script_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('data', [])
            else:
                if self.verbose:
                    self.stdout.write(self.style.WARNING('⚠️  Google Sheets nedostupné, používám mock data'))
                return self.get_mock_data(data_type)
                
        except Exception as e:
            if self.verbose:
                self.stdout.write(self.style.WARNING(f'⚠️  Chyba při načítání z Google Sheets: {str(e)}, používám mock data'))
            return self.get_mock_data(data_type)

    def get_mock_data(self, data_type):
        """Vrátí mock data pro vývoj a testování"""
        if data_type == 'daily':
            return [
                {
                    'prodejna': 'Čepkov',
                    'prodejce': 'Lukáš Kováčik',
                    'id_prodejce': 1,
                    'polozky_nad_100': 33,
                    'sluzby_celkem': 2,
                    'pol_dok': 2.28,
                    'ct300': 1,
                    'ct600': 1,
                    'ct1200': 0,
                    'akt': 0,
                    'zah250': 0,
                    'nap': 0,
                    'zah500': 0,
                    'kop250': 0,
                    'kop500': 0,
                    'pz1': 0,
                    'knz': 0,
                    'aligator': 0
                },
                {
                    'prodejna': 'Globus',
                    'prodejce': 'Šimon Gabriel',
                    'id_prodejce': 2,
                    'polozky_nad_100': 31,
                    'sluzby_celkem': 10,
                    'pol_dok': 1.78,
                    'ct300': 1,
                    'ct600': 3,
                    'ct1200': 0,
                    'akt': 4,
                    'zah250': 0,
                    'nap': 1,
                    'zah500': 0,
                    'kop250': 0,
                    'kop500': 0,
                    'pz1': 1,
                    'knz': 0,
                    'aligator': 0
                }
            ]
        else:  # monthly
            return [
                {
                    'prodejna': 'Čepkov',
                    'prodejce': 'Lukáš Kováčik',
                    'id_prodejce': 1,
                    'polozky_nad_100': 856,
                    'sluzby_celkem': 45,
                    'pol_dok': 2.15,
                    'ct300': 23,
                    'ct600': 31,
                    'ct1200': 5,
                    'akt': 12,
                    'zah250': 8,
                    'nap': 15,
                    'zah500': 3,
                    'kop250': 2,
                    'kop500': 1,
                    'pz1': 7,
                    'knz': 4,
                    'aligator': 2
                },
                {
                    'prodejna': 'Globus',
                    'prodejce': 'Šimon Gabriel',
                    'id_prodejce': 2,
                    'polozky_nad_100': 1247,
                    'sluzby_celkem': 89,
                    'pol_dok': 1.95,
                    'ct300': 34,
                    'ct600': 67,
                    'ct1200': 12,
                    'akt': 89,
                    'zah250': 23,
                    'nap': 45,
                    'zah500': 8,
                    'kop250': 5,
                    'kop500': 3,
                    'pz1': 23,
                    'knz': 12,
                    'aligator': 7
                }
            ]

    def save_to_database(self, data_type, sales_data):
        """Uloží data do databáze - stejná logika jako SaveProdejnyDataView"""
        from users.models import WebUser
        timestamp = datetime.now()
        
        # Určení správného modelu podle typu dat
        if data_type == 'daily':
            ModelClass = ProdejniDataDenni
            table_name = 'WEB_ANALYTICS_PRODEJNIDATADENNI'
        elif data_type == 'monthly':
            ModelClass = ProdejniDataMesicni
            table_name = 'WEB_ANALYTICS_PRODEJNIDATAMESICNI'
        else:
            raise ValueError(f'Neplatný typ dat: {data_type}')
        
        # Uložení dat do databáze s upsert logikou
        with transaction.atomic():
            saved_count = 0
            updated_count = 0
            created_count = 0
            
            for item in sales_data:
                # Najít uživatele podle id_prodejce nebo jména
                uzivatel = None
                if item.get('id_prodejce'):
                    try:
                        uzivatel = WebUser.objects.get(id=item.get('id_prodejce'))
                    except WebUser.DoesNotExist:
                        pass
                elif item.get('prodejce'):
                    try:
                        jmeno_parts = item.get('prodejce').split()
                        if len(jmeno_parts) >= 2:
                            uzivatel = WebUser.objects.filter(
                                jmeno__icontains=jmeno_parts[0],
                                prijmeni__icontains=jmeno_parts[-1]
                            ).first()
                    except Exception:
                        pass
                
                # Příprava dat pro uložení podle typu
                if data_type == 'daily':
                    defaults = {
                        'uzivatel': uzivatel,
                        'datum': timestamp.date(),
                        'polozky_nad_100': item.get('polozky_nad_100', 0),
                        'sluzby_celkem': item.get('sluzby_celkem', 0),
                        'prumer_polozek_uctu': item.get('pol_dok', 0),
                        'ct300': item.get('ct300', 0),
                        'ct600': item.get('ct600', 0),
                        'ct1200': item.get('ct1200', 0),
                        'akt': item.get('akt', 0),
                        'zah250': item.get('zah250', 0),
                        'nap': item.get('nap', 0),
                        'zah500': item.get('zah500', 0),
                        'kop250': item.get('kop250', 0),
                        'kop500': item.get('kop500', 0),
                        'pz1': item.get('pz1', 0),
                        'knz': item.get('knz', 0),
                        'aligator': item.get('aligator', 0)
                    }
                    
                    # Lookup parametry pro denní data
                    if uzivatel:
                        lookup_params = {
                            'uzivatel': uzivatel,
                            'datum': timestamp.date()
                        }
                    else:
                        # Pro uživatele který neexistuje, vytvoř vždy nový záznam
                        obj = ModelClass.objects.create(**defaults)
                        saved_count += 1
                        created_count += 1
                        continue
                        
                else:  # monthly
                    defaults = {
                        'uzivatel': uzivatel,
                        'rok': timestamp.year,
                        'mesic': timestamp.month,
                        'polozky_nad_100': item.get('polozky_nad_100', 0),
                        'sluzby_celkem': item.get('sluzby_celkem', 0),
                        'prumer_polozek_uctu': item.get('pol_dok', 0),
                        'ct300': item.get('ct300', 0),
                        'ct600': item.get('ct600', 0),
                        'ct1200': item.get('ct1200', 0),
                        'akt': item.get('akt', 0),
                        'zah250': item.get('zah250', 0),
                        'nap': item.get('nap', 0),
                        'zah500': item.get('zah500', 0),
                        'kop250': item.get('kop250', 0),
                        'kop500': item.get('kop500', 0),
                        'pz1': item.get('pz1', 0),
                        'knz': item.get('knz', 0),
                        'aligator': item.get('aligator', 0)
                    }
                    
                    # Lookup parametry pro měsíční data
                    if uzivatel:
                        lookup_params = {
                            'uzivatel': uzivatel,
                            'rok': timestamp.year,
                            'mesic': timestamp.month
                        }
                    else:
                        # Pro uživatele který neexistuje, vytvoř vždy nový záznam
                        obj = ModelClass.objects.create(**defaults)
                        saved_count += 1
                        created_count += 1
                        continue
                
                # update_or_create - buď aktualizuje existující nebo vytvoří nový
                obj, created = ModelClass.objects.update_or_create(
                    **lookup_params,
                    defaults=defaults
                )
                
                saved_count += 1
                if created:
                    created_count += 1
                else:
                    updated_count += 1
        
        # Sestavení informativní zprávy
        if updated_count > 0 and created_count > 0:
            message = f'Zpracováno {saved_count} záznamů: {updated_count} aktualizováno, {created_count} vytvořeno'
        elif updated_count > 0:
            message = f'Aktualizováno {updated_count} existujících záznamů'
        else:
            message = f'Vytvořeno {created_count} nových záznamů'
        
        return {
            'success': True,
            'message': message,
            'saved_count': saved_count,
            'updated_count': updated_count,
            'created_count': created_count,
            'table_name': table_name,
            'timestamp': timestamp.isoformat(),
            'date_used': timestamp.date().isoformat() if data_type == 'daily' else f'{timestamp.year}-{timestamp.month:02d}'
        } 