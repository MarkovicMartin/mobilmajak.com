"""
Management command pro přenos dat z active_company_access do WEB_PRISTUPY_PRODEJNY
"""

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from web_pristupy.models import WEB_PRISTUPY_PRODEJNY

class Command(BaseCommand):
    help = 'Přenese data z tabulky active_company_access do WEB_PRISTUPY_PRODEJNY'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Pouze simuluje přenos bez zápisu do databáze',
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Vymaže existující záznamy v cílové tabulce před přenosem',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        clear_existing = options['clear_existing']
        
        self.stdout.write("🔄 Zahajuji přenos dat z active_company_access do WEB_PRISTUPY_PRODEJNY...")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️  DRY RUN MODE - žádné změny nebudou provedeny"))
        
        try:
            with transaction.atomic():
                # Kontrola zdrojové tabulky
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM active_company_access")
                    source_count = cursor.fetchone()[0]
                    
                    if source_count == 0:
                        self.stdout.write(self.style.ERROR("❌ Zdrojová tabulka active_company_access je prázdná"))
                        return
                    
                    self.stdout.write(f"📊 Nalezeno {source_count} záznamů ve zdrojové tabulce")
                
                # Vymazání existujících dat (pokud je požadováno)
                if clear_existing and not dry_run:
                    deleted_count = WEB_PRISTUPY_PRODEJNY.objects.count()
                    WEB_PRISTUPY_PRODEJNY.objects.all().delete()
                    self.stdout.write(f"🗑️  Smazáno {deleted_count} existujících záznamů")
                
                # Načtení dat ze zdrojové tabulky
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            id, company_name, website_url, username, password, 
                            category, store, description, notes, added_by, 
                            last_used, is_active, created_at, updated_at
                        FROM active_company_access 
                        ORDER BY store, company_name
                    """)
                    
                    rows = cursor.fetchall()
                    
                if not dry_run:
                    # Přenos dat
                    created_objects = []
                    for row in rows:
                        (id, company_name, website_url, username, password, 
                         category, store, description, notes, added_by, 
                         last_used, is_active, created_at, updated_at) = row
                        
                        # Vytvoření nového objektu
                        new_access = WEB_PRISTUPY_PRODEJNY(
                            company_name=company_name or "",
                            website_url=website_url or "",
                            username=username or "",
                            password=password or "",
                            category=category or "",
                            store=store or "",
                            description=description or "",
                            notes=notes or "",
                            added_by=added_by or "",
                            last_used=last_used,
                            is_active=bool(is_active),
                            created_at=created_at,
                            updated_at=updated_at
                        )
                        created_objects.append(new_access)
                    
                    # Bulk create pro rychlejší vložení
                    WEB_PRISTUPY_PRODEJNY.objects.bulk_create(created_objects)
                    
                    self.stdout.write(f"✅ Úspěšně přeneseno {len(created_objects)} záznamů")
                else:
                    self.stdout.write(f"🔍 Bylo by přeneseno {len(rows)} záznamů")
                
                # Kontrola výsledku
                if not dry_run:
                    final_count = WEB_PRISTUPY_PRODEJNY.objects.count()
                    self.stdout.write(f"📊 Celkový počet záznamů v cílové tabulce: {final_count}")
                    
                    # Statistiky podle prodejen
                    stores_stats = WEB_PRISTUPY_PRODEJNY.get_all_stores()
                    self.stdout.write("🏪 Rozdělení podle prodejen:")
                    for store_stat in stores_stats:
                        self.stdout.write(f"   - {store_stat['store']}: {store_stat['count']} přístupů")
                
                self.stdout.write(self.style.SUCCESS("🎉 Přenos dat byl úspěšně dokončen!"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba během přenosu dat: {str(e)}"))
            raise 