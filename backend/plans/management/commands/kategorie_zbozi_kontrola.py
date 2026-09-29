"""Ověří odškrtnuté kategorie zboží proti Sympliu. Cron 23:30."""
from django.core.management.base import BaseCommand

from plans.kategorie_zbozi_noc import spustit


class Command(BaseCommand):
    help = 'Noční kontrola odškrtnutých P kódů a připsání bodu za plánovací kategorii.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Spustit i přes otevírací dobu a bez čekání na locky actorů.',
        )

    def handle(self, *args, **options):
        spustit(stdout=self.stdout, force=bool(options['force']))
