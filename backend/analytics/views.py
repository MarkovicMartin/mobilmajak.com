import json
import requests
from datetime import datetime, date, timedelta
from django.utils.dateparse import parse_date
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.db import transaction
from django.db.models import F, Sum, Count, Avg, Q, Max
from django.db.models.functions import TruncMonth, TruncWeek, TruncDate, Cast, Coalesce, ExtractHour, ExtractWeekDay
from django.db.models import DateField
from django.db import models
from django.utils import timezone
# import datetime  # Removed to prevent conflict with from datetime import ...
from collections import defaultdict, Counter
from django.db.models import Case, When, IntegerField, DecimalField
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils.decorators import method_decorator
from rest_framework.decorators import permission_classes
from .models import ProdejniData, ProdejniDataDenni, ProdejniDataMesicni, GoogleSheetsConfig, WebProdejeAll, WebZasilkovna, WebVykupy
from .technik_utils import (
    merge_technici_rows,
    aggregate_by_canonical_technik,
    technik_filter_q,
    resolve_technik_display,
)
from users.models import WebUser
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import connection


def _count_unique_receipts(queryset):
    """Spočítá unikátní doklady - jen podle čísla dokladu (sloupec Doklad).
    Ignoruje NULL/empty doklady.
    OPTIMALIZOVÁNO: Používá distinct jen na 1 sloupec místo 4 (mnohem rychlejší).
    """
    cleaned = queryset.exclude(doklad__isnull=True).exclude(doklad='')
    return cleaned.values('doklad').distinct().count()


def _excluded_names_q():
    """Q výraz pro vyloučení přeprav/služeb, které se nemají započítat do průměru položek/účtenka
    
    Doprava se pozná podle toho, že NEMÁ vyplněný KÓD (sloupec 'kod' je prázdný nebo NULL).
    """
    return (
        Q(kod__isnull=True) |
        Q(kod__exact='')
    )

