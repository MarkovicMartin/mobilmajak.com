"""Import hodin z Excelů Směny *.xlsx do prumer_mzdy_override.json."""
from pathlib import Path

from django.core.management.base import BaseCommand

from shifts.prumer_mzdy_override import DATA_PATH, load_prumer_mzdy_overrides
from shifts.smeny_excel_import import import_prumer_hodiny_from_excels, write_prumer_override_json


def _merge_with_existing(payload, rok=2026, mesice=(3, 4, 5)):
    existing = load_prumer_mzdy_overrides()
    users = {
        surname: {'mesice': list(data.get('mesice', []))}
        for surname, data in existing.items()
    }
    for surname, new_rows in payload.get('uzivatele', {}).items():
        if isinstance(new_rows, dict):
            new_rows = new_rows.get('mesice', [])
        kept = [
            row for row in users.get(surname, {}).get('mesice', [])
            if not (row.get('rok') == rok and row.get('mesic') in mesice)
        ]
        kept.extend(new_rows)
        kept.sort(key=lambda r: (r.get('rok', 0), r.get('mesic', 0)))
        users[surname] = {'mesice': kept}
    return {'uzivatele': dict(sorted(users.items()))}


class Command(BaseCommand):
    help = 'Načte březen–květen (a volitelně červen) z Excelů směn do prumer_mzdy_override.json.'

    def add_arguments(self, parser):
        parser.add_argument(
            'soubory',
            nargs='*',
            help='Cesty k Excelům Směny <prodejna>.xlsx',
        )
        parser.add_argument('--rok', type=int, default=2026)
        parser.add_argument('--mesice', default='3,4,5', help='Čísla měsíců, např. 3,4,5')
        parser.add_argument('--vcetne-cervna', action='store_true', help='Přidat i měsíc 6 ke kontrole')
        parser.add_argument('--dry-run', action='store_true', help='Jen vypsat, nezapisovat JSON')
        parser.add_argument('--output', default=str(DATA_PATH))

    def handle(self, *args, **options):
        paths = [Path(p) for p in options['soubory']]
        missing = [p for p in paths if not p.is_file()]
        if missing:
            for p in missing:
                self.stderr.write(f'Chybí soubor: {p}')
            return

        mesice = [int(x.strip()) for x in options['mesice'].split(',') if x.strip()]
        if options['vcetne_cervna'] and 6 not in mesice:
            mesice.append(6)

        payload, merged = import_prumer_hodiny_from_excels(
            paths, rok=options['rok'], mesice=tuple(mesice),
        )
        payload = _merge_with_existing(payload, rok=options['rok'], mesice=tuple(mesice))

        self.stdout.write(f'Import {len(paths)} souborů → {len(payload["uzivatele"])} lidí')
        for surname, data in sorted(payload['uzivatele'].items()):
            rows = data.get('mesice', []) if isinstance(data, dict) else data
            parts = ', '.join(
                f'{r["mesic"]:02d}/{r["rok"]}: {r["odpracovano_h"]:.1f}h' for r in rows
            )
            self.stdout.write(f'  {surname}: {parts}')

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('Dry-run – JSON neuložen.'))
            return

        write_prumer_override_json(payload, options['output'])
        self.stdout.write(self.style.SUCCESS(f'Uloženo: {options["output"]}'))
