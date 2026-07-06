from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from finance.services import import_symplio_pokladna_file, log_finance_system


class Command(BaseCommand):
    help = 'Import výdejů z historie pokladny Symplio (XLSX export)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file', dest='files', action='append', default=[],
            help='Cesta k XLSX (lze opakovat)',
        )
        parser.add_argument(
            '--input-dir', default='',
            help='Složka s *.xlsx a volitelně *.meta.json (prodejna_id)',
        )
        parser.add_argument('--prodejna-id', type=int, default=None, help='ID prodejny (WEB_PRODEJNY)')
        parser.add_argument('--dry-run', action='store_true', help='Bez zápisu do DB')

    def handle(self, *args, **options):
        files = list(options['files'] or [])
        input_dir = (options['input_dir'] or '').strip()

        if input_dir:
            base = Path(input_dir)
            if not base.is_dir():
                raise CommandError(f'input-dir neexistuje: {base}')
            files.extend(str(p) for p in sorted(base.glob('*.xlsx')))

        if not files:
            self.stdout.write(self.style.WARNING('Žádné XLSX k importu (--file nebo --input-dir)'))
            return

        total_created = total_updated = total_skipped = total_non_vydej = 0
        for path_str in files:
            path = Path(path_str)
            if not path.is_file():
                self.stdout.write(self.style.WARNING(f'Přeskočeno (soubor neexistuje): {path}'))
                continue

            prodejna_id = options['prodejna_id']
            meta_path = path.with_suffix('.meta.json')
            if meta_path.is_file():
                import json
                meta = json.loads(meta_path.read_text(encoding='utf-8'))
                prodejna_id = meta.get('prodejna_id', prodejna_id)

            if prodejna_id is None:
                raise CommandError(
                    f'Chybí prodejna_id pro {path.name} – použij --prodejna-id nebo {meta_path.name}',
                )

            result = import_symplio_pokladna_file(
                path, prodejna_id=prodejna_id, dry_run=options['dry_run'],
            )
            total_created += result['created']
            total_updated += result['updated']
            total_skipped += result['skipped']
            total_non_vydej += result['non_vydej']
            self.stdout.write(
                f'{path.name}: nových {result["created"]}, aktualizováno {result["updated"]}, '
                f'přeskočeno {result["skipped"]}, ne-výdej {result["non_vydej"]}',
            )

        summary = (
            f'souborů {len(files)}, nových {total_created}, aktualizováno {total_updated}, '
            f'přeskočeno {total_skipped}, ne-výdej {total_non_vydej}'
        )
        if not options['dry_run'] and (total_created or total_updated):
            log_finance_system('symplio_pokladna_import', summary)

        self.stdout.write(self.style.SUCCESS(f'Hotovo: {summary}'))
