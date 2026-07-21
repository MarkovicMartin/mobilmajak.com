"""Porovnání loginů z Mastersheet s modulem Přístupy (bez hesel v git)."""

from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand

from web_pristupy.mastersheet_logins import (
    DEFAULT_EXCEL,
    LOGINS_JSON,
    PLACEHOLDER_PASSWORD,
    load_mastersheet_logins,
    normalize_key,
    normalize_store,
    resolve_website_url,
)
from web_pristupy.models import WEB_PRISTUPY_PRODEJNY


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
        parser.add_argument(
            '--fill-urls',
            action='store_true',
            help='Doplnit prázdné website_url u existujících záznamů (heuristika + aliasy)',
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
                url = resolve_website_url(item['service'])
                url_note = f' → {url}' if url else ' (bez URL)'
                lines.append(
                    f'- **{normalize_store(item["store"])}** / {item["service"]} → `{item["username"]}`{url_note}'
                )
            if len(missing) > 30:
                lines.append(f'- … a dalších {len(missing) - 30}')

        lines.extend([
            '',
            'Hesla nejsou v git. Chybějící doplnit ručně v modulu Přístupy nebo `--import-missing` (placeholder heslo).',
            'Prázdné odkazy: `--fill-urls` (heuristika z názvu služby / domény).',
        ])

        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'Report: {report_path}'))
        self.stdout.write(f'Shoda: {len(present)}, chybí: {len(missing)}')

        if options['fill_urls']:
            self._fill_empty_urls(dry_run=options['dry_run'])

        if options['import_missing'] and missing:
            created = 0
            with_url = 0
            for item in missing:
                store = normalize_store(item['store'])
                website_url = resolve_website_url(item['service'])
                if options['dry_run']:
                    url_note = website_url or '(bez URL)'
                    self.stdout.write(f'  [dry] {store} / {item["service"]} → {url_note}')
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
                    website_url=website_url or '',
                    username=item['username'][:100],
                    password=PLACEHOLDER_PASSWORD,
                    store=store,
                    added_by='mastersheet-import',
                    is_active=True,
                )
                created += 1
                if website_url:
                    with_url += 1
            if options['dry_run']:
                self.stdout.write(self.style.WARNING(
                    f'Dry-run – přidalo by se {len(missing)} záznamů'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'Přidáno {created} záznamů (heslo DOPLNIT_RUCNE, s URL: {with_url})'
                ))

    def _fill_empty_urls(self, *, dry_run: bool):
        from django.db.models import Q

        qs = WEB_PRISTUPY_PRODEJNY.objects.filter(is_active=True).filter(
            Q(website_url='') | Q(website_url__isnull=True)
        )
        updated = 0
        skipped = 0
        for row in qs.iterator():
            url = resolve_website_url(row.company_name)
            if not url:
                skipped += 1
                continue
            if dry_run:
                self.stdout.write(f'  [dry url] {row.store} / {row.company_name} → {url}')
            else:
                WEB_PRISTUPY_PRODEJNY.objects.filter(pk=row.id).update(website_url=url)
            updated += 1
        label = 'Dry-run – doplnilo by se' if dry_run else 'Doplněno'
        self.stdout.write(self.style.SUCCESS(
            f'{label} {updated} URL (bez odvoditelné URL: {skipped})'
        ))
