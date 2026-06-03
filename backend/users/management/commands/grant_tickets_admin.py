"""
Přidá modul tickets_admin uživateli (správa ticketů bez role ADMIN).

Příklad:
  python manage.py grant_tickets_admin markovic
"""
from django.core.management.base import BaseCommand, CommandError

from users.models import WebUser


class Command(BaseCommand):
    help = 'Udělí uživateli modul tickets_admin (správa a úprava ticketů)'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Uživatelské jméno (login)')

    def handle(self, *args, **options):
        username = (options['username'] or '').strip()
        if not username:
            raise CommandError('Zadejte uživatelské jméno.')

        user = WebUser.objects.filter(uzivatelske_jmeno__iexact=username).first()
        if not user:
            raise CommandError(f'Uživatel "{username}" nenalezen.')

        moduly = list(user.moduly or [])
        if 'tickets_admin' in moduly:
            self.stdout.write(self.style.WARNING(
                f'{user.uzivatelske_jmeno} už má modul tickets_admin.'
            ))
            return

        moduly.append('tickets_admin')
        user.moduly = moduly
        user.save(update_fields=['moduly'])
        self.stdout.write(self.style.SUCCESS(
            f'Modul tickets_admin přidán uživateli {user.uzivatelske_jmeno} '
            f'({user.jmeno} {user.prijmeni}).'
        ))
