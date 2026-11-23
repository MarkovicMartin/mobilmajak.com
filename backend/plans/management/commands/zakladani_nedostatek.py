"""Zápis nedostatku z týdenního zakládání karet. Cron se nenasazuje."""
from django.core.management.base import BaseCommand, CommandError

from plans.models import ZakladaniNedostatek
from plans.zakladani import NeplatnyNedostatek, zapis_nedostatek


class Command(BaseCommand):
    help = (
        'Zapíše nedostatek, který týdenní zakládání nemůže poznamenat ve Sympliu. '
        'Stejný otevřený kód a typ se nezdvojuje.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--kod', required=True)
        parser.add_argument(
            '--typ',
            required=True,
            choices=[kod for kod, _nazev in ZakladaniNedostatek.TYP_CHOICES],
        )
        parser.add_argument('--text', required=True)
        parser.add_argument('--nazev', default='')
        parser.add_argument('--zbozi-id', type=int, default=None)

    def handle(self, *args, **options):
        try:
            row, novy = zapis_nedostatek(
                kod=options['kod'],
                typ=options['typ'],
                text=options['text'],
                nazev=options['nazev'],
                zbozi_id=options['zbozi_id'],
            )
        except (NeplatnyNedostatek, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        stav = 'založeno' if novy else 'aktualizováno'
        self.stdout.write(f'{stav} {row.id} {row.kod} {row.typ}')
