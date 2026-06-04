"""
Sloučí kategorii OSTATNI do PRISLUSENSTVI_OSTATNI (Zbytek) v uložených plánech.

Příklad – červen až prosinec 2026 + přepočet prodejců:
  python manage.py sloucit_ostatni_zbytek --rok 2026 --od-mesice 6 --prepocet-prodejci

Dry-run:
  python manage.py sloucit_ostatni_zbytek --rok 2026 --od-mesice 6 --dry-run
"""
from django.core.management.base import BaseCommand

from plans.plan_kategorie_ops import sloucit_ostatni_obdobi
from plans.prodejci_prepocet import prepocet_prodejci_mesice


class Command(BaseCommand):
    help = 'Sloučí OSTATNI do Zbytku v plánech (prodejna + prodejci).'

    def add_arguments(self, parser):
        parser.add_argument('--rok', type=int, required=True)
        parser.add_argument('--od-mesice', type=int, default=6)
        parser.add_argument('--do-mesice', type=int, default=12)
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument(
            '--prepocet-prodejci',
            action='store_true',
            help='Po sloučení spustit přepočet přiřazení prodejců podle směn',
        )

    def handle(self, *args, **options):
        rok = options['rok']
        od_m = options['od_mesice']
        do_m = options['do_mesice']
        dry = options['dry_run']

        vysledky = sloucit_ostatni_obdobi(rok, od_m, do_m, dry_run=dry)
        for v in vysledky:
            if v.get('skipped'):
                self.stdout.write(f"  {v['mesic']:02d}/{rok}: přeskočeno ({v.get('reason')})")
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  {v['mesic']:02d}/{rok}: prodejny={v['prodejny']}, "
                        f"prodejci={v['prodejci_radky']}"
                        + (' [dry-run]' if dry else '')
                    )
                )

        if dry or not options['prepocet_prodejci']:
            return

        mesice = [(rok, m) for m in range(od_m, do_m + 1)]
        pr = prepocet_prodejci_mesice(mesice)
        self.stdout.write(self.style.SUCCESS(f"Přepočet prodejců: {pr['pocet_prepocet']} měsíců."))
