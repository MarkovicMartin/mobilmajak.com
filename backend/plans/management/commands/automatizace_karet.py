"""Zápis problému sobotního zpracování karet. Do Symplia nezapisuje a cron nenasazuje."""
import json

from django.core.management.base import BaseCommand, CommandError

from plans.automatizace_karet import NeplatnyProblem, problemy_mereni, zapis_problem
from plans.models import ZakladaniNedostatek


class Command(BaseCommand):
    help = (
        'Zapíše problém automatizace karet z !Import / PARTNER PL. '
        'Stejný otevřený kód a typ se nezdvojuje. Kartu ve Sympliu nemění.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--kod', default='')
        parser.add_argument(
            '--typ',
            default='',
            choices=['', *[kod for kod, _nazev in ZakladaniNedostatek.TYP_CHOICES]],
        )
        parser.add_argument('--text', default='')
        parser.add_argument('--nazev', default='')
        parser.add_argument('--zbozi-id', type=int, default=None)
        parser.add_argument(
            '--mereni',
            default='',
            help='JSON pole měření karet. Zapisují se jen konkrétní mezery u zboží skladem.',
        )

    def handle(self, *args, **options):
        if options['mereni']:
            self._z_mereni(options['mereni'])
            return
        if not options['kod'] or not options['typ'] or not options['text']:
            raise CommandError('Zadej --kod, --typ a --text, nebo --mereni.')
        self._jeden(options)

    def _jeden(self, options):
        try:
            row, novy = zapis_problem(
                kod=options['kod'],
                typ=options['typ'],
                text=options['text'],
                nazev=options['nazev'],
                zbozi_id=options['zbozi_id'],
            )
        except (NeplatnyProblem, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        stav = 'založeno' if novy else 'aktualizováno'
        self.stdout.write(f'{stav} {row.id} {row.kod} {row.typ}')

    def _z_mereni(self, raw):
        try:
            polozky = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CommandError('Měření není JSON.') from exc
        if not isinstance(polozky, list):
            raise CommandError('Měření musí být seznam.')
        zapsano = 0
        for mereni in polozky:
            if not isinstance(mereni, dict):
                continue
            for problem in problemy_mereni(mereni):
                row, novy = zapis_problem(
                    kod=mereni.get('kod'),
                    typ=problem['typ'],
                    text=problem['text'],
                    nazev=mereni.get('nazev') or '',
                    zbozi_id=mereni.get('zbozi_id'),
                )
                if novy:
                    zapsano += 1
                self.stdout.write(f'{row.kod} {row.typ}')
        self.stdout.write(f'Nových problémů {zapsano}.')