@method_decorator(permission_classes([AllowAny]), name='dispatch')
class ProdejnyDataView(View):
    """API endpoint pro načítání dat z Google Sheets"""
    
    def get(self, request):
        """Načte data z Google Sheets podle typu (daily/monthly)"""
        data_type = request.GET.get('type', 'daily')
        
        try:
            # Načte konfiguraci Google Sheets
            config = GoogleSheetsConfig.objects.filter(is_active=True).first()
            if not config:
                return JsonResponse({
                    'error': 'Google Sheets konfigurace není nastavena',
                    'data': [],
                    'lastUpdate': None
                }, status=500)
            
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
                return JsonResponse({
                    'data': data.get('data', []),
                    'lastUpdate': data.get('lastUpdate', datetime.now().isoformat()),
                    'success': True
                })
            else:
                # Fallback na mock data pro vývoj
                mock_data = self._get_mock_data(data_type)
                return JsonResponse({
                    'data': mock_data,
                    'lastUpdate': datetime.now().isoformat(),
                    'success': True,
                    'note': 'Používám mock data - Google Sheets nedostupné'
                })
                
        except Exception as e:
            # Fallback na mock data při chybě
            mock_data = self._get_mock_data(data_type)
            return JsonResponse({
                'data': mock_data,
                'lastUpdate': datetime.now().isoformat(),
                'success': True,
                'error': str(e),
                'note': 'Používám mock data - chyba při načítání'
            })
    
    def _get_mock_data(self, data_type):
        """Vrátí mock data pro vývoj"""
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
                    'prodejna': 'Šternberk',
                    'prodejce': 'Jan Létal',
                    'id_prodejce': 5,
                    'polozky_nad_100': 5,
                    'sluzby_celkem': 1,
                    'pol_dok': 1.5,
                    'ct300': 0,
                    'ct600': 0,
                    'ct1200': 0,
                    'akt': 1,
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
                },
                {
                    'prodejna': 'Vsetín',
                    'prodejce': 'Jan Snyrych',
                    'id_prodejce': 6,
                    'polozky_nad_100': 17,
                    'sluzby_celkem': 3,
                    'pol_dok': 1.58,
                    'ct300': 1,
                    'ct600': 0,
                    'ct1200': 0,
                    'akt': 0,
                    'zah250': 0,
                    'nap': 0,
                    'zah500': 0,
                    'kop250': 0,
                    'kop500': 0,
                    'pz1': 0,
                    'knz': 2,
                    'aligator': 0
                },
                {
                    'prodejna': 'Přerov',
                    'prodejce': 'Jakub Málek',
                    'id_prodejce': 3,
                    'polozky_nad_100': 17,
                    'sluzby_celkem': 2,
                    'pol_dok': 3.5,
                    'ct300': 0,
                    'ct600': 0,
                    'ct1200': 1,
                    'akt': 1,
                    'zah250': 0,
                    'nap': 0,
                    'zah500': 0,
                    'kop250': 0,
                    'kop500': 0,
                    'pz1': 0,
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


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(permission_classes([AllowAny]), name='dispatch')
class SaveProdejnyDataView(View):
    """API endpoint pro uložení dat do databáze"""
    
    def post(self, request):
        """Uloží aktuální data do databáze pro historické sledování"""
        try:
            data = json.loads(request.body)
            data_type = data.get('dataType')
            sales_data = data.get('data', [])
            timestamp_str = data.get('timestamp')
            
            # Validace
            if not data_type or not sales_data:
                return JsonResponse({'error': 'Chybí povinná data'}, status=400)
            
            # Parsování timestampu
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                timestamp = datetime.now()
            
            # Určení správného modelu podle typu dat
            if data_type == 'daily':
                ModelClass = ProdejniDataDenni
                table_name = 'WEB_ANALYTICS_PRODEJNIDATADENNI'
            elif data_type == 'monthly':
                ModelClass = ProdejniDataMesicni
                table_name = 'WEB_ANALYTICS_PRODEJNIDATAMESICNI'
            else:
                return JsonResponse({'error': f'Neplatný typ dat: {data_type}'}, status=400)
            
            # Uložení dat do databáze s upsert logikou
            with transaction.atomic():
                saved_count = 0
                updated_count = 0
                created_count = 0
                
                for item in sales_data:
                    # Najít uživatele podle id_prodejce nebo jména
                    uzivatel = None
                    debug_info = f"Item: id_prodejce={item.get('id_prodejce')}, prodejce={item.get('prodejce')}"
                    
                    if item.get('id_prodejce'):
                        try:
                            uzivatel = WebUser.objects.get(id=item.get('id_prodejce'))
                            debug_info += f" -> Nalezen podle ID: {uzivatel.uzivatelske_jmeno}"
                        except WebUser.DoesNotExist:
                            debug_info += f" -> ID {item.get('id_prodejce')} neexistuje v databázi"
                    elif item.get('prodejce'):
                        try:
                            jmeno_parts = item.get('prodejce').split()
                            if len(jmeno_parts) >= 2:
                                uzivatel = WebUser.objects.filter(
                                    jmeno__icontains=jmeno_parts[0],
                                    prijmeni__icontains=jmeno_parts[-1]
                                ).first()
                                if uzivatel:
                                    debug_info += f" -> Nalezen podle jména: {uzivatel.uzivatelske_jmeno}"
                                else:
                                    debug_info += f" -> Jméno '{jmeno_parts[0]} {jmeno_parts[-1]}' nebylo nalezeno"
                            else:
                                debug_info += f" -> Neplatné jméno: '{item.get('prodejce')}'"
                        except Exception as e:
                            debug_info += f" -> Chyba při hledání podle jména: {str(e)}"
                    else:
                        debug_info += " -> Chybí id_prodejce i prodejce"
                    
                    print(debug_info)
                    
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
                            # Pokud uživatel existuje, aktualizujeme jeho záznam
                            lookup_params = {
                                'uzivatel': uzivatel,
                                'datum': timestamp.date()
                            }
                        else:
                            # Pokud uživatel neexistuje, vytvoříme nový záznam s NULL uživatelem  
                            # Django uloží separátní záznamy protože NULL != NULL
                            lookup_params = {
                                'uzivatel': None,
                                'datum': timestamp.date()
                            }
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
                            # Pokud uživatel existuje, aktualizujeme jeho záznam
                            lookup_params = {
                                'uzivatel': uzivatel,
                                'rok': timestamp.year,
                                'mesic': timestamp.month
                            }
                        else:
                            # Pokud uživatel neexistuje, vytvoříme nový záznam s NULL uživatelem
                            lookup_params = {
                                'uzivatel': None,
                                'rok': timestamp.year,
                                'mesic': timestamp.month
                            }
                    
                    # Ukládání podle existence uživatele
                    if uzivatel:
                        # Pokud uživatel existuje, použij update_or_create
                        obj, created = ModelClass.objects.update_or_create(
                            **lookup_params,
                            defaults=defaults
                        )
                    else:
                        # Pokud uživatel neexistuje, vytvoř vždy nový záznam
                        obj = ModelClass.objects.create(**defaults)
                        created = True
                    
                    saved_count += 1
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
            
            # Sestavení informativní zprávy
            if updated_count > 0 and created_count > 0:
                message = f'Úspěšně zpracováno {saved_count} záznamů: {updated_count} aktualizováno, {created_count} vytvořeno v {table_name}'
            elif updated_count > 0:
                message = f'Úspěšně aktualizováno {updated_count} existujících záznamů v {table_name}'
            else:
                message = f'Úspěšně vytvořeno {created_count} nových záznamů v {table_name}'
            
            return JsonResponse({
                'success': True,
                'message': message,
                'saved_count': saved_count,
                'updated_count': updated_count,
                'created_count': created_count,
                'data_type': data_type,
                'table_name': table_name,
                'timestamp': timestamp.isoformat(),
                'date_used': timestamp.date().isoformat() if data_type == 'daily' else f'{timestamp.year}-{timestamp.month:02d}'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Neplatný JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Chyba při ukládání: {str(e)}'}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(permission_classes([AllowAny]), name='dispatch')
class DebugProdejnyDataView(View):
    """Debug endpoint pro diagnostiku ukládání dat"""
    
    def post(self, request):
        """Analyzuje data bez ukládání a ukáže debug informace"""
        try:
            data = json.loads(request.body)
            data_type = data.get('dataType')
            sales_data = data.get('data', [])
            
            if not data_type or not sales_data:
                return JsonResponse({'error': 'Chybí povinná data'}, status=400)
            
            debug_results = []
            found_users = []
            missing_users = []
            
            # Analýza každého záznamu
            for item in sales_data:
                item_debug = {
                    'raw_data': item,
                    'id_prodejce': item.get('id_prodejce'),
                    'prodejce': item.get('prodejce'),
                    'user_found': False,
                    'user_info': None,
                    'reason': None
                }
                
                # Najít uživatele podle id_prodejce nebo jména
                uzivatel = None
                if item.get('id_prodejce'):
                    try:
                        uzivatel = WebUser.objects.get(id=item.get('id_prodejce'))
                        item_debug['user_found'] = True
                        item_debug['user_info'] = {
                            'id': uzivatel.id,
                            'uzivatelske_jmeno': uzivatel.uzivatelske_jmeno,
                            'jmeno': uzivatel.jmeno,
                            'prijmeni': uzivatel.prijmeni
                        }
                        item_debug['reason'] = f"Nalezen podle ID: {uzivatel.uzivatelske_jmeno}"
                        found_users.append(item_debug)
                    except WebUser.DoesNotExist:
                        item_debug['reason'] = f"ID {item.get('id_prodejce')} neexistuje v databázi"
                        missing_users.append(item_debug)
                elif item.get('prodejce'):
                    try:
                        jmeno_parts = item.get('prodejce').split()
                        if len(jmeno_parts) >= 2:
                            uzivatel = WebUser.objects.filter(
                                jmeno__icontains=jmeno_parts[0],
                                prijmeni__icontains=jmeno_parts[-1]
                            ).first()
                            if uzivatel:
                                item_debug['user_found'] = True
                                item_debug['user_info'] = {
                                    'id': uzivatel.id,
                                    'uzivatelske_jmeno': uzivatel.uzivatelske_jmeno,
                                    'jmeno': uzivatel.jmeno,
                                    'prijmeni': uzivatel.prijmeni
                                }
                                item_debug['reason'] = f"Nalezen podle jména: {uzivatel.uzivatelske_jmeno}"
                                found_users.append(item_debug)
                            else:
                                item_debug['reason'] = f"Jméno '{jmeno_parts[0]} {jmeno_parts[-1]}' nebylo nalezeno v databázi"
                                missing_users.append(item_debug)
                        else:
                            item_debug['reason'] = f"Neplatné jméno: '{item.get('prodejce')}'"
                            missing_users.append(item_debug)
                    except Exception as e:
                        item_debug['reason'] = f"Chyba při hledání podle jména: {str(e)}"
                        missing_users.append(item_debug)
                else:
                    item_debug['reason'] = "Chybí id_prodejce i prodejce"
                    missing_users.append(item_debug)
                
                debug_results.append(item_debug)
            
            # Seznam všech uživatelů v databázi
            all_users = WebUser.objects.filter(aktivni=True).values(
                'id', 'uzivatelske_jmeno', 'jmeno', 'prijmeni'
            )
            
            return JsonResponse({
                'success': True,
                'summary': {
                    'total_records': len(sales_data),
                    'found_users_count': len(found_users),
                    'missing_users_count': len(missing_users),
                    'would_save_count': len(found_users)
                },
                'found_users': found_users,
                'missing_users': missing_users,
                'all_users_in_db': list(all_users),
                'debug_results': debug_results,
                'data_type': data_type
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Neplatný JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Chyba při debug analýze: {str(e)}'}, status=500)


@require_http_methods(["GET"])
@permission_classes([AllowAny])
def get_data_by_date(request):
    """Získá data z databáze pro konkrétní datum"""
    data_type = request.GET.get('type', 'daily')
    target_date = request.GET.get('date')  # format: YYYY-MM-DD
    
    if not target_date:
        return JsonResponse({'error': 'Parametr date je povinný (format: YYYY-MM-DD)'}, status=400)
    
    try:
        from datetime import datetime
        # Parsování data
        try:
            date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Neplatný formát data. Použijte YYYY-MM-DD'}, status=400)
        
        # Určení správného modelu podle typu dat
        if data_type == 'daily':
            ModelClass = ProdejniDataDenni
            # Pro denní data filtrujeme podle konkrétního data
            historical_data = ModelClass.objects.filter(
                datum=date_obj
            ).select_related('uzivatel').order_by('uzivatel__jmeno')
        elif data_type == 'monthly':
            ModelClass = ProdejniDataMesicni
            # Pro měsíční data filtrujeme podle roku a měsíce
            historical_data = ModelClass.objects.filter(
                rok=date_obj.year,
                mesic=date_obj.month
            ).select_related('uzivatel').order_by('uzivatel__jmeno')
        else:
            return JsonResponse({'error': f'Neplatný typ dat: {data_type}'}, status=400)
        
        # Serializace dat
        data = []
        for item in historical_data:
            # Sestavení jména prodejce a prodejny
            if item.uzivatel:
                prodejna = 'Prodejna'
                prodejce = f"{item.uzivatel.jmeno} {item.uzivatel.prijmeni}".strip()
                id_prodejce = item.uzivatel.id
            else:
                prodejna = 'Neznámá prodejna'
                prodejce = 'Neznámý prodejce'
                id_prodejce = None
            
            data.append({
                'id': item.id,
                'timestamp': item.datum.isoformat() if data_type == 'daily' else f"{item.rok}-{item.mesic:02d}-01",
                'prodejna': prodejna,
                'prodejce': prodejce,
                'id_prodejce': id_prodejce,
                'polozky_nad_100': item.polozky_nad_100,
                'sluzby_celkem': item.sluzby_celkem,
                'pol_dok': float(item.prumer_polozek_uctu),
                'ct300': item.ct300,
                'ct600': item.ct600,
                'ct1200': item.ct1200,
                'akt': item.akt,
                'zah250': item.zah250,
                'nap': item.nap,
                'zah500': item.zah500,
                'kop250': item.kop250,
                'kop500': item.kop500,
                'pz1': item.pz1,
                'knz': item.knz,
                'aligator': item.aligator
            })
        
        # Pokud nejsou data, vrátíme prázdný seznam s informativní zprávou
        if not data:
            date_str = date_obj.strftime('%d.%m.%Y')
            period_str = f"měsíc {date_obj.strftime('%m/%Y')}" if data_type == 'monthly' else f"den {date_str}"
            message = f'Pro {period_str} nejsou k dispozici žádná data.'
        else:
            date_str = date_obj.strftime('%d.%m.%Y')
            period_str = f"měsíc {date_obj.strftime('%m/%Y')}" if data_type == 'monthly' else f"den {date_str}"
            message = f'Načtena data za {period_str}'
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'data_type': data_type,
            'target_date': target_date,
            'formatted_date': date_obj.strftime('%d.%m.%Y'),
            'message': message,
            'table_used': ModelClass._meta.db_table
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Chyba při načítání: {str(e)}'}, status=500)


@require_http_methods(["GET"])
@permission_classes([AllowAny])
def get_historical_data(request):
    """Získá historická data z databáze"""
    data_type = request.GET.get('type', 'daily')
    limit = int(request.GET.get('limit', 100))
    
    try:
        if data_type == 'daily':
            data = ProdejniDataDenni.objects.all().order_by('-timestamp')[:limit]
        else:
            data = ProdejniDataMesicni.objects.all().order_by('-timestamp')[:limit]
        
        result = []
        for item in data:
            result.append({
                'id': item.id,
                'timestamp': item.timestamp.isoformat(),
                'prodejna': item.prodejna,
                'prodejce': item.prodejce,
                'id_prodejce': item.id_prodejce,
                'polozky_nad_100': item.polozky_nad_100,
                'sluzby_celkem': item.sluzby_celkem,
                'pol_dok': float(item.pol_dok),
                'ct300': item.ct300,
                'ct600': item.ct600,
                'ct1200': item.ct1200,
                'akt': item.akt,
                'zah250': item.zah250,
                'nap': item.nap,
                'zah500': item.zah500,
                'kop250': item.kop250,
                'kop500': item.kop500,
                'pz1': item.pz1,
                'knz': item.knz,
                'aligator': item.aligator
            })
        
        return JsonResponse({
            'data': result,
            'count': len(result),
            'type': data_type
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'data': []
        }, status=500)


# Nové endpointy pro analytiku prodejce

@require_http_methods(["GET"])
@permission_classes([AllowAny])
def get_salesperson_analytics(request):
    """Získá analytiku pro konkrétního prodejce"""
    user_id = request.GET.get('user_id')
    data_type = request.GET.get('type', 'daily')  # daily/monthly
    date = request.GET.get('date')  # volitelné - konkrétní datum
    
    if not user_id:
        return JsonResponse({'error': 'Chybí user_id parametr'}, status=400)
    
    try:
        # Určí model podle typu dat
        if data_type == 'daily':
            model = ProdejniDataDenni
        else:
            model = ProdejniDataMesicni
        
        # Filtruje data podle ID prodejce
        queryset = model.objects.filter(id_prodejce=user_id)
        
        # Pokud je zadáno konkrétní datum
        if date:
            try:
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                queryset = queryset.filter(timestamp__date=date_obj.date())
            except ValueError:
                return JsonResponse({'error': 'Neplatný formát data. Použijte YYYY-MM-DD'}, status=400)
        
        # Seřadí podle data (nejnovější první)
        queryset = queryset.order_by('-timestamp')
        
        result = []
        for item in queryset:
            result.append({
                'id': item.id,
                'timestamp': item.timestamp.isoformat(),
                'prodejna': item.prodejna,
                'prodejce': item.prodejce,
                'id_prodejce': item.id_prodejce,
                'polozky_nad_100': item.polozky_nad_100,
                'sluzby_celkem': item.sluzby_celkem,
                'pol_dok': float(item.pol_dok),
                'ct300': item.ct300,
                'ct600': item.ct600,
                'ct1200': item.ct1200,
                'akt': item.akt,
                'zah250': item.zah250,
                'nap': item.nap,
                'zah500': item.zah500,
                'kop250': item.kop250,
                'kop500': item.kop500,
                'pz1': item.pz1,
                'knz': item.knz,
                'aligator': item.aligator
            })
        
        # Vypočítá součty pro celkový přehled
        total_summary = {
            'celkem_polozky_nad_100': sum(item['polozky_nad_100'] for item in result),
            'celkem_sluzby': sum(item['sluzby_celkem'] for item in result),
            'celkem_ct300': sum(item['ct300'] for item in result),
            'celkem_ct600': sum(item['ct600'] for item in result),
            'celkem_ct1200': sum(item['ct1200'] for item in result),
            'celkem_akt': sum(item['akt'] for item in result),
            'celkem_zah250': sum(item['zah250'] for item in result),
            'celkem_nap': sum(item['nap'] for item in result),
            'celkem_zah500': sum(item['zah500'] for item in result),
            'celkem_kop250': sum(item['kop250'] for item in result),
            'celkem_kop500': sum(item['kop500'] for item in result),
            'celkem_pz1': sum(item['pz1'] for item in result),
            'celkem_knz': sum(item['knz'] for item in result),
            'celkem_aligator': sum(item['aligator'] for item in result),
            'prumer_pol_dok': sum(item['pol_dok'] for item in result) / len(result) if result else 0
        }
        
        return JsonResponse({
            'data': result,
            'summary': total_summary,
            'count': len(result),
            'type': data_type,
            'user_id': user_id
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'data': [],
            'summary': {}
        }, status=500)


@require_http_methods(["GET"])
@permission_classes([AllowAny])
def get_salesperson_today_data(request):
    """Získá dnešní data pro konkrétního prodejce"""
    user_id = request.GET.get('user_id')
    
    if not user_id:
        return JsonResponse({'error': 'Chybí user_id parametr'}, status=400)
    
    try:
        today = datetime.now().date()
        
        # Zkusí najít dnešní data v databázi
        today_data = ProdejniDataDenni.objects.filter(
            uzivatel_id=user_id,
            datum=today
        ).first()
        
        if today_data:
            # Data existují v databázi
            result = {
                'id': today_data.id,
                'timestamp': today_data.datum.isoformat(),
                'prodejna': 'Prodejna',  # TODO: Po implementaci prodejen nahradit správnou hodnotou
                'prodejce': today_data.uzivatel.jmeno if today_data.uzivatel else '',
                'id_prodejce': today_data.uzivatel_id,
                'polozky_nad_100': today_data.polozky_nad_100,
                'sluzby_celkem': today_data.sluzby_celkem,
                'pol_dok': float(today_data.prumer_polozek_uctu),
                'ct300': today_data.ct300,
                'ct600': today_data.ct600,
                'ct1200': today_data.ct1200,
                'akt': today_data.akt,
                'zah250': today_data.zah250,
                'nap': today_data.nap,
                'zah500': today_data.zah500,
                'kop250': today_data.kop250,
                'kop500': today_data.kop500,
                'pz1': today_data.pz1,
                'knz': today_data.knz,
                'aligator': today_data.aligator,
                'source': 'database'
            }
        else:
            # Zkusí načíst z Google Sheets
            try:
                config = GoogleSheetsConfig.objects.filter(is_active=True).first()
                if config:
                    script_url = f"https://script.google.com/macros/s/AKfycbx9vCVq2YO6gDNn-1cGN10Y14dj2yCWvcAiSoQwmlCr2U7bNYTjag6CxlImqhMjPqtYeA/exec"
                    params = {
                        'spreadsheetId': config.spreadsheet_id,
                        'sheetName': config.daily_sheet_name,
                        'action': 'getData'
                    }
                    
                    response = requests.get(script_url, params=params, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        sheets_data = data.get('data', [])
                        
                        # Najde data pro konkrétního prodejce
                        user_data = None
                        for item in sheets_data:
                            if str(item.get('id_prodejce')) == str(user_id):
                                user_data = item
                                break
                        
                        if user_data:
                            result = {
                                'id': None,
                                'timestamp': datetime.now().isoformat(),
                                'prodejna': user_data.get('prodejna', ''),
                                'prodejce': user_data.get('prodejce', ''),
                                'id_prodejce': user_data.get('id_prodejce'),
                                'polozky_nad_100': user_data.get('polozky_nad_100', 0),
                                'sluzby_celkem': user_data.get('sluzby_celkem', 0),
                                'pol_dok': float(user_data.get('pol_dok', 0)),
                                'ct300': user_data.get('ct300', 0),
                                'ct600': user_data.get('ct600', 0),
                                'ct1200': user_data.get('ct1200', 0),
                                'akt': user_data.get('akt', 0),
                                'zah250': user_data.get('zah250', 0),
                                'nap': user_data.get('nap', 0),
                                'zah500': user_data.get('zah500', 0),
                                'kop250': user_data.get('kop250', 0),
                                'kop500': user_data.get('kop500', 0),
                                'pz1': user_data.get('pz1', 0),
                                'knz': user_data.get('knz', 0),
                                'aligator': user_data.get('aligator', 0),
                                'source': 'google_sheets'
                            }
                        else:
                            result = {
                                'message': 'Pro dnešní den nejsou k dispozici žádná data',
                                'source': 'none'
                            }
                    else:
                        result = {
                            'message': 'Nepodařilo se načíst data z Google Sheets',
                            'source': 'error'
                        }
                else:
                    result = {
                        'message': 'Google Sheets konfigurace není nastavena',
                        'source': 'error'
                    }
            except Exception as e:
                result = {
                    'message': f'Chyba při načítání dat: {str(e)}',
                    'source': 'error'
                }
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'source': 'error'
        }, status=500)


@require_http_methods(["GET"])
@permission_classes([AllowAny])
def get_salesperson_monthly_data(request):
    """Získá měsíční data pro konkrétního prodejce"""
    user_id = request.GET.get('user_id')
    
    if not user_id:
        return JsonResponse({'error': 'Chybí user_id parametr'}, status=400)
    
    try:
        current_month = datetime.now().replace(day=1).date()
        
        # Zkusí najít měsíční data v databázi
        current_year = datetime.now().year
        current_month_num = datetime.now().month
        monthly_data = ProdejniDataMesicni.objects.filter(
            uzivatel_id=user_id,
            rok=current_year,
            mesic=current_month_num
        ).first()
        
        if monthly_data:
            # Data existují v databázi
            result = {
                'id': monthly_data.id,
                'timestamp': f"{monthly_data.rok}-{monthly_data.mesic:02d}-01",
                'prodejna': 'Prodejna',
                'prodejce': monthly_data.uzivatel.jmeno if monthly_data.uzivatel else '',
                'id_prodejce': monthly_data.uzivatel_id,
                'polozky_nad_100': monthly_data.polozky_nad_100,
                'sluzby_celkem': monthly_data.sluzby_celkem,
                'pol_dok': float(monthly_data.prumer_polozek_uctu),
                'ct300': monthly_data.ct300,
                'ct600': monthly_data.ct600,
                'ct1200': monthly_data.ct1200,
                'akt': monthly_data.akt,
                'zah250': monthly_data.zah250,
                'nap': monthly_data.nap,
                'zah500': monthly_data.zah500,
                'kop250': monthly_data.kop250,
                'kop500': monthly_data.kop500,
                'pz1': monthly_data.pz1,
                'knz': monthly_data.knz,
                'aligator': monthly_data.aligator,
                'source': 'database'
            }
        else:
            # Zkusí načíst z Google Sheets
            try:
                config = GoogleSheetsConfig.objects.filter(is_active=True).first()
                if config:
                    script_url = f"https://script.google.com/macros/s/AKfycbx9vCVq2YO6gDNn-1cGN10Y14dj2yCWvcAiSoQwmlCr2U7bNYTjag6CxlImqhMjPqtYeA/exec"
                    params = {
                        'spreadsheetId': config.spreadsheet_id,
                        'sheetName': config.monthly_sheet_name,
                        'action': 'getData'
                    }
                    
                    response = requests.get(script_url, params=params, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        sheets_data = data.get('data', [])
                        
                        # Najde data pro konkrétního prodejce
                        user_data = None
                        for item in sheets_data:
                            if str(item.get('id_prodejce')) == str(user_id):
                                user_data = item
                                break
                        
                        if user_data:
                            result = {
                                'id': None,
                                'timestamp': datetime.now().isoformat(),
                                'prodejna': user_data.get('prodejna', ''),
                                'prodejce': user_data.get('prodejce', ''),
                                'id_prodejce': user_data.get('id_prodejce'),
                                'polozky_nad_100': user_data.get('polozky_nad_100', 0),
                                'sluzby_celkem': user_data.get('sluzby_celkem', 0),
                                'pol_dok': float(user_data.get('pol_dok', 0)),
                                'ct300': user_data.get('ct300', 0),
                                'ct600': user_data.get('ct600', 0),
                                'ct1200': user_data.get('ct1200', 0),
                                'akt': user_data.get('akt', 0),
                                'zah250': user_data.get('zah250', 0),
                                'nap': user_data.get('nap', 0),
                                'zah500': user_data.get('zah500', 0),
                                'kop250': user_data.get('kop250', 0),
                                'kop500': user_data.get('kop500', 0),
                                'pz1': user_data.get('pz1', 0),
                                'knz': user_data.get('knz', 0),
                                'aligator': user_data.get('aligator', 0),
                                'source': 'google_sheets'
                            }
                        else:
                            result = {
                                'message': 'Pro aktuální měsíc nejsou k dispozici žádná data',
                                'source': 'none'
                            }
                    else:
                        result = {
                            'message': 'Nepodařilo se načíst data z Google Sheets',
                            'source': 'error'
                        }
                else:
                    result = {
                        'message': 'Google Sheets konfigurace není nastavena',
                        'source': 'error'
                    }
            except Exception as e:
                result = {
                    'message': f'Chyba při načítání dat: {str(e)}',
                    'source': 'error'
                }
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'source': 'error'
        }, status=500)


def calculate_points_for_data(data):
    """
    Vypočítá body podle zadané logiky:
    - Za každou prodanou položku nad 100 Kč = 15 bodů
    - CT300 = 15 bodů
    - CT600 = 50 bodů  
    - CT1200 = 100 bodů
    - AKT = 30 bodů
    - ZAH250 = 30 bodů
    - ZAH500 = 50 bodů
    - ZAH (obecně) = 50 bodů
    - KOP250 = 30 bodů
    - KOP500 = 50 bodů
    - NAP = 50 bodů
    - PZ1 = 100 bodů
    - KNZ = 30 bodů
    - ALIGATOR = 0 bodů
    """
    points = 0
    
    # Body za položky nad 100 Kč
    points += data.get('polozky_nad_100', 0) * 15
    
    # Body za specifické produkty
    points += data.get('ct300', 0) * 15
    points += data.get('ct600', 0) * 50
    points += data.get('ct1200', 0) * 100
    points += data.get('akt', 0) * 30
    points += data.get('zah250', 0) * 30
    points += data.get('zah500', 0) * 50
    points += data.get('kop250', 0) * 30
    points += data.get('kop500', 0) * 50
    points += data.get('nap', 0) * 50
    points += data.get('pz1', 0) * 100
    points += data.get('knz', 0) * 30
    points += data.get('aligator', 0) * 0  # ALIGATOR je za 0 bodů
    
    return points


@require_http_methods(["GET"])
@permission_classes([AllowAny])
def get_salesperson_points_today(request):
    """Získá dnešní bodový stav pro konkrétního prodejce"""
    user_id = request.GET.get('user_id')
    
    if not user_id:
        return JsonResponse({'error': 'Chybí user_id parametr'}, status=400)
    
    try:
        today = datetime.now().date()
        
        # Zkusí najít dnešní data v databázi
        today_data = ProdejniDataDenni.objects.filter(
            uzivatel_id=user_id,
            datum=today
        ).first()
        
        if today_data:
            # Data existují v databázi
            data = {
                'polozky_nad_100': today_data.polozky_nad_100,
                'ct300': today_data.ct300,
                'ct600': today_data.ct600,
                'ct1200': today_data.ct1200,
                'akt': today_data.akt,
                'zah250': today_data.zah250,
                'nap': today_data.nap,
                'zah500': today_data.zah500,
                'kop250': today_data.kop250,
                'kop500': today_data.kop500,
                'pz1': today_data.pz1,
                'knz': today_data.knz,
                'aligator': today_data.aligator
            }
            
            total_points = calculate_points_for_data(data)
            
            result = {
                'id': today_data.id,
                'date': today_data.datum.isoformat(),
                'prodejna': 'Prodejna',
                'prodejce': today_data.uzivatel.jmeno if today_data.uzivatel else '',
                'id_prodejce': today_data.uzivatel_id,
                'total_points': total_points,
                'breakdown': {
                    'polozky_nad_100': {'count': data['polozky_nad_100'], 'points': data['polozky_nad_100'] * 15},
                    'ct300': {'count': data['ct300'], 'points': data['ct300'] * 15},
                    'ct600': {'count': data['ct600'], 'points': data['ct600'] * 50},
                    'ct1200': {'count': data['ct1200'], 'points': data['ct1200'] * 100},
                    'akt': {'count': data['akt'], 'points': data['akt'] * 30},
                    'zah250': {'count': data['zah250'], 'points': data['zah250'] * 30},
                    'nap': {'count': data['nap'], 'points': data['nap'] * 50},
                    'zah500': {'count': data['zah500'], 'points': data['zah500'] * 50},
                    'kop250': {'count': data['kop250'], 'points': data['kop250'] * 30},
                    'kop500': {'count': data['kop500'], 'points': data['kop500'] * 50},
                    'pz1': {'count': data['pz1'], 'points': data['pz1'] * 100},
                    'knz': {'count': data['knz'], 'points': data['knz'] * 30},
                    'aligator': {'count': data['aligator'], 'points': data['aligator'] * 0}
                },
                'source': 'database'
            }
        else:
            # Zkusí načíst z Google Sheets
            try:
                config = GoogleSheetsConfig.objects.filter(is_active=True).first()
                if config:
                    script_url = f"https://script.google.com/macros/s/AKfycbx9vCVq2YO6gDNn-1cGN10Y14dj2yCWvcAiSoQwmlCr2U7bNYTjag6CxlImqhMjPqtYeA/exec"
                    params = {
                        'spreadsheetId': config.spreadsheet_id,
                        'sheetName': config.daily_sheet_name,
                        'action': 'getData'
                    }
                    
                    response = requests.get(script_url, params=params, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        sheets_data = data.get('data', [])
                        
                        # Najde data pro konkrétního prodejce
                        user_data = None
                        for item in sheets_data:
                            if str(item.get('id_prodejce')) == str(user_id):
                                user_data = item
                                break
                        
                        if user_data:
                            total_points = calculate_points_for_data(user_data)
                            
                            result = {
                                'id': None,
                                'date': datetime.now().date().isoformat(),
                                'prodejna': user_data.get('prodejna', ''),
                                'prodejce': user_data.get('prodejce', ''),
                                'id_prodejce': user_data.get('id_prodejce'),
                                'total_points': total_points,
                                'breakdown': {
                                    'polozky_nad_100': {'count': user_data.get('polozky_nad_100', 0), 'points': user_data.get('polozky_nad_100', 0) * 15},
                                    'ct300': {'count': user_data.get('ct300', 0), 'points': user_data.get('ct300', 0) * 15},
                                    'ct600': {'count': user_data.get('ct600', 0), 'points': user_data.get('ct600', 0) * 50},
                                    'ct1200': {'count': user_data.get('ct1200', 0), 'points': user_data.get('ct1200', 0) * 100},
                                    'akt': {'count': user_data.get('akt', 0), 'points': user_data.get('akt', 0) * 30},
                                    'zah250': {'count': user_data.get('zah250', 0), 'points': user_data.get('zah250', 0) * 30},
                                    'nap': {'count': user_data.get('nap', 0), 'points': user_data.get('nap', 0) * 50},
                                    'zah500': {'count': user_data.get('zah500', 0), 'points': user_data.get('zah500', 0) * 50},
                                    'kop250': {'count': user_data.get('kop250', 0), 'points': user_data.get('kop250', 0) * 30},
                                    'kop500': {'count': user_data.get('kop500', 0), 'points': user_data.get('kop500', 0) * 50},
                                    'pz1': {'count': user_data.get('pz1', 0), 'points': user_data.get('pz1', 0) * 100},
                                    'knz': {'count': user_data.get('knz', 0), 'points': user_data.get('knz', 0) * 30},
                                    'aligator': {'count': user_data.get('aligator', 0), 'points': user_data.get('aligator', 0) * 0}
                                },
                                'source': 'google_sheets'
                            }
                        else:
                            result = {
                                'message': 'Pro dnešní den nejsou k dispozici žádná data',
                                'total_points': 0,
                                'source': 'none'
                            }
                    else:
                        result = {
                            'message': 'Nepodařilo se načíst data z Google Sheets',
                            'total_points': 0,
                            'source': 'error'
                        }
                else:
                    result = {
                        'message': 'Google Sheets konfigurace není nastavena',
                        'total_points': 0,
                        'source': 'error'
                    }
            except Exception as e:
                result = {
                    'message': f'Chyba při načítání dat: {str(e)}',
                    'total_points': 0,
                    'source': 'error'
                }
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'total_points': 0,
            'source': 'error'
        }, status=500)


@require_http_methods(["GET"])
@permission_classes([AllowAny])
def get_salesperson_points_monthly(request):
    """Získá měsíční bodový stav pro konkrétního prodejce"""
    user_id = request.GET.get('user_id')
    
    if not user_id:
        return JsonResponse({'error': 'Chybí user_id parametr'}, status=400)
    
    try:
        current_year = datetime.now().year
        current_month_num = datetime.now().month
        
        # Zkusí najít měsíční data v databázi
        monthly_data = ProdejniDataMesicni.objects.filter(
            uzivatel_id=user_id,
            rok=current_year,
            mesic=current_month_num
        ).first()
        
        if monthly_data:
            # Data existují v databázi
            data = {
                'polozky_nad_100': monthly_data.polozky_nad_100,
                'ct300': monthly_data.ct300,
                'ct600': monthly_data.ct600,
                'ct1200': monthly_data.ct1200,
                'akt': monthly_data.akt,
                'zah250': monthly_data.zah250,
                'nap': monthly_data.nap,
                'zah500': monthly_data.zah500,
                'kop250': monthly_data.kop250,
                'kop500': monthly_data.kop500,
                'pz1': monthly_data.pz1,
                'knz': monthly_data.knz,
                'aligator': monthly_data.aligator
            }
            
            total_points = calculate_points_for_data(data)
            
            result = {
                'id': monthly_data.id,
                'date': f"{monthly_data.rok}-{monthly_data.mesic:02d}-01",
                'prodejna': 'Prodejna',
                'prodejce': monthly_data.uzivatel.jmeno if monthly_data.uzivatel else '',
                'id_prodejce': monthly_data.uzivatel_id,
                'total_points': total_points,
                'breakdown': {
                    'polozky_nad_100': {'count': data['polozky_nad_100'], 'points': data['polozky_nad_100'] * 15},
                    'ct300': {'count': data['ct300'], 'points': data['ct300'] * 15},
                    'ct600': {'count': data['ct600'], 'points': data['ct600'] * 50},
                    'ct1200': {'count': data['ct1200'], 'points': data['ct1200'] * 100},
                    'akt': {'count': data['akt'], 'points': data['akt'] * 30},
                    'zah250': {'count': data['zah250'], 'points': data['zah250'] * 30},
                    'nap': {'count': data['nap'], 'points': data['nap'] * 50},
                    'zah500': {'count': data['zah500'], 'points': data['zah500'] * 50},
                    'kop250': {'count': data['kop250'], 'points': data['kop250'] * 30},
                    'kop500': {'count': data['kop500'], 'points': data['kop500'] * 50},
                    'pz1': {'count': data['pz1'], 'points': data['pz1'] * 100},
                    'knz': {'count': data['knz'], 'points': data['knz'] * 30},
                    'aligator': {'count': data['aligator'], 'points': data['aligator'] * 0}
                },
                'source': 'database'
            }
        else:
            # Zkusí načíst z Google Sheets
            try:
                config = GoogleSheetsConfig.objects.filter(is_active=True).first()
                if config:
                    script_url = f"https://script.google.com/macros/s/AKfycbx9vCVq2YO6gDNn-1cGN10Y14dj2yCWvcAiSoQwmlCr2U7bNYTjag6CxlImqhMjPqtYeA/exec"
                    params = {
                        'spreadsheetId': config.spreadsheet_id,
                        'sheetName': config.monthly_sheet_name,
                        'action': 'getData'
                    }
                    
                    response = requests.get(script_url, params=params, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        sheets_data = data.get('data', [])
                        
                        # Najde data pro konkrétního prodejce
                        user_data = None
                        for item in sheets_data:
                            if str(item.get('id_prodejce')) == str(user_id):
                                user_data = item
                                break
                        
                        if user_data:
                            total_points = calculate_points_for_data(user_data)
                            
                            result = {
                                'id': None,
                                'date': f"{current_year}-{current_month_num:02d}-01",
                                'prodejna': user_data.get('prodejna', ''),
                                'prodejce': user_data.get('prodejce', ''),
                                'id_prodejce': user_data.get('id_prodejce'),
                                'total_points': total_points,
                                'breakdown': {
                                    'polozky_nad_100': {'count': user_data.get('polozky_nad_100', 0), 'points': user_data.get('polozky_nad_100', 0) * 15},
                                    'ct300': {'count': user_data.get('ct300', 0), 'points': user_data.get('ct300', 0) * 15},
                                    'ct600': {'count': user_data.get('ct600', 0), 'points': user_data.get('ct600', 0) * 50},
                                    'ct1200': {'count': user_data.get('ct1200', 0), 'points': user_data.get('ct1200', 0) * 100},
                                    'akt': {'count': user_data.get('akt', 0), 'points': user_data.get('akt', 0) * 30},
                                    'zah250': {'count': user_data.get('zah250', 0), 'points': user_data.get('zah250', 0) * 30},
                                    'nap': {'count': user_data.get('nap', 0), 'points': user_data.get('nap', 0) * 50},
                                    'zah500': {'count': user_data.get('zah500', 0), 'points': user_data.get('zah500', 0) * 50},
                                    'kop250': {'count': user_data.get('kop250', 0), 'points': user_data.get('kop250', 0) * 30},
                                    'kop500': {'count': user_data.get('kop500', 0), 'points': user_data.get('kop500', 0) * 50},
                                    'pz1': {'count': user_data.get('pz1', 0), 'points': user_data.get('pz1', 0) * 100},
                                    'knz': {'count': user_data.get('knz', 0), 'points': user_data.get('knz', 0) * 30},
                                    'aligator': {'count': user_data.get('aligator', 0), 'points': user_data.get('aligator', 0) * 0}
                                },
                                'source': 'google_sheets'
                            }
                        else:
                            result = {
                                'message': 'Pro aktuální měsíc nejsou k dispozici žádná data',
                                'total_points': 0,
                                'source': 'none'
                            }
                    else:
                        result = {
                            'message': 'Nepodařilo se načíst data z Google Sheets',
                            'total_points': 0,
                            'source': 'error'
                        }
                else:
                    result = {
                        'message': 'Google Sheets konfigurace není nastavena',
                        'total_points': 0,
                        'source': 'error'
                    }
            except Exception as e:
                result = {
                    'message': f'Chyba při načítání dat: {str(e)}',
                    'total_points': 0,
                    'source': 'error'
                }
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'total_points': 0,
            'source': 'error'
        }, status=500)


@require_http_methods(["GET"])
@permission_classes([AllowAny])
def get_leaderboard_monthly_points(request):
    """Získá žebříček prodejců podle bodů za aktuální měsíc"""
    try:
        current_year = datetime.now().year
        current_month_num = datetime.now().month
        
        # Načte všechna měsíční data pro aktuální měsíc
        monthly_data = ProdejniDataMesicni.objects.filter(
            rok=current_year,
            mesic=current_month_num,
            uzivatel__isnull=False  # Pouze prodejci s účtem
        ).select_related('uzivatel').order_by('uzivatel__jmeno')
        
        leaderboard = []
        
        for data in monthly_data:
            # Převod dat na formát pro výpočet bodů
            data_dict = {
                'polozky_nad_100': data.polozky_nad_100,
                'ct300': data.ct300,
                'ct600': data.ct600,
                'ct1200': data.ct1200,
                'akt': data.akt,
                'zah250': data.zah250,
                'nap': data.nap,
                'zah500': data.zah500,
                'kop250': data.kop250,
                'kop500': data.kop500,
                'pz1': data.pz1,
                'knz': data.knz,
                'aligator': data.aligator
            }
            
            total_points = calculate_points_for_data(data_dict)
            
            leaderboard.append({
                'id': data.uzivatel.id,
                'prodejce': f"{data.uzivatel.jmeno} {data.uzivatel.prijmeni}".strip(),
                'prodejna': 'Prodejna',  # TODO: Po implementaci prodejen nahradit správnou hodnotou
                'total_points': total_points,
                'polozky_nad_100': data.polozky_nad_100,
                'sluzby_celkem': data.sluzby_celkem,
                'prumer_polozek_uctu': float(data.prumer_polozek_uctu),
                'breakdown': {
                    'polozky_nad_100': {'count': data.polozky_nad_100, 'points': data.polozky_nad_100 * 15},
                    'ct300': {'count': data.ct300, 'points': data.ct300 * 15},
                    'ct600': {'count': data.ct600, 'points': data.ct600 * 50},
                    'ct1200': {'count': data.ct1200, 'points': data.ct1200 * 100},
                    'akt': {'count': data.akt, 'points': data.akt * 30},
                    'zah250': {'count': data.zah250, 'points': data.zah250 * 30},
                    'nap': {'count': data.nap, 'points': data.nap * 50},
                    'zah500': {'count': data.zah500, 'points': data.zah500 * 50},
                    'kop250': {'count': data.kop250, 'points': data.kop250 * 30},
                    'kop500': {'count': data.kop500, 'points': data.kop500 * 50},
                    'pz1': {'count': data.pz1, 'points': data.pz1 * 100},
                    'knz': {'count': data.knz, 'points': data.knz * 30},
                    'aligator': {'count': data.aligator, 'points': data.aligator * 0}
                }
            })
        
        # Pokud nejsou data v databázi, zkusí Google Sheets
        if not leaderboard:
            try:
                config = GoogleSheetsConfig.objects.filter(is_active=True).first()
                if config:
                    script_url = f"https://script.google.com/macros/s/AKfycbx9vCVq2YO6gDNn-1cGN10Y14dj2yCWvcAiSoQwmlCr2U7bNYTjag6CxlImqhMjPqtYeA/exec"
                    params = {
                        'spreadsheetId': config.spreadsheet_id,
                        'sheetName': config.monthly_sheet_name,
                        'action': 'getData'
                    }
                    
                    response = requests.get(script_url, params=params, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        sheets_data = data.get('data', [])
                        
                        for item in sheets_data:
                            if item.get('id_prodejce') and item.get('prodejce'):
                                total_points = calculate_points_for_data(item)
                                
                                leaderboard.append({
                                    'id': item.get('id_prodejce'),
                                    'prodejce': item.get('prodejce', 'Neznámý'),
                                    'prodejna': item.get('prodejna', 'Neznámá prodejna'),
                                    'total_points': total_points,
                                    'polozky_nad_100': item.get('polozky_nad_100', 0),
                                    'sluzby_celkem': item.get('sluzby_celkem', 0),
                                    'prumer_polozek_uctu': float(item.get('pol_dok', 0)),
                                    'breakdown': {
                                        'polozky_nad_100': {'count': item.get('polozky_nad_100', 0), 'points': item.get('polozky_nad_100', 0) * 15},
                                        'ct300': {'count': item.get('ct300', 0), 'points': item.get('ct300', 0) * 15},
                                        'ct600': {'count': item.get('ct600', 0), 'points': item.get('ct600', 0) * 50},
                                        'ct1200': {'count': item.get('ct1200', 0), 'points': item.get('ct1200', 0) * 100},
                                        'akt': {'count': item.get('akt', 0), 'points': item.get('akt', 0) * 30},
                                        'zah250': {'count': item.get('zah250', 0), 'points': item.get('zah250', 0) * 30},
                                        'nap': {'count': item.get('nap', 0), 'points': item.get('nap', 0) * 50},
                                        'zah500': {'count': item.get('zah500', 0), 'points': item.get('zah500', 0) * 50},
                                        'kop250': {'count': item.get('kop250', 0), 'points': item.get('kop250', 0) * 30},
                                        'kop500': {'count': item.get('kop500', 0), 'points': item.get('kop500', 0) * 50},
                                        'pz1': {'count': item.get('pz1', 0), 'points': item.get('pz1', 0) * 100},
                                        'knz': {'count': item.get('knz', 0), 'points': item.get('knz', 0) * 30},
                                        'aligator': {'count': item.get('aligator', 0), 'points': item.get('aligator', 0) * 0}
                                    }
                                })
            except Exception as e:
                print(f"Chyba při načítání z Google Sheets: {str(e)}")
        
        # Pokud stále nejsou data, použij mock data
        if not leaderboard:
            leaderboard = [
                {
                    'id': 1,
                    'prodejce': 'Lukáš Kováčik',
                    'prodejna': 'Čepkov',
                    'total_points': 8750,
                    'polozky_nad_100': 515,
                    'sluzby_celkem': 45,
                    'prumer_polozek_uctu': 2.15,
                    'breakdown': {
                        'polozky_nad_100': {'count': 515, 'points': 7725},
                        'ct300': {'count': 23, 'points': 345},
                        'ct600': {'count': 15, 'points': 750},
                        'ct1200': {'count': 0, 'points': 0},
                        'akt': {'count': 12, 'points': 360},
                        'zah250': {'count': 8, 'points': 240},
                        'nap': {'count': 15, 'points': 750},
                        'zah500': {'count': 3, 'points': 150},
                        'kop250': {'count': 2, 'points': 60},
                        'kop500': {'count': 1, 'points': 50},
                        'pz1': {'count': 7, 'points': 700},
                        'knz': {'count': 4, 'points': 120},
                        'aligator': {'count': 2, 'points': 0}
                    }
                },
                {
                    'id': 5,
                    'prodejce': 'Jan Létal',
                    'prodejna': 'Šternberk',
                    'total_points': 7865,
                    'polozky_nad_100': 484,
                    'sluzby_celkem': 38,
                    'prumer_polozek_uctu': 1.95,
                    'breakdown': {
                        'polozky_nad_100': {'count': 484, 'points': 7260},
                        'ct300': {'count': 18, 'points': 270},
                        'ct600': {'count': 12, 'points': 600},
                        'ct1200': {'count': 1, 'points': 100},
                        'akt': {'count': 8, 'points': 240},
                        'zah250': {'count': 6, 'points': 180},
                        'nap': {'count': 11, 'points': 550},
                        'zah500': {'count': 2, 'points': 100},
                        'kop250': {'count': 1, 'points': 30},
                        'kop500': {'count': 1, 'points': 50},
                        'pz1': {'count': 5, 'points': 500},
                        'knz': {'count': 3, 'points': 90},
                        'aligator': {'count': 1, 'points': 0}
                    }
                },
                {
                    'id': 2,
                    'prodejce': 'Šimon Gabriel',
                    'prodejna': 'Globus',
                    'total_points': 5905,
                    'polozky_nad_100': 356,
                    'sluzby_celkem': 67,
                    'prumer_polozek_uctu': 1.78,
                    'breakdown': {
                        'polozky_nad_100': {'count': 356, 'points': 5340},
                        'ct300': {'count': 14, 'points': 210},
                        'ct600': {'count': 8, 'points': 400},
                        'ct1200': {'count': 0, 'points': 0},
                        'akt': {'count': 22, 'points': 660},
                        'zah250': {'count': 5, 'points': 150},
                        'nap': {'count': 7, 'points': 350},
                        'zah500': {'count': 1, 'points': 50},
                        'kop250': {'count': 2, 'points': 60},
                        'kop500': {'count': 0, 'points': 0},
                        'pz1': {'count': 3, 'points': 300},
                        'knz': {'count': 6, 'points': 180},
                        'aligator': {'count': 3, 'points': 0}
                    }
                }
            ]
        
        # Seřadí podle bodů sestupně
        leaderboard.sort(key=lambda x: x['total_points'], reverse=True)
        
        # Přidá pozice
        for index, seller in enumerate(leaderboard):
            seller['position'] = index + 1
        
        return JsonResponse({
            'success': True,
            'data': leaderboard,
            'count': len(leaderboard),
            'month': current_month_num,
            'year': current_year,
            'type': 'points',
            'source': 'database' if monthly_data.exists() else 'google_sheets'
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'data': [],
            'success': False
        }, status=500)


@require_http_methods(["GET"])
@permission_classes([AllowAny])
def get_leaderboard_average_items(request):
    """Získá žebříček prodejců podle průměru položek na účtenku za aktuální měsíc"""
    try:
        current_year = datetime.now().year
        current_month_num = datetime.now().month
        
        # Načte všechna měsíční data pro aktuální měsíc
        monthly_data = ProdejniDataMesicni.objects.filter(
            rok=current_year,
            mesic=current_month_num,
            uzivatel__isnull=False,  # Pouze prodejci s účtem
            prumer_polozek_uctu__gt=0  # Pouze s průměrem větším než 0
        ).select_related('uzivatel').order_by('-prumer_polozek_uctu')
        
        leaderboard = []
        
        for data in monthly_data:
            leaderboard.append({
                'id': data.uzivatel.id,
                'prodejce': f"{data.uzivatel.jmeno} {data.uzivatel.prijmeni}".strip(),
                'prodejna': 'Prodejna',  # TODO: Po implementaci prodejen nahradit správnou hodnotou
                'prumer_polozek_uctu': float(data.prumer_polozek_uctu),
                'polozky_nad_100': data.polozky_nad_100,
                'sluzby_celkem': data.sluzby_celkem,
                'total_points': calculate_points_for_data({
                    'polozky_nad_100': data.polozky_nad_100,
                    'ct300': data.ct300,
                    'ct600': data.ct600,
                    'ct1200': data.ct1200,
                    'akt': data.akt,
                    'zah250': data.zah250,
                    'nap': data.nap,
                    'zah500': data.zah500,
                    'kop250': data.kop250,
                    'kop500': data.kop500,
                    'pz1': data.pz1,
                    'knz': data.knz,
                    'aligator': data.aligator
                })
            })
        
        # Pokud nejsou data v databázi, zkusí Google Sheets
        if not leaderboard:
            try:
                config = GoogleSheetsConfig.objects.filter(is_active=True).first()
                if config:
                    script_url = f"https://script.google.com/macros/s/AKfycbx9vCVq2YO6gDNn-1cGN10Y14dj2yCWvcAiSoQwmlCr2U7bNYTjag6CxlImqhMjPqtYeA/exec"
                    params = {
                        'spreadsheetId': config.spreadsheet_id,
                        'sheetName': config.monthly_sheet_name,
                        'action': 'getData'
                    }
                    
                    response = requests.get(script_url, params=params, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        sheets_data = data.get('data', [])
                        
                        for item in sheets_data:
                            pol_dok = float(item.get('pol_dok', 0))
                            if item.get('id_prodejce') and item.get('prodejce') and pol_dok > 0:
                                leaderboard.append({
                                    'id': item.get('id_prodejce'),
                                    'prodejce': item.get('prodejce', 'Neznámý'),
                                    'prodejna': item.get('prodejna', 'Neznámá prodejna'),
                                    'prumer_polozek_uctu': pol_dok,
                                    'polozky_nad_100': item.get('polozky_nad_100', 0),
                                    'sluzby_celkem': item.get('sluzby_celkem', 0),
                                    'total_points': calculate_points_for_data(item)
                                })
            except Exception as e:
                print(f"Chyba při načítání z Google Sheets: {str(e)}")
        
        # Pokud stále nejsou data, použij mock data
        if not leaderboard:
            leaderboard = [
                {
                    'id': 3,
                    'prodejce': 'Jakub Málek',
                    'prodejna': 'Přerov',
                    'prumer_polozek_uctu': 4.36,
                    'polozky_nad_100': 289,
                    'sluzby_celkem': 34,
                    'total_points': 4565
                },
                {
                    'id': 1,
                    'prodejce': 'Lukáš Kováčik',
                    'prodejna': 'Čepkov',
                    'prumer_polozek_uctu': 2.15,
                    'polozky_nad_100': 515,
                    'sluzby_celkem': 45,
                    'total_points': 8750
                },
                {
                    'id': 5,
                    'prodejce': 'Jan Létal',
                    'prodejna': 'Šternberk',
                    'prumer_polozek_uctu': 1.95,
                    'polozky_nad_100': 484,
                    'sluzby_celkem': 38,
                    'total_points': 7865
                },
                {
                    'id': 2,
                    'prodejce': 'Šimon Gabriel',
                    'prodejna': 'Globus',
                    'prumer_polozek_uctu': 1.78,
                    'polozky_nad_100': 356,
                    'sluzby_celkem': 67,
                    'total_points': 5905
                }
            ]
        
        # Seřadí podle průměru položek na účtenku sestupně
        leaderboard.sort(key=lambda x: x['prumer_polozek_uctu'], reverse=True)
        
        # Přidá pozice
        for index, seller in enumerate(leaderboard):
            seller['position'] = index + 1
        
        return JsonResponse({
            'success': True,
            'data': leaderboard,
            'count': len(leaderboard),
            'month': current_month_num,
            'year': current_year,
            'type': 'average_items',
            'source': 'database' if monthly_data.exists() else 'google_sheets'
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'data': [],
            'success': False
        }, status=500)


@require_http_methods(["GET"])
@permission_classes([AllowAny])
def get_last_backup_info(request):
    """Vrátí informace o posledním importu dat.

    Preferuje nové zdroje: WEB_PRODEJE_ALL (pokud existuje), jinak WEB_PRODEJE.
    Zachovává kompatibilitu s původní strukturou odpovědi.
    """
    try:
        # Používáme výhradně WEB_PRODEJE_ALL
        latest_web_prodeje = None
        latest_web_prodeje_all = WebProdejeAll.objects.order_by('-datum_vlozeni').first()

        total_web_prodeje = 0
        total_web_prodeje_all = WebProdejeAll.objects.count()
        
        # Počet záznamů za poslední měsíc
        from datetime import datetime, timedelta
        month_ago = datetime.now() - timedelta(days=30)
        recent_records = 0
        recent_records_all = WebProdejeAll.objects.filter(datum_vlozeni__gte=month_ago).count()
        
        # Vybereme nejnovější timestamp napříč tabulkami
        latest_iso_web_prodeje = latest_web_prodeje.datum_vlozeni.isoformat() if latest_web_prodeje else None
        latest_iso_web_prodeje_all = latest_web_prodeje_all.datum_vlozeni.isoformat() if latest_web_prodeje_all else None
        
        def max_iso(a, b):
            if a and b:
                return a if a > b else b
            return a or b
        
        last_any_import = latest_iso_web_prodeje_all
        
        response_data = {
            # Původní klíče (kompatibilita s frontendem)
            'last_daily_backup': last_any_import,
            'last_monthly_backup': last_any_import,
            # Nové klíče pro přesnější diagnostiku
            'daily_count': total_web_prodeje,
            'monthly_count': recent_records,
            'web_prodeje_count': 0,
            'web_prodeje_latest': None,
            'web_prodeje_all_count': total_web_prodeje_all,
            'web_prodeje_all_latest': latest_web_prodeje_all.datum_vlozeni.isoformat() if latest_web_prodeje_all else None,
            'backup_frequency': 'real-time',
            'backup_status': 'aktivní' if (total_web_prodeje_all or total_web_prodeje) else 'neaktivní',
            'data_source': 'WEB_PRODEJE_ALL' if total_web_prodeje_all else 'WEB_PRODEJE',
            'total_records': total_web_prodeje_all or total_web_prodeje,
            'recent_records': recent_records_all if total_web_prodeje_all else recent_records
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'error': f'Chyba při načítání informací o WEB_PRODEJE: {str(e)}',
            'last_daily_backup': None,
            'last_monthly_backup': None,
            'daily_count': 0,
            'monthly_count': 0,
            'web_prodeje_count': 0,
            'web_prodeje_latest': None,
            'backup_frequency': 'real-time',
            'backup_status': 'chyba',
            'data_source': 'WEB_PRODEJE',
            'total_records': 0,
            'recent_records': 0
        }, status=500)


@require_http_methods(["GET"])
@permission_classes([AllowAny])
def get_charts_data(request):
    """Získá agregovaná data pro interaktivní grafy"""
    try:
        # Parametry z requestu
        data_type = request.GET.get('type', 'daily')  # daily/monthly
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        prodejny = request.GET.getlist('prodejny[]')  # může být více prodejen
        metriky = request.GET.getlist('metriky[]')    # může být více metrik
        prodejce_id = request.GET.get('prodejce_id')
        
        # Výchozí metriky pokud nejsou specifikované
        if not metriky:
            metriky = ['polozky_nad_100']
        
        # Určení modelu podle typu dat
        if data_type == 'daily':
            ModelClass = ProdejniDataDenni
            date_field = 'datum'
        else:
            ModelClass = ProdejniDataMesicni
            date_field = 'rok'
        
        # Základní queryset
        queryset = ModelClass.objects.all()
        
        # Filtrování podle data
        if start_date and data_type == 'daily':
            queryset = queryset.filter(datum__gte=start_date)
        if end_date and data_type == 'daily':
            queryset = queryset.filter(datum__lte=end_date)
            
        # Filtrování podle prodejce
        if prodejce_id:
            queryset = queryset.filter(uzivatel_id=prodejce_id)
            
        # Filtrování podle prodejen (zatím podle uživatele)
        if prodejny:
            # Pro teď filtrujeme podle uživatelů, později můžeme přidat prodejna field
            uzivatel_ids = []
            # TODO: Po implementaci prodejen opravit filtrování
            # for prodejna in prodejny:
            #     # Najdeme uživatele podle názvu prodejny (zjednodušené)
            #     users = WebUser.objects.filter(prodejna__icontains=prodejna)
            #     uzivatel_ids.extend([u.id for u in users])
            # Dočasně zahrneme všechny uživatele
            uzivatel_ids = list(WebUser.objects.values_list('id', flat=True))
            if uzivatel_ids:
                queryset = queryset.filter(uzivatel_id__in=uzivatel_ids)
        
        # Seřazení podle data
        if data_type == 'daily':
            queryset = queryset.order_by('datum')
        else:
            queryset = queryset.order_by('rok', 'mesic')
        
        # Agregace dat pro graf
        chart_data = []
        aggregations = {}
        
        # Inicializace agregací pro každou metriku
        for metrika in metriky:
            aggregations[metrika] = {
                'sum': 0,
                'count': 0,
                'min': float('inf'),
                'max': float('-inf'),
                'values': []
            }
        
        # Zpracování dat
        for record in queryset:
            if data_type == 'daily':
                date_str = record.datum.strftime('%Y-%m-%d')
                display_date = record.datum.strftime('%d.%m.')
            else:
                date_str = f"{record.rok}-{record.mesic:02d}"
                display_date = f"{record.mesic}/{record.rok}"
            
            # Najdeme existující záznam pro toto datum nebo vytvoříme nový
            existing_point = None
            for point in chart_data:
                if point['date'] == date_str:
                    existing_point = point
                    break
            
            if not existing_point:
                existing_point = {
                    'date': date_str,
                    'displayDate': display_date,
                }
                chart_data.append(existing_point)
            
            # Přidáme data pro každou metriku
            for metrika in metriky:
                value = getattr(record, metrika, 0)
                
                # Pokud je to první prodejna/uživatel pro toto datum, nastavíme hodnotu
                if metrika not in existing_point:
                    existing_point[metrika] = value
                else:
                    # Jinak přičteme (sčítáme více prodejen)
                    existing_point[metrika] += value
                
                # Aktualizace agregací
                aggregations[metrika]['sum'] += value
                aggregations[metrika]['count'] += 1
                aggregations[metrika]['min'] = min(aggregations[metrika]['min'], value)
                aggregations[metrika]['max'] = max(aggregations[metrika]['max'], value)
                aggregations[metrika]['values'].append(value)
        
        # Výpočet finálních agregací
        final_aggregations = {}
        for metrika in metriky:
            agg = aggregations[metrika]
            if agg['count'] > 0:
                avg = agg['sum'] / agg['count']
                # Trend (jednoduchý výpočet z prvních a posledních hodnot)
                trend = 0
                if len(agg['values']) >= 2:
                    first_half = agg['values'][:len(agg['values'])//2]
                    second_half = agg['values'][len(agg['values'])//2:]
                    first_avg = sum(first_half) / len(first_half)
                    second_avg = sum(second_half) / len(second_half)
                    trend = ((second_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0
                
                final_aggregations[metrika] = {
                    'sum': agg['sum'],
                    'average': round(avg, 2),
                    'min': agg['min'] if agg['min'] != float('inf') else 0,
                    'max': agg['max'] if agg['max'] != float('-inf') else 0,
                    'count': agg['count'],
                    'trend': round(trend, 1)  # procenta
                }
            else:
                final_aggregations[metrika] = {
                    'sum': 0,
                    'average': 0,
                    'min': 0,
                    'max': 0,
                    'count': 0,
                    'trend': 0
                }
        
        # Seřadíme data podle data
        chart_data.sort(key=lambda x: x['date'])
        
        return JsonResponse({
            'success': True,
            'data': chart_data,
            'aggregations': final_aggregations,
            'meta': {
                'type': data_type,
                'start_date': start_date,
                'end_date': end_date,
                'prodejny': prodejny,
                'metriky': metriky,
                'prodejce_id': prodejce_id,
                'total_records': len(chart_data)
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'data': [],
            'aggregations': {}
        }, status=500)


# =============================================================================
# CELKOVÁ ČÍSLA - API endpointy pro analýzu dat z WEB_PRODEJE
# =============================================================================

from django.db.models import Sum, Count, Avg, Q, F, DateField
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, Coalesce, Cast
from dateutil.parser import parse as parse_date
from decimal import Decimal
from users.models import WebUser


@api_view(['GET'])
@permission_classes([AllowAny])  # Povolíme přístup pro testování
def celkova_cisla_view(request):
    """
    Hlavní endpoint pro modul 'Celková čísla'
    Vrací agregovaná data z tabulky WEB_PRODEJE_ALL podle zadaných filtrů
    """
    
    try:
        # Získání filtrů z GET parametrů
        start_date = request.GET.get('start_date')  # Formát: YYYY-MM-DD
        end_date = request.GET.get('end_date')      # Formát: YYYY-MM-DD
        period = request.GET.get('period', 'custom')  # daily, weekly, monthly, monthly_select, custom
        selected_month = request.GET.get('selected_month')  # Formát: YYYY-MM
        kanal = request.GET.get('kanal', 'all')     # all, prodejna, eshop, allegro, servis
        prodejna_id = request.GET.get('prodejna_id')  # ID konkrétní prodejny
        kategorie = request.GET.get('kategorie')    # Filtr podle hlavní kategorie
        
        # Základní QuerySet - NOVĚ používáme WEB_PRODEJE_ALL
        queryset = WebProdejeAll.objects.all()
        
        # Filtrování podle data
        if period != 'custom' and period != 'monthly_select':
            # Automatické období
            today = date.today()
            if period == 'daily':
                start_date = today
                end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1)
                end_date = today
                
        if start_date:
            try:
                start_date_parsed = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                # Filtrování podle sloupce 'Vystaveno' z WEB_PRODEJE_ALL
                queryset = queryset.filter(typ__gte=start_date_parsed.strftime('%Y-%m-%d'))
            except:
                pass
                
        if end_date:
            try:
                end_date_parsed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                # Pokud je ve sloupci 'Vystaveno' i čas, použijeme horní mez následující den (strictly < next day)
                end_upper = (end_date_parsed + timedelta(days=1)).strftime('%Y-%m-%d')
                queryset = queryset.filter(typ__lt=end_upper)
            except:
                pass
                
        # Filtrování podle vybraného měsíce
        if period == 'monthly_select' and selected_month:
            try:
                # selected_month je ve formátu YYYY-MM
                year, month = selected_month.split('-')
                start_date = date(int(year), int(month), 1)
                # Poslední den měsíce
                if int(month) == 12:
                    end_date = date(int(year) + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(int(year), int(month) + 1, 1) - timedelta(days=1)
                
                queryset = queryset.filter(
                    typ__gte=start_date.strftime('%Y-%m-%d'),
                    typ__lte=end_date.strftime('%Y-%m-%d')
                )
            except:
                pass
        
        # NOVÉ filtrování podle prodejního kanálu pro WEB_PRODEJE_ALL
        if kanal == 'eshop':
            # ESHOP: sloupec 18 (Marketingovy_kanal) = 'e-shop'
            # MINUS servis (sloupec 11 obsahuje "servis eda")  
            # MINUS allegro (sloupec 19 obsahuje "Baselinker")
            queryset = queryset.filter(marketingovy_kanal='e-shop').exclude(
                Q(objednavku_zalozil__icontains='servis eda') & Q(k_servisu='ANO')
            ).exclude(dropshipping='Baselinker')
        elif kanal == 'servis':
            # SERVIS: sloupec 11 obsahuje "servis eda" A k_servisu='ANO'
            queryset = queryset.filter(objednavku_zalozil__icontains='servis eda', k_servisu='ANO')
        elif kanal == 'allegro':
            # ALLEGRO: sloupec 19 (Dropshipping) = 'Baselinker'
            queryset = queryset.filter(dropshipping='Baselinker')
        elif kanal == 'prodejna':
            # PRODEJNA: všechno ostatní (mimo eshop, allegro, servis)
            queryset = queryset.exclude(marketingovy_kanal='e-shop').exclude(
                dropshipping='Baselinker'
            ).exclude(Q(objednavku_zalozil__icontains='servis eda') & Q(k_servisu='ANO'))
        
        # Filtrování podle prodejny
        if prodejna_id:
            queryset = queryset.filter(id_prodejny=prodejna_id)
            
        # Filtrování podle kategorie
        if kategorie:
            queryset = queryset.filter(kategorie__icontains=kategorie)
        
        # NOVÉ agregace pro WEB_PRODEJE_ALL
        aggregations = queryset.aggregate(
            # Základní počty
            celkem_polozek=Count('id'),
            celkem_kusu=Sum('pocet_kusu'),
            
            # Finanční metriky podle nových sloupců
            # Sloupec 13: Cena_ks_vcl_DPH - celkový obrat s DPH
            celkovy_obrat=Sum(
                F('pocet_kusu') * F('cena_ks_vcl_dph'), 
                default=0
            ),
            # Sloupec 14: Cena_ks_bez_DPH - obrat bez DPH (už předpočítaný)
            celkovy_obrat_bez_dph=Sum(
                F('pocet_kusu') * F('cena_ks_bez_dph'), 
                output_field=models.DecimalField(max_digits=15, decimal_places=2),
                default=0
            ),
            # Sloupec 22: ZISK - už předpočítaný zisk
            celkovy_zisk=Sum(
                F('pocet_kusu') * F('zisk'), 
                output_field=models.DecimalField(max_digits=15, decimal_places=2),
                default=0
            ),
            prumerna_cena=Avg('cena_ks_vcl_dph'),
            
            # Počty unikátních dokladů (účtenek/faktur)
            pocet_dokladu=Count('doklad', distinct=True),
        )
        
        # Výpočet marže
        if aggregations['celkovy_obrat'] and aggregations['celkovy_obrat'] > 0:
            aggregations['marze_procenta'] = round(
                (aggregations['celkovy_zisk'] / aggregations['celkovy_obrat']) * 100, 2
            )
        else:
            aggregations['marze_procenta'] = 0
            
        # Průměrná hodnota objednávky (AOV)
        if aggregations['pocet_dokladu'] and aggregations['pocet_dokladu'] > 0:
            aggregations['prumerna_objednavka'] = round(
                aggregations['celkovy_obrat'] / aggregations['pocet_dokladu'], 2
            )
        else:
            aggregations['prumerna_objednavka'] = 0
            
        # VÝKUPY - agregace z tabulky WEB_VYKUPY
        vykupy_qs = WebVykupy.objects.all()
        
        # Aplikace filtrů data na výkupy (používá se sloupec 'vystaveno')
        if start_date:
            try:
                sd = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                vykupy_qs = vykupy_qs.filter(vystaveno__gte=sd)
            except: pass
            
        if end_date:
            try:
                ed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                # Pro data bez času stačí lte, ale pro jistotu (pokud by DB měla čas) používáme logiku
                vykupy_qs = vykupy_qs.filter(vystaveno__lte=ed)
            except: pass
            
        vykupy_stats = vykupy_qs.aggregate(
            pocet_kusu=Count('id'),
            celkova_cena_bez_dph=Sum('cena_ks_bez_dph', default=0)
        )
        
        aggregations['vykupy_pocet'] = vykupy_stats.get('pocet_kusu', 0)
        aggregations['vykupy_suma'] = float(vykupy_stats.get('celkova_cena_bez_dph') or 0)
        
        # NOVÝ rozklad podle kanálů pro WEB_PRODEJE_ALL
        # Vyloučení logistických názvů (stejná logika jako v E‑shop analytice)
        shipping_exclude_q = (
            Q(nazev__icontains='Zásilkovna') | Q(nazev__icontains='ZASILKOVNA') |
            Q(nazev__icontains='Zásielkovňa') | Q(nazev__icontains='ZASIELKOVNA') |
            Q(nazev__icontains='Balíkovna') | Q(nazev__icontains='BALIKOVNA') |
            Q(nazev__icontains='Osobní odběr') | Q(nazev__icontains='OSOBNI ODBER')
        )

        # ESHOP: přísná definice jako v sekci E-shop (čistý e-shop)
        eshop_metrics = queryset.filter(
                marketingovy_kanal='e-shop'
            ).filter(
                Q(objednavku_zalozil__isnull=True) | Q(objednavku_zalozil='')
            ).filter(
                Q(poznamka__isnull=True) | Q(poznamka='')
            ).exclude(
                dropshipping='Baselinker'
            ).exclude(
                kategorie_1__icontains='!Servis'
            ).exclude(
                shipping_exclude_q
            ).aggregate(
                obrat=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
                marze=Sum(F('pocet_kusu') * F('zisk'), default=0),
                polozky=Count('id')
            )

        # ALLEGRO: dropshipping = Baselinker
        allegro_metrics = queryset.filter(dropshipping='Baselinker').aggregate(
                obrat=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
                marze=Sum(F('pocet_kusu') * F('zisk'), default=0),
                polozky=Count('id')
            )

        # SERVIS: objednavku_zalozil obsahuje "servis eda" A k_servisu='ANO'
        servis_metrics = queryset.filter(objednavku_zalozil__icontains='servis eda', k_servisu='ANO').aggregate(
                obrat=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
                marze=Sum(F('pocet_kusu') * F('zisk'), default=0),
                polozky=Count('id')
            )

        # PRODEJNA = celkový součet MINUS (eshop + allegro + servis) – zaručený součet
        total_obrat = aggregations.get('celkovy_obrat_bez_dph') or 0
        total_marze = aggregations.get('celkovy_zisk') or 0
        total_polozky = aggregations.get('celkem_polozek') or 0

        prodejna_metrics = {
            'obrat': max(0, float(total_obrat) - float(eshop_metrics['obrat'] or 0) - float(allegro_metrics['obrat'] or 0) - float(servis_metrics['obrat'] or 0)),
            'marze': max(0, float(total_marze) - float(eshop_metrics['marze'] or 0) - float(allegro_metrics['marze'] or 0) - float(servis_metrics['marze'] or 0)),
            'polozky': max(0, int(total_polozky) - int(eshop_metrics['polozky'] or 0) - int(allegro_metrics['polozky'] or 0) - int(servis_metrics['polozky'] or 0))
        }

        kanaly = {
            'prodejna': prodejna_metrics,
            'eshop': eshop_metrics,
            'allegro': allegro_metrics,
            'servis': servis_metrics,
        }
        
        # Top kategorie
        top_kategorie = queryset.values('kategorie').annotate(
            obrat=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
            polozky=Count('id')
        ).order_by('-obrat')[:10]
        
        # Top prodejny
        top_prodejny = queryset.values('stredisko', 'id_prodejny').annotate(
            obrat=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
            marze=Sum(F('pocet_kusu') * F('zisk'), default=0),
            polozky=Count('id')
        ).order_by('-obrat')[:10]
        
        # Nejprodávanější produkty
        top_produkty = queryset.values('kod', 'nazev').annotate(
            celkem_kusu=Sum('pocet_kusu'),
            obrat=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0)
        ).order_by('-celkem_kusu')[:10]
        
        # ========== ZÁSILKOVNA DATA ==========
        # Načítání provizních dat ze Zásilkovny
        zasilkovna_queryset = WebZasilkovna.objects.all()
        
        # Filtrování podle období
        if start_date:
            try:
                start_parsed = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                # Filtrujeme záznamy od začátku měsíce start_date
                zasilkovna_queryset = zasilkovna_queryset.filter(
                    rok__gte=start_parsed.year
                ).filter(
                    Q(rok__gt=start_parsed.year) | Q(mesic__gte=start_parsed.month)
                )
            except:
                pass
        
        if end_date:
            try:
                end_parsed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                # Filtrujeme záznamy do konce měsíce end_date
                zasilkovna_queryset = zasilkovna_queryset.filter(
                    rok__lte=end_parsed.year
                ).filter(
                    Q(rok__lt=end_parsed.year) | Q(mesic__lte=end_parsed.month)
                )
            except:
                pass
        
        # Filtrování podle prodejny
        if prodejna_id:
            zasilkovna_queryset = zasilkovna_queryset.filter(id_prodejna=prodejna_id)
        
        # Agregace dat ze Zásilkovny
        zasilkovna_agg = zasilkovna_queryset.aggregate(
            celkove_provize=Sum('celkove_provize_mesic', default=0),
            pocet_zaznamu=Count('id')
        )
        
        # Rozklad podle prodejen
        zasilkovna_prodejny = list(
            zasilkovna_queryset.values('prodejna', 'id_prodejna')
            .annotate(
                provize=Sum('celkove_provize_mesic', default=0),
                pocet_mesicu=Count('id')
            )
            .order_by('-provize')
        )
        
        # Sestavení zásilkovna dat
        zasilkovna_data = {
            'celkove_provize': float(zasilkovna_agg['celkove_provize'] or 0),
            'pocet_zaznamu': zasilkovna_agg['pocet_zaznamu'],
            'detail_prodejen': zasilkovna_prodejny
        }
        
        # Konvertování Decimal na float pro JSON serialization
        def convert_decimals(obj):
            if isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(item) for item in obj]
            elif isinstance(obj, Decimal):
                return float(obj)
            return obj
        
        response_data = {
            'success': True,
            'aggregations': convert_decimals(aggregations),
            'breakdown': {
                'kanaly': convert_decimals(kanaly),
                'top_kategorie': convert_decimals(list(top_kategorie)),
                'top_prodejny': convert_decimals(list(top_prodejny)),
                'top_produkty': convert_decimals(list(top_produkty))
            },
            'zasilkovna': convert_decimals(zasilkovna_data),
            'filters': {
                'start_date': start_date,
                'end_date': end_date,
                'period': period,
                'kanal': kanal,
                'prodejna_id': prodejna_id,
                'kategorie': kategorie
            },
            'meta': {
                'total_records': queryset.count(),
                'generated_at': datetime.now().isoformat()
            }
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Chyba při zpracování dat: {str(e)}',
            'aggregations': {},
            'breakdown': {}
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def celkova_cisla_trendy_view(request):
    """
    Endpoint pro trendová data - denní/týdenní/měsíční rozklady
    """
    
    try:
        # Získání parametrů
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        group_by = request.GET.get('group_by', 'daily')  # daily, weekly, monthly
        
        queryset = WebProdejeAll.objects.all()
        
        # Filtrování podle data
        if start_date:
            try:
                start_date_parsed = parse_date(start_date).date()
                queryset = queryset.filter(typ__gte=start_date_parsed.strftime('%Y-%m-%d'))
            except:
                pass
                
        if end_date:
            try:
                end_date_parsed = parse_date(end_date).date()
                queryset = queryset.filter(typ__lte=end_date_parsed.strftime('%Y-%m-%d'))
            except:
                pass
        
        # Protože 'typ' je varchar s datem ve formátu "DD. MM. YYYY", 
        # musíme data seskupit jinak
        # Pro jednoduchost použiji omezené seskupování podle typu
        trendy = queryset.values('typ').annotate(
            obrat=Sum(F('pocet_kusu') * F('cena_ks_vcl_dph'), default=0),
            zisk=Sum(F('pocet_kusu') * F('zisk'), default=0),
            polozky=Count('id'),
            kusy=Sum('pocet_kusu')
        ).order_by('typ')[:50]  # Omezíme na 50 dnů
        
        return JsonResponse({
            'success': True,
            'trendy': [
                {
                    'datum': item['typ'],
                    'obrat': float(item['obrat'] or 0),
                    'zisk': float(item['zisk'] or 0),
                    'polozky': item['polozky'],
                    'kusy': item['kusy'] or 0
                }
                for item in trendy
            ]
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'trendy': []
        }, status=500)


# ===============================
# CELKOVÁ ČÍSLA – ČASOVÉ ŘADY PODLE KATEGORIÍ
# ===============================
@api_view(['GET'])
@permission_classes([AllowAny])
def celkova_categories_timeseries_view(request):
    """
    Časové řady pro modul Celková čísla pro libovolný kanál
    Parametry:
      - dimension: kategorie | kategorie_1 | kategorie_2 | stredisko
      - group_by: daily | weekly | monthly
      - kanal: all | prodejna | eshop | allegro | servis
      - selected[]: výběr hodnot dimenze (pokud prázdné, vybereme TOP)
      - běžné datumové filtry (period/start_date/end_date/selected_month)
    """
    try:
        dimension = request.GET.get('dimension', 'kategorie')
        group_by = request.GET.get('group_by', 'monthly')
        kanal = request.GET.get('kanal', 'all')
        selected = request.GET.getlist('selected[]') or request.GET.getlist('selected')

        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        period = request.GET.get('period', 'custom')
        selected_month = request.GET.get('selected_month')

        if dimension not in {'kategorie','kategorie_1','kategorie_2','stredisko'}:
            return JsonResponse({'success': False, 'error': 'Neplatná dimenze'}, status=400)

        qs = WebProdejeAll.objects.all()

        # datumové filtry
        if period != 'custom' and period != 'monthly_select':
            today = date.today()
            if period == 'daily':
                start_date = today
                end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1)
                end_date = today
        elif period == 'monthly_select' and selected_month:
            # YYYY-MM
            try:
                y, m = selected_month.split('-')
                start_date = date(int(y), int(m), 1)
                # end to next month -1 day
                if int(m) == 12:
                    end_date = date(int(y)+1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(int(y), int(m)+1, 1) - timedelta(days=1)
            except Exception:
                pass

        if start_date:
            try:
                sd = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                qs = qs.filter(typ__gte=sd.strftime('%Y-%m-%d'))
            except Exception:
                pass
        if end_date:
            try:
                ed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                qs = qs.filter(typ__lte=ed.strftime('%Y-%m-%d'))
            except Exception:
                pass

        # filtr kanálu – logika jako v celkova_cisla_view
        if kanal == 'eshop':
            qs = qs.filter(marketingovy_kanal='e-shop').exclude(
                Q(objednavku_zalozil__icontains='servis eda')
            ).exclude(dropshipping='Baselinker')
        elif kanal == 'allegro':
            qs = qs.filter(dropshipping='Baselinker')
        elif kanal == 'servis':
            qs = qs.filter(objednavku_zalozil__icontains='servis eda', k_servisu='ANO')
        elif kanal == 'prodejna':
            qs = qs.exclude(marketingovy_kanal='e-shop').exclude(dropshipping='Baselinker').exclude(
                Q(objednavku_zalozil__icontains='servis eda') & Q(k_servisu='ANO')
            )

        # připrav dostupné TOP hodnoty
        top_values = list(
            qs.values(dimension).annotate(obrat=Sum(F('pocet_kusu')*F('cena_ks_bez_dph'), default=0))
              .order_by('-obrat').values_list(dimension, flat=True)[:10]
        )
        if not selected:
            selected = [v for v in top_values if v][:4]

        # periodická agregace
        date_cast = Cast('typ', DateField())
        if group_by == 'daily':
            period_expr = TruncDate(date_cast)
        elif group_by == 'weekly':
            period_expr = TruncWeek(date_cast)
        else:
            period_expr = TruncMonth(date_cast)

        base = qs
        if selected:
            base = base.filter(**{f"{dimension}__in": selected})

        rows = (
            base.annotate(period=period_expr)
                .values('period', dimension)
                .annotate(
                    obrat=Sum(F('pocet_kusu')*F('cena_ks_bez_dph'), default=0),
                    zisk=Sum(F('pocet_kusu')*F('zisk'), default=0),
                    kusy=Sum('pocet_kusu'),
                    polozky=Count('id'),
                    objednavky=Count('doklad', distinct=True),
                )
                .order_by('period')
        )

        series_map = {name: [] for name in selected}
        for r in rows:
            key = r.get(dimension) or 'Nezařazeno'
            if key not in series_map:
                series_map[key] = []
            series_map[key].append({
                'date': r['period'],
                'obrat': float(r['obrat'] or 0),
                'zisk': float(r['zisk'] or 0),
                'kusy': r['kusy'] or 0,
                'polozky': r['polozky'] or 0,
                'objednavky': r['objednavky'] or 0,
            })

        data = [{'key': k, 'points': v} for k,v in series_map.items()]
        return JsonResponse({
            'success': True,
            'dimension': dimension,
            'available': top_values,
            'selected': selected,
            'group_by': group_by,
            'data': data,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ===============================
# CELKOVÁ ČÍSLA – DETAIL/ITEMS PRO KANÁLY
# ===============================
@api_view(['GET'])
@permission_classes([AllowAny])
def celkova_prodejna_detail_view(request):
    """Detail kanálu Prodejna – rozklad podle středisek + top kategorie"""
    try:
        from stores.models import Prodejna
        
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        period = request.GET.get('period', 'custom')
        selected_month = request.GET.get('selected_month')

        qs = WebProdejeAll.objects.all()

        # datumové filtry
        if period != 'custom' and period != 'monthly_select':
            today = date.today()
            if period == 'daily':
                start_date = today
                end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1)
                end_date = today
        elif period == 'monthly_select' and selected_month:
            try:
                y, m = selected_month.split('-')
                start_date = date(int(y), int(m), 1)
                end_date = (date(int(y)+1,1,1)-timedelta(days=1)) if int(m)==12 else (date(int(y),int(m)+1,1)-timedelta(days=1))
            except Exception:
                pass

        # Parsování datumů pro prodeje i výkupy
        sd_parsed = None
        ed_parsed = None
        if start_date:
            try:
                sd_parsed = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                qs = qs.filter(typ__gte=sd_parsed.strftime('%Y-%m-%d'))
            except Exception:
                pass
        if end_date:
            try:
                ed_parsed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                qs = qs.filter(typ__lte=ed_parsed.strftime('%Y-%m-%d'))
            except Exception:
                pass

        # prodejna = vše mimo e-shop, allegro, servis
        qs = qs.exclude(marketingovy_kanal='e-shop').exclude(dropshipping='Baselinker').exclude(
            Q(objednavku_zalozil__icontains='servis eda') & Q(k_servisu='ANO')
        )

        # Agregace pouze podle id_prodejny (ne stredisko)
        prodejny_agg = qs.values('id_prodejny').annotate(
            obrat=Sum(F('pocet_kusu')*F('cena_ks_bez_dph'), default=0),
            marze=Sum(F('pocet_kusu')*F('zisk'), default=0),
            polozky=Count('id'),
            doklady=Count('doklad', distinct=True),
        ).order_by('-obrat')

        # Načtení názvů prodejen z WEB_PRODEJNY
        prodejny_names = {p.id: p.nazev for p in Prodejna.objects.all()}

        top_kategorie = qs.values('kategorie').annotate(
            obrat=Sum(F('pocet_kusu')*F('cena_ks_bez_dph'), default=0),
            polozky=Count('id')
        ).order_by('-obrat')[:15]

        # VÝKUPY - agregace z WEB_VYKUPY podle id_prodejny
        vykupy_qs = WebVykupy.objects.all()
        if sd_parsed:
            vykupy_qs = vykupy_qs.filter(vystaveno__gte=sd_parsed)
        if ed_parsed:
            vykupy_qs = vykupy_qs.filter(vystaveno__lte=ed_parsed)
        
        vykupy_agg = vykupy_qs.values('id_prodejny').annotate(
            vykupy_suma=Sum('cena_ks_bez_dph', default=0),
            vykupy_pocet=Count('id')
        )
        # Převod na dict pro rychlé vyhledávání
        vykupy_map = {v['id_prodejny']: {'suma': v['vykupy_suma'], 'pocet': v['vykupy_pocet']} for v in vykupy_agg}

        def convert(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, dict):
                return {k: convert(v) for k,v in obj.items()}
            if isinstance(obj, list):
                return [convert(v) for v in obj]
            return obj

        # Obohacení prodejen o název a výkupy
        prodejny_list = []
        for p in prodejny_agg:
            p_dict = dict(p)
            id_prod = p_dict.get('id_prodejny')
            # Název z WEB_PRODEJNY
            p_dict['stredisko'] = prodejny_names.get(id_prod, f'ID {id_prod}')
            # Výkupy
            vyk = vykupy_map.get(id_prod, {'suma': 0, 'pocet': 0})
            p_dict['vykupy_suma'] = float(vyk['suma']) if vyk['suma'] else 0
            p_dict['vykupy_pocet'] = vyk['pocet'] or 0
            prodejny_list.append(p_dict)

        return JsonResponse({'success': True, 'breakdown': {'prodejny': convert(prodejny_list), 'top_kategorie': convert(list(top_kategorie))}})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def celkova_channel_items_view(request):
    """
    Vrací položky pro daný kanál:
     - channel='eshop' | 'allegro' | 'servis' | 'prodejna'
     - prodejna může mít parametr stredisko pro zúžení
     - odpověď: seznam položek s 'nazev', 'kod', a 'doklad' nebo 'objednavka' dle kanálu
    """
    try:
        channel = request.GET.get('channel')
        if channel not in {'eshop','allegro','servis','prodejna'}:
            return JsonResponse({'success': False, 'error': 'Neplatný kanál'}, status=400)

        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        period = request.GET.get('period', 'custom')
        selected_month = request.GET.get('selected_month')
        stredisko = request.GET.get('stredisko')
        limit = int(request.GET.get('limit','200'))

        qs = WebProdejeAll.objects.all()

        if period != 'custom' and period != 'monthly_select':
            today = date.today()
            if period == 'daily':
                start_date = today; end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7); end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1); end_date = today
        elif period == 'monthly_select' and selected_month:
            try:
                y,m = selected_month.split('-')
                start_date = date(int(y), int(m), 1)
                end_date = (date(int(y)+1,1,1)-timedelta(days=1)) if int(m)==12 else (date(int(y),int(m)+1,1)-timedelta(days=1))
            except Exception:
                pass

        if start_date:
            try:
                sd = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                qs = qs.filter(typ__gte=sd.strftime('%Y-%m-%d'))
            except Exception:
                pass
        if end_date:
            try:
                ed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                qs = qs.filter(typ__lte=ed.strftime('%Y-%m-%d'))
            except Exception:
                pass

        if channel == 'eshop':
            qs = qs.filter(marketingovy_kanal='e-shop').filter(Q(objednavku_zalozil__isnull=True)|Q(objednavku_zalozil='')).filter(Q(poznamka__isnull=True)|Q(poznamka='')).exclude(dropshipping='Baselinker').exclude(kategorie_1__icontains='!Servis')
            items = list(qs.order_by('-typ').values('objednavka','nazev','kod')[:max(1,min(limit,1000))])
        elif channel == 'allegro':
            qs = qs.filter(dropshipping='Baselinker')
            items = list(qs.order_by('-typ').values('objednavka','nazev','kod')[:max(1,min(limit,1000))])
        elif channel == 'servis':
            qs = qs.filter(objednavku_zalozil__icontains='servis eda', k_servisu='ANO')
            items = list(qs.order_by('-typ').values('objednavka','nazev','kod')[:max(1,min(limit,1000))])
        else:  # prodejna
            qs = qs.exclude(marketingovy_kanal='e-shop').exclude(dropshipping='Baselinker').exclude(
                Q(objednavku_zalozil__icontains='servis eda') & Q(k_servisu='ANO')
            )
            if stredisko:
                qs = qs.filter(stredisko=stredisko)
            items = list(qs.order_by('-typ').values('doklad','nazev','kod')[:max(1,min(limit,1000))])

        return JsonResponse({'success': True, 'items': items, 'count': len(items)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e), 'items': []}, status=500)


# =============================================================================
# E-SHOP - API endpointy pro analýzu e-shop dat z WEB_PRODEJE
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def eshop_data_view(request):
    """
    Hlavní endpoint pro modul 'E-shop' (nově nad WEB_PRODEJE_ALL)
    - E-shop (čistý): sloupec 11 (objednavku_zalozil) je prázdný
    - Allegro: sloupec 19 (dropshipping) = 'Baselinker'
    - Servis: metrika pro obrat bez DPH z celé servisní množiny (pro kontext)
    """

    try:
        # Získání filtrů z GET parametrů
        start_date = request.GET.get('start_date')  # Formát: YYYY-MM-DD
        end_date = request.GET.get('end_date')      # Formát: YYYY-MM-DD
        period = request.GET.get('period', 'custom')  # daily, weekly, monthly, custom
        exclude_allegro = request.GET.get('exclude_allegro', 'false') == 'true'  # Vyloučit ALLEGRO z celkových počtů

        # Základní QuerySet nad WEB_PRODEJE_ALL
        queryset = WebProdejeAll.objects.all()

        # Filtrování podle data
        if period != 'custom':
            # Automatické období
            today = date.today()
            if period == 'daily':
                start_date = today
                end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1)
                end_date = today

        if start_date:
            try:
                start_date_parsed = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                queryset = queryset.filter(typ__gte=start_date_parsed.strftime('%Y-%m-%d'))
            except Exception:
                pass

        if end_date:
            try:
                end_date_parsed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                queryset = queryset.filter(typ__lte=end_date_parsed.strftime('%Y-%m-%d'))
            except Exception:
                pass

        # Podmnožiny: e-shop čistý a allegro
        # Vyloučíme i logistické/pickup položky (nepatří do analytiky): Zásilkovna/Zásielkovňa/Balíkovna/Osobní odběr
        shipping_exclude_q = (
            Q(nazev__icontains='Zásilkovna') |
            Q(nazev__icontains='ZASILKOVNA') |
            Q(nazev__icontains='Zásielkovňa') |
            Q(nazev__icontains='ZASIELKOVNA') |
            Q(nazev__icontains='Balíkovna') |
            Q(nazev__icontains='BALIKOVNA') |
            Q(nazev__icontains='Osobní odběr') |
            Q(nazev__icontains='OSOBNI ODBER') |
            Q(nazev__icontains='Česká pošta') |
            Q(nazev__icontains='Ceska posta') |
            Q(nazev__icontains='Allegro doručení') |
            Q(nazev__icontains='Allegro doruceni')
        )
        eshop_pure_qs = (
            queryset
            .filter(marketingovy_kanal='e-shop')
            .filter(Q(objednavku_zalozil__isnull=True) | Q(objednavku_zalozil=''))  # sloupec 11 prázdný
            .filter(Q(poznamka__isnull=True) | Q(poznamka=''))                      # sloupec 10 prázdný
            .exclude(dropshipping='Baselinker')                                      # vyloučit Allegro
            .exclude(kategorie_1__icontains='!Servis')                               # sloupec 23 nesmí obsahovat !Servis
            .exclude(Q(kategorie__isnull=True) | Q(kategorie='') | Q(kategorie__iexact='Nezařazeno'))  # nevstupuje Nezařazeno (doručení)
            .exclude(shipping_exclude_q)
        )

        allegro_qs = (
            queryset
            .filter(dropshipping='Baselinker')
            .exclude(Q(kategorie__isnull=True) | Q(kategorie='') | Q(kategorie__iexact='Nezařazeno'))  # nevstupuje Nezařazeno (doručení)
            .exclude(shipping_exclude_q)
        )

        # Výhradně dopravné (zobrazení v samostatné dlaždici) – suma bez DPH
        shipping_qs = queryset.filter(shipping_exclude_q)

        # Servisová množina (pro obrat bez DPH celého servisu)
        base_servis_q = (
            Q(objednavku_zalozil__icontains='servis eda') &
            Q(k_servisu='ANO')
        )
        servis_qs = WebProdejeAll.objects.filter(base_servis_q)
        # Aplikace stejných datumových filtrů i na servis
        if start_date:
            try:
                start_date_parsed = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                servis_qs = servis_qs.filter(typ__gte=start_date_parsed.strftime('%Y-%m-%d'))
            except Exception:
                pass
        if end_date:
            try:
                end_date_parsed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                servis_qs = servis_qs.filter(typ__lte=end_date_parsed.strftime('%Y-%m-%d'))
            except Exception:
                pass

        # Agregace
        allegro_aggs = allegro_qs.aggregate(
            obrat_bez_dph=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
            zisk=Sum(F('pocet_kusu') * F('zisk'), default=0),
            polozky=Count('id'),
            objednavky=Count('doklad', distinct=True)
        )

        eshop_aggs = eshop_pure_qs.aggregate(
            obrat_bez_dph=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
            zisk=Sum(F('pocet_kusu') * F('zisk'), default=0),
            polozky=Count('id'),
            objednavky=Count('doklad', distinct=True)
        )

        servis_aggs = servis_qs.aggregate(
            obrat_bez_dph=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0)
        )

        shipping_aggs = shipping_qs.aggregate(
            obrat_bez_dph=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0)
        )

        # Celkové počty (eshop_pure + volitelně allegro)
        overall_pocet_obj = (eshop_aggs.get('objednavky') or 0) + (0 if exclude_allegro else (allegro_aggs.get('objednavky') or 0))
        overall_pocet_pol = (eshop_aggs.get('polozky') or 0) + (0 if exclude_allegro else (allegro_aggs.get('polozky') or 0))

        # Sestavení metrik
        metrics = {
            'servis_obrat_bez_dph': float(servis_aggs.get('obrat_bez_dph') or 0),
            'allegro_obrat_bez_dph': float(allegro_aggs.get('obrat_bez_dph') or 0),
            'allegro_zisk': float(allegro_aggs.get('zisk') or 0),
            'eshop_obrat_bez_dph': float(eshop_aggs.get('obrat_bez_dph') or 0),
            'eshop_zisk': float(eshop_aggs.get('zisk') or 0),
            'pocet_objednavek': int(overall_pocet_obj),
            'pocet_polozek': int(overall_pocet_pol),
        }

        response_data = {
            'success': True,
            'metrics': metrics,
            'channels': {
                'eshop': {
                    'obrat_bez_dph': float(eshop_aggs.get('obrat_bez_dph') or 0),
                    'zisk': float(eshop_aggs.get('zisk') or 0),
                    'polozky': int(eshop_aggs.get('polozky') or 0),
                    'objednavky': int(eshop_aggs.get('objednavky') or 0),
                },
                'allegro': {
                    'obrat_bez_dph': float(allegro_aggs.get('obrat_bez_dph') or 0),
                    'zisk': float(allegro_aggs.get('zisk') or 0),
                    'polozky': int(allegro_aggs.get('polozky') or 0),
                    'objednavky': int(allegro_aggs.get('objednavky') or 0),
                },
                'shipping': {
                    'obrat_bez_dph': float(shipping_aggs.get('obrat_bez_dph') or 0)
                }
            },
            'filters': {
                'start_date': start_date,
                'end_date': end_date,
                'period': period,
                'exclude_allegro': exclude_allegro,
            },
            'meta': {
                'total_records': eshop_pure_qs.count() + (0 if exclude_allegro else allegro_qs.count()),
                'generated_at': datetime.now().isoformat(),
                'data_source': 'WEB_PRODEJE_ALL'
            }
        }

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Chyba při zpracování E-shop dat: {str(e)}',
            'metrics': {}
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def eshop_channel_detail_view(request):
    """
    Detail pro zvolený E‑shop kanál (eshop|allegro) nad WEB_PRODEJE_ALL
    Vrací rozpad podle kategorie, podkategorie 1, podkategorie 2 a top produktů.
    Parametry: channel in {'eshop','allegro'}, period/start_date/end_date
    """
    try:
        channel = request.GET.get('channel', 'eshop')  # eshop | allegro
        if channel not in {'eshop', 'allegro'}:
            return JsonResponse({'success': False, 'error': 'Neplatný kanál'}, status=400)

        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        period = request.GET.get('period', 'custom')

        qs = WebProdejeAll.objects.all()

        # Datumové filtry
        if period != 'custom':
            today = date.today()
            if period == 'daily':
                start_date = today
                end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1)
                end_date = today

        if start_date:
            try:
                sd = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                qs = qs.filter(typ__gte=sd.strftime('%Y-%m-%d'))
            except Exception:
                pass
        if end_date:
            try:
                ed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                qs = qs.filter(typ__lte=ed.strftime('%Y-%m-%d'))
            except Exception:
                pass

        # Filtr kanálu
        if channel == 'allegro':
            qs = qs.filter(dropshipping='Baselinker')
        else:  # eshop (bez Allegra) – striktní definice: mk='e-shop', objednavku_zalozil prázdné, poznamka prázdná, kategorie_1 neobsahuje !Servis
            qs = (
                qs.filter(marketingovy_kanal='e-shop')
                  .filter(Q(objednavku_zalozil__isnull=True) | Q(objednavku_zalozil=''))
                  .filter(Q(poznamka__isnull=True) | Q(poznamka=''))
                  .exclude(dropshipping='Baselinker')
                  .exclude(kategorie_1__icontains='!Servis')
            )

        # Agregace
        def agg(values_field):
            return (
                qs.values(values_field)
                .annotate(
                    obrat_bez_dph=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
                    zisk=Sum(F('pocet_kusu') * F('zisk'), default=0),
                    polozky=Count('id'),
                    doklady=Count('doklad', distinct=True),
                )
                .order_by('-obrat_bez_dph')[:20]
            )

        kategorie = list(agg('kategorie'))
        kategorie_1 = list(agg('kategorie_1'))
        kategorie_2 = list(agg('kategorie_2'))

        top_produkty = list(
            qs.values('kod', 'nazev')
            .annotate(
                celkem_kusu=Sum('pocet_kusu'),
                obrat_bez_dph=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
                zisk=Sum(F('pocet_kusu') * F('zisk'), default=0),
            )
            .order_by('-celkem_kusu')[:30]
        )

        def convert(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert(v) for v in obj]
            return obj

        return JsonResponse({
            'success': True,
            'channel': channel,
            'breakdown': convert({
                'kategorie': kategorie,
                'kategorie_1': kategorie_1,
                'kategorie_2': kategorie_2,
                'top_produkty': top_produkty,
            })
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def eshop_channel_items_view(request):
    """
    Seznam položek pro zvolený E‑shop kanál a segment.
    Parametry: channel in {'eshop','allegro'}
               segment in {'kategorie','kategorie_1','kategorie_2','produkt'}
               value (u produktu může být 'kod' nebo 'nazev')
               limit (default 200)
    """
    try:
        channel = request.GET.get('channel', 'eshop')
        segment = request.GET.get('segment')
        value = request.GET.get('value')
        product_code = request.GET.get('kod')
        limit = int(request.GET.get('limit', '200'))

        if channel not in {'eshop', 'allegro'}:
            return JsonResponse({'success': False, 'error': 'Neplatný kanál'}, status=400)
        if segment not in {'kategorie', 'kategorie_1', 'kategorie_2', 'produkt'}:
            return JsonResponse({'success': False, 'error': 'Neplatný segment'}, status=400)

        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        period = request.GET.get('period', 'custom')

        qs = WebProdejeAll.objects.all()

        # datum
        if period != 'custom':
            today = date.today()
            if period == 'daily':
                start_date = today
                end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1)
                end_date = today

        if start_date:
            try:
                sd = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                qs = qs.filter(typ__gte=sd.strftime('%Y-%m-%d'))
            except Exception:
                pass
        if end_date:
            try:
                ed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                qs = qs.filter(typ__lte=ed.strftime('%Y-%m-%d'))
            except Exception:
                pass

        if channel == 'allegro':
            qs = qs.filter(dropshipping='Baselinker').exclude(
                Q(nazev__icontains='Zásilkovna') |
                Q(nazev__icontains='ZASILKOVNA') |
                Q(nazev__icontains='Zásielkovňa') |
                Q(nazev__icontains='ZASIELKOVNA') |
                Q(nazev__icontains='Balíkovna') |
                Q(nazev__icontains='BALIKOVNA') |
                Q(nazev__icontains='Osobní odběr') |
                Q(nazev__icontains='OSOBNI ODBER')
            )
        else:
            qs = (
                qs.filter(marketingovy_kanal='e-shop')
                  .filter(Q(objednavku_zalozil__isnull=True) | Q(objednavku_zalozil=''))
                  .filter(Q(poznamka__isnull=True) | Q(poznamka=''))
                  .exclude(dropshipping='Baselinker')
                  .exclude(kategorie_1__icontains='!Servis')
                  .exclude(
                      Q(nazev__icontains='Zásilkovna') |
                      Q(nazev__icontains='ZASILKOVNA') |
                      Q(nazev__icontains='Zásielkovňa') |
                      Q(nazev__icontains='ZASIELKOVNA') |
                      Q(nazev__icontains='Balíkovna') |
                      Q(nazev__icontains='BALIKOVNA') |
                      Q(nazev__icontains='Osobní odběr') |
                      Q(nazev__icontains='OSOBNI ODBER')
                  )
            )

        # segment
        if segment == 'produkt':
            if product_code:
                qs = qs.filter(kod=product_code)
            elif value:
                qs = qs.filter(nazev=value)
        else:
            # mapování: pokud je hodnota prázdná, vezmeme "Nezařazeno" = NULL/''
            if segment == 'kategorie':
                if value is None or value == '':
                    qs = qs.filter(Q(kategorie__isnull=True) | Q(kategorie=''))
                else:
                    qs = qs.filter(kategorie=value)
            elif segment == 'kategorie_1':
                if value is None or value == '':
                    qs = qs.filter(Q(kategorie_1__isnull=True) | Q(kategorie_1=''))
                else:
                    qs = qs.filter(kategorie_1=value)
            elif segment == 'kategorie_2':
                if value is None or value == '':
                    qs = qs.filter(Q(kategorie_2__isnull=True) | Q(kategorie_2=''))
                else:
                    qs = qs.filter(kategorie_2=value)

        items = list(
            qs.order_by('-typ')
              .values('objednavka', 'nazev', 'kod')[:max(1, min(limit, 1000))]
        )

        return JsonResponse({'success': True, 'items': items, 'count': qs.count()})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e), 'items': []}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def eshop_categories_analytics_view(request):
    """
    Kategorie/podkategorie analytika pro E‑shop (WEB_PRODEJE_ALL) včetně vratek (negativní cena s DPH)
    - Vrací top kategorie, podkategorie 1 a podkategorie 2 podle obratu bez DPH
    - Součástí jsou metriky vratek: vraceno_polozek, vraceno_objednavek, vraceno_hodnota
    """
    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        period = request.GET.get('period', 'custom')

        qs = WebProdejeAll.objects.all()

        # Datumové filtry
        if period != 'custom':
            today = date.today()
            if period == 'daily':
                start_date = today
                end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1)
                end_date = today

        if start_date:
            try:
                sd = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                qs = qs.filter(typ__gte=sd.strftime('%Y-%m-%d'))
            except Exception:
                pass
        if end_date:
            try:
                ed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                qs = qs.filter(typ__lte=ed.strftime('%Y-%m-%d'))
            except Exception:
                pass

        # E‑shop filtr (přesná definice) + vyloučení logistiky a servisu
        qs = (
            qs.filter(marketingovy_kanal='e-shop')
              .filter(Q(objednavku_zalozil__isnull=True) | Q(objednavku_zalozil=''))
              .filter(Q(poznamka__isnull=True) | Q(poznamka=''))
              .exclude(dropshipping='Baselinker')
              .exclude(kategorie_1__icontains='!Servis')
              .exclude(
                  Q(nazev__icontains='Zásilkovna') | Q(nazev__icontains='ZASILKOVNA') |
                  Q(nazev__icontains='Zásielkovňa') | Q(nazev__icontains='ZASIELKOVNA') |
                  Q(nazev__icontains='Balíkovna') | Q(nazev__icontains='BALIKOVNA') |
                  Q(nazev__icontains='Osobní odběr') | Q(nazev__icontains='OSOBNI ODBER')
              )
        )

        # Pomocné výrazy pro vratky
        vratka_filter = Q(cena_ks_vcl_dph__lt=0)
        vratka_hodnota_expr = Sum(
            Case(
                When(vratka_filter, then=F('pocet_kusu') * F('cena_ks_bez_dph')),
                default=0,
                output_field=DecimalField(max_digits=16, decimal_places=2)
            )
        )

        def build(values_field):
            return (
                qs.values(values_field)
                .annotate(
                    obrat_bez_dph=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
                    zisk=Sum(F('pocet_kusu') * F('zisk'), default=0),
                    polozky=Count('id'),
                    objednavky=Count('doklad', distinct=True),
                    vraceno_hodnota=vratka_hodnota_expr,
                    vraceno_polozek=Count('id', filter=vratka_filter),
                    vraceno_objednavek=Count('doklad', filter=vratka_filter, distinct=True),
                )
                .order_by('-obrat_bez_dph')[:20]
            )

        kategorie = list(build('kategorie'))
        kategorie_1 = list(build('kategorie_1'))
        kategorie_2 = list(build('kategorie_2'))

        # Souhrn vratek + celkové počty napříč E‑shopem
        base_totals = qs.aggregate(
            total_polozek=Count('id'),
            total_objednavek=Count('doklad', distinct=True),
            total_kusu=Sum('pocet_kusu')
        )
        returns_total = qs.aggregate(
            vraceno_hodnota=vratka_hodnota_expr,
            vraceno_polozek=Count('id', filter=vratka_filter),
            vraceno_objednavek=Count('doklad', filter=vratka_filter, distinct=True),
            vraceno_kusu=Sum('pocet_kusu', filter=vratka_filter)
        )
        # Procenta vratkovosti (objednávky/položky)
        total_orders = base_totals.get('total_objednavek') or 0
        total_items = base_totals.get('total_polozek') or 0
        returns_total['return_rate_orders'] = round(((returns_total.get('vraceno_objednavek') or 0) / total_orders) * 100, 2) if total_orders else 0
        returns_total['return_rate_items'] = round(((returns_total.get('vraceno_polozek') or 0) / total_items) * 100, 2) if total_items else 0
        returns_total.update(base_totals)

        def convert(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert(v) for v in obj]
            return obj

        return JsonResponse({
            'success': True,
            'data': convert({
                'kategorie': kategorie,
                'kategorie_1': kategorie_1,
                'kategorie_2': kategorie_2,
            }),
            'returns': convert(returns_total),
            'meta': {
                'total_records': qs.count(),
                'generated_at': datetime.now().isoformat(),
                'data_source': 'WEB_PRODEJE_ALL'
            }
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def eshop_categories_timeseries_view(request):
    """
    Časové řady pro E‑shop podle zvolené dimenze (kategorie/kategorie_1/kategorie_2)
    Parametry:
      - dimension: 'kategorie' | 'kategorie_1' | 'kategorie_2'
      - selected[]: opakované parametry s hodnotami dimenze (pokud chybí, vyberou se TOP podle obratu)
      - group_by: 'daily' | 'weekly' | 'monthly' (default 'monthly')
      - start_date, end_date, period (stejně jako jinde)
    """
    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        period = request.GET.get('period', 'custom')
        group_by = request.GET.get('group_by', 'monthly')
        dimension = request.GET.get('dimension', 'kategorie')
        selected = request.GET.getlist('selected[]') or request.GET.getlist('selected')

        if dimension not in {'kategorie', 'kategorie_1', 'kategorie_2'}:
            return JsonResponse({'success': False, 'error': 'Neplatná dimenze'}, status=400)

        qs = WebProdejeAll.objects.all()

        # Datumové filtry
        if period != 'custom':
            today = date.today()
            if period == 'daily':
                start_date = today
                end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1)
                end_date = today

        if start_date:
            try:
                sd = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                qs = qs.filter(typ__gte=sd.strftime('%Y-%m-%d'))
            except Exception:
                pass
        if end_date:
            try:
                ed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                qs = qs.filter(typ__lte=ed.strftime('%Y-%m-%d'))
            except Exception:
                pass

        # E‑shop filtr + vyloučení logistiky a servisu
        qs = (
            qs.filter(marketingovy_kanal='e-shop')
              .filter(Q(objednavku_zalozil__isnull=True) | Q(objednavku_zalozil=''))
              .filter(Q(poznamka__isnull=True) | Q(poznamka=''))
              .exclude(dropshipping='Baselinker')
              .exclude(kategorie_1__icontains='!Servis')
              .exclude(
                  Q(nazev__icontains='Zásilkovna') | Q(nazev__icontains='ZASILKOVNA') |
                  Q(nazev__icontains='Zásielkovňa') | Q(nazev__icontains='ZASIELKOVNA') |
                  Q(nazev__icontains='Balíkovna') | Q(nazev__icontains='BALIKOVNA') |
                  Q(nazev__icontains='Osobní odběr') | Q(nazev__icontains='OSOBNI ODBER')
              )
        )

        # Předvýběr TOP hodnot dimenze (pokud selected chybí)
        top_values = list(
            qs.values(dimension)
              .annotate(obrat=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0))
              .order_by('-obrat')
              .values_list(dimension, flat=True)[:10]
        )
        if not selected:
            selected = [v for v in top_values if v]
            selected = selected[:4]  # defaultně 4 křivky

        # Agregace časové řady
        date_cast = Cast('typ', DateField())
        if group_by == 'daily':
            period_expr = TruncDate(date_cast)
        elif group_by == 'weekly':
            period_expr = TruncWeek(date_cast)
        else:
            period_expr = TruncMonth(date_cast)

        base = qs
        if selected:
            base = base.filter(**{f"{dimension}__in": selected})

        time_rows = (
            base.annotate(period=period_expr)
                .values('period', dimension)
                .annotate(
                    obrat=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
                    zisk=Sum(F('pocet_kusu') * F('zisk'), default=0),
                    kusy=Sum('pocet_kusu'),
                    polozky=Count('id'),
                    objednavky=Count('doklad', distinct=True),
                )
                .order_by('period')
        )

        # Transformace na strukturu pro grafy
        series_map = {name: [] for name in selected}
        for row in time_rows:
            key = row.get(dimension) or 'Nezařazeno'
            if key not in series_map:
                series_map[key] = []
            series_map[key].append({
                'date': row['period'],
                'obrat': float(row['obrat'] or 0),
                'zisk': float(row['zisk'] or 0),
                'kusy': row['kusy'] or 0,
                'polozky': row['polozky'] or 0,
                'objednavky': row['objednavky'] or 0,
            })

        data = [
            {
                'key': key,
                'points': points
            } for key, points in series_map.items()
        ]

        return JsonResponse({
            'success': True,
            'dimension': dimension,
            'available': top_values,
            'selected': selected,
            'group_by': group_by,
            'data': data,
            'meta': {
                'total_records': qs.count(),
                'generated_at': datetime.now().isoformat(),
                'data_source': 'WEB_PRODEJE_ALL'
            }
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# =============================================================================
# SERVIS - API endpointy pro analýzu servisních dat z WEB_PRODEJE_ALL
# =============================================================================

SERVIS_ODMENA_RATE = Decimal('0.10')
SERVIS_ODMENA_SAZBA = 10


def _base_servis_q():
    return Q(objednavku_zalozil__icontains='servis eda') & Q(k_servisu='ANO')


def _servisni_prace_segment_q():
    return Q(kategorie__icontains='!Servis') & ~Q(kategorie_1__icontains='Služby')


def aggregate_servisni_prace(queryset):
    """Agregace segmentu Servisní práce + odměna 10 % z marže."""
    prace_qs = queryset.filter(_servisni_prace_segment_q())
    result = prace_qs.aggregate(
        obrat_bez_dph=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
        marze=Sum(F('pocet_kusu') * F('zisk'), default=0),
        polozky=Count('id'),
        doklady=Count('doklad', distinct=True),
    )
    marze = Decimal(str(result['marze'] or 0))
    odmena = round(marze * SERVIS_ODMENA_RATE, 2)
    return {
        'obrat_bez_dph': float(result['obrat_bez_dph'] or 0),
        'marze': float(marze),
        'polozky': result['polozky'] or 0,
        'doklady': result['doklady'] or 0,
        'odmena': float(odmena),
        'odmena_sazba': SERVIS_ODMENA_SAZBA,
    }


def _technik_display_name_for_user(user):
    return f'{user.jmeno} {user.prijmeni}'.strip()


def _apply_servis_date_filters(queryset, start_date=None, end_date=None, period='custom'):
    """Aplikuje period/start_date/end_date na queryset (typ jako YYYY-MM-DD string)."""
    if period != 'custom':
        today = date.today()
        if period == 'daily':
            start_date = today
            end_date = today
        elif period == 'weekly':
            start_date = today - timedelta(days=7)
            end_date = today
        elif period == 'monthly':
            start_date = today.replace(day=1)
            end_date = today

    if start_date:
        try:
            sd = parse_date(start_date).date() if isinstance(start_date, str) else start_date
            queryset = queryset.filter(typ__gte=sd.strftime('%Y-%m-%d'))
        except Exception:
            pass
    if end_date:
        try:
            ed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
            end_upper = (ed + timedelta(days=1)).strftime('%Y-%m-%d')
            queryset = queryset.filter(typ__lt=end_upper)
        except Exception:
            pass
    return queryset


def servisni_prace_for_user(user, typ_exact=None, typ_month_prefix=None, start_date=None, end_date=None, period='custom', prodejna_id=None):
    """
    Servisní práce + odměna pro uživatele mapovaného přes technik_id.
    Vrací (data_dict, reason) – reason je None při úspěchu, jinak kód pro frontend.
    """
    if not user or not getattr(user, 'technik_id', None):
        return None, 'no_technik_id'

    display_name = _technik_display_name_for_user(user)
    if not display_name:
        return None, 'no_technik_name'

    qs = WebProdejeAll.objects.filter(_base_servis_q()).filter(technik_filter_q(display_name))

    if typ_exact:
        qs = qs.filter(typ=typ_exact)
    elif typ_month_prefix:
        qs = qs.filter(typ__startswith=typ_month_prefix)
    else:
        qs = _apply_servis_date_filters(qs, start_date, end_date, period)

    if prodejna_id:
        qs = qs.filter(id_prodejny=prodejna_id)

    return aggregate_servisni_prace(qs), None


def _attach_servisni_prace(result, user_id, typ_exact=None, typ_month_prefix=None):
    try:
        user = WebUser.objects.get(id=user_id)
    except WebUser.DoesNotExist:
        result['servisni_prace'] = None
        result['servisni_prace_reason'] = 'user_not_found'
        return result

    data, reason = servisni_prace_for_user(user, typ_exact=typ_exact, typ_month_prefix=typ_month_prefix)
    result['servisni_prace'] = data
    if reason:
        result['servisni_prace_reason'] = reason
    return result


def _servis_points_for_user_id(user_id, typ_exact=None, typ_month_prefix=None):
    """Vrátí (body z 10 % marže servisních prací, servisni_prace dict nebo None)."""
    try:
        user = WebUser.objects.get(id=user_id)
    except WebUser.DoesNotExist:
        return 0, None

    data, _reason = servisni_prace_for_user(user, typ_exact=typ_exact, typ_month_prefix=typ_month_prefix)
    if not data:
        return 0, None

    points = int(round(data.get('odmena') or 0))
    return points, data


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def servis_data_view(request):
    """
    Hlavní endpoint pro modul 'Servis' (pouze WEB_PRODEJE_ALL)
    - Celková čísla: záznamy kde `objednavku_zalozil` obsahuje "servis eda" A `k_servisu` == "ANO"
    - Rozklad prodejen: podle `id_prodejny`/`stredisko` (sloupec 8)
    - Servisní položky: pouze ty s k_servisu='ANO'
    - Čistě služby: `kategorie_1` == "Služby" s k_servisu='ANO'
    """

    try:
        # Získání filtrů z GET parametrů
        start_date = request.GET.get('start_date')  # Formát: YYYY-MM-DD
        end_date = request.GET.get('end_date')      # Formát: YYYY-MM-DD
        period = request.GET.get('period', 'custom')  # daily, weekly, monthly, custom
        prodejna_id = request.GET.get('prodejna_id')  # ID konkrétní prodejny

        # Základní QuerySet pro CELKOVÁ ČÍSLA a ROZKLAD PRODEJEN
        # Servisní položky: MUSÍ mít k_servisu='ANO' A obsahovat "servis eda"
        base_servis_q = (
            Q(objednavku_zalozil__icontains='servis eda') &
            Q(k_servisu='ANO')
        )
        queryset = WebProdejeAll.objects.filter(base_servis_q)

        # Filtrování podle data
        if period != 'custom':
            today = date.today()
            if period == 'daily':
                start_date = today
                end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1)
                end_date = today

        if start_date:
            try:
                start_date_parsed = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                queryset = queryset.filter(typ__gte=start_date_parsed.strftime('%Y-%m-%d'))
            except:
                pass

        if end_date:
            try:
                end_date_parsed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                queryset = queryset.filter(typ__lte=end_date_parsed.strftime('%Y-%m-%d'))
            except:
                pass

        # Filtrování podle prodejny
        if prodejna_id:
            queryset = queryset.filter(id_prodejny=prodejna_id)

        # Základní agregace pro CELKOVÁ ČÍSLA SERVISU (servis eda)
        aggregations = queryset.aggregate(
            celkem_polozek=Count('id'),
            celkem_kusu=Sum('pocet_kusu'),
            celkovy_obrat_bez_dph=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
            celkovy_obrat_s_dph=Sum(F('pocet_kusu') * F('cena_ks_vcl_dph'), default=0),
            celkovy_zisk=Sum(F('pocet_kusu') * F('zisk'), default=0),
            prumerna_cena_s_dph=Avg('cena_ks_vcl_dph'),
            prumerna_cena_bez_dph=Avg('cena_ks_bez_dph'),
            pocet_dokladu=Count('doklad', distinct=True),
        )

        # Výpočet marže a AOV
        if aggregations['celkovy_obrat_bez_dph'] and aggregations['celkovy_obrat_bez_dph'] > 0:
            aggregations['marze_procenta'] = round(
                (aggregations['celkovy_zisk'] / aggregations['celkovy_obrat_bez_dph']) * 100, 2
            )
        else:
            aggregations['marze_procenta'] = 0

        # Marže v korunách (alias)
        aggregations['marze_korun'] = aggregations['celkovy_zisk'] or 0

        if aggregations['pocet_dokladu'] and aggregations['pocet_dokladu'] > 0:
            aggregations['prumerna_objednavka_bez_dph'] = round(
                (aggregations['celkovy_obrat_bez_dph'] or 0) / aggregations['pocet_dokladu'], 2
            )
        else:
            aggregations['prumerna_objednavka_bez_dph'] = 0

        # Rozklad podle prodejen v rámci servisu (viz base_servis_q)
        prodejny_breakdown = queryset.values('stredisko', 'id_prodejny').annotate(
            obrat_bez_dph=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
            marze=Sum(F('pocet_kusu') * F('zisk'), default=0),
            polozky=Count('id'),
            doklady=Count('doklad', distinct=True)
        ).order_by('-obrat_bez_dph')

        # Přidání metrik čistě služeb k jednotlivým prodejnám
        for prodejna in prodejny_breakdown:
            sluzby_queryset = WebProdejeAll.objects.filter(
                stredisko=prodejna['stredisko'],
                id_prodejny=prodejna['id_prodejny']
            ).filter(
                Q(kategorie_1__istartswith='Služby') | Q(kategorie__icontains='!Servis')
            ).filter(k_servisu='ANO')
            if start_date:
                try:
                    start_date_parsed = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                    sluzby_queryset = sluzby_queryset.filter(typ__gte=start_date_parsed.strftime('%Y-%m-%d'))
                except:
                    pass
            if end_date:
                try:
                    end_date_parsed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                    end_upper = (end_date_parsed + timedelta(days=1)).strftime('%Y-%m-%d')
                    sluzby_queryset = sluzby_queryset.filter(typ__lt=end_upper)
                except:
                    pass

            sluzby_aggregations = sluzby_queryset.aggregate(
                sluzby_obrat=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
                sluzby_zisk=Sum(F('pocet_kusu') * F('zisk'), default=0),
                sluzby_polozky=Count('id'),
                sluzby_doklady=Count('doklad', distinct=True)
            )

            prodejna['sluzby_obrat'] = sluzby_aggregations['sluzby_obrat']
            prodejna['sluzby_zisk'] = sluzby_aggregations['sluzby_zisk']
            prodejna['sluzby_polozky'] = sluzby_aggregations['sluzby_polozky']
            prodejna['sluzby_doklady'] = sluzby_aggregations['sluzby_doklady']

            # Průměrná cena na doklad (bez DPH) v rámci rozkladu
            if prodejna['doklady'] and prodejna['doklady'] > 0:
                prodejna['prumerna_cena_na_doklad'] = round((prodejna['obrat_bez_dph'] or 0) / prodejna['doklady'], 2)
            else:
                prodejna['prumerna_cena_na_doklad'] = 0

        # Dataset pro servisní položky: základní servisní filtr + kategorie musí obsahovat "!Servis"
        servis_items_queryset = WebProdejeAll.objects.filter(base_servis_q).filter(kategorie__icontains='!Servis')
        if start_date:
            try:
                start_date_parsed = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                servis_items_queryset = servis_items_queryset.filter(typ__gte=start_date_parsed.strftime('%Y-%m-%d'))
            except:
                pass
        if end_date:
            try:
                end_date_parsed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                end_upper = (end_date_parsed + timedelta(days=1)).strftime('%Y-%m-%d')
                servis_items_queryset = servis_items_queryset.filter(typ__lt=end_upper)
            except:
                pass
        if prodejna_id:
            servis_items_queryset = servis_items_queryset.filter(id_prodejny=prodejna_id)

        # Rozklad podle typů servisu (kategorie_1) - pouze položky s kategorie obsahuje "!Servis"
        typy_servisu = servis_items_queryset.values('kategorie_1').annotate(
            obrat=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
            zisk=Sum(F('pocet_kusu') * F('zisk'), default=0),
            polozky=Count('id'),
            kusy=Sum('pocet_kusu')
        ).order_by('-obrat')[:15]

        podkategorie = servis_items_queryset.values('kategorie_2').annotate(
            obrat=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
            zisk=Sum(F('pocet_kusu') * F('zisk'), default=0),
            polozky=Count('id'),
            kusy=Sum('pocet_kusu')
        ).order_by('-obrat')[:15]

        top_servisni_sluzby = servis_items_queryset.values('kod', 'nazev').annotate(
            celkem_kusu=Sum('pocet_kusu'),
            obrat=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
            zisk=Sum(F('pocet_kusu') * F('zisk'), default=0)
        ).order_by('-celkem_kusu')[:20]

        # Analýza podle značek telefonů z "!Servis"
        znacky_telefonu = servis_items_queryset.values('kategorie_2').annotate(
            obrat=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
            polozky=Count('id'),
            kusy=Sum('pocet_kusu')
        ).filter(kategorie_2__isnull=False).exclude(kategorie_2='').order_by('-obrat')[:10]

        # ČISTĚ SLUŽBY - pouze `kategorie_1 = 'Služby'` s k_servisu='ANO'
        ciste_sluzby_queryset = WebProdejeAll.objects.filter(kategorie_1='Služby', k_servisu='ANO')
        if start_date:
            try:
                start_date_parsed = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                ciste_sluzby_queryset = ciste_sluzby_queryset.filter(typ__gte=start_date_parsed.strftime('%Y-%m-%d'))
            except:
                pass
        if end_date:
            try:
                end_date_parsed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                end_upper = (end_date_parsed + timedelta(days=1)).strftime('%Y-%m-%d')
                ciste_sluzby_queryset = ciste_sluzby_queryset.filter(typ__lt=end_upper)
            except:
                pass
        if prodejna_id:
            ciste_sluzby_queryset = ciste_sluzby_queryset.filter(id_prodejny=prodejna_id)

        ciste_sluzby_aggregations = ciste_sluzby_queryset.aggregate(
            celkem_polozek=Count('id'),
            celkem_kusu=Sum('pocet_kusu'),
            celkovy_obrat_bez_dph=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
            celkovy_obrat_s_dph=Sum(F('pocet_kusu') * F('cena_ks_vcl_dph'), default=0),
            celkovy_zisk=Sum(F('pocet_kusu') * F('zisk'), default=0),
            prumerna_cena_bez_dph=Avg('cena_ks_bez_dph'),
            prumerna_cena_s_dph=Avg('cena_ks_vcl_dph'),
            pocet_dokladu=Count('doklad', distinct=True),
        )

        if ciste_sluzby_aggregations['celkovy_obrat_bez_dph'] and ciste_sluzby_aggregations['celkovy_obrat_bez_dph'] > 0:
            ciste_sluzby_aggregations['marze_procenta'] = round(
                (ciste_sluzby_aggregations['celkovy_zisk'] / ciste_sluzby_aggregations['celkovy_obrat_bez_dph']) * 100, 2
            )
        else:
            ciste_sluzby_aggregations['marze_procenta'] = 0

        if ciste_sluzby_aggregations['pocet_dokladu'] and ciste_sluzby_aggregations['pocet_dokladu'] > 0:
            ciste_sluzby_aggregations['prumerna_objednavka_bez_dph'] = round(
                ciste_sluzby_aggregations['celkovy_obrat_bez_dph'] / ciste_sluzby_aggregations['pocet_dokladu'], 2
            )
        else:
            ciste_sluzby_aggregations['prumerna_objednavka_bez_dph'] = 0

        # Rozklad podle techniků (sloupec "Technik") – použijeme STEJNÉ FILTRY (datum + prodejna)
        technici_qs = queryset.filter(technik__isnull=False).exclude(technik='')
        technici_breakdown_queryset = (
            technici_qs
            .values('technik')
            .annotate(
                obrat_bez_dph=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
                marze=Sum(F('pocet_kusu') * F('zisk'), default=0),
                polozky=Count('id'),
                doklady=Count('doklad', distinct=True)
            )
            .order_by('-obrat_bez_dph')
        )

        technici_breakdown = []
        for t in technici_breakdown_queryset:
            prumer_na_doklad = 0
            if t['doklady']:
                prumer_na_doklad = round((t['obrat_bez_dph'] or 0) / t['doklady'], 2)

            # přidáme i čistě služby pro technika (robustně detekujeme služby)
            t_sluzby_qs = WebProdejeAll.objects.filter(
                technik=t['technik']
            ).filter(
                Q(kategorie_1__istartswith='Služby') | Q(kategorie__icontains='!Servis')
            ).filter(k_servisu='ANO')
            if start_date:
                try:
                    start_date_parsed = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                    t_sluzby_qs = t_sluzby_qs.filter(typ__gte=start_date_parsed.strftime('%Y-%m-%d'))
                except:
                    pass
            if end_date:
                try:
                    end_date_parsed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                    end_upper = (end_date_parsed + timedelta(days=1)).strftime('%Y-%m-%d')
                    t_sluzby_qs = t_sluzby_qs.filter(typ__lt=end_upper)
                except:
                    pass
            if prodejna_id:
                t_sluzby_qs = t_sluzby_qs.filter(id_prodejny=prodejna_id)
            t_sluzby_aggs = t_sluzby_qs.aggregate(
                sluzby_obrat=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
                sluzby_zisk=Sum(F('pocet_kusu') * F('zisk'), default=0),
                sluzby_polozky=Count('id'),
                sluzby_doklady=Count('doklad', distinct=True)
            )
            t.update({
                'prumerna_cena_na_doklad': prumer_na_doklad,
                **t_sluzby_aggs
            })
            # Přidáme technika do výsledného seznamu
            technici_breakdown.append(t)

        technici_breakdown = merge_technici_rows(technici_breakdown)

        # VÝBĚR VÍTĚZŮ (medaile)
        top_all = None  # nejlepší prodejco/technik podle celkového obratu bez DPH
        top_service = None  # nejlepší servisní technik (služby + servisní práce)
        top_seller_only = None  # nejlepší prodavač mimo servis (prodejna/e-shop/allegro)

        if technici_breakdown:
            # Nejlepší celkově – podle obrat_bez_dph
            top_all = max(technici_breakdown, key=lambda x: (x.get('obrat_bez_dph') or 0))

            # Nejlepší servisní technik: součet čistě služeb a servisních prací
            # sluzby_obrat už máme. Přičteme odhad "servisní práce" = (servis celkem - služby), kde servis celkem bereme jako obrat z base_servis_q
            # Použijeme stejné již filtrované QS (datum, prodejna) jako pro rozpad techniků,
            # aby se karta nelišila od seznamu techniků
            servis_by_technik = list(
                technici_qs
                .values('technik')
                .annotate(obrat_bez_dph=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0))
            )
            obrat_servis_map = aggregate_by_canonical_technik(servis_by_technik)
            best_service_score = -1
            top_service = None
            for t in technici_breakdown:
                sluzby_obrat = float(t.get('sluzby_obrat') or 0)
                servis_total = obrat_servis_map.get(t['technik'], 0.0)
                prace_obrat = max(servis_total - sluzby_obrat, 0.0)
                score = sluzby_obrat + prace_obrat
                if score > best_service_score:
                    best_service_score = score
                    top_service = {**t, 'service_score': score}

            # Nejlepší prodavač: obrat PŘÍSLUŠENSTVÍ k servisní objednávce
            prislusenstvi_by_technik = list(
                technici_qs
                .filter(
                    Q(objednavku_zalozil__icontains='servis eda') &
                    Q(kategorie__iexact='PŘÍSLUŠENSTVÍ') &
                    Q(k_servisu='ANO')
                )
                .values('technik')
                .annotate(obrat_bez_dph=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0))
            )
            prislusenstvi_obrat_map = aggregate_by_canonical_technik(prislusenstvi_by_technik)

            best_seller_score = -1
            top_seller_only = None
            for t in technici_breakdown:
                accessories = prislusenstvi_obrat_map.get(t['technik'], 0.0)
                if accessories > best_seller_score:
                    best_seller_score = accessories
                    top_seller_only = {**t, 'seller_score': accessories}

        # Konverze Decimal -> float
        def convert_decimals(obj):
            if isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(item) for item in obj]
            elif isinstance(obj, Decimal):
                return float(obj)
            return obj

        response_data = {
            'success': True,
            'aggregations': convert_decimals(aggregations),
            'ciste_sluzby': convert_decimals(ciste_sluzby_aggregations),
            'breakdown': {
                'prodejny': convert_decimals(list(prodejny_breakdown)),
                'technici': convert_decimals(list(technici_breakdown)),
                'typy_servisu': convert_decimals(list(typy_servisu)),
                'podkategorie': convert_decimals(list(podkategorie)),
                'top_servisni_sluzby': convert_decimals(list(top_servisni_sluzby)),
                'znacky_telefonu': convert_decimals(list(znacky_telefonu))
            },
            'awards': convert_decimals({
                'top_all': top_all,
                'top_service': top_service,
                'top_seller': top_seller_only,
            }),
            'filters': {
                'start_date': start_date,
                'end_date': end_date,
                'period': period,
                'prodejna_id': prodejna_id
            },
            'meta': {
                'total_records': queryset.count(),
                'generated_at': datetime.now().isoformat()
            }
        }

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Chyba při zpracování servisních dat: {str(e)}',
            'aggregations': {},
            'breakdown': {}
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def servis_trendy_view(request):
    """
    Trendová data servisu pouze z WEB_PRODEJE_ALL
    Základ: objednavku_zalozil obsahuje "servis eda".
    """

    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        group_by = request.GET.get('group_by', 'daily')  # daily, weekly, monthly

        queryset = WebProdejeAll.objects.filter(
            objednavku_zalozil__icontains='servis eda', k_servisu='ANO'
        )

        if start_date:
            try:
                start_date_parsed = parse_date(start_date).date()
                queryset = queryset.filter(typ__gte=start_date_parsed.strftime('%Y-%m-%d'))
            except:
                pass

        if end_date:
            try:
                end_date_parsed = parse_date(end_date).date()
                queryset = queryset.filter(typ__lte=end_date_parsed.strftime('%Y-%m-%d'))
            except:
                pass

        trendy = queryset.values('typ').annotate(
            obrat=Sum(F('pocet_kusu') * F('cena_ks_vcl_dph'), default=0),
            zisk=Sum(F('pocet_kusu') * F('zisk'), default=0),
            polozky=Count('id'),
            kusy=Sum('pocet_kusu')
        ).order_by('typ')[:50]

        return JsonResponse({
            'success': True,
            'trendy': [
                {
                    'datum': item['typ'],
                    'obrat': float(item['obrat'] or 0),
                    'zisk': float(item['zisk'] or 0),
                    'polozky': item['polozky'],
                    'kusy': item['kusy'] or 0
                }
                for item in trendy
            ]
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'trendy': []
        }, status=500)


