"""
Nastavení mzda_zaklad, mzda_doplnky a mzda_cestovne dle vzorové tabulky Květen 26.

Variabilní složka → mzda_doplnky (počítá se do přesčasu/dovolené).
Cestovné → mzda_cestovne (mimo přesčas i dovolenou).
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from users.mzda_utils import normalize_mzda_doplnky
from users.models import WebUser

# Základ + variabilní složka + cestovné (body/měsíc) dle Google Sheet „Květen 26“
SHEET_PROFILES = {
    'Valenta': {'zaklad': 14000, 'variabilni': 5000, 'cestovne': 0},
    'Létal': {'zaklad': 14000, 'variabilni': 2000, 'cestovne': 0},
    'Gabriel': {'zaklad': 14000, 'variabilni': 4000, 'cestovne': 0},
    'Valčík': {'zaklad': 14000, 'variabilni': 2000, 'cestovne': 2300},
    'Králik': {'zaklad': 14000, 'variabilni': 2000, 'cestovne': 2300},
    'Karas': {'zaklad': 14000, 'variabilni': 2000, 'cestovne': 0},
    'Kováčik': {'zaklad': 14000, 'variabilni': 4000, 'cestovne': 0},
    'Babušík': {'zaklad': 14000, 'variabilni': 2000, 'cestovne': 0},
    'Kolarčík': {'zaklad': 14000, 'variabilni': 4000, 'cestovne': 2300},
    'Krumpolc': {'zaklad': 14000, 'variabilni': 2000, 'cestovne': 0},
    'Hekele': {'zaklad': 14000, 'variabilni': 5000, 'cestovne': 0},
    'Vychodil': {'zaklad': 17000, 'variabilni': 0, 'cestovne': 0},
}


def _doplnky_for_variabilni(castka):
    if not castka:
        return []
    return normalize_mzda_doplnky([{
        'kod': 'variabilni_slozka',
        'nazev': 'Variabilní složka',
        'castka': castka,
    }])


class Command(BaseCommand):
    help = 'Nastaví mzdu dle vzorové tabulky Květen 26 (základ + variabilní + cestovné).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Jen vypsat změny')

    def handle(self, *args, **options):
        dry = options['dry_run']
        updated = 0
        missing = []

        for prijmeni, prof in SHEET_PROFILES.items():
            user = (
                WebUser.objects.filter(prijmeni=prijmeni, aktivni=True)
                .exclude(role='ADMIN')
                .first()
            )
            if not user:
                missing.append(prijmeni)
                continue

            zaklad = Decimal(str(prof['zaklad']))
            cestovne = Decimal(str(prof.get('cestovne') or 0))
            doplnky = _doplnky_for_variabilni(prof.get('variabilni') or 0)

            old = (
                f'zaklad={user.mzda_zaklad} doplnky={user.mzda_doplnky} '
                f'cestovne={user.mzda_cestovne}'
            )
            new = f'zaklad={zaklad} doplnky={doplnky} cestovne={cestovne}'

            if old == new:
                self.stdout.write(f'  {prijmeni}: beze změny')
                continue

            self.stdout.write(f'  {prijmeni}: {old} -> {new}')
            if not dry:
                user.mzda_zaklad = zaklad
                user.mzda_doplnky = doplnky
                user.mzda_cestovne = cestovne
                user.save(update_fields=['mzda_zaklad', 'mzda_doplnky', 'mzda_cestovne'])
            updated += 1

        if missing:
            self.stdout.write(self.style.WARNING(f'Nenalezeno: {", ".join(missing)}'))
        suffix = ' (dry-run)' if dry else ''
        self.stdout.write(self.style.SUCCESS(f'Hotovo: {updated} uživatelů aktualizováno{suffix}'))
