"""
Vyplní technik_id v WEB_USERS podle jména a příjmení.
Stejná logika jako migrace 0010_populate_technik_id.
Spustit: python manage.py populate_technik_id
"""
from django.core.management.base import BaseCommand
from users.models import WebUser

# ID -> (jmeno, prijmeni) - techniciMap z actoru + 4 doplněné
MAPPING = [
    (78, 'Miroslav', 'Hoza'),
    (96, 'Martin', 'Šimek'),
    (101, 'Martin', 'Markovič'),
    (102, 'Hugo', 'Šedlbauer'),
    (103, 'Radek', 'Bulandra'),
    (105, 'Jiří', 'Stolín'),
    (106, 'Jakub', 'Šmolc'),
    (108, 'Šimon', 'Erbes'),
    (109, 'Nikol', 'Dostálová'),
    (110, 'Ondřej', 'Půlpábek'),
    (111, 'Lukáš', 'Kováčik'),
    (116, 'Šimon', 'Gabriel'),
    (117, 'Šimon', 'Bílek'),
    (118, 'Tomáš', 'Valenta'),
    (121, 'František', 'Vychodil'),
    (125, 'Adam', 'Kolarčík'),
    (126, 'Aplikace', 'MyRepair.app'),
    (135, 'Karolína', 'Macková'),
    (148, 'Benny', 'Babušík'),
    (153, 'Tomáš', 'Doležal'),
    (156, 'Patrik', 'Šebák'),
    (157, 'Štěpán', 'Kundera'),
    (167, 'Adéla', 'Koldová'),
    (177, 'Jakub', 'Králík'),
    (178, 'Barbora', 'Ludvigová'),
    (216, 'Lukáš', 'Krumpolc'),
    (231, 'Jiří', 'Pohořelský'),
    (238, 'Kuba', 'Málek'),
    (240, 'Jakub', 'Málek'),
    (261, 'Jan', 'Létal'),
    (268, 'Šimon', 'Kosev'),
    (270, 'Jan', 'Šnyrych'),
    (271, 'Brigádník', 'Majákovský'),
    (290, 'Marek', 'Pich'),
    (314, 'Daniel', 'Mahďák'),
    (317, 'David', 'Valčík'),
    (323, 'Monika', 'Křížková'),
    (336, 'Lukáš', 'Hekele'),
]


class Command(BaseCommand):
    help = 'Vyplní technik_id v WEB_USERS podle jména a příjmení (mapování z actoru).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Pouze vypíše změny, nic neuloží.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        updated = 0
        for technik_id, jmeno, prijmeni in MAPPING:
            qs = WebUser.objects.filter(jmeno=jmeno, prijmeni=prijmeni)
            count = qs.count()
            if count:
                if not dry_run:
                    qs.update(technik_id=technik_id)
                self.stdout.write(f'  {jmeno} {prijmeni} → technik_id={technik_id} ({count} řádků)')
                updated += count
        if dry_run:
            self.stdout.write(self.style.WARNING(f'Dry-run: bylo by aktualizováno {updated} uživatelů.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'technik_id: aktualizováno {updated} uživatelů.'))
