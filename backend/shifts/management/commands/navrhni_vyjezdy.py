"""Denní návrh směn na jiné prodejně (poslední den měsíce, cíl +2)."""

from datetime import date

from django.core.management.base import BaseCommand

from shifts.vyjezd import dopln_vyjezdy, due_months


class Command(BaseCommand):
    help = 'Založí návrhy výjezdů pro měsíc, který se navrhuje dnes (nebo --mesic).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mesic',
            type=str,
            default=None,
            help='Jeden měsíc YYYY-MM mimo automatické okno.',
        )

    def handle(self, *args, **options):
        raw = options.get('mesic')
        if raw:
            parts = raw.strip().split('-')
            if len(parts) != 2:
                self.stderr.write('Neplatný formát --mesic (očekáváno YYYY-MM).')
                return
            targets = [(int(parts[0]), int(parts[1]))]
        else:
            targets = due_months(date.today())
            if not targets:
                self.stdout.write('Dnes se návrh nezakládá.')
                return

        for rok, mesic in targets:
            result = dopln_vyjezdy(rok, mesic)
            self.stdout.write(
                f'{mesic}/{rok}: nových návrhů {result["vytvoreno"]} '
                f'({len(result["uzivatele"])} prodejců).'
            )
            if result['vytvoreno']:
                self.stdout.write(self.style.SUCCESS(f'Návrh {mesic}/{rok} založen.'))