# =============================================================================
# SERVIS - DETAIL PRODEJNY (rozpad Služby / Příslušenství k servisu / Servisní práce)
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def servis_prodejna_detail_view(request):
    """
    Vrátí rozpad pro konkrétní prodejnu dle pravidel (pouze servisní položky s k_servisu='ANO'):
    - Služby: KATEGORIE obsahuje "!Servis" a KATEGORIE_1 začíná na "Služby"
    - Příslušenství k servisu: Objednavku_zalozil obsahuje "servis eda" a KATEGORIE == "PŘÍSLUŠENSTVÍ" a k_servisu == "ANO"
    - Servisní práce: KATEGORIE obsahuje "!Servis" a KATEGORIE_1 neobsahuje "Služby"
    Všechny kategorie musí mít k_servisu='ANO' a objednavku_zalozil obsahuje 'servis eda'.
    """

    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        period = request.GET.get('period', 'custom')
        prodejna_id = request.GET.get('prodejna_id')
        stredisko = request.GET.get('stredisko')

        # Základní servisní filtr - stejný jako v hlavní funkci
        base_servis_q = (
            Q(objednavku_zalozil__icontains='servis eda') &
            Q(k_servisu='ANO')
        )
        
        # základní queryset pro danou prodejnu - pouze servisní položky
        queryset = WebProdejeAll.objects.filter(base_servis_q)
        if prodejna_id:
            queryset = queryset.filter(id_prodejny=prodejna_id)
        if stredisko:
            queryset = queryset.filter(stredisko=stredisko)

        if period != 'custom':
            today = date.today()
            if period == 'daily':
                start_date = today
                end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1)
                end_date = today

        if start_date:
            try:
                sd = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                queryset = queryset.filter(typ__gte=sd.strftime('%Y-%m-%d'))
            except:
                pass
        if end_date:
            try:
                ed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                end_upper = (ed + timedelta(days=1)).strftime('%Y-%m-%d')
                queryset = queryset.filter(typ__lt=end_upper)
            except:
                pass

        def agg(qs):
            return qs.aggregate(
                obrat_bez_dph=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
                marze=Sum(F('pocet_kusu') * F('zisk'), default=0),
                polozky=Count('id'),
                doklady=Count('doklad', distinct=True),
            )

        # Služby
        sluzby_qs = queryset.filter(
            Q(kategorie__icontains='!Servis') & Q(kategorie_1__istartswith='Služby')
        )
        sluzby = agg(sluzby_qs)

        # Příslušenství k servisu
        prisl_qs = queryset.filter(
            Q(objednavku_zalozil__icontains='servis eda') & Q(kategorie__iexact='PŘÍSLUŠENSTVÍ') & Q(k_servisu='ANO')
        )
        prislusenstvi = agg(prisl_qs)

        # Servisní práce
        prace_qs = queryset.filter(
            Q(kategorie__icontains='!Servis') & ~Q(kategorie_1__icontains='Služby')
        )
        servisni_prace = agg(prace_qs)

        def convert(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            return obj

        return JsonResponse({
            'success': True,
            'detail': {
                'stredisko': stredisko,
                'prodejna_id': prodejna_id,
                'breakdown': {
                    'sluzby': convert(sluzby),
                    'prislusenstvi_k_servisu': convert(prislusenstvi),
                    'servisni_prace': convert(servisni_prace),
                }
            },
            'filters': {
                'start_date': start_date,
                'end_date': end_date,
                'period': period,
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'detail': {}
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def servis_prodejna_items_view(request):
    """
    Vrátí seznam položek (nazev, objednavka) pro konkrétní prodejnu a vybraný segment:
    segment in { 'sluzby', 'prislusenstvi', 'prace' }
    Respektuje period/start_date/end_date, prodejna_id/stredisko a volitelný limit (default 100).
    """

    try:
        segment = request.GET.get('segment')  # sluzby | prislusenstvi | prace
        if segment not in {'sluzby', 'prislusenstvi', 'prace'}:
            return JsonResponse({'success': False, 'error': 'Neplatný segment'}, status=400)

        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        period = request.GET.get('period', 'custom')
        prodejna_id = request.GET.get('prodejna_id')
        stredisko = request.GET.get('stredisko')
        limit = int(request.GET.get('limit', '100'))

        # Základní servisní filtr
        base_servis_q = (
            Q(objednavku_zalozil__icontains='servis eda') &
            Q(k_servisu='ANO')
        )
        
        qs = WebProdejeAll.objects.filter(base_servis_q)
        if prodejna_id:
            qs = qs.filter(id_prodejny=prodejna_id)
        if stredisko:
            qs = qs.filter(stredisko=stredisko)

        if period != 'custom':
            today = date.today()
            if period == 'daily':
                start_date = today
                end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1)
                end_date = today

        if start_date:
            try:
                sd = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                qs = qs.filter(typ__gte=sd.strftime('%Y-%m-%d'))
            except:
                pass
        if end_date:
            try:
                ed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                end_upper = (ed + timedelta(days=1)).strftime('%Y-%m-%d')
                qs = qs.filter(typ__lt=end_upper)
            except:
                pass

        if segment == 'sluzby':
            qs = qs.filter(Q(kategorie__icontains='!Servis') & Q(kategorie_1__istartswith='Služby'))
        elif segment == 'prislusenstvi':
            qs = qs.filter(Q(objednavku_zalozil__icontains='servis eda') & Q(kategorie__iexact='PŘÍSLUŠENSTVÍ') & Q(k_servisu='ANO'))
        else:  # 'prace'
            qs = qs.filter(Q(kategorie__icontains='!Servis') & ~Q(kategorie_1__icontains='Služby'))

        items = (
            qs.order_by('-typ')
              .values('objednavka', 'nazev')[:max(1, min(limit, 1000))]
        )

        return JsonResponse({
            'success': True,
            'items': list(items),
            'count': qs.count()
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e), 'items': []}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def servis_technik_detail_view(request):
    """
    Detail pro konkrétního technika – pouze servisní položky s k_servisu='ANO'.
    Filtry: period/start_date/end_date a parametr technik (povinný).
    """
    try:
        technik = request.GET.get('technik')
        if not technik:
            return JsonResponse({'success': False, 'error': 'Chybí parametr technik'}, status=400)

        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        period = request.GET.get('period', 'custom')

        # Základní servisní filtr
        base_servis_q = (
            Q(objednavku_zalozil__icontains='servis eda') &
            Q(k_servisu='ANO')
        )
        
        display_name = resolve_technik_display(technik)
        qs = WebProdejeAll.objects.filter(base_servis_q).filter(technik_filter_q(display_name))

        if period != 'custom':
            today = date.today()
            if period == 'daily':
                start_date = today
                end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1)
                end_date = today

        if start_date:
            try:
                sd = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                qs = qs.filter(typ__gte=sd.strftime('%Y-%m-%d'))
            except:
                pass
        if end_date:
            try:
                ed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                end_upper = (ed + timedelta(days=1)).strftime('%Y-%m-%d')
                qs = qs.filter(typ__lt=end_upper)
            except:
                pass

        def agg(q):
            return q.aggregate(
                obrat_bez_dph=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
                marze=Sum(F('pocet_kusu') * F('zisk'), default=0),
                polozky=Count('id'),
                doklady=Count('doklad', distinct=True),
            )

        sluzby = agg(qs.filter(Q(kategorie__icontains='!Servis') & Q(kategorie_1__istartswith='Služby')))
        prislusenstvi = agg(qs.filter(Q(objednavku_zalozil__icontains='servis eda') & Q(kategorie__iexact='PŘÍSLUŠENSTVÍ') & Q(k_servisu='ANO')))
        servisni_prace = agg(qs.filter(Q(kategorie__icontains='!Servis') & ~Q(kategorie_1__icontains='Služby')))

        def convert(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            return obj

        return JsonResponse({
            'success': True,
            'detail': {
                'technik': display_name,
                'breakdown': {
                    'sluzby': convert(sluzby),
                    'prislusenstvi_k_servisu': convert(prislusenstvi),
                    'servisni_prace': convert(servisni_prace),
                }
            }
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def servis_technik_items_view(request):
    """
    Seznam položek (nazev, objednavka) pro daného technika a segment (sluzby|prislusenstvi|prace).
    Respektuje period/start_date/end_date. Parametr technik je povinný.
    """
    try:
        technik = request.GET.get('technik')
        segment = request.GET.get('segment')
        if not technik or segment not in {'sluzby', 'prislusenstvi', 'prace'}:
            return JsonResponse({'success': False, 'error': 'Chybí technik nebo neplatný segment'}, status=400)

        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        period = request.GET.get('period', 'custom')
        limit = int(request.GET.get('limit', '200'))

        # Základní servisní filtr
        base_servis_q = _base_servis_q()
        
        display_name = resolve_technik_display(technik)
        qs = WebProdejeAll.objects.filter(base_servis_q).filter(technik_filter_q(display_name))

        if period != 'custom':
            today = date.today()
            if period == 'daily':
                start_date = today
                end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1)
                end_date = today

        if start_date:
            try:
                sd = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                qs = qs.filter(typ__gte=sd.strftime('%Y-%m-%d'))
            except:
                pass
        if end_date:
            try:
                ed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                end_upper = (ed + timedelta(days=1)).strftime('%Y-%m-%d')
                qs = qs.filter(typ__lt=end_upper)
            except:
                pass

        if segment == 'sluzby':
            qs = qs.filter(Q(kategorie__icontains='!Servis') & Q(kategorie_1__istartswith='Služby'))
        elif segment == 'prislusenstvi':
            qs = qs.filter(Q(objednavku_zalozil__icontains='servis eda') & Q(kategorie__iexact='PŘÍSLUŠENSTVÍ') & Q(k_servisu='ANO'))
        else:
            qs = qs.filter(Q(kategorie__icontains='!Servis') & ~Q(kategorie_1__icontains='Služby'))

        items = qs.order_by('-typ').values('objednavka', 'nazev')[:max(1, min(limit, 1000))]

        return JsonResponse({'success': True, 'items': list(items), 'count': qs.count()})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e), 'items': []}, status=500)

# =============================================================================
# PRODEJNÍ ANALYTIKA - API endpointy pro pokročilé analýzy z WEB_PRODEJE
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def prodejni_analytika_view(request):
    """
    Hlavní endpoint pro modul 'Prodejní analytika'
    Vrací grafy prodejů za různé kategorie v různých časech na různých prodejnách z WEB_PRODEJE
    """
    
    try:
        # Získání filtrů z GET parametrů
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        period = request.GET.get('period', 'monthly')  # daily, weekly, monthly, yearly, custom, monthly_select
        selected_month = request.GET.get('selected_month')  # YYYY-MM (stejně jako v Celková čísla)
        analysis_type = request.GET.get('type', 'categories')  # categories, stores, time, products
        prodejna_id = request.GET.get('prodejna_id')
        kanal = request.GET.get('kanal', 'all')
        kategorie = request.GET.get('kategorie', 'all')
        
        # Základní QuerySet
        queryset = WebProdejeAll.objects.all()
        
        # Filtrování podle data
        if period not in ('custom', 'monthly_select'):
            today = date.today()
            if period == 'daily':
                start_date = today
                end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1)
                end_date = today
            elif period == 'yearly':
                start_date = today.replace(month=1, day=1)
                end_date = today
                
        # Vybraný měsíc (YYYY-MM)
        if period == 'monthly_select' and selected_month:
            try:
                year, month = selected_month.split('-')
                start_date = date(int(year), int(month), 1)
                if int(month) == 12:
                    end_date = date(int(year) + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(int(year), int(month) + 1, 1) - timedelta(days=1)
            except Exception:
                pass

        if start_date:
            try:
                start_date_parsed = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                queryset = queryset.filter(typ__gte=start_date_parsed.strftime('%Y-%m-%d'))
            except:
                pass
                
        if end_date:
            try:
                end_date_parsed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                # horní mez následující den pro plné pokrytí
                queryset = queryset.filter(typ__lt=(end_date_parsed + timedelta(days=1)).strftime('%Y-%m-%d'))
            except:
                pass


# (Zákaznický endpoint bude definován níže, mimo tělo funkce prodejni_analytika_view)
        
        # Filtrování podle prodejního kanálu
        if kanal == 'eshop':
            queryset = queryset.filter(marketingovy_kanal='e-shop')
        elif kanal == 'prodejna':
            queryset = queryset.exclude(marketingovy_kanal='e-shop')
        elif kanal == 'allegro':
            queryset = queryset.filter(dropshipping='Baselinker')
        
        # Filtrování podle prodejny
        if prodejna_id:
            queryset = queryset.filter(id_prodejny=prodejna_id)
            
        # Filtrování podle kategorie
        if kategorie and kategorie != 'all':
            queryset = queryset.filter(kategorie__icontains=kategorie)
        
        # Základní agregace
        base_aggregations = queryset.aggregate(
            celkem_polozek=Count('id'),
            celkem_kusu=Sum('pocet_kusu'),
            celkovy_obrat=Sum(F('pocet_kusu') * F('cena_ks_vcl_dph'), default=0),
            celkovy_zisk=Sum(F('pocet_kusu') * F('zisk'), default=0),
            pocet_dokladu=Count('doklad', distinct=True),
            prumerna_cena=Avg('cena_ks_vcl_dph')
        )
        
        # Výpočet marže
        if base_aggregations['celkovy_obrat'] and base_aggregations['celkovy_obrat'] > 0:
            base_aggregations['marze_procenta'] = round(
                (base_aggregations['celkovy_zisk'] / base_aggregations['celkovy_obrat']) * 100, 2
            )
        else:
            base_aggregations['marze_procenta'] = 0
            
        # Průměrná hodnota objednávky
        if base_aggregations['pocet_dokladu'] and base_aggregations['pocet_dokladu'] > 0:
            base_aggregations['prumerna_objednavka'] = round(
                base_aggregations['celkovy_obrat'] / base_aggregations['pocet_dokladu'], 2
            )
        else:
            base_aggregations['prumerna_objednavka'] = 0
        
        response_data = {
            'success': True,
            'analysis_type': analysis_type,
            'period': period,
            'aggregations': convert_decimals(base_aggregations),
            'meta': {
                'total_records': queryset.count(),
                'generated_at': datetime.now().isoformat()
            }
        }
        
        # Přidání specifických analýz podle typu
        if analysis_type == 'categories':
            response_data['categories'] = get_category_analysis(queryset, period)
        elif analysis_type == 'stores':
            response_data['stores'] = get_store_analysis(queryset, period)
        elif analysis_type == 'time':
            response_data['time'] = get_time_analysis(queryset, period)
        elif analysis_type == 'products':
            response_data['products'] = get_product_analysis(queryset, period)
        
        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Chyba při zpracování analytiky: {str(e)}',
            'data': []
        }, status=500)


