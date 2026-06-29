from django.core.management.base import BaseCommand

from finance.fio_client import FioImportNotAvailable, fetch_all_accounts
from finance.fio_status import get_fio_import_status
from finance.services import upsert_fio_row


class Command(BaseCommand):
    help = 'Import nákladů z Fio API (vyžaduje FINANCE_FIO_ENABLED=1 a admin token)'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7, help='Počet dní zpět (výchozí 7)')
        parser.add_argument('--dry-run', action='store_true', help='Bez zápisu do DB')

    def handle(self, *args, **options):
        status = get_fio_import_status()
        if not status['available']:
            self.stdout.write(self.style.WARNING(status['message']))
            self.stdout.write(
                self.style.NOTICE(
                    'Tip: ruční náklady fungují bez Fio. '
                    'Po získání admin účtu nastavte FINANCE_FIO_ENABLED=1 v backend/.env.'
                )
            )
            return

        from datetime import date, timedelta

        days = max(1, options['days'])
        dry_run = options['dry_run']
        date_to = date.today()
        date_from = date_to - timedelta(days=days - 1)

        self.stdout.write(f'Fio import {date_from} – {date_to}' + (' [DRY RUN]' if dry_run else ''))

        try:
            rows = fetch_all_accounts(date_from, date_to)
        except FioImportNotAvailable as exc:
            self.stdout.write(self.style.WARNING(exc.message))
            return
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Fio API chyba: {exc}'))
            return

        created = skipped = 0
        for row in rows:
            result = upsert_fio_row(row, dry_run=dry_run)
            if result == 'created':
                created += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f'Hotovo: staženo {len(rows)}, nových {created}, přeskočeno {skipped}'
        ))
