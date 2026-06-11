"""Dry-run porovnání legacy vs nové rozdělení SERVIS plánu."""
import json

from django.core.management.base import BaseCommand

from plans.prodejci_auto import porovnej_servis_rozdeleni
from stores.models import Prodejna


class Command(BaseCommand):
    help = 'Porovná legacy a nové SERVIS podíly pro prodejnu/měsíc (bez zápisu do DB).'

    def add_arguments(self, parser):
        parser.add_argument('--rok', type=int, required=True)
        parser.add_argument('--mesic', type=int, required=True)
        parser.add_argument('--prodejna', type=str, default='Globus', help='Název nebo ID prodejny')

    def handle(self, *args, **options):
        prodejna_arg = options['prodejna']
        if str(prodejna_arg).isdigit():
            prodejna = Prodejna.objects.get(id=int(prodejna_arg))
        else:
            prodejna = Prodejna.objects.get(nazev=prodejna_arg)

        report = porovnej_servis_rozdeleni(options['rok'], options['mesic'], prodejna.id)
        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