# =============================================================================
# PRODEJNÍ ANALYTIKA – Telefony a příslušenství ≥ 100 Kč na doklad (WEB_PRODEJE_ALL)
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def phones_accessories_view(request):
    """
    Analýza: kolik příslušenství/služeb ≥ 100 Kč prodáváme k telefonům.

    Postup:
    1) Najdeme doklady obsahující telefony (kategorie: POUŽITÉ TELEFONY, NOVÉ TELEFONY, Kaufland, Telefony Písek, !Výkup bazaru)
    2) Pro tyto doklady spočítáme počet položek na účtence s cenou ≥ {threshold} Kč (mimo telefonních kategorií)
    3) Vrátíme souhrny + seznam dokladů bez příslušenství ≥ {threshold}
    Parametry: start_date, end_date, period/custom/monthly_select+selected_month, kanal, prodejna_id, threshold
    """
    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        period = request.GET.get('period', 'custom')
        selected_month = request.GET.get('selected_month')
        kanal = request.GET.get('kanal', 'all')
        prodejna_id = request.GET.get('prodejna_id')
        threshold = request.GET.get('threshold', '100')
        try:
            threshold = float(threshold)
        except Exception:
            threshold = 100.0

        qs = WebProdejeAll.objects.all()

        # Kanál
        if kanal == 'eshop':
            qs = qs.filter(marketingovy_kanal='e-shop')
        elif kanal == 'prodejna':
            qs = qs.exclude(marketingovy_kanal='e-shop')
        elif kanal == 'allegro':
            qs = qs.filter(dropshipping='Baselinker')

        if prodejna_id:
            qs = qs.filter(id_prodejny=prodejna_id)

        # Období
        if period not in ('custom', 'monthly_select'):
            today = date.today()
            if period == 'daily':
                start_date = today
                end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1)
                end_date = today
        elif period == 'monthly_select' and selected_month:
            try:
                year, month = selected_month.split('-')
                start_date = date(int(year), int(month), 1)
                if int(month) == 12:
                    end_date = date(int(year) + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(int(year), int(month) + 1, 1) - timedelta(days=1)
            except Exception:
                pass

        if start_date:
            try:
                sd = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                qs = qs.filter(typ__gte=sd.strftime('%Y-%m-%d'))
            except Exception:
                pass
        if end_date:
            try:
                ed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                qs = qs.filter(typ__lt=(ed + timedelta(days=1)).strftime('%Y-%m-%d'))
            except Exception:
                pass

        # Definice telefonních kategorií
        phone_filter = (
            Q(kategorie__iexact='POUŽITÉ TELEFONY') |
            Q(kategorie__iexact='NOVÉ TELEFONY') |
            Q(kategorie__icontains='Kaufland') |
            Q(kategorie__icontains='Telefony Písek') |
            Q(kategorie__icontains='!Výkup bazaru')
        )

        phones_qs = qs.filter(phone_filter)

        # Doklady s telefony
        phone_docs = list(
            phones_qs.exclude(doklad__isnull=True).exclude(doklad='')
                     .values_list('doklad', flat=True).distinct()
        )

        if not phone_docs:
            return JsonResponse({
                'success': True,
                'totals': {
                    'phones': 0,
                    'accessories_items_over_threshold': 0,
                    'accessories_per_phone': 0.0
                },
                'receipts': {
                    'with_accessory': 0,
                    'without_accessory': 0,
                    'without_accessory_list': []
                },
                'meta': {
                    'threshold': threshold,
                    'data_source': 'WEB_PRODEJE_ALL',
                    'generated_at': datetime.now().isoformat()
                }
            })

        # Počty telefonů - ruční výpočet aby se správně odečítala storna
        from django.db.models.functions import Coalesce as DJCoalesce
        
        # Spočítáme čistý počet telefonů (prodeje mínus storna)
        # Storna poznáme podle záporné ceny, ne záporného počtu kusů
        total_phones = 0
        for phone in phones_qs.values('pocet_kusu', 'cena_ks_bez_dph'):
            kusy = phone['pocet_kusu'] or 0
            cena = float(phone['cena_ks_bez_dph'] or 0)
            
            if cena < 0:  # Storno (záporná cena)
                total_phones -= kusy  # Odečteme kusy
            else:  # Normální prodej (kladná cena)
                total_phones += kusy  # Přičteme kusy

        # Počty telefonů na doklad (kusy) - pro statistiky dokladů
        phones_by_doc = (
            phones_qs.values('doklad')
                     .annotate(phones_items=Count('id'), phones_kusy=Sum(DJCoalesce('pocet_kusu', 1)))
        )
        phones_map = {row['doklad']: row for row in phones_by_doc}

        # Počty příslušenství/služeb >= threshold na doklad (mimo telefonních kategorií)
        accessories_by_doc = (
            qs.filter(doklad__in=phone_docs, cena_ks_vcl_dph__gte=threshold)
              .exclude(phone_filter)
              .values('doklad')
              .annotate(items_kusy=Sum(DJCoalesce('pocet_kusu', 1)), items=Count('id'))
        )
        acc_map = {row['doklad']: row for row in accessories_by_doc}

        total_acc_items = 0
        receipts_no_acc = []

        # Metadata per doklad (datum, prodejna)
        meta_map = {
            r['doklad']: r
            for r in qs.filter(doklad__in=phone_docs)
                       .values('doklad', 'typ', 'stredisko')
                       .order_by('doklad', '-typ')
        }

        for dok, row in phones_map.items():
            acc_row = acc_map.get(dok)
            acc_items = int((acc_row or {}).get('items_kusy') or 0)
            total_acc_items += acc_items
            if acc_items == 0:
                meta = meta_map.get(dok) or {}
                receipts_no_acc.append({
                    'doklad': dok,
                    'phones_kusy': int(row.get('phones_kusy') or 0),
                    'date': meta.get('typ'),
                    'stredisko': meta.get('stredisko')
                })

        accessories_per_phone = float(total_acc_items) / float(total_phones) if total_phones else 0.0

        # Výpočet finančních údajů pro telefony (obrat, marže) - ručně kvůli problémům s mixed types
        obrat_bez_dph = 0
        marze_korun = 0
        
        for phone in phones_qs.values('pocet_kusu', 'cena_ks_bez_dph', 'zisk'):
            pocet = phone['pocet_kusu'] or 0
            cena_bez_dph = float(phone['cena_ks_bez_dph'] or 0)
            zisk_item = float(phone['zisk'] or 0)
            
            obrat_bez_dph += pocet * cena_bez_dph
            marze_korun += pocet * zisk_item
        
        marze_procenta = (marze_korun / obrat_bez_dph * 100) if obrat_bez_dph > 0 else 0

        return JsonResponse({
            'success': True,
            'totals': {
                'phones': total_phones,
                'accessories_items_over_threshold': total_acc_items,
                'accessories_per_phone': round(accessories_per_phone, 2)
            },
            'aggregations': {
                'celkovy_obrat': obrat_bez_dph,
                'celkovy_zisk': marze_korun,  # Bude přejmenováno na "celková marže" ve frontendu
                'marze_procenta': round(marze_procenta, 1),
                'celkem_polozek': total_phones
            },
            'receipts': {
                'with_accessory': len(phones_map) - len(receipts_no_acc),
                'without_accessory': len(receipts_no_acc),
                'without_accessory_list': receipts_no_acc[:300]
            },
            'meta': {
                'threshold': threshold,
                'data_source': 'WEB_PRODEJE_ALL',
                'generated_at': datetime.now().isoformat(),
                'note': 'aggregations obsahuje finanční data pouze pro telefony'
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def phones_accessories_receipt_items_view(request):
    """
    Vrátí položky na daném dokladu. Parametry: doklad, threshold (volitelně pro zvýraznění), include_prices=true|false
    """
    try:
        doklad = request.GET.get('doklad')
        threshold = request.GET.get('threshold')
        try:
            threshold = float(threshold) if threshold is not None else None
        except Exception:
            threshold = None

        if not doklad:
            return JsonResponse({'success': False, 'error': 'Chybí parametr doklad'}, status=400)

        qs = WebProdejeAll.objects.filter(doklad=doklad).order_by('id')
        items = []
        for r in qs.values('kod', 'nazev', 'pocet_kusu', 'cena_ks_vcl_dph', 'kategorie', 'kategorie_1', 'kategorie_2'):
            val = float(r.get('cena_ks_vcl_dph') or 0)
            items.append({
                'kod': r['kod'],
                'nazev': r['nazev'],
                'pocet_kusu': r['pocet_kusu'] or 0,
                'cena_ks_vcl_dph': val,
                'kategorie': r['kategorie'],
                'kategorie_1': r['kategorie_1'],
                'kategorie_2': r['kategorie_2'],
                'over_threshold': (threshold is not None and val >= threshold)
            })

        return JsonResponse({'success': True, 'items': items})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def phones_accessories_by_salesperson_view(request):
    """
    Souhrn po prodejcích: telefony (kusy), příslušenství/služby ≥ threshold (kusy) a počet dokladů pouze s telefonem.
    Parametry: start_date, end_date, period, selected_month, kanal, prodejna_id, threshold
    """
    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        period = request.GET.get('period', 'custom')
        selected_month = request.GET.get('selected_month')
        kanal = request.GET.get('kanal', 'all')
        prodejna_id = request.GET.get('prodejna_id')
        threshold = request.GET.get('threshold', '100')
        try:
            threshold = float(threshold)
        except Exception:
            threshold = 100.0

        qs = WebProdejeAll.objects.all()

        # Kanál
        if kanal == 'eshop':
            qs = qs.filter(marketingovy_kanal='e-shop')
        elif kanal == 'prodejna':
            qs = qs.exclude(marketingovy_kanal='e-shop')
        elif kanal == 'allegro':
            qs = qs.filter(dropshipping='Baselinker')

        if prodejna_id:
            qs = qs.filter(id_prodejny=prodejna_id)

        # Období
        if period not in ('custom', 'monthly_select'):
            today = date.today()
            if period == 'daily':
                start_date = today
                end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1)
                end_date = today
        elif period == 'monthly_select' and selected_month:
            try:
                year, month = selected_month.split('-')
                start_date = date(int(year), int(month), 1)
                if int(month) == 12:
                    end_date = date(int(year) + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(int(year), int(month) + 1, 1) - timedelta(days=1)
            except Exception:
                pass

        if start_date:
            try:
                sd = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                qs = qs.filter(typ__gte=sd.strftime('%Y-%m-%d'))
            except Exception:
                pass
        if end_date:
            try:
                ed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                qs = qs.filter(typ__lt=(ed + timedelta(days=1)).strftime('%Y-%m-%d'))
            except Exception:
                pass

        # Definice telefonních kategorií
        phone_filter = (
            Q(kategorie__iexact='POUŽITÉ TELEFONY') |
            Q(kategorie__iexact='NOVÉ TELEFONY') |
            Q(kategorie__icontains='Kaufland') |
            Q(kategorie__icontains='Telefony Písek') |
            Q(kategorie__icontains='!Výkup bazaru')
        )

        from django.db.models.functions import Coalesce as DJCoalesce

        phones_qs = qs.filter(phone_filter)

        # Telefony: doklad + id_prodejce + kusy
        phone_rows = (
            phones_qs.exclude(doklad__isnull=True).exclude(doklad='')
                     .values('id_prodejce', 'doklad')
                     .annotate(phones_kusy=Sum(DJCoalesce('pocet_kusu', 1)))
        )

        # Seznam všech dokladů s telefony
        phone_docs = list({r['doklad'] for r in phone_rows})

        # Příslušenství/služby ≥ threshold podle dokladů (mimo telefonních kategorií)
        acc_map = {}
        if phone_docs:
            for row in (
                qs.filter(doklad__in=phone_docs, cena_ks_vcl_dph__gte=threshold)
                  .exclude(phone_filter)
                  .values('doklad')
                  .annotate(items_kusy=Sum(DJCoalesce('pocet_kusu', 1)))
            ):
                acc_map[row['doklad']] = int(row['items_kusy'] or 0)

        # Metadata dokladů (datum, středisko)
        meta_map = {
            r['doklad']: r
            for r in qs.filter(doklad__in=phone_docs)
                       .values('doklad', 'typ', 'stredisko')
        }

        # Mapování prodejce -> jméno
        users = {u.id: u for u in WebUser.objects.filter(id__in=list({r['id_prodejce'] for r in phone_rows if r['id_prodejce'] is not None}))}

        # Agregace po prodejcích
        result_rows = {}
        for r in phone_rows:
            pid = r['id_prodejce'] or 0
            doc = r['doklad']
            phones_kusy = int(r.get('phones_kusy') or 0)
            acc_kusy = int(acc_map.get(doc, 0))
            row = result_rows.setdefault(pid, {
                'id_prodejce': pid,
                'jmeno': (users.get(pid).jmeno if users.get(pid) else ''),
                'prijmeni': (users.get(pid).prijmeni if users.get(pid) else ''),
                'phones_kusy': 0,
                'accessories_kusy': 0,
                'phones_only_docs': 0,
                'phones_only_list': []
            })
            row['phones_kusy'] += phones_kusy
            row['accessories_kusy'] += acc_kusy
            if acc_kusy == 0:
                row['phones_only_docs'] += 1
                meta = meta_map.get(doc) or {}
                if len(row['phones_only_list']) < 50:
                    row['phones_only_list'].append({
                        'doklad': doc,
                        'date': meta.get('typ'),
                        'stredisko': meta.get('stredisko'),
                        'phones_kusy': phones_kusy
                    })

        return JsonResponse({
            'success': True,
            'rows': list(result_rows.values()),
            'meta': {
                'threshold': threshold,
                'generated_at': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def phones_accessories_salesperson_receipts_view(request):
    """
    Vrátí seznam dokladů pro konkrétního prodejce. Parametry: prodejce_id, kind=without|with, threshold, + common filters.
    """
    try:
        prodejce_id = request.GET.get('prodejce_id')
        if not prodejce_id:
            return JsonResponse({'success': False, 'error': 'Chybí prodejce_id'}, status=400)
        kind = request.GET.get('kind', 'without')
        threshold = float(request.GET.get('threshold', '100'))

        # Reuse filtering from summary
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        period = request.GET.get('period', 'custom')
        selected_month = request.GET.get('selected_month')
        kanal = request.GET.get('kanal', 'all')
        prodejna_id = request.GET.get('prodejna_id')

        qs = WebProdejeAll.objects.all()
        if kanal == 'eshop':
            qs = qs.filter(marketingovy_kanal='e-shop')
        elif kanal == 'prodejna':
            qs = qs.exclude(marketingovy_kanal='e-shop')
        elif kanal == 'allegro':
            qs = qs.filter(dropshipping='Baselinker')
        if prodejna_id:
            qs = qs.filter(id_prodejny=prodejna_id)
        if period not in ('custom', 'monthly_select'):
            today = date.today()
            if period == 'daily':
                start_date = today; end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7); end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1); end_date = today
        elif period == 'monthly_select' and selected_month:
            y, m = selected_month.split('-')
            start_date = date(int(y), int(m), 1)
            end_date = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        if start_date:
            sd = parse_date(start_date).date() if isinstance(start_date, str) else start_date
            qs = qs.filter(typ__gte=sd.strftime('%Y-%m-%d'))
        if end_date:
            ed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
            qs = qs.filter(typ__lt=(ed + timedelta(days=1)).strftime('%Y-%m-%d'))

        phone_filter = (
            Q(kategorie__iexact='POUŽITÉ TELEFONY') |
            Q(kategorie__iexact='NOVÉ TELEFONY') |
            Q(kategorie__icontains='Kaufland') |
            Q(kategorie__icontains='Telefony Písek') |
            Q(kategorie__icontains='!Výkup bazaru')
        )

        from django.db.models.functions import Coalesce as DJCoalesce

        phones_qs = qs.filter(phone_filter, id_prodejce=prodejce_id)
        phone_docs = list(
            phones_qs.exclude(doklad__isnull=True).exclude(doklad='')
                     .values_list('doklad', flat=True).distinct()
        )
        if not phone_docs:
            return JsonResponse({'success': True, 'receipts': []})

        acc_map = {}
        for row in (
            qs.filter(doklad__in=phone_docs, cena_ks_vcl_dph__gte=threshold)
              .exclude(phone_filter)
              .values('doklad')
              .annotate(items_kusy=Sum(DJCoalesce('pocet_kusu', 1)))
        ):
            acc_map[row['doklad']] = int(row['items_kusy'] or 0)

        receipts = []
        for r in (
            phones_qs.values('doklad')
                     .annotate(phones_kusy=Sum(DJCoalesce('pocet_kusu', 1)), datum=F('typ'), stredisko=F('stredisko'))
        ):
            has_acc = (acc_map.get(r['doklad'], 0) > 0)
            if (kind == 'without' and not has_acc) or (kind == 'with' and has_acc):
                receipts.append({
                    'doklad': r['doklad'],
                    'phones_kusy': int(r['phones_kusy'] or 0),
                    'date': r['datum'],
                    'stredisko': r['stredisko']
                })

        receipts.sort(key=lambda x: str(x.get('date') or ''), reverse=True)
        return JsonResponse({'success': True, 'receipts': receipts[:300]})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =============================================================================
# ZÁKAZNÍCI - Počet unikátních zákazníků podle dokladů/objednávek (WEB_PRODEJE_ALL)
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def zakaznici_view(request):
    """
    Vrací počty zákazníků na základě unikátních dokladů/objednávek z tabulky WEB_PRODEJE_ALL.
    Jeden unikátní doklad/objednávka = jeden zákazník.

    Odpověď obsahuje:
    - totals: today, month, all
    - channels: prodejna, eshop, allegro
    - stores: rozpad podle prodejen (today, month, all)
    """

    try:
        today = date.today()
        today_iso = today.strftime('%Y-%m-%d')
        ym = today.strftime('%Y-%m')

        base_qs = WebProdejeAll.objects.all()

        # Unikátní identifikátor dokladu/objednávky
        unique_doc = Coalesce('doklad', 'objednavka')

        # Pomocné filtry kanálů
        eshop_q = Q(marketingovy_kanal='e-shop')
        allegro_q = Q(dropshipping='Baselinker')
        prodejna_q = ~eshop_q & ~allegro_q

        # Totální počty
        total_all = base_qs.exclude(Q(doklad__isnull=True) & Q(objednavka__isnull=True)).aggregate(
            customers=Count(unique_doc, distinct=True)
        )['customers'] or 0

        total_today = base_qs.filter(typ=today_iso).exclude(Q(doklad__isnull=True) & Q(objednavka__isnull=True)).aggregate(
            customers=Count(unique_doc, distinct=True)
        )['customers'] or 0

        total_month = base_qs.filter(typ__startswith=ym).exclude(Q(doklad__isnull=True) & Q(objednavka__isnull=True)).aggregate(
            customers=Count(unique_doc, distinct=True)
        )['customers'] or 0

        # Kanály
        def channel_counts(q_filter):
            ch_all = base_qs.filter(q_filter).exclude(Q(doklad__isnull=True) & Q(objednavka__isnull=True)).aggregate(
                customers=Count(unique_doc, distinct=True)
            )['customers'] or 0
            ch_today = base_qs.filter(q_filter, typ=today_iso).exclude(Q(doklad__isnull=True) & Q(objednavka__isnull=True)).aggregate(
                customers=Count(unique_doc, distinct=True)
            )['customers'] or 0
            ch_month = base_qs.filter(q_filter, typ__startswith=ym).exclude(Q(doklad__isnull=True) & Q(objednavka__isnull=True)).aggregate(
                customers=Count(unique_doc, distinct=True)
            )['customers'] or 0
            return {
                'today': ch_today,
                'month': ch_month,
                'all': ch_all,
            }

        channels = {
            'prodejna': channel_counts(prodejna_q),
            'eshop': channel_counts(eshop_q),
            'allegro': channel_counts(allegro_q),
        }

        # Prodejny – rozpad podle střediska/ID prodejny
        def stores_breakdown(qs):
            rows = (
                qs.exclude(Q(doklad__isnull=True) & Q(objednavka__isnull=True))
                  .values('stredisko', 'id_prodejny')
                  .annotate(customers=Count(unique_doc, distinct=True))
                  .order_by('-customers')
            )
            return list(rows)

        stores = {
            'today': stores_breakdown(base_qs.filter(typ=today_iso)),
            'month': stores_breakdown(base_qs.filter(typ__startswith=ym)),
            'all': stores_breakdown(base_qs),
        }

        return JsonResponse({
            'success': True,
            'totals': {
                'today': total_today,
                'month': total_month,
                'all': total_all,
            },
            'channels': channels,
            'stores': stores,
            'meta': {
                'data_source': 'WEB_PRODEJE_ALL',
                'unique_definition': 'unikátní doklad nebo objednávka = 1 zákazník',
                'generated_at': datetime.now().isoformat(),
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def zakaznici_timeseries_view(request):
    """
    Časová řada návštěvnosti (počet zákazníků = unikátních dokladů/objednávek)
    Parametry:
      - period: daily | monthly (default: daily)
      - start_date, end_date: YYYY-MM-DD (volitelné; default: posledních 30 dní)
      - prodejny[]: seznam ID prodejen (volitelné)
    Vrací celkovou řadu + top 5 (nebo vybrané) prodejen jako samostatné řady.
    """
    try:
        today = date.today()
        default_start = (today - timedelta(days=30)).strftime('%Y-%m-%d')
        start_date = request.GET.get('start_date', default_start)
        end_date = request.GET.get('end_date', today.strftime('%Y-%m-%d'))
        period = request.GET.get('period', 'daily')  # daily | monthly
        prodejny = request.GET.getlist('prodejny[]')  # ID prodejen

        qs = WebProdejeAll.objects.all()

        # Filter by date range
        if start_date:
            qs = qs.filter(typ__gte=start_date)
        if end_date:
            qs = qs.filter(typ__lte=end_date)

        unique_doc = Coalesce('doklad', 'objednavka')

        # Grouping key
        if period == 'monthly':
            group_key = TruncMonth(Cast('typ', DateField()))
            label_fmt = '%Y-%m'
        else:
            group_key = Cast('typ', DateField())
            label_fmt = '%Y-%m-%d'

        # Total series
        total_rows = (
            qs.exclude(Q(doklad__isnull=True) & Q(objednavka__isnull=True))
              .annotate(g=group_key)
              .values('g')
              .annotate(customers=Count(unique_doc, distinct=True))
              .order_by('g')
        )
        series = [
            {
                'label': (r['g'].strftime(label_fmt) if hasattr(r['g'], 'strftime') else str(r['g'])),
                'customers': r['customers'] or 0
            }
            for r in total_rows
        ]

        # Store series (top 5 by total customers in period or selected)
        store_list = []
        if prodejny:
            store_list = list(
                qs.filter(id_prodejny__in=prodejny)
                  .values('stredisko', 'id_prodejny')
                  .distinct()
            )
        else:
            store_list = list(
                qs.exclude(Q(doklad__isnull=True) & Q(objednavka__isnull=True))
                  .values('stredisko', 'id_prodejny')
                  .annotate(c=Count(unique_doc, distinct=True))
                  .order_by('-c')[:5]
            )

        stores_series = []
        for s in store_list:
            sid = s.get('id_prodejny')
            name = s.get('stredisko') or f"ID {sid or ''}"
            s_rows = (
                qs.filter(id_prodejny=sid)
                  .exclude(Q(doklad__isnull=True) & Q(objednavka__isnull=True))
                  .annotate(g=group_key)
                  .values('g')
                  .annotate(customers=Count(unique_doc, distinct=True))
                  .order_by('g')
            )
            stores_series.append({
                'name': name,
                'id_prodejny': sid,
                'series': [
                    {
                        'label': (r['g'].strftime(label_fmt) if hasattr(r['g'], 'strftime') else str(r['g'])),
                        'customers': r['customers'] or 0
                    }
                    for r in s_rows
                ]
            })

        return JsonResponse({
            'success': True,
            'period': period,
            'start_date': start_date,
            'end_date': end_date,
            'series': series,
            'stores': stores_series,
            'meta': {
                'data_source': 'WEB_PRODEJE_ALL',
                'unique_definition': 'unikátní doklad nebo objednávka = 1 zákazník',
                'generated_at': datetime.now().isoformat(),
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def get_category_analysis(queryset, period):
    """Analýza prodejů podle kategorií"""
    try:
        # Agregace podle kategorií
        category_data = queryset.values('kategorie').annotate(
            obrat=Sum(F('pocet_kusu') * F('cena_ks_vcl_dph'), default=0),
            zisk=Sum(F('pocet_kusu') * F('zisk'), default=0),
            polozky=Count('id'),
            kusy=Sum('pocet_kusu')
        ).order_by('-obrat')[:20]
        
        # Agregace podle období
        if period == 'daily':
            time_data = queryset.extra(
                select={'date': 'DATE(typ)'}
            ).values('date', 'kategorie').annotate(
                obrat=Sum(F('pocet_kusu') * F('cena_ks_vcl_dph'), default=0),
                polozky=Count('id')
            ).order_by('date', '-obrat')
        else:
            time_data = queryset.annotate(
                month=TruncMonth(Cast('typ', DateField()))
            ).values('month', 'kategorie').annotate(
                obrat=Sum(F('pocet_kusu') * F('cena_ks_vcl_dph'), default=0),
                polozky=Count('id')
            ).order_by('month', '-obrat')
        
        # Konvertování datetime.date na string pro JSON serialization
        def convert_dates(obj):
            if isinstance(obj, dict):
                return {k: convert_dates(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_dates(item) for item in obj]
            elif hasattr(obj, 'strftime'):  # datetime.date nebo datetime.datetime
                return obj.strftime('%Y-%m-%d')
            return obj
        
        return {
            'top_categories': convert_decimals(list(category_data)),
            'time_series': convert_dates(convert_decimals(list(time_data)))
        }
    except Exception as e:
        return {'error': str(e)}


def get_store_analysis(queryset, period):
    """Analýza prodejů podle prodejen"""
    try:
        # Agregace podle prodejen
        store_data = queryset.values('stredisko', 'id_prodejny').annotate(
            obrat=Sum(F('pocet_kusu') * F('cena_ks_vcl_dph'), default=0),
            zisk=Sum(F('pocet_kusu') * F('zisk'), default=0),
            polozky=Count('id'),
            kusy=Sum('pocet_kusu')
        ).order_by('-obrat')
        
        # Agregace podle období
        if period == 'daily':
            time_data = queryset.extra(
                select={'date': 'DATE(typ)'}
            ).values('date', 'stredisko').annotate(
                obrat=Sum(F('pocet_kusu') * F('cena_ks_vcl_dph'), default=0),
                polozky=Count('id')
            ).order_by('date', '-obrat')
        else:
            time_data = queryset.annotate(
                month=TruncMonth(Cast('typ', DateField()))
            ).values('month', 'stredisko').annotate(
                obrat=Sum(F('pocet_kusu') * F('cena_ks_vcl_dph'), default=0),
                polozky=Count('id')
            ).order_by('month', '-obrat')
        
        # Konvertování datetime.date na string pro JSON serialization
        def convert_dates(obj):
            if isinstance(obj, dict):
                return {k: convert_dates(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_dates(item) for item in obj]
            elif hasattr(obj, 'strftime'):  # datetime.date nebo datetime.datetime
                return obj.strftime('%Y-%m-%d')
            return obj
        
        return {
            'top_stores': convert_decimals(list(store_data)),
            'time_series': convert_dates(convert_decimals(list(time_data)))
        }
    except Exception as e:
        return {'error': str(e)}


def get_time_analysis(queryset, period):
    """Analýza prodejů v čase"""
    try:
        # Agregace podle času
        if period == 'daily':
            time_data = queryset.extra(
                select={'date': 'DATE(typ)'}
            ).values('date').annotate(
                obrat=Sum(F('pocet_kusu') * F('cena_ks_vcl_dph'), default=0),
                zisk=Sum(F('pocet_kusu') * F('zisk'), default=0),
                polozky=Count('id'),
                kusy=Sum('pocet_kusu')
            ).order_by('date')
        else:
            time_data = queryset.annotate(
                month=TruncMonth(Cast('typ', DateField()))
            ).values('month').annotate(
                obrat=Sum(F('pocet_kusu') * F('cena_ks_vcl_dph'), default=0),
                zisk=Sum(F('pocet_kusu') * F('zisk'), default=0),
                polozky=Count('id'),
                kusy=Sum('pocet_kusu')
            ).order_by('month')
        
        # Výpočet trendů
        if len(time_data) >= 2:
            first_obrat = time_data[0]['obrat']
            last_obrat = time_data[-1]['obrat']
            if first_obrat > 0:
                growth_rate = ((last_obrat - first_obrat) / first_obrat) * 100
            else:
                growth_rate = 0
        else:
            growth_rate = 0
        
        # Konvertování datetime.date na string pro JSON serialization
        def convert_dates(obj):
            if isinstance(obj, dict):
                return {k: convert_dates(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_dates(item) for item in obj]
            elif hasattr(obj, 'strftime'):  # datetime.date nebo datetime.datetime
                return obj.strftime('%Y-%m-%d')
            return obj
        
        return {
            'time_series': convert_dates(convert_decimals(list(time_data))),
            'growth_rate': round(growth_rate, 2),
            'prediction': calculate_prediction(time_data)
        }
    except Exception as e:
        return {'error': str(e)}


def get_product_analysis(queryset, period):
    """Analýza prodejů podle produktů"""
    try:
        # Agregace podle produktů
        product_data = queryset.values('kod', 'nazev').annotate(
            obrat=Sum(F('pocet_kusu') * F('cena_ks_vcl_dph'), default=0),
            zisk=Sum(F('pocet_kusu') * F('zisk'), default=0),
            polozky=Count('id'),
            kusy=Sum('pocet_kusu')
        ).order_by('-obrat')[:50]
        
        # Agregace podle období
        if period == 'daily':
            time_data = queryset.extra(
                select={'date': 'DATE(typ)'}
            ).values('date', 'kod', 'nazev').annotate(
                obrat=Sum(F('pocet_kusu') * F('cena_ks_vcl_dph'), default=0),
                polozky=Count('id')
            ).order_by('date', '-obrat')
        else:
            time_data = queryset.annotate(
                month=TruncMonth(Cast('typ', DateField()))
            ).values('month', 'kod', 'nazev').annotate(
                obrat=Sum(F('pocet_kusu') * F('cena_ks_vcl_dph'), default=0),
                polozky=Count('id')
            ).order_by('month', '-obrat')
        
        # Konvertování datetime.date na string pro JSON serialization
        def convert_dates(obj):
            if isinstance(obj, dict):
                return {k: convert_dates(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_dates(item) for item in obj]
            elif hasattr(obj, 'strftime'):  # datetime.date nebo datetime.datetime
                return obj.strftime('%Y-%m-%d')
            return obj
        
        return {
            'top_products': convert_decimals(list(product_data)),
            'time_series': convert_dates(convert_decimals(list(time_data)))
        }
    except Exception as e:
        return {'error': str(e)}


def calculate_prediction(time_data):
    """Jednoduchá predikce na základě trendu"""
    try:
        if len(time_data) < 2:
            return None
        
        # Jednoduchá lineární predikce
        recent_data = time_data[-5:] if len(time_data) >= 5 else time_data
        obraty = [item['obrat'] for item in recent_data]
        
        if len(obraty) >= 2:
            # Průměrný růst
            growth_rates = []
            for i in range(1, len(obraty)):
                if obraty[i-1] > 0:
                    growth_rate = (obraty[i] - obraty[i-1]) / obraty[i-1]
                    growth_rates.append(growth_rate)
            
            if growth_rates:
                avg_growth = sum(growth_rates) / len(growth_rates)
                last_obrat = obraty[-1]
                prediction = last_obrat * (1 + avg_growth)
                return round(prediction, 2)
        
        return None
    except Exception as e:
        return None


def convert_decimals(obj):
    """Konvertuje Decimal objekty na float pro JSON serialization"""
    if isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj


# =============================================================================
# GRAFY Z WEB_PRODEJE - API endpointy pro interaktivní grafy
# =============================================================================

@require_http_methods(["GET"])
@permission_classes([AllowAny])
def get_web_prodeje_charts_data(request):
    """Získá agregovaná data pro interaktivní grafy z tabulky WEB_PRODEJE"""
    try:
        # Parametry z requestu
        data_type = request.GET.get('type', 'daily')  # daily/monthly
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        prodejny = request.GET.getlist('prodejny[]')  # může být více prodejen
        metriky = request.GET.getlist('metriky[]')    # může být více metrik
        prodejce_id = request.GET.get('prodejce_id')
        
        # Výchozí metriky pokud nejsou specifikované
        if not metriky:
            metriky = ['polozky_nad_100']
        
        # Základní QuerySet z WEB_PRODEJE
        queryset = WebProdejeAll.objects.all()
        
        # Filtrování podle data přes CAST na DATE (spolehlivé pro string i date typy)
        try:
            queryset = queryset.annotate(typ_date=Cast('typ', DateField()))
            if start_date:
                sd = parse_date(start_date) if isinstance(start_date, str) else start_date
                if sd:
                    queryset = queryset.filter(typ_date__gte=sd)
            if end_date:
                ed = parse_date(end_date) if isinstance(end_date, str) else end_date
                if ed:
                    queryset = queryset.filter(typ_date__lte=ed)
        except Exception:
            # Fallback
            if start_date:
                try:
                    sd = parse_date(start_date).isoformat() if isinstance(start_date, str) else start_date.isoformat()
                    queryset = queryset.filter(typ__gte=sd)
                except Exception:
                    pass
            if end_date:
                try:
                    ed = parse_date(end_date).isoformat() if isinstance(end_date, str) else end_date.isoformat()
                    queryset = queryset.filter(typ__lte=ed)
                except Exception:
                    pass
        
        # Filtrování podle prodejce
        if prodejce_id:
            queryset = queryset.filter(id_prodejce=prodejce_id)
            
        # Filtrování podle prodejen
        if prodejny:
            queryset = queryset.filter(stredisko__in=prodejny)
        
        # Helper: výpočet průměru položek na účtenku (položky ≥ 29 Kč, bez dopravy)
        def compute_avg_per_group(base_qs, group_fn):
            rows = (
                base_qs
                .annotate(g=group_fn(Cast('typ', DateField())))
                .values('g', 'doklad', 'pokladna', 'typ', 'id_prodejny', 'nazev', 'pocet_kusu', 'cena_ks_vcl_dph', 'kod')
            )
            avg = {}
            per_group_sum = {}
            per_group_receipts = {}
            excluded_q = _excluded_names_q()
            for r in rows:
                g = r['g']
                # denominator: unikátní doklady
                key = (r['doklad'], r['pokladna'], r['typ'], r['id_prodejny'])
                if g not in per_group_receipts:
                    per_group_receipts[g] = set()
                if r['doklad']:
                    per_group_receipts[g].add(key)
                # numerator: součet kusů pouze pro reálné položky ≥ 29 Kč a ne přeprava/výdej
                if r['pocet_kusu'] is not None and r['cena_ks_vcl_dph'] is not None:
                    # Doprava nemá vyplněný kód - vyloučíme položky bez kódu
                    kod = r.get('kod')
                    is_excluded = not kod or kod == ''
                    if (not is_excluded) and float(r['cena_ks_vcl_dph']) >= 29:
                        per_group_sum[g] = per_group_sum.get(g, 0) + int(r['pocet_kusu'] or 0)
            for g in set(list(per_group_sum.keys()) + list(per_group_receipts.keys())):
                denom = len(per_group_receipts.get(g, set())) or 1
                avg[g] = round(per_group_sum.get(g, 0) / denom, 2)
            return avg

        # Agregace dat podle období
        if data_type == 'daily':
            # Denní agregace – použijeme ORM anotaci nad polem `typ` (db_column 'Vystaveno')
            chart_data = queryset.annotate(
                displayDate=Cast('typ', DateField())
            ).values('displayDate').annotate(
                polozky_nad_100=Sum('pocet_kusu', filter=Q(cena_ks_vcl_dph__gte=100) & Q(kod__isnull=False) & ~Q(kod=''), default=0),
                sluzby_celkem=Count('id', filter=Q(kategorie__icontains='!Servis')),
                prumer_polozek_uctu=Avg('pocet_kusu'),
                ct300=Count('id', filter=Q(kod__icontains='CT300')),
                ct600=Count('id', filter=Q(kod__icontains='CT600')),
                ct1200=Count('id', filter=Q(kod__icontains='CT1200')),
                akt=Count('id', filter=Q(kod__icontains='AKT')),
                zah250=Count('id', filter=Q(kod__icontains='ZAH250')),
                nap=Count('id', filter=Q(kod__icontains='NAP')),
                zah500=Count('id', filter=Q(kod__icontains='ZAH500')),
                kop250=Count('id', filter=Q(kod__icontains='KOP250')),
                kop500=Count('id', filter=Q(kod__icontains='KOP500')),
                pz1=Count('id', filter=Q(kod__icontains='PZ1')),
                knz=Count('id', filter=Q(kod__icontains='KNZ')),
                aligator=Count('id', filter=Q(kod__icontains='ALIGATOR'))
            ).order_by('displayDate')
            # Přepočet průměru položek/účtenku přes správný vzorec
            avg_map = compute_avg_per_group(queryset, lambda x: x)
            chart_data = [
                {**item, 'prumer_polozek_uctu': avg_map.get(item['displayDate'], 0)} for item in chart_data
            ]
            # Pokud je zadán rozsah dat, doplníme prázdné dny s nulami (frontend pak nemusí odhadovat)
            if start_date and end_date:
                try:
                    sd = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                    ed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                    existing = {str(item['displayDate']): item for item in chart_data}
                    filled = []
                    cur = sd
                    while cur <= ed:
                        key = cur.isoformat()
                        if key in existing:
                            filled.append(existing[key])
                        else:
                            # vytvoříme záznam s nulovými hodnotami
                            base = {'displayDate': cur}
                            for m in ['polozky_nad_100','sluzby_celkem','prumer_polozek_uctu','ct300','ct600','ct1200','akt','zah250','nap','zah500','kop250','kop500','pz1','knz','aligator']:
                                base[m] = 0
                            filled.append(base)
                        cur = cur + timedelta(days=1)
                    chart_data = filled
                except Exception:
                    pass
        elif data_type == 'weekly':
            chart_data = queryset.annotate(
                displayDate=TruncWeek(Cast('typ', DateField()))
            ).values('displayDate').annotate(
                polozky_nad_100=Sum('pocet_kusu', filter=Q(cena_ks_vcl_dph__gte=100) & Q(kod__isnull=False) & ~Q(kod=''), default=0),
                sluzby_celkem=Count('id', filter=Q(kategorie__icontains='!Servis')),
                prumer_polozek_uctu=Avg('pocet_kusu'),
                ct300=Count('id', filter=Q(kod__icontains='CT300')),
                ct600=Count('id', filter=Q(kod__icontains='CT600')),
                ct1200=Count('id', filter=Q(kod__icontains='CT1200')),
                akt=Count('id', filter=Q(kod__icontains='AKT')),
                zah250=Count('id', filter=Q(kod__icontains='ZAH250')),
                nap=Count('id', filter=Q(kod__icontains='NAP')),
                zah500=Count('id', filter=Q(kod__icontains='ZAH500')),
                kop250=Count('id', filter=Q(kod__icontains='KOP250')),
                kop500=Count('id', filter=Q(kod__icontains='KOP500')),
                pz1=Count('id', filter=Q(kod__icontains='PZ1')),
                knz=Count('id', filter=Q(kod__icontains='KNZ')),
                aligator=Count('id', filter=Q(kod__icontains='ALIGATOR'))
            ).order_by('displayDate')
            avg_map = compute_avg_per_group(queryset, TruncWeek)
            chart_data = [
                {**item, 'prumer_polozek_uctu': avg_map.get(item['displayDate'], 0)} for item in chart_data
            ]
        else:
            # Měsíční agregace
            chart_data = queryset.annotate(
                displayDate=TruncMonth(Cast('typ', DateField()))
            ).values('displayDate').annotate(
                polozky_nad_100=Sum('pocet_kusu', filter=Q(cena_ks_vcl_dph__gte=100) & Q(kod__isnull=False) & ~Q(kod=''), default=0),
                sluzby_celkem=Count('id', filter=Q(kategorie__icontains='!Servis')),
                prumer_polozek_uctu=Avg('pocet_kusu'),
                ct300=Count('id', filter=Q(kod__icontains='CT300')),
                ct600=Count('id', filter=Q(kod__icontains='CT600')),
                ct1200=Count('id', filter=Q(kod__icontains='CT1200')),
                akt=Count('id', filter=Q(kod__icontains='AKT')),
                zah250=Count('id', filter=Q(kod__icontains='ZAH250')),
                nap=Count('id', filter=Q(kod__icontains='NAP')),
                zah500=Count('id', filter=Q(kod__icontains='ZAH500')),
                kop250=Count('id', filter=Q(kod__icontains='KOP250')),
                kop500=Count('id', filter=Q(kod__icontains='KOP500')),
                pz1=Count('id', filter=Q(kod__icontains='PZ1')),
                knz=Count('id', filter=Q(kod__icontains='KNZ')),
                aligator=Count('id', filter=Q(kod__icontains='ALIGATOR'))
            ).order_by('displayDate')
            avg_map = compute_avg_per_group(queryset, TruncMonth)
            chart_data = [
                {**item, 'prumer_polozek_uctu': avg_map.get(item['displayDate'], 0)} for item in chart_data
            ]
        
        # Výpočet agregací pro každou metriku
        aggregations = {}
        for metrika in metriky:
            if metrika in ['polozky_nad_100', 'sluzby_celkem', 'ct300', 'ct600', 'ct1200', 'akt', 'zah250', 'nap', 'zah500', 'kop250', 'kop500', 'pz1', 'knz', 'aligator']:
                values = [item[metrika] for item in chart_data if item[metrika] is not None]
                if values:
                    aggregations[metrika] = {
                        'sum': sum(values),
                        'average': round(sum(values) / len(values), 2),
                        'min': min(values),
                        'max': max(values),
                        'count': len(values),
                        'trend': calculate_trend(values)
                    }
                else:
                    aggregations[metrika] = {
                        'sum': 0,
                        'average': 0,
                        'min': 0,
                        'max': 0,
                        'count': 0,
                        'trend': 0
                    }
            elif metrika == 'prumer_polozek_uctu':
                values = [item[metrika] for item in chart_data if item[metrika] is not None]
                if values:
                    aggregations[metrika] = {
                        'sum': sum(values),
                        'average': round(sum(values) / len(values), 2),
                        'min': min(values),
                        'max': max(values),
                        'count': len(values),
                        'trend': calculate_trend(values)
                    }
                else:
                    aggregations[metrika] = {
                        'sum': 0,
                        'average': 0,
                        'min': 0,
                        'max': 0,
                        'count': 0,
                        'trend': 0
                    }
        
        # Konvertování Decimal na float pro JSON serialization
        def convert_decimals(obj):
            if isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(item) for item in obj]
            elif isinstance(obj, Decimal):
                return float(obj)
            return obj
        
        return JsonResponse({
            'success': True,
            'data': convert_decimals(list(chart_data)),
            'aggregations': convert_decimals(aggregations),
            'meta': {
                'total_records': queryset.count(),
                'generated_at': datetime.now().isoformat(),
                'data_source': 'WEB_PRODEJE'
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Chyba při zpracování grafových dat: {str(e)}',
            'data': [],
            'aggregations': {}
        }, status=500)


def calculate_trend(values):
    """Vypočítá trend (růst/pokles) pro dané hodnoty"""
    if len(values) < 2:
        return 0
    
    # Jednoduchý výpočet trendu: (poslední - první) / první * 100
    first_value = values[0]
    last_value = values[-1]
    
    if first_value == 0:
        return 0
    
    trend = ((last_value - first_value) / first_value) * 100
    return round(trend, 2)


# =============================================================================
# WEB_PRODEJE POLOŽKY - API endpoint pro modul "Prodejny - Položky"
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def web_prodeje_polozky_view(request):
    """
    API endpoint pro modul 'Prodejny - Položky' - čte přímo z tabulky WEB_PRODEJE_ALL
    """
    
    try:
        # Získání parametrů (nové + staré pro zpětnou kompatibilitu)
        period = request.GET.get('period', 'custom')  # daily, weekly, monthly, monthly_select, custom
        selected_month = request.GET.get('selected_month')  # Formát: YYYY-MM
        start_date = request.GET.get('start_date')  # Formát: YYYY-MM-DD
        end_date = request.GET.get('end_date')      # Formát: YYYY-MM-DD
        
        # Staré parametry pro zpětnou kompatibilitu
        data_type = request.GET.get('type', 'daily')  # daily nebo monthly
        target_date = request.GET.get('date')  # pro historická data (YYYY-MM-DD)
        
        from stores.models import Prodejna
        prodejny_map = {p.id: p.nazev for p in Prodejna.objects.all()}
        
        # Test databázového připojení
        try:
            # Zkusíme základní dotaz na WEB_PRODEJE_ALL
            queryset = WebProdejeAll.objects.all()
            count = queryset.count()
            print(f"🔍 WEB_PRODEJE_ALL celkem: {count} záznamů")
            
            if count == 0:
                # Fallback na mock data
                data_list = [
                    {
                        'id_prodejce': 1,
                        'prodejce': 'Mock Prodejce',
                        'prodejna': 'Mock Prodejna',
                        'polozky_nad_100': 10,
                        'sluzby_celkem': 2,
                        'pol_dok': 1.5,
                        'ct300': 1,
                        'ct600': 0,
                        'ct1200': 0,
                        'akt': 0,
                        'zah250': 0,
                        'nap': 1,
                        'zah500': 0,
                        'kop250': 0,
                        'kop500': 0,
                        'pz1': 0,
                        'knz': 0,
                        'sklicka': 0,
                        'lepeni': 0,
                        'aligator': 0
                    }
                ]
                return Response({
                    'success': True,
                    'data': data_list,
                    'count': len(data_list),
                    'lastUpdate': datetime.now().isoformat(),
                    'period': period,
                    'selected_month': selected_month,
                    'source': 'WEB_PRODEJE_ALL (mock - no data)',
                    'message': 'Žádná data v tabulce WEB_PRODEJE_ALL'
                })
            
            # Filtrování podle období
            today = date.today()
            
            # Nová logika pro selected_month
            if period == 'monthly_select' and selected_month:
                try:
                    # selected_month je ve formátu YYYY-MM
                    year, month = selected_month.split('-')
                    start_date = date(int(year), int(month), 1)
                    # Poslední den měsíce
                    if int(month) == 12:
                        end_date = date(int(year) + 1, 1, 1) - timedelta(days=1)
                    else:
                        end_date = date(int(year), int(month) + 1, 1) - timedelta(days=1)
                    
                    queryset = queryset.filter(
                        typ__gte=start_date.strftime('%Y-%m-%d'),
                        typ__lte=end_date.strftime('%Y-%m-%d')
                    )
                    print(f"🔍 Filtr měsíce: {selected_month} ({start_date} až {end_date})")
                except Exception as e:
                    print(f"❌ Chyba při parsování selected_month: {e}")
            # Stará logika pro target_date (zpětná kompatibilita)
            elif target_date:
                if data_type == 'daily':
                    queryset = queryset.filter(typ=target_date)
                else:  # monthly
                    year_month = target_date[:7]  # YYYY-MM
                    queryset = queryset.filter(typ__startswith=year_month)
            # Vlastní období
            elif start_date and end_date:
                queryset = queryset.filter(
                    typ__gte=start_date,
                    typ__lte=end_date
                )
            else:
                # Pro dnešní data
                today_str = today.strftime('%Y-%m-%d')
                queryset = queryset.filter(typ=today_str)
            
            print(f"🔍 Po filtru data: {queryset.count()} záznamů")
            
            # ⚡ OPTIMALIZACE: Jeden agregační dotaz místo N dotazů na prodejce
            from django.db.models import Case, When, Value, IntegerField, CharField
            
            # Agregujeme data pro všechny prodejce najednou (GROUP BY id_prodejce)
            agregace = queryset.filter(
                id_prodejce__isnull=False
            ).values('id_prodejce').annotate(
                # 1. Položky nad 100 Kč (suma Pocet_kusu, bez dopravného)
                polozky_nad_100=Sum(
                    'pocet_kusu',
                    filter=Q(cena_ks_vcl_dph__gte=100) & Q(kod__isnull=False) & ~Q(kod=''),
                    default=0
                ),
                # 2. Služby podle kódů
                ct300=Count('id', filter=Q(kod='P114194')),
                ct600=Count('id', filter=Q(kod='CT600')),
                ct1200=Count('id', filter=Q(kod='CT1200')),
                akt=Count('id', filter=Q(kod='AKT')),
                zah250=Count('id', filter=Q(kod='ZAH250')),
                nap=Count('id', filter=Q(kod__in=['NAP', 'NAN'])),
                zah500=Count('id', filter=Q(kod='ZAH500')),
                kop250=Count('id', filter=Q(kod='KOP250')),
                kop500=Count('id', filter=Q(kod='KOP500')),
                pz1=Count('id', filter=Q(kod='PZ1')),
                knz=Count('id', filter=Q(kod='KNZ')),
                # 3. SUNSHINE
                sunshine=Count('id', filter=Q(nazev__icontains='SUNSHINE')),
                # 4. Sklíčka a Lepení
                sklicka=Count('id', filter=Q(kategorie_1='Skla a fólie')),
                lepeni=Count('id', filter=Q(kod='LOS')),
                # 5. Položky nad 29 Kč (bez dopravného - stejná logika jako v profilu)
                polozky_nad_29=Count('id', filter=Q(cena_ks_vcl_dph__gte=29) & Q(kod__isnull=False) & ~Q(kod='')),
                # 6. Pomocné hodnoty pro výpočet unikátních dokladů
                prvni_stredisko=Max('stredisko')  # Pro fallback prodejna
            ).order_by('-polozky_nad_100')[:20]  # Top 20 prodejců
            
            print(f"🔍 Agregovaná data pro {len(agregace)} prodejců")
            
            # ⚡ VÝKUPY: Agregujeme výkupy pro stejné období a prodejce
            # Sloupec `vystaveno` v WEB_VYKUPY odpovídá `typ` v WEB_PRODEJE_ALL
            vykupy_qs = WebVykupy.objects.all()
            if period == 'monthly_select' and selected_month:
                vykupy_qs = vykupy_qs.filter(vystaveno__gte=start_date, vystaveno__lte=end_date)
            elif target_date:
                if data_type == 'daily':
                    vykupy_qs = vykupy_qs.filter(vystaveno=target_date)
                else:
                    vykupy_qs = vykupy_qs.filter(vystaveno__startswith=target_date[:7])
            elif start_date and end_date:
                vykupy_qs = vykupy_qs.filter(vystaveno__gte=start_date, vystaveno__lte=end_date)
            else:
                vykupy_qs = vykupy_qs.filter(vystaveno=today.strftime('%Y-%m-%d'))

            vykupy_agregace = vykupy_qs.values('id_prodejce').annotate(
                pocet_vykupu=Sum('pocet_kusů', default=0)
            )
            vykupy_map = {v['id_prodejce']: v['pocet_vykupu'] for v in vykupy_agregace if v['id_prodejce'] is not None}
            
            # Načteme všechny prodejce najednou (místo N dotazů)
            prodejci_ids = [p['id_prodejce'] for p in agregace]
            users_dict = {
                u.id: u 
                for u in WebUser.objects.filter(id__in=prodejci_ids)
            }
            
            # Výpočet unikátních dokladů pro každého prodejce (rychlejší než v smyčce)
            doklady_cache = {}
            for prodejce_id in prodejci_ids:
                prodejce_qs = queryset.filter(id_prodejce=prodejce_id)
                doklady_cache[prodejce_id] = _count_unique_receipts(prodejce_qs)
            
            # Sestavíme výsledná data
            data_list = []
            for agg_data in agregace:
                prodejce_id = agg_data['id_prodejce']
                
                # Získáme jméno prodejce z cache
                if prodejce_id in users_dict:
                    user = users_dict[prodejce_id]
                    prodejce_jmeno = f"{user.jmeno} {user.prijmeni}".strip()
                    # Namapujeme ID prodejny na název
                    p_id = getattr(user, 'prodejna_id', None)
                    prodejna_nazev = prodejny_map.get(p_id, str(p_id)) if p_id else 'Neznámá'
                else:
                    prodejce_jmeno = f"Prodejce {prodejce_id}"
                    prodejna_nazev = agg_data.get('prvni_stredisko', 'Neznámá')
                
                # Výpočet služeb celkem
                sluzby_celkem = (
                    agg_data['ct300'] + agg_data['ct600'] + agg_data['ct1200'] +
                    agg_data['akt'] + agg_data['zah250'] + agg_data['nap'] +
                    agg_data['zah500'] + agg_data['kop250'] + agg_data['kop500'] +
                    agg_data['pz1'] + agg_data['knz']
                )
                
                # Výpočet průměru položek na doklad
                unikatni_doklady = doklady_cache.get(prodejce_id, 0)
                prumer_polozek = round(
                    agg_data['polozky_nad_29'] / unikatni_doklady, 2
                ) if unikatni_doklady > 0 else 0
                
                data_list.append({
                    'id_prodejce': prodejce_id,
                    'prodejce': prodejce_jmeno,
                    'prodejna': str(prodejna_nazev),
                    'polozky_nad_100': agg_data['polozky_nad_100'],
                    'sluzby_celkem': sluzby_celkem,
                    'sunshine': agg_data['sunshine'],
                    'pol_dok': prumer_polozek,
                    'polozky_nad_29': agg_data['polozky_nad_29'],
                    'unikatni_doklady': unikatni_doklady,
                    'ct300': agg_data['ct300'],
                    'ct600': agg_data['ct600'],
                    'ct1200': agg_data['ct1200'],
                    'akt': agg_data['akt'],
                    'zah250': agg_data['zah250'],
                    'nap': agg_data['nap'],
                    'zah500': agg_data['zah500'],
                    'kop250': agg_data['kop250'],
                    'kop500': agg_data['kop500'],
                    'pz1': agg_data['pz1'],
                    'knz': agg_data['knz'],
                    'sklicka': agg_data['sklicka'],
                    'lepeni': agg_data['lepeni'],
                    'vykupy': vykupy_map.get(prodejce_id, 0),
                    'aligator': 0
                })
            
            # Seřazení podle počtu položek nad 100 Kč (sestupně)
            data_list.sort(key=lambda x: x['polozky_nad_100'], reverse=True)
                
            return Response({
                'success': True,
                'data': data_list,
                'count': len(data_list),
                'lastUpdate': datetime.now().isoformat(),
                'dataType': data_type,
                'date': target_date,
                'source': 'WEB_PRODEJE_ALL'
            })
            
        except Exception as db_error:
            print(f"❌ Databázová chyba: {db_error}")
            # Fallback na mock data
            data_list = [
                {
                    'id_prodejce': 999,
                    'prodejce': 'Error Fallback',
                    'prodejna': 'DB Error',
                    'polozky_nad_100': 0,
                    'sluzby_celkem': 0,
                    'pol_dok': 0.0,
                    'ct300': 0,
                    'ct600': 0,
                    'ct1200': 0,
                    'akt': 0,
                    'zah250': 0,
                    'nap': 0,
                    'zah500': 0,
                    'kop250': 0,
                    'kop500': 0,
                    'pz1': 0,
                    'knz': 0,
                    'sklicka': 0,
                    'lepeni': 0,
                    'aligator': 0
                }
            ]
            return Response({
                'success': True,
                'data': data_list,
                'count': len(data_list),
                'lastUpdate': datetime.now().isoformat(),
                'dataType': data_type,
                'date': target_date,
                'source': 'WEB_PRODEJE_ALL (fallback)',
                'error': str(db_error)
            })
        
    except Exception as e:
        print(f"❌ Obecná chyba: {e}")
        return Response({
            'success': False,
            'error': str(e),
            'data': [],
            'count': 0
        }, status=500)


# =============================================================================
# WEB_PRODEJE - Profil prodejce (Můj profil)
# =============================================================================

@require_http_methods(["GET"])
@permission_classes([AllowAny])
def web_prodeje_salesperson_today(request):
    """Denní souhrn + porovnání průměru s poslední směnou (WEB_PRODEJE_ALL)"""
    user_id = request.GET.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'Chybí user_id parametr'}, status=400)

    try:
        today_iso = date.today().strftime('%Y-%m-%d')
        queryset = WebProdejeAll.objects.filter(id_prodejce=user_id, typ=today_iso)
        result = _aggregate_web_prodeje_all_salesperson(queryset, user_id, today_iso)

        # poslední směna = poslední den s daty před dneškem
        prev_rec = (
            WebProdejeAll.objects.filter(id_prodejce=user_id, typ__lt=today_iso)
            .order_by('-typ')
            .first()
        )
        if prev_rec:
            prev_date = str(prev_rec.typ)[:10]
            prev_qs = WebProdejeAll.objects.filter(id_prodejce=user_id, typ=prev_date)
            prev = _aggregate_web_prodeje_all_salesperson(prev_qs, user_id, prev_date)
            result['compare'] = {
                'previous_date': prev_date,
                'previous_avg': prev.get('prumer_polozek_uctu', 0),
                'delta_avg': round(result.get('prumer_polozek_uctu', 0) - prev.get('prumer_polozek_uctu', 0), 2)
            }

        result['source'] = 'database'
        _attach_servisni_prace(result, user_id, typ_exact=today_iso)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e), 'source': 'error'}, status=500)


@require_http_methods(["GET"])
@permission_classes([AllowAny])
def web_prodeje_salesperson_monthly(request):
    """Měsíční souhrn + porovnání průměru s minulým měsícem (WEB_PRODEJE_ALL)"""
    user_id = request.GET.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'Chybí user_id parametr'}, status=400)

    try:
        today = date.today()
        ym = today.strftime('%Y-%m')
        queryset = WebProdejeAll.objects.filter(id_prodejce=user_id, typ__startswith=ym)
        result = _aggregate_web_prodeje_all_salesperson(queryset, user_id, f"{ym}-01")

        prev_month = (today.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        prev_qs = WebProdejeAll.objects.filter(id_prodejce=user_id, typ__startswith=prev_month)
        prev = _aggregate_web_prodeje_all_salesperson(prev_qs, user_id, f"{prev_month}-01")
        result['compare'] = {
            'previous_month': prev_month,
            'previous_avg': prev.get('prumer_polozek_uctu', 0),
            'delta_avg': round(result.get('prumer_polozek_uctu', 0) - prev.get('prumer_polozek_uctu', 0), 2)
        }

        result['source'] = 'database'
        _attach_servisni_prace(result, user_id, typ_month_prefix=ym)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e), 'source': 'error'}, status=500)


@require_http_methods(["GET"])
@permission_classes([AllowAny])
def web_prodeje_salesperson_points_today(request):
    """Denní body + porovnání s poslední směnou pro konkrétního prodejce z tabulky WEB_PRODEJE_ALL"""
    user_id = request.GET.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'Chybí user_id parametr'}, status=400)

    try:
        today_iso = date.today().strftime('%Y-%m-%d')
        today_qs = WebProdejeAll.objects.filter(id_prodejce=user_id, typ=today_iso)
        base = _aggregate_web_prodeje_all_salesperson(today_qs, user_id, today_iso)
        product_points = calculate_points_for_data(base)
        servis_points, servis_data = _servis_points_for_user_id(user_id, typ_exact=today_iso)
        total_points = product_points + servis_points

        # poslední den se záznamy (minulá směna)
        last_rec = (
            WebProdejeAll.objects.filter(id_prodejce=user_id, typ__lt=today_iso)
            .order_by('-typ')
            .first()
        )
        compare = None
        if last_rec:
            prev_date = str(last_rec.typ)[:10]
            prev_qs = WebProdejeAll.objects.filter(id_prodejce=user_id, typ=prev_date)
            prev_base = _aggregate_web_prodeje_all_salesperson(prev_qs, user_id, prev_date)
            prev_product_points = calculate_points_for_data(prev_base)
            prev_servis_points, _ = _servis_points_for_user_id(user_id, typ_exact=prev_date)
            prev_points = prev_product_points + prev_servis_points
            compare = {
                'previous_date': prev_date,
                'previous_points': prev_points,
                'delta_points': total_points - prev_points,
            }

        payload = _build_points_payload(base, total_points, 'database', servis_data=servis_data, servis_points=servis_points)
        if compare:
            payload['compare'] = compare
        return JsonResponse(payload)
    except Exception as e:
        return JsonResponse({'error': str(e), 'source': 'error', 'total_points': 0}, status=500)


@require_http_methods(["GET"])
@permission_classes([AllowAny])
def web_prodeje_salesperson_points_monthly(request):
    """Měsíční body + porovnání s minulým měsícem pro konkrétního prodejce (WEB_PRODEJE_ALL)"""
    user_id = request.GET.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'Chybí user_id parametr'}, status=400)

    try:
        today = date.today()
        ym = today.strftime('%Y-%m')
        queryset = WebProdejeAll.objects.filter(id_prodejce=user_id, typ__startswith=ym)
        base = _aggregate_web_prodeje_all_salesperson(queryset, user_id, f"{ym}-01")
        product_points = calculate_points_for_data(base)
        servis_points, servis_data = _servis_points_for_user_id(user_id, typ_month_prefix=ym)
        total_points = product_points + servis_points

        # minulý měsíc
        prev_month = (today.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        prev_qs = WebProdejeAll.objects.filter(id_prodejce=user_id, typ__startswith=prev_month)
        prev_base = _aggregate_web_prodeje_all_salesperson(prev_qs, user_id, f"{prev_month}-01")
        prev_product_points = calculate_points_for_data(prev_base)
        prev_servis_points, _ = _servis_points_for_user_id(user_id, typ_month_prefix=prev_month)
        prev_points = prev_product_points + prev_servis_points

        payload = _build_points_payload(base, total_points, 'database', servis_data=servis_data, servis_points=servis_points)
        payload['compare'] = {
            'previous_month': prev_month,
            'previous_points': prev_points,
            'delta_points': total_points - prev_points,
        }
        return JsonResponse(payload)
    except Exception as e:
        return JsonResponse({'error': str(e), 'source': 'error', 'total_points': 0}, status=500)


def _aggregate_web_prodeje_all_salesperson(queryset, user_id, iso_date):
    """Vypočítá metriky pro daný queryset a uživatele.
    Vrací dict kompatibilní s ProfileAnalytics kartami.
    """
    # Bez záznamů → prázdná data
    if queryset.count() == 0:
        return {
            'date': iso_date,
            'prodejna': 'Prodejna',
            'prodejce': f'Prodejce {user_id}',
            'id_prodejce': int(user_id),
            'polozky_nad_100': 0,
            'sluzby_celkem': 0,
            'pol_dok': 0.0,
            'ct300': 0,
            'ct600': 0,
            'ct1200': 0,
            'akt': 0,
            'zah250': 0,
            'nap': 0,
            'zah500': 0,
            'kop250': 0,
            'kop500': 0,
            'pz1': 0,
            'knz': 0,
            'aligator': 0,
        }

    # Základní info
    try:
        user = WebUser.objects.get(id=user_id)
        prodejce_jmeno = f"{user.jmeno} {user.prijmeni}".strip()
    except Exception:
        prodejce_jmeno = f"Prodejce {user_id}"

    # Vynecháváme dopravné (položky bez kódu), počítáme podle Pocet_kusu
    polozky_nad_100 = queryset.filter(cena_ks_vcl_dph__gte=100).exclude(kod__isnull=True).exclude(kod='').aggregate(total=Sum('pocet_kusu', default=0))['total'] or 0

    # Služby
    ct300 = queryset.filter(kod='P114194').count()
    ct600 = queryset.filter(kod='CT600').count()
    ct1200 = queryset.filter(kod='CT1200').count()
    akt = queryset.filter(kod='AKT').count()
    zah250 = queryset.filter(kod='ZAH250').count()
    nap = queryset.filter(kod__in=['NAP', 'NAN']).count()
    zah500 = queryset.filter(kod='ZAH500').count()
    kop250 = queryset.filter(kod='KOP250').count()
    kop500 = queryset.filter(kod='KOP500').count()
    pz1 = queryset.filter(kod='PZ1').count()
    knz = queryset.filter(kod='KNZ').count()

    sluzby_celkem = (
        ct300 + ct600 + ct1200 + akt + zah250 + nap + zah500 + kop250 + kop500 + pz1 + knz
    )

    # Průměr položek/účtu: počet položek s cenou ≥ 29 Kč / počet unikátních dokladů
    # Odfiltrujeme prázdné/NULL doklady, aby se počítaly pouze platné účtenky
    polozky_nad_29 = queryset.filter(cena_ks_vcl_dph__gte=29).exclude(_excluded_names_q()).count()
    unikatni_doklady = _count_unique_receipts(queryset)
    prumer_polozek = round(polozky_nad_29 / unikatni_doklady, 2) if unikatni_doklady else 0

    return {
        'date': iso_date,
        'prodejna': 'Prodejna',
        'prodejce': prodejce_jmeno,
        'id_prodejce': int(user_id),
        'polozky_nad_100': polozky_nad_100,
        'sluzby_celkem': sluzby_celkem,
        'pol_dok': prumer_polozek,
        'prumer_polozek_uctu': prumer_polozek,  # alias pro FE kompatibilitu
        'ct300': ct300,
        'ct600': ct600,
        'ct1200': ct1200,
        'akt': akt,
        'zah250': zah250,
        'nap': nap,
        'zah500': zah500,
        'kop250': kop250,
        'kop500': kop500,
        'pz1': pz1,
        'knz': knz,
        'aligator': 0,
    }


def _build_points_payload(base_data, total_points, source, servis_data=None, servis_points=0):
    """Sestaví payload pro body včetně breakdownu"""
    breakdown = {
        'polozky_nad_100': {'count': base_data.get('polozky_nad_100', 0), 'points': base_data.get('polozky_nad_100', 0) * 15},
        'ct300': {'count': base_data.get('ct300', 0), 'points': base_data.get('ct300', 0) * 15},
        'ct600': {'count': base_data.get('ct600', 0), 'points': base_data.get('ct600', 0) * 50},
        'ct1200': {'count': base_data.get('ct1200', 0), 'points': base_data.get('ct1200', 0) * 100},
        'akt': {'count': base_data.get('akt', 0), 'points': base_data.get('akt', 0) * 30},
        'zah250': {'count': base_data.get('zah250', 0), 'points': base_data.get('zah250', 0) * 30},
        'nap': {'count': base_data.get('nap', 0), 'points': base_data.get('nap', 0) * 50},
        'zah500': {'count': base_data.get('zah500', 0), 'points': base_data.get('zah500', 0) * 50},
        'kop250': {'count': base_data.get('kop250', 0), 'points': base_data.get('kop250', 0) * 30},
        'kop500': {'count': base_data.get('kop500', 0), 'points': base_data.get('kop500', 0) * 50},
        'pz1': {'count': base_data.get('pz1', 0), 'points': base_data.get('pz1', 0) * 100},
        'knz': {'count': base_data.get('knz', 0), 'points': base_data.get('knz', 0) * 30},
        'aligator': {'count': base_data.get('aligator', 0), 'points': 0},
    }
    if servis_data is not None:
        breakdown['servis_marze'] = {
            'marze': servis_data.get('marze', 0),
            'odmena_sazba': servis_data.get('odmena_sazba', SERVIS_ODMENA_SAZBA),
            'points': servis_points,
        }

    return {
        'date': base_data.get('date'),
        'prodejna': base_data.get('prodejna'),
        'prodejce': base_data.get('prodejce'),
        'id_prodejce': base_data.get('id_prodejce'),
        'total_points': total_points,
        'breakdown': breakdown,
        'source': source,
    }


# =============================================================================
# WEB_PRODEJE - Leaderboardy (měsíční)
# =============================================================================

@require_http_methods(["GET"])
@permission_classes([AllowAny])
def web_prodeje_leaderboard_points(request):
    """Žebříček prodejců podle bodů za aktuální měsíc (WEB_PRODEJE_ALL)
    Rozšířeno: přidává last_month_points = celkové body za minulý měsíc.
    OPTIMALIZOVÁNO: Používá agregační dotaz místo smyček (10-50x rychlejší).
    """
    try:
        ym = date.today().strftime('%Y-%m')
        month_queryset = WebProdejeAll.objects.filter(typ__startswith=ym)

        # Vypočítej období pro minulý měsíc (YYYY-MM)
        today = date.today()
        first_of_month = today.replace(day=1)
        prev_month_last_day = first_of_month - timedelta(days=1)
        prev_ym = prev_month_last_day.strftime('%Y-%m')
        prev_month_queryset = WebProdejeAll.objects.filter(typ__startswith=prev_ym)

        # ===== AKTUÁLNÍ MĚSÍC - JEDEN AGREGAČNÍ DOTAZ =====
        current_aggregation = month_queryset.filter(id_prodejce__isnull=False).values('id_prodejce').annotate(
            polozky_nad_100=Sum('pocet_kusu', filter=Q(cena_ks_vcl_dph__gte=100) & ~Q(kod__isnull=True) & ~Q(kod='')),
            ct300=Count('id', filter=Q(kod='P114194')),
            ct600=Count('id', filter=Q(kod='CT600')),
            ct1200=Count('id', filter=Q(kod='CT1200')),
            akt=Count('id', filter=Q(kod='AKT')),
            zah250=Count('id', filter=Q(kod='ZAH250')),
            nap=Count('id', filter=Q(kod__in=['NAP', 'NAN'])),
            zah500=Count('id', filter=Q(kod='ZAH500')),
            kop250=Count('id', filter=Q(kod='KOP250')),
            kop500=Count('id', filter=Q(kod='KOP500')),
            pz1=Count('id', filter=Q(kod='PZ1')),
            knz=Count('id', filter=Q(kod='KNZ')),
            polozky_nad_29=Count('id', filter=Q(cena_ks_vcl_dph__gte=29) & Q(kod__isnull=False) & ~Q(kod='')),
            prodejna_nazev=Max('stredisko'),
        )

        # ===== PŘEDCHOZÍ MĚSÍC - JEDEN AGREGAČNÍ DOTAZ =====
        prev_aggregation = prev_month_queryset.filter(id_prodejce__isnull=False).values('id_prodejce').annotate(
            prev_polozky_nad_100=Sum('pocet_kusu', filter=Q(cena_ks_vcl_dph__gte=100) & ~Q(kod__isnull=True) & ~Q(kod='')),
            prev_ct300=Count('id', filter=Q(kod='P114194')),
            prev_ct600=Count('id', filter=Q(kod='CT600')),
            prev_ct1200=Count('id', filter=Q(kod='CT1200')),
            prev_akt=Count('id', filter=Q(kod='AKT')),
            prev_zah250=Count('id', filter=Q(kod='ZAH250')),
            prev_nap=Count('id', filter=Q(kod__in=['NAP', 'NAN'])),
            prev_zah500=Count('id', filter=Q(kod='ZAH500')),
            prev_kop250=Count('id', filter=Q(kod='KOP250')),
            prev_kop500=Count('id', filter=Q(kod='KOP500')),
            prev_pz1=Count('id', filter=Q(kod='PZ1')),
            prev_knz=Count('id', filter=Q(kod='KNZ')),
        )

        # Převést předchozí měsíc na slovník pro rychlé vyhledávání
        prev_data = {item['id_prodejce']: item for item in prev_aggregation}

        # Načíst všechny uživatele najednou (místo N dotazů)
        prodejci_ids = [item['id_prodejce'] for item in current_aggregation]
        users = {u.id: u for u in WebUser.objects.filter(id__in=prodejci_ids)}

        leaderboard = []

        for item in current_aggregation:
            prodejce_id = item['id_prodejce']
            
            # Jméno a prodejna
            user = users.get(prodejce_id)
            if user:
                prodejce_jmeno = f"{user.jmeno} {user.prijmeni}".strip()
                prodejna_nazev = item['prodejna_nazev'] or str(getattr(user, 'prodejna_id', 'Neznámá'))
            else:
                prodejce_jmeno = f"Prodejce {prodejce_id}"
                prodejna_nazev = item['prodejna_nazev'] or 'Neznámá'

            # Unikátní doklady - ZJEDNODUŠENO: pouze distinct na sloupec Doklad (místo 4 sloupců)
            seller_qs = month_queryset.filter(id_prodejce=prodejce_id)
            unikatni_doklady = (
                seller_qs.exclude(doklad__isnull=True)
                        .exclude(doklad='')
                        .values('doklad')
                        .distinct()
                        .count()
            )
            prumer = round((item['polozky_nad_29'] or 0) / unikatni_doklady, 2) if unikatni_doklady else 0

            # Body aktuálního měsíce
            total_points = calculate_points_for_data({
                'polozky_nad_100': item['polozky_nad_100'] or 0,
                'ct300': item['ct300'] or 0,
                'ct600': item['ct600'] or 0,
                'ct1200': item['ct1200'] or 0,
                'akt': item['akt'] or 0,
                'zah250': item['zah250'] or 0,
                'nap': item['nap'] or 0,
                'zah500': item['zah500'] or 0,
                'kop250': item['kop250'] or 0,
                'kop500': item['kop500'] or 0,
                'pz1': item['pz1'] or 0,
                'knz': item['knz'] or 0,
                'aligator': 0,
            })

            # Body minulého měsíce
            prev_item = prev_data.get(prodejce_id, {})
            if prev_item:
                last_month_points = calculate_points_for_data({
                    'polozky_nad_100': prev_item.get('prev_polozky_nad_100') or 0,
                    'ct300': prev_item.get('prev_ct300') or 0,
                    'ct600': prev_item.get('prev_ct600') or 0,
                    'ct1200': prev_item.get('prev_ct1200') or 0,
                    'akt': prev_item.get('prev_akt') or 0,
                    'zah250': prev_item.get('prev_zah250') or 0,
                    'nap': prev_item.get('prev_nap') or 0,
                    'zah500': prev_item.get('prev_zah500') or 0,
                    'kop250': prev_item.get('prev_kop250') or 0,
                    'kop500': prev_item.get('prev_kop500') or 0,
                    'pz1': prev_item.get('prev_pz1') or 0,
                    'knz': prev_item.get('prev_knz') or 0,
                    'aligator': 0,
                })
            else:
                last_month_points = 0

            leaderboard.append({
                'id': int(prodejce_id),
                'prodejce': prodejce_jmeno,
                'prodejna': str(prodejna_nazev),
                'total_points': total_points,
                'last_month_points': last_month_points,
                'polozky_nad_100': item['polozky_nad_100'] or 0,
                'prumer_polozek_uctu': prumer,
            })

        # Seřadit desc podle bodů a přidat pozice
        leaderboard.sort(key=lambda x: x['total_points'], reverse=True)
        for idx, item in enumerate(leaderboard):
            item['position'] = idx + 1

        return JsonResponse({
            'success': True,
            'data': leaderboard,
            'count': len(leaderboard),
            'month': int(date.today().strftime('%m')),
            'year': int(date.today().strftime('%Y')),
            'type': 'points',
            'source': 'WEB_PRODEJE_ALL'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e), 'data': []}, status=500)


@require_http_methods(["GET"])
@permission_classes([AllowAny])
def web_prodeje_leaderboard_average_items(request):
    """Žebříček prodejců podle průměru položek/účtenka za aktuální měsíc (WEB_PRODEJE_ALL)
    OPTIMALIZOVÁNO: Používá agregační dotaz místo smyček (10-50x rychlejší).
    """
    try:
        ym = date.today().strftime('%Y-%m')
        month_queryset = WebProdejeAll.objects.filter(typ__startswith=ym)

        # Globální agregace pro správný celofiremní průměr
        global_polozky_nad_29 = month_queryset.filter(cena_ks_vcl_dph__gte=29).exclude(_excluded_names_q()).count()
        global_unikatni_doklady = _count_unique_receipts(month_queryset)
        global_prumer = round(global_polozky_nad_29 / global_unikatni_doklady, 2) if global_unikatni_doklady else 0

        # ===== JEDEN AGREGAČNÍ DOTAZ PRO VŠECHNY PRODEJCE =====
        aggregation = month_queryset.filter(id_prodejce__isnull=False).values('id_prodejce').annotate(
            polozky_nad_100=Sum('pocet_kusu', filter=Q(cena_ks_vcl_dph__gte=100) & ~Q(kod__isnull=True) & ~Q(kod='')),
            polozky_nad_29=Count('id', filter=Q(cena_ks_vcl_dph__gte=29) & Q(kod__isnull=False) & ~Q(kod='')),
            ct300=Count('id', filter=Q(kod='P114194')),
            ct600=Count('id', filter=Q(kod='CT600')),
            ct1200=Count('id', filter=Q(kod='CT1200')),
            akt=Count('id', filter=Q(kod='AKT')),
            zah250=Count('id', filter=Q(kod='ZAH250')),
            nap=Count('id', filter=Q(kod__in=['NAP', 'NAN'])),
            zah500=Count('id', filter=Q(kod='ZAH500')),
            kop250=Count('id', filter=Q(kod='KOP250')),
            kop500=Count('id', filter=Q(kod='KOP500')),
            pz1=Count('id', filter=Q(kod='PZ1')),
            knz=Count('id', filter=Q(kod='KNZ')),
            prodejna_nazev=Max('stredisko'),
        )

        # Načíst všechny uživatele najednou (místo N dotazů)
        prodejci_ids = [item['id_prodejce'] for item in aggregation]
        users = {u.id: u for u in WebUser.objects.filter(id__in=prodejci_ids)}

        leaderboard = []

        for item in aggregation:
            prodejce_id = item['id_prodejce']
            
            # Jméno a prodejna
            user = users.get(prodejce_id)
            if user:
                prodejce_jmeno = f"{user.jmeno} {user.prijmeni}".strip()
                prodejna_nazev = getattr(user, 'prodejna_id', 'Neznámá')
            else:
                prodejce_jmeno = f"Prodejce {prodejce_id}"
                prodejna_nazev = item['prodejna_nazev'] or 'Neznámá'

            # Unikátní doklady - ponecháno jako individuální dotaz (optimalizace distinct je komplikovaná)
            seller_qs = month_queryset.filter(id_prodejce=prodejce_id)
            unikatni_doklady = _count_unique_receipts(seller_qs)
            prumer = round((item['polozky_nad_29'] or 0) / unikatni_doklady, 2) if unikatni_doklady else 0

            # Body pro info v kartách
            total_points = calculate_points_for_data({
                'polozky_nad_100': item['polozky_nad_100'] or 0,
                'ct300': item['ct300'] or 0,
                'ct600': item['ct600'] or 0,
                'ct1200': item['ct1200'] or 0,
                'akt': item['akt'] or 0,
                'zah250': item['zah250'] or 0,
                'nap': item['nap'] or 0,
                'zah500': item['zah500'] or 0,
                'kop250': item['kop250'] or 0,
                'kop500': item['kop500'] or 0,
                'pz1': item['pz1'] or 0,
                'knz': item['knz'] or 0,
                'aligator': 0,
            })

            leaderboard.append({
                'id': int(prodejce_id),
                'prodejce': prodejce_jmeno,
                'prodejna': str(prodejna_nazev),
                'prumer_polozek_uctu': prumer,
                'polozky_nad_100': item['polozky_nad_100'] or 0,
                'total_points': total_points,
            })

        # Řazení desc podle průměru
        leaderboard.sort(key=lambda x: x['prumer_polozek_uctu'], reverse=True)
        for idx, item in enumerate(leaderboard):
            item['position'] = idx + 1

        return JsonResponse({
            'success': True,
            'data': leaderboard,
            'count': len(leaderboard),
            'month': int(date.today().strftime('%m')),
            'year': int(date.today().strftime('%Y')),
            'type': 'average_items',
            'source': 'WEB_PRODEJE_ALL',
            'meta': {
                'global_polozky_nad_29': global_polozky_nad_29,
                'global_unikatni_doklady': global_unikatni_doklady,
                'global_average': global_prumer,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e), 'data': []}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def debug_servis_rozdil_view(request):
    """
    DEBUG endpoint: Najde položky, které způsobují rozdíl mezi celkovým obratem servisu a součtem typů servisu
    """
    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        period = request.GET.get('period', 'custom')
        prodejna_id = request.GET.get('prodejna_id')

        # Stejná logika filtrování jako v servis_data_view
        base_servis_q = (
            Q(objednavku_zalozil__icontains='servis eda') &
            Q(k_servisu='ANO')
        )
        base_queryset = WebProdejeAll.objects.filter(base_servis_q)
        
        # Aplikuj datumové filtry
        if period != 'custom':
            today = date.today()
            if period == 'daily':
                start_date = today
                end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1)
                end_date = today

        if start_date:
            try:
                start_date_parsed = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                base_queryset = base_queryset.filter(typ__gte=start_date_parsed.strftime('%Y-%m-%d'))
            except:
                pass

        if end_date:
            try:
                end_date_parsed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                end_upper = (end_date_parsed + timedelta(days=1)).strftime('%Y-%m-%d')
                base_queryset = base_queryset.filter(typ__lt=end_upper)
            except:
                pass

        if prodejna_id:
            base_queryset = base_queryset.filter(id_prodejny=prodejna_id)

        # Najdi položky, které JSOU v celkovém servisu, ale NEJSOU v typech servisu
        navic_polozky_qs = base_queryset.exclude(kategorie__icontains='!Servis')
        
        # Agregace pro "navíc" položky
        navic_agg = navic_polozky_qs.aggregate(
            obrat_bez_dph=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
            polozky=Count('id'),
            kusy=Sum('pocet_kusu')
        )

        # Seznam konkrétních položek (max 50 pro ukázku)
        navic_items = list(navic_polozky_qs.values(
            'objednavka', 'nazev', 'kod', 'kategorie', 'kategorie_1', 'kategorie_2',
            'objednavku_zalozil', 'k_servisu', 'cena_ks_bez_dph', 'pocet_kusu',
            'stredisko'
        ).order_by('-cena_ks_bez_dph')[:50])
        
        # Rozklad podle toho, proč se položky počítají do celkového servisu
        servis_eda_count = navic_polozky_qs.filter(objednavku_zalozil__icontains='servis eda').count()
        k_servisu_ano_count = navic_polozky_qs.filter(k_servisu='ANO').count()
        
        return JsonResponse({
            'success': True,
            'navic_agregace': {
                'obrat_bez_dph': float(navic_agg['obrat_bez_dph'] or 0),
                'polozky': navic_agg['polozky'] or 0,
                'kusy': navic_agg['kusy'] or 0,
            },
            'duvody': {
                'servis_eda_polozky': servis_eda_count,
                'k_servisu_ano_polozky': k_servisu_ano_count,
            },
            'priklad_polozek': navic_items,
            'meta': {
                'celkem_navic': navic_polozky_qs.count(),
                'generated_at': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def servis_typ_items_view(request):
    """
    Vrátí seznam položek (nazev, objednavka) pro konkrétní typ servisu podle kategorie_1:
    Respektuje period/start_date/end_date, prodejna_id/stredisko a volitelný limit (default 100).
    """

    try:
        typ_servisu = request.GET.get('typ_servisu')  # hodnota kategorie_1
        if not typ_servisu:
            return JsonResponse({'success': False, 'error': 'Chybí parametr typ_servisu'}, status=400)

        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        period = request.GET.get('period', 'custom')
        prodejna_id = request.GET.get('prodejna_id')
        stredisko = request.GET.get('stredisko')
        limit = int(request.GET.get('limit', '100'))

        # Základní filtr pro servis - stejný jako v servis_data_view
        base_servis_q = (
            Q(objednavku_zalozil__icontains='servis eda') &
            Q(k_servisu='ANO')
        )
        qs = WebProdejeAll.objects.filter(base_servis_q).filter(kategorie__icontains='!Servis')
        
        # Filtr podle kategorie_1 (typ servisu)
        qs = qs.filter(kategorie_1=typ_servisu)
        
        if prodejna_id:
            qs = qs.filter(id_prodejny=prodejna_id)
        if stredisko:
            qs = qs.filter(stredisko=stredisko)

        if period != 'custom':
            today = date.today()
            if period == 'daily':
                start_date = today
                end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1)
                end_date = today

        if start_date:
            try:
                sd = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                qs = qs.filter(typ__gte=sd.strftime('%Y-%m-%d'))
            except:
                pass
        if end_date:
            try:
                ed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                end_upper = (ed + timedelta(days=1)).strftime('%Y-%m-%d')
                qs = qs.filter(typ__lt=end_upper)
            except:
                pass

        items = (
            qs.order_by('-typ')
              .values('objednavka', 'nazev', 'kod', 'cena_ks_bez_dph', 'pocet_kusu', 'stredisko')[:max(1, min(limit, 1000))]
        )

        return JsonResponse({
            'success': True,
            'items': list(items),
            'count': qs.count(),
            'typ_servisu': typ_servisu
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e), 'items': []}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def zasilkovna_detail_view(request):
    """
    Endpoint pro detailní rozpad Zásilkovna dat podle prodejen a měsíců
    Vrací:
    - celkove_provize: celková suma provizí
    - pocet_prodejen: počet unikátních prodejen
    - pocet_mesicu: počet měsíců v datech
    - prodejny: agregace podle prodejen
    - mesice: seznam všech záznamů po měsících a prodejnách
    """
    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        period = request.GET.get('period', 'custom')
        selected_month = request.GET.get('selected_month')
        prodejna_id = request.GET.get('prodejna_id')
        
        # Základní queryset
        qs = WebZasilkovna.objects.all()
        
        # Datumové filtry
        if period != 'custom' and period != 'monthly_select':
            today = date.today()
            if period == 'daily':
                start_date = today
                end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1)
                end_date = today
        elif period == 'monthly_select' and selected_month:
            try:
                y, m = selected_month.split('-')
                start_date = date(int(y), int(m), 1)
                if int(m) == 12:
                    end_date = date(int(y) + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(int(y), int(m) + 1, 1) - timedelta(days=1)
            except Exception:
                pass
        
        if start_date:
            try:
                start_parsed = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                qs = qs.filter(
                    rok__gte=start_parsed.year
                ).filter(
                    Q(rok__gt=start_parsed.year) | Q(mesic__gte=start_parsed.month)
                )
            except Exception:
                pass
        
        if end_date:
            try:
                end_parsed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                qs = qs.filter(
                    rok__lte=end_parsed.year
                ).filter(
                    Q(rok__lt=end_parsed.year) | Q(mesic__lte=end_parsed.month)
                )
            except Exception:
                pass
        
        # Filtrování podle prodejny
        if prodejna_id:
            qs = qs.filter(id_prodejna=prodejna_id)
        
        # Agregace podle prodejen
        prodejny = qs.values('prodejna', 'id_prodejna').annotate(
            celkove_provize=Sum('celkove_provize_mesic', default=0),
            za_zpracovani=Sum('za_zpracovani', default=0),
            za_vyber_dobirky=Sum('za_vyber_dobirky', default=0),
            ostatni_provize=Sum('ostatni_provize', default=0),
            pocet_mesicu=Count('id')
        ).order_by('-celkove_provize')
        
        # Seznam všech záznamů po měsících
        mesice = qs.values(
            'rok', 'mesic', 'prodejna', 'id_prodejna'
        ).annotate(
            provize=Sum('celkove_provize_mesic', default=0),
            za_zpracovani=Sum('za_zpracovani', default=0),
            za_vyber_dobirky=Sum('za_vyber_dobirky', default=0),
            ostatni_provize=Sum('ostatni_provize', default=0)
        ).order_by('-rok', '-mesic', 'prodejna')
        
        # Celková agregace
        celkem_agg = qs.aggregate(
            celkove_provize=Sum('celkove_provize_mesic', default=0),
            pocet_zaznamu=Count('id')
        )
        
        # Počet unikátních prodejen a měsíců
        pocet_prodejen = qs.values('id_prodejna').distinct().count()
        pocet_mesicu = qs.values('rok', 'mesic').distinct().count()
        
        # Konverze Decimal na float
        def convert_decimals(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert_decimals(item) for item in obj]
            return obj
        
        # Přidání názvu s aliasem pro prodejny
        prodejny_list = convert_decimals(list(prodejny))
        for p in prodejny_list:
            p['nazev'] = p.get('prodejna', '')
            p['nazev_plny'] = p.get('prodejna', '')
            # Přiřazení barvy podle prodejny
            barvy = {
                'SENIMO': '#e74c3c',
                'GLOBUS': '#3498db',
                'PREROV': '#27ae60',
                'ZLIN': '#9b59b6',
                'VSETIN': '#f39c12',
                'STERNBERK': '#2ecc71'
            }
            # Najdi zkratku prodejny v názvu
            p['barva'] = '#0066cc'  # default
            for zkratka, barva in barvy.items():
                if zkratka.lower() in p['prodejna'].lower():
                    p['barva'] = barva
                    break
        
        # Přidání názvu s aliasem pro měsíce
        mesice_list = convert_decimals(list(mesice))
        for m in mesice_list:
            m['nazev'] = m.get('prodejna', '')
            m['nazev_plny'] = m.get('prodejna', '')
        
        return JsonResponse({
            'success': True,
            'celkove_provize': float(celkem_agg['celkove_provize'] or 0),
            'pocet_prodejen': pocet_prodejen,
            'pocet_mesicu': pocet_mesicu,
            'prodejny': prodejny_list,
            'mesice': mesice_list
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Chyba při zpracování Zásilkovna dat: {str(e)}'
        }, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def celkova_servis_detail_view(request):
    """
    Detail kanálu SERVIS – rozklad podle typů servisu
    Vrací agregovaná data podle kategorie_1 (typ servisu)
    """
    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        period = request.GET.get('period', 'custom')
        selected_month = request.GET.get('selected_month')
        prodejna_id = request.GET.get('prodejna_id')
        
        # Základní queryset pro SERVIS
        qs = WebProdejeAll.objects.filter(
            Q(objednavku_zalozil__icontains='servis eda') & Q(k_servisu='ANO')
        )
        
        # Datumové filtry
        if period != 'custom' and period != 'monthly_select':
            today = date.today()
            if period == 'daily':
                start_date = today
                end_date = today
            elif period == 'weekly':
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == 'monthly':
                start_date = today.replace(day=1)
                end_date = today
        elif period == 'monthly_select' and selected_month:
            try:
                y, m = selected_month.split('-')
                start_date = date(int(y), int(m), 1)
                if int(m) == 12:
                    end_date = date(int(y) + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(int(y), int(m) + 1, 1) - timedelta(days=1)
            except Exception:
                pass
        
        if start_date:
            try:
                start_parsed = parse_date(start_date).date() if isinstance(start_date, str) else start_date
                qs = qs.filter(typ__gte=start_parsed.strftime('%Y-%m-%d'))
            except Exception:
                pass
        
        if end_date:
            try:
                end_parsed = parse_date(end_date).date() if isinstance(end_date, str) else end_date
                end_upper = (end_parsed + timedelta(days=1)).strftime('%Y-%m-%d')
                qs = qs.filter(typ__lt=end_upper)
            except Exception:
                pass
        
        # Filtrování podle prodejny
        if prodejna_id:
            qs = qs.filter(id_prodejny=prodejna_id)
        
        # Agregace podle prodejen (stredisko)
        prodejny = qs.values('stredisko', 'id_prodejny').annotate(
            obrat=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
            marze=Sum(F('pocet_kusu') * F('zisk'), default=0),
            polozky=Count('id'),
            doklady=Count('doklad', distinct=True)
        ).order_by('-obrat')
        
        # Celková agregace
        celkem_agg = qs.aggregate(
            celkovy_obrat=Sum(F('pocet_kusu') * F('cena_ks_bez_dph'), default=0),
            celkova_marze=Sum(F('pocet_kusu') * F('zisk'), default=0),
            celkem_polozky=Count('id'),
            celkem_doklady=Count('doklad', distinct=True)
        )
        
        # Konverze Decimal na float
        def convert_decimals(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert_decimals(item) for item in obj]
            return obj
        
        # Přidání barev pro prodejny
        prodejny_list = convert_decimals(list(prodejny))
        barvy = ['#e74c3c', '#3498db', '#27ae60', '#9b59b6', '#f39c12', '#2ecc71', '#1abc9c', '#34495e']
        for i, prodejna in enumerate(prodejny_list):
            prodejna['barva'] = barvy[i % len(barvy)]
            prodejna['nazev'] = prodejna.get('stredisko', 'Nezařazeno')
            prodejna['nazev_plny'] = prodejna.get('stredisko', 'Nezařazeno')
        
        return JsonResponse({
            'success': True,
            'celkovy_obrat': float(celkem_agg['celkovy_obrat'] or 0),
            'celkova_marze': float(celkem_agg['celkova_marze'] or 0),
            'celkem_polozky': celkem_agg['celkem_polozky'],
            'celkem_doklady': celkem_agg['celkem_doklady'],
            'prodejny': prodejny_list
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Chyba při zpracování SERVIS dat: {str(e)}'
        }, status=500)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def webhook_monthly_stats(request):
    """
    Webhook endpoint pro získání měsíčních statistik firmy
    URL: /api/analytics/webhook/monthly-stats/
    """
    try:
        # SQL dotaz pro měsíční statistiky
        sql_query = """
        SELECT 
            SUM(pocet_kusu * cena_ks_bez_dph) as celkovy_obrat_bez_dph,
            SUM(pocet_kusu * cena_ks_vcl_dph) as celkovy_obrat_s_dph,
            SUM(pocet_kusu * zisk) as celkovy_zisk,
            COUNT(*) as pocet_polozek,
            COUNT(DISTINCT doklad) as pocet_dokladu,
            ROUND(AVG(pocet_kusu * cena_ks_bez_dph), 2) as prumerny_obrat_na_polozku
        FROM WEB_PRODEJE_ALL 
        WHERE 
            YEAR(Vystaveno) = YEAR(CURDATE()) 
            AND MONTH(Vystaveno) = MONTH(CURDATE())
            AND cena_ks_bez_dph IS NOT NULL 
            AND cena_ks_bez_dph > 0
        """
        
        # Spuštění SQL dotazu
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            result = cursor.fetchone()
            
            if result:
                # Zpracování výsledku
                data = {
                    'success': True,
                    'datum': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'obdobi': f'{datetime.now().year}-{datetime.now().month:02d}',
                    'statistiky': {
                        'celkovy_obrat_bez_dph': float(result[0]) if result[0] else 0,
                        'celkovy_obrat_s_dph': float(result[1]) if result[1] else 0,
                        'celkovy_zisk': float(result[2]) if result[2] else 0,
                        'pocet_polozek': int(result[3]) if result[3] else 0,
                        'pocet_dokladu': int(result[4]) if result[4] else 0,
                        'prumerny_obrat_na_polozku': float(result[5]) if result[5] else 0
                    }
                }
                
                # Formátování čísel pro lepší čitelnost
                formatted_stats = {}
                for key, value in data['statistiky'].items():
                    if isinstance(value, (int, float)) and value > 1000:
                        formatted_stats[f'{key}_formatted'] = f"{value:,.0f}".replace(',', ' ')
                
                # Přidání formátovaných hodnot
                data['statistiky'].update(formatted_stats)
                
                return JsonResponse(data, status=200)
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Žádná data nenalezena pro aktuální měsíc'
                }, status=404)
                
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Chyba při zpracování dat: {str(e)}'
        }, status=500)


# =============================================================================
# STORE TRAFFIC ANALYTICS (NOVÝ MODUL "PRODEJNY & ZÁKAZNÍCI")
# =============================================================================

@method_decorator(permission_classes([AllowAny]), name='dispatch')
class StoreTrafficView(View):
    """
    Nový endpoint pro modul "Prodejny & Zákazníci".
    Poskytuje data o návštěvnosti (unikátní doklady/účtenky).
    """

    def get(self, request):
        try:
            print(f"DEBUG REQUEST GET: {request.GET}")
            # Parametry
            date_from = request.GET.get('date_from')
            date_to = request.GET.get('date_to')
            stredisko = request.GET.get('stredisko')

            # Validace datumů
            try:
                if date_from:
                    d1 = datetime.strptime(date_from, '%Y-%m-%d').date()
                else:
                    d1 = date.today().replace(day=1)
                    date_from = d1.strftime('%Y-%m-%d')
                    
                if date_to:
                    d2 = datetime.strptime(date_to, '%Y-%m-%d').date()
                else:
                    d2 = date.today()
                    date_to = d2.strftime('%Y-%m-%d')
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Neplatný formát data (očekáváno YYYY-MM-DD)'}, status=400)

            # Srovnávací období (volitelné)
            s_d1, s_d2 = None, None
            s_date_from = request.GET.get('s_date_from')
            s_date_to = request.GET.get('s_date_to')
            
            if s_date_from and s_date_to:
                try:
                    s_d1 = datetime.strptime(s_date_from, '%Y-%m-%d').date()
                    s_d2 = datetime.strptime(s_date_to, '%Y-%m-%d').date()
                except ValueError:
                    # Pokud je srovnávací období vadné, ignorujeme ho (nebo můžeme vrátit 400)
                    s_date_from, s_date_to = None, None

            # Granularita grafu (daily/hourly)
            granularity = request.GET.get('granularity', 'daily')

            # Base QuerySet
            qs = WebProdejeAll.objects.exclude(
                Q(doklad__isnull=True) & Q(objednavka__isnull=True)
            )
            
            # Filtrování podle střediska
            if stredisko:
                qs = qs.filter(stredisko=stredisko)

            # --- 1. PRIMÁRNÍ DATA ---
            qs_primary = qs.filter(typ__gte=date_from, typ__lte=date_to)
            
            unique_doc = Coalesce('doklad', 'objednavka')
            
            # Celková návštěvnost
            total_visits = qs_primary.aggregate(
                visits=Count(unique_doc, distinct=True)
            )['visits'] or 0

            # Denní průměr (z počtu dní v rozsahu)
            days_count = (d2 - d1).days + 1
            daily_avg = total_visits / days_count if days_count > 0 else 0

            # Graf (Timeline)
            timeline_data = []
            if granularity == 'hourly':
                # Seskupení po hodinách (datum + hodina) - Python zpracování
                 timeline_qs = (
                     qs_primary
                     .annotate(
                         p_date=F('typ'), 
                         p_time=F('cas_prodeje')
                     )
                     .values('p_date', 'p_time')
                     .annotate(visits=Count(unique_doc, distinct=True))
                 )
                 
                 # Agregace v Pythonu (protože cas_prodeje může být různé)
                 timeline_agg = defaultdict(int) 
                 for item in timeline_qs:
                     d = item['p_date']
                     t = item['p_time']
                     v = item['visits']
                     
                     if not t: # Skip if time is missing
                         continue
                         
                     h = 0
                     try:
                         if hasattr(t, 'hour'): 
                             h = t.hour
                         elif isinstance(t, str): 
                             h = int(t.split(':')[0])
                     except:
                         continue # Skip invalid time formats
                     
                     key = f"{d} {h:02d}:00"
                     timeline_agg[key] += v
                 
                 timeline_data = [{'date': k, 'visits': v} for k, v in sorted(timeline_agg.items())]
            else:
                # Daily fallback
                timeline_qs = (
                    qs_primary
                    .values('typ')
                    .annotate(visits=Count(unique_doc, distinct=True))
                    .order_by('typ')
                )
                for item in timeline_qs:
                    if item['typ']: # Ensure date is present
                        timeline_data.append({
                            'date': item['typ'],
                            'visits': item['visits']
                        })

            # Heatmap / Stats (Den v týdnu x Hodina)
            # Problém: ExtractHour nefunguje na TimeField v této verzi Django/MySQL
            # Řešení: Načteme data a zpracujeme v Pythonu
            
            # Načteme všechny relevantní záznamy s časem
            heatmap_records = list(
                qs_primary
                .exclude(cas_prodeje__isnull=True)
                .annotate(weekday=ExtractWeekDay('typ'))
                .values('weekday', 'cas_prodeje', 'doklad', 'objednavka')
            )
            
            # Spočítáme počet výskytů každého dne v týdnu v období
            weekday_counts = {i: 0 for i in range(1, 8)}
            curr = d1
            while curr <= d2:
                iso = curr.isoweekday()
                dj_wd = (iso % 7) + 1
                weekday_counts[dj_wd] += 1
                curr += timedelta(days=1)
            
            # Agregace v Pythonu: (weekday, hour) -> set unikátních dokladů
            heatmap_agg = defaultdict(set)
            for record in heatmap_records:
                wd = record['weekday']
                time_val = record['cas_prodeje']
                doc = record.get('doklad') or record.get('objednavka')
                
                if not wd or not time_val or not doc:
                    continue
                
                # Extrahujeme hodinu z času
                if hasattr(time_val, 'hour'):
                    hour = time_val.hour
                elif isinstance(time_val, str):
                    try:
                        hour = int(time_val.split(':')[0])
                    except:
                        continue
                else:
                    continue
                
                heatmap_agg[(wd, hour)].add(doc)
            
            # Vytvoříme výsledná data s průměry
            heatmap_data = []
            for (wd, hour), docs in heatmap_agg.items():
                count_days = weekday_counts.get(wd, 1)
                visits_count = len(docs)
                avg = visits_count / count_days if count_days > 0 else 0
                
                heatmap_data.append({
                    'weekday': wd, # 1=Sun...7=Sat
                    'hour': hour,
                    'visits_total': visits_count,
                    'visits_avg': round(avg, 1)
                })
            
            # --- 2. SROVNÁVACÍ DATA ---
            comparison = None
            if s_date_from and s_date_to:
                qs_comp = qs.filter(typ__gte=s_date_from, typ__lte=s_date_to)
                comp_visits = qs_comp.aggregate(
                    visits=Count(unique_doc, distinct=True)
                )['visits'] or 0
                
                diff = 0
                if comp_visits > 0:
                    diff = ((total_visits - comp_visits) / comp_visits) * 100
                elif total_visits > 0:
                    # Pokud srovnání je 0 a my máme návštěvy, je to "nekonečný" nárůst, dáme 100% (nebo null)
                    diff = 100 
                
                comparison = {
                    'visits': comp_visits,
                    'diff_percent': round(diff, 1)
                }

            # Seznam dostupných prodejen pro filtr
            # Získáme unikátní názvy středisek z celé tabulky (nebo za poslední rok pro rychlost)
            # Pro optimalizaci můžeme omezit, ale stredisko by nemělo mít moc variant.
            available_stores = list(
                WebProdejeAll.objects
                .exclude(stredisko__isnull=True)
                .exclude(stredisko='')
                .values_list('stredisko', flat=True)
                .distinct()
                .order_by('stredisko')
            )

            # Result construction
            # Note: The provided snippet uses 'visits_diff' which is not defined in the original code.
            # Assuming 'visits_diff' should be 'comparison' and 'daily_avg' should be rounded as before.
            # Also, the 'meta' field from the original response is re-added.
            result = {
                'success': True,
                'summary': {
                    'total_visits': total_visits,
                    'daily_avg': round(daily_avg, 1), # Kept original rounding logic
                },
                'available_stores': available_stores,
                'comparison': comparison, # Used 'comparison' as defined in the original code
                'timeline': list(timeline_data),
                'heatmap': heatmap_data,
                'meta': { # Re-added meta field
                    'days_count': days_count,
                    'weekday_counts': weekday_counts
                }
            }

            return JsonResponse(result)

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({'success': False, 'error': str(e)}, status=500)