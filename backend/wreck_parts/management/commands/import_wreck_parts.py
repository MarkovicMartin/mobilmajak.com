"""Import dílů z vraků z Mastersheet Excel nebo bootstrap JSON."""

import json
from pathlib import Path

import openpyxl
from django.core.management.base import BaseCommand
from django.db import transaction

from wreck_parts.models import WreckPart

DEFAULT_EXCEL = Path.home() / 'Downloads' / 'Mastersheet - prodejny.xlsx'
BOOTSTRAP_JSON = Path(__file__).resolve().parents[2] / 'bootstrap' / 'mastersheet.json'

STORE_MARKERS = {
    'globus', 'čepkov', 'cepkov', 'šternberk', 'sternberk', 'přerov', 'prerov',
    'senimo', 'vsetín', 'vsetin', 'litovelská', 'litovelska',
}
STORE_MAP = {
    'globus': 'Globus', 'čepkov': 'Čepkov', 'cepkov': 'Čepkov',
    'šternberk': 'Šternberk', 'sternberk': 'Šternberk',
    'přerov': 'Přerov', 'prerov': 'Přerov', 'senimo': 'Senimo',
    'vsetín': 'Vsetín', 'vsetin': 'Vsetín',
    'litovelská': 'Litovelská', 'litovelska': 'Litovelská',
}


PART_TYPE_MAX = 100


def _cell(row, idx, default=None):
    return row[idx] if idx < len(row) else default


def _normalize_store(store):
    store = (store or 'Globus').strip()
    return 'Globus' if store == 'Neuvedeno' else store


def _normalize_item(item):
    """Zkrátí part_type; zbytek přesune do notes (limit DB sloupce)."""
    part_type = (item.get('part_type') or 'Díly').strip()
    notes = (item.get('notes') or '').strip()
    item['store'] = _normalize_store(item.get('store'))
    if len(part_type) > PART_TYPE_MAX:
        overflow = part_type[PART_TYPE_MAX:].strip()
        part_type = part_type[:PART_TYPE_MAX].rstrip(' ,;')
        notes = f'{overflow}; {notes}'.strip('; ').strip() if overflow else notes
    item['part_type'] = part_type or 'Díly'
    item['notes'] = notes
    return item


def parse_excel(path: Path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb['Díly z vraků']
    items = []
    current_store = 'Globus'

    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue
        if not row or all(c is None or c == '' for c in row):
            continue

        c0 = _cell(row, 0)
        if (
            c0
            and len([x for x in row if x is not None and x != '']) == 1
            and isinstance(c0, str)
            and c0.strip().lower() in STORE_MARKERS
        ):
            current_store = STORE_MAP[c0.strip().lower()]
            continue

        model = str(c0).strip() if c0 else ''
        if not model:
            continue

        c1 = _cell(row, 1)
        if isinstance(c1, (int, float)) and c1 == int(c1):
            items.append({
                'model_name': model,
                'part_type': 'LCD',
                'quantity': int(c1),
                'store': current_store,
                'notes': '',
            })
        else:
            part_type = str(c1).strip() if c1 else 'Díly'
            notes_parts = [str(x).strip() for x in row[2:] if x]
            items.append({
                'model_name': model,
                'part_type': part_type,
                'quantity': 1,
                'store': current_store,
                'notes': '; '.join(notes_parts),
            })

    wb.close()
    return [_normalize_item(item) for item in items]


class Command(BaseCommand):
    help = 'Import dílů z vraků z Mastersheet (Excel nebo bootstrap JSON).'

    def add_arguments(self, parser):
        parser.add_argument('--excel', type=str, default='', help='Cesta k Mastersheet Excel')
        parser.add_argument('--json', type=str, default='', help='Cesta k JSON (výchozí bootstrap)')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--clear', action='store_true', help='Smazat existující záznamy před importem')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        excel_path = Path(options['excel']) if options['excel'] else DEFAULT_EXCEL
        json_path = Path(options['json']) if options['json'] else BOOTSTRAP_JSON

        if excel_path.is_file():
            self.stdout.write(f'Čtu Excel: {excel_path}')
            items = parse_excel(excel_path)
        elif json_path.is_file():
            self.stdout.write(f'Čtu JSON: {json_path}')
            items = json.loads(json_path.read_text(encoding='utf-8'))
        else:
            self.stderr.write(self.style.ERROR('Nenalezen Excel ani bootstrap JSON.'))
            return

        items = [_normalize_item(item) for item in items]
        self.stdout.write(f'Nalezeno {len(items)} položek')

        if dry_run:
            for item in items[:5]:
                self.stdout.write(f'  {item}')
            self.stdout.write(self.style.WARNING('DRY RUN – nic neuloženo'))
            return

        with transaction.atomic():
            if options['clear']:
                deleted, _ = WreckPart.objects.all().delete()
                self.stdout.write(f'Smazáno {deleted} záznamů')
            else:
                updated = WreckPart.objects.filter(store='Neuvedeno').update(store='Globus')
                if updated:
                    self.stdout.write(f'Přemapováno {updated} záznamů Neuvedeno → Globus')

            created = 0
            for item in items:
                _, was_created = WreckPart.objects.get_or_create(
                    model_name=item['model_name'],
                    part_type=item['part_type'],
                    store=item['store'],
                    defaults={
                        'quantity': item.get('quantity', 1),
                        'notes': item.get('notes', ''),
                    },
                )
                if was_created:
                    created += 1

        self.stdout.write(self.style.SUCCESS(f'Hotovo: {created} nových, celkem v DB {WreckPart.objects.count()}'))
