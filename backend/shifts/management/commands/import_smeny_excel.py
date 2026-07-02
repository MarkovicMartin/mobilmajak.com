"""Import jednotlivých směn z Excelů do tabulky WEB_SMENY."""
from pathlib import Path

from django.core.management.base import BaseCommand

from shifts.smeny_excel_shift_import import (
    apply_parsed_shifts,
    compare_monthly_hours_with_json,
    parse_shifts_files,
)


class Command(BaseCommand):
    help = 'Naimportuje březen–květen (volitelně jiné měsíce) z Excelů směn do tabulky směn.'

    def add_arguments(self, parser):
        parser.add_argument(
            'soubory',
            nargs='*',
            help='Cesty k Excelům Směny <prodejna>.xlsx',
        )
        parser.add_argument('--rok', type=int, default=2026)
        parser.add_argument('--mesice', default='3,4,5', help='Čísla měsíců, např. 3,4,5')
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Zapsat do DB (bez tohoto přepínače jen náhled)',
        )
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Před importem smazat dříve importované směny se stejnou poznámkou',
        )
        parser.add_argument(
            '--replace-period',
            action='store_true',
            help='Před importem smazat všechny směny v cílovém období (březen–květen)',
        )

    def handle(self, *args, **options):
        paths = [Path(p) for p in options['soubory']]
        missing = [p for p in paths if not p.is_file()]
        if missing:
            for p in missing:
                self.stderr.write(f'Chybí soubor: {p}')
            return

        mesice = tuple(int(x.strip()) for x in options['mesice'].split(',') if x.strip())
        shifts = parse_shifts_files(paths, rok=options['rok'], mesice=mesice)
        stats, user_dupes = apply_parsed_shifts(
            shifts,
            rok=options['rok'],
            mesice=mesice,
            dry_run=not options['apply'],
            replace=options['replace'],
            replace_period=options['replace_period'],
        )

        self.stdout.write(
            f'Parsováno {stats.parsed} směn z {len(paths)} souborů '
            f'({options["rok"]}, měsíce {",".join(str(m) for m in mesice)})'
        )
        if user_dupes:
            self.stdout.write(self.style.WARNING(
                'Duplicitní mapování příjmení: ' + ', '.join(sorted(user_dupes))
            ))

        self.stdout.write(
            f'{"Vytvořeno" if options["apply"] else "Připraveno"}: {stats.created}, '
            f'přeskočeno existující: {stats.skipped_existing}, '
            f'bez uživatele: {stats.skipped_user}, '
            f'bez prodejny: {stats.skipped_store}'
        )

        if not options['apply']:
            self.stdout.write(self.style.WARNING('Náhled – pro zápis použijte --apply'))
        elif options['replace_period']:
            self.stdout.write(self.style.SUCCESS('Import dokončen (nahrazeno celé období).'))
        elif options['replace']:
            self.stdout.write(self.style.SUCCESS('Import dokončen (replace).'))
        else:
            self.stdout.write(self.style.SUCCESS('Import dokončen.'))

        if options['apply']:
            self._print_json_comparison(options['rok'], mesice)

    def _print_json_comparison(self, rok, mesice):
        rows = compare_monthly_hours_with_json(rok=rok, mesice=mesice)
        if not rows:
            self.stdout.write('Porovnání s JSON: žádná data.')
            return
        self.stdout.write('')
        self.stdout.write('Porovnání součtů: JSON override vs. směny v DB')
        bad = 0
        for row in rows:
            status = 'OK' if row['ok'] else 'ROZDÍL'
            if not row['ok']:
                bad += 1
            self.stdout.write(
                f"  {row['surname']} {row['mesic']:02d}/{rok}: "
                f"JSON {row['json_h']:.1f} h, směny {row['smeny_h']:.1f} h, "
                f"Δ {row['diff']:+.1f} h [{status}]"
            )
        if bad:
            self.stdout.write(self.style.WARNING(f'Rozdíly u {bad} řádků (tolerance 0.5 h).'))
        else:
            self.stdout.write(self.style.SUCCESS('Všechny součty sedí s JSON (±0.5 h).'))
