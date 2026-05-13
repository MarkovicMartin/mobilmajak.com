"""
Management command pro přidání modulu 'access' všem existujícím uživatelům
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import WebUser

class Command(BaseCommand):
    help = 'Přidá modul "access" všem existujícím uživatelům'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Pouze simuluje přidání bez zápisu do databáze',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write("🔧 Přidávám modul 'access' všem uživatelům...")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️  DRY RUN MODE - žádné změny nebudou provedeny"))
        
        try:
            with transaction.atomic():
                # Získej všechny uživatele
                users = WebUser.objects.all()
                
                if not users.exists():
                    self.stdout.write(self.style.WARNING("⚠️  Žádní uživatelé nenalezeni"))
                    return
                
                updated_count = 0
                already_has_count = 0
                
                for user in users:
                    # Inicializuj moduly pokud jsou None nebo prázdné
                    if user.moduly is None:
                        user.moduly = []
                    
                    # Zkontroluj zda už modul 'access' má
                    if 'access' not in user.moduly:
                        user.moduly.append('access')
                        if not dry_run:
                            user.save()
                        updated_count += 1
                        self.stdout.write(f"✅ Přidán modul 'access' uživateli: {user.uzivatelske_jmeno} ({user.jmeno} {user.prijmeni})")
                    else:
                        already_has_count += 1
                        self.stdout.write(f"ℹ️  Uživatel {user.uzivatelske_jmeno} už má modul 'access'")
                
                # Souhrn
                self.stdout.write(f"\n📊 Souhrn:")
                self.stdout.write(f"   - Celkem uživatelů: {users.count()}")
                self.stdout.write(f"   - Aktualizováno: {updated_count}")
                self.stdout.write(f"   - Už mělo modul: {already_has_count}")
                
                if dry_run:
                    self.stdout.write(self.style.WARNING("\n⚠️  DRY RUN - žádné změny nebyly provedeny"))
                    # Rollback transakce v dry-run módu
                    transaction.set_rollback(True)
                else:
                    self.stdout.write(self.style.SUCCESS(f"\n🎉 Modul 'access' byl úspěšně přidán {updated_count} uživatelům!"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chyba při přidávání modulu: {str(e)}"))
            raise 