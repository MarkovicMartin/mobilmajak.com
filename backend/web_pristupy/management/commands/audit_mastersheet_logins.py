"""Porovnání loginů z Mastersheet s modulem Přístupy (bez hesel v git)."""

import json
import re
from collections import defaultdict
from pathlib import Path

import openpyxl
from django.core.management.base import BaseCommand

from web_pristupy.models import WEB_PRISTUPY_PRODEJNY

DEFAULT_EXCEL = Path.home() / 'Downloads' / 'Mastersheet - prodejny.xlsx'
LOGINS_JSON = Path(__file__).resolve().parents[4] / 'docs' / 'mastersheet-prihlasovaci-loginy.json'

STORE_ALIASES = {
    'GLOBUS': 'Globus',
    'ZLÍN ČEPKOV': 'Čepkov',
    'ZLIN CEPKOV': 'Čepkov',
    'ČEPKOV': 'Čepkov',
    'ŠTERNBERK': 'Šternberk',
    'STERNBERK': 'Šternberk',
    'PŘEROV': 'Přerov',
    'PREROV': 'Přerov',
    'SENIMO': 'Senimo',
    'VSETÍN': 'Vsetín',
    'VSETIN': 'Vsetín',
    'LITOVELSKÁ': 'Litovelská',
    'LITOVELSKA': 'Litovelská',
}


def normalize_store(name: str) -> str:
    key = re.sub(r'\s+', ' ', (name or '').strip()).upper()
    return STORE_ALIASES.get(key, name.strip().title())


def normalize_key(store, service, username):
    return (
        normalize_store(store).lower(),
        re.sub(r'\s+', ' ', (service or '').strip()).lower(),
        (username or '').strip().lower(),
    )


def load_mastersheet_logins(excel_path: Path, json_path: Path):
    if json_path.is_file():
        return json.loads(json_path.read_text(encoding='utf-8'))

    wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    ws = wb['Přihl.údaje']
    logins = []
    current_store = None
    for row in ws.iter_rows(values_only=True):
        c0 = row[0] if row else None
        c1 = row[1] if len(row) > 1 else None
        if c0 and str(c0).startswith('Prodejna'):
            current_store = str(c0).replace('Prodejna ', '').strip()
            continue
        if not current_store or not c1:
            continue
        service = str(c0).strip() if c0 else ''
        if 'příhlašovací' in service.lower():
            continue
        logins.append({
            'store': current_store,
            'service': service,
            'username': str(c1).strip(),
        })
    wb.close()
    return logins


class Command(BaseCommand):
    help = 'Audit loginů Mastersheet vs WEB_PRISTUPY_PRODEJNY (bez hesel).'

    def add_arguments(self, parser):
        parser.add_argument('--excel', type=str, default='')
        parser.add_argument('--json', type=str, default='')
        parser.add_argument('--report', type=str, default='', help='Cesta k výstupnímu MD reportu')
        parser.add_argument(
            '--import-missing',
            action='store_true',
            help='Přidat chybějící záznamy s placeholder heslem (nutná ruční úprava)',
        )
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        excel_path = Path(options['excel']) if options['excel'] else DEFAULT_EXCEL
        json_path = Path(options['json']) if options['json'] else LOGINS_JSON
        report_path = (
            Path(options['report'])
            if options['report']
            else Path(__file__).resolve().parents[4] / 'docs' / 'mastersheet-login-audit.md'
        )

        ms_logins = load_mastersheet_logins(excel_path, json_path)
        self.stdout.write(f'Mastersheet: {len(ms_logins)} loginů')

        db_keys = set()
        db_by_store = defaultdict(int)
        for row in WEB_PRISTUPY_PRODEJNY.objects.filter(is_active=True):
            db_keys.add(normalize_key(row.store, row.company_name, row.username))
            db_by_store[normalize_store(row.store)] += 1

        missing = []
        present = []
        by_store = defaultdict(lambda: {'present': 0, 'missing': 0, 'ms_total': 0})

        for item in ms_logins:
            store = normalize_store(item['store'])
            key = normalize_key(item['store'], item['service'], item['username'])
            by_store[store]['ms_total'] += 1
            if key in db_keys:
                present.append(item)
                by_store[store]['present'] += 1
            else:
                missing.append(item)
                by_store[store]['missing'] += 1

        lines = [
            '# Audit přihlašovacích údajů – Mastersheet vs Přístupy',
            '',
            f'Zdroj Mastersheet: {len(ms_logins)} záznamů (bez hesel).',
            f'DB aktivní přístupy: {WEB_PRISTUPY_PRODEJNY.objects.filter(is_active=True).count()}.',
            f'Shoda: **{len(present)}** | Chybí v DB: **{len(missing)}**',
            '',
            '## Po prodejně',
            '',
            '| Prodejna | Mastersheet | V DB (shoda) | Chybí | DB celkem |',
            '|----------|-------------|--------------|-------|-----------|',
        ]
        all_stores = sorted(set(by_store.keys()) | set(db_by_store.keys()))
        for store in all_stores:
            stats = by_store[store]
            lines.append(
                f'| {store} | {stats["ms_total"]} | {stats["present"]} | {stats["missing"]} | {db_by_store.get(store, 0)} |'
            )

        if missing:
            lines.extend(['', '## Ukázka chybějících (max 30)', ''])
            for item in missing[:30]:
                lines.append(
                    f'- **{normalize_store(item["store"])}** / {item["service"]} → `{item["username"]}`'
                )
            if len(missing) > 30:
                lines.append(f'- … a dalších {len(missing) - 30}')

        lines.extend([
            '',
            'Hesla nejsou v git. Chybějící doplnit ručně v modulu Přístupy nebo `--import-missing` (placeholder heslo).',
        ])

        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'Report: {report_path}'))
        self.stdout.write(f'Shoda: {len(present)}, chybí: {len(missing)}')

        if options['import_missing'] and missing:
            created = 0
            for item in missing:
                store = normalize_store(item['store'])
                if options['dry_run']:
                    self.stdout.write(f'  [dry] {store} / {item["service"]}')
                    continue
                exists = WEB_PRISTUPY_PRODEJNY.objects.filter(
                    store__iexact=store,
                    company_name__iexact=item['service'],
                    username__iexact=item['username'],
                ).exists()
                if exists:
                    continue
                WEB_PRISTUPY_PRODEJNY.objects.create(
                    company_name=item['service'][:200],
                    website_url='',
                    username=item['username'][:100],
                    password='DOPLNIT_RUCNE',
                    store=store,
                    added_by='mastersheet-import',
                    is_active=True,
                )
                created += 1
            self.stdout.write(self.style.SUCCESS(f'Přidáno {created} záznamů (heslo DOPLNIT_RUCNE)'))
