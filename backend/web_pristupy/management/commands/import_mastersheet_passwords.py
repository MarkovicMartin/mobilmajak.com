"""Doplnění hesel z Mastersheet Excelu do existujících záznamů Přístupy."""

from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from web_pristupy.mastersheet_logins import (
    DEFAULT_EXCEL,
    build_password_index,
    load_mastersheet_logins_from_excel,
    needs_password_update,
    normalize_store,
    plan_password_updates,
    summarize_by_store,
)
from web_pristupy.models import WEB_PRISTUPY_PRODEJNY


class Command(BaseCommand):
    help = (
        'Doplní hesla z listu Přihl.údaje (Excel) do záznamů s DOPLNIT_RUCNE nebo prázdným heslem. '
        'Existující hesla se nepřepisují.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--excel',
            type=str,
            default='',
            help=f'Cesta k Mastersheet Excelu (výchozí: {DEFAULT_EXCEL})',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Jen vypsat statistiky, nic neukládat',
        )

    def handle(self, *args, **options):
        excel_path = Path(options['excel']) if options['excel'] else DEFAULT_EXCEL
        if not excel_path.is_file():
            self.stderr.write(self.style.ERROR(f'Excel nenalezen: {excel_path}'))
            return

        ms_logins = load_mastersheet_logins_from_excel(excel_path, include_passwords=True)
        password_index = build_password_index(ms_logins)
        self.stdout.write(
            f'Mastersheet: {len(ms_logins)} loginů, {len(password_index)} s heslem'
        )

        db_rows = list(
            WEB_PRISTUPY_PRODEJNY.objects.filter(is_active=True).values(
                'id', 'store', 'company_name', 'username', 'password'
            )
        )
        plan = plan_password_updates(db_rows, password_index)

        updated = plan['updated']
        self.stdout.write(f'K aktualizaci: {len(updated)}')
        self.stdout.write(f'Přeskočeno (už má heslo): {len(plan["skipped_has_password"])}')
        self.stdout.write(f'Přeskočeno (bez shody v Excelu): {len(plan["skipped_no_match"])}')
        if plan['skipped_empty_excel']:
            self.stdout.write(
                f'Přeskočeno (shoda bez hesla v Excelu): {len(plan["skipped_empty_excel"])}'
            )

        if updated:
            self.stdout.write('')
            self.stdout.write('Aktualizace po prodejně:')
            for store, count in summarize_by_store(updated).items():
                self.stdout.write(f'  {store}: {count}')

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('Dry-run – žádné změny v DB'))
            self._report_remaining_placeholders()
            return

        if not updated:
            self.stdout.write(self.style.WARNING('Nic k aktualizaci'))
            self._report_remaining_placeholders()
            return

        with transaction.atomic():
            for item in updated:
                WEB_PRISTUPY_PRODEJNY.objects.filter(pk=item['id']).update(
                    password=item['new_password']
                )

        self.stdout.write(self.style.SUCCESS(f'Aktualizováno {len(updated)} hesel'))
        self._report_remaining_placeholders()

    def _report_remaining_placeholders(self):
        remaining = WEB_PRISTUPY_PRODEJNY.objects.filter(is_active=True).values(
            'id', 'store', 'company_name', 'username', 'password'
        )
        placeholders = [r for r in remaining if needs_password_update(r['password'])]
        self.stdout.write(f'Zbývá DOPLNIT_RUCNE / prázdné: {len(placeholders)}')
        if placeholders:
            by_store = summarize_by_store(placeholders)
            for store, count in by_store.items():
                self.stdout.write(f'  {store}: {count}')
