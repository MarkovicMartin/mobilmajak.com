from django.core.management.base import BaseCommand

from finance.fio_client import FioImportNotAvailable, fetch_all_accounts, fetch_all_balances
from finance.fio_status import get_fio_import_status
from finance.models import FinanceZustatek
from finance.services import log_finance_system, upsert_fio_row


class Command(BaseCommand):
    help = 'Import nákladů z Fio API (vyžaduje FINANCE_FIO_ENABLED=1 a admin token)'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7, help='Počet dní zpět (výchozí 7)')
        parser.add_argument('--date-from', default='', help='YYYY-MM-DD (místo --days)')
        parser.add_argument('--date-to', default='', help='YYYY-MM-DD (výchozí dnes)')
        parser.add_argument('--dry-run', action='store_true', help='Bez zápisu do DB')
        parser.add_argument('--skip-balance', action='store_true', help='Neukládat snapshot zůstatku')

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

        dry_run = options['dry_run']
        date_from_s = (options['date_from'] or '').strip()
        date_to_s = (options['date_to'] or '').strip()
        if date_from_s:
            date_from = date.fromisoformat(date_from_s)
            date_to = date.fromisoformat(date_to_s) if date_to_s else date.today()
        else:
            days = max(1, options['days'])
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

        created = skipped = incoming = 0
        for row in rows:
            result = upsert_fio_row(row, dry_run=dry_run)
            if result == 'created':
                created += 1
            elif result == 'incoming':
                incoming += 1
            else:
                skipped += 1

        balance_saved = 0
        if not dry_run and not options['skip_balance']:
            try:
                for bal in fetch_all_balances():
                    FinanceZustatek.objects.create(
                        datum=bal['datum'],
                        typ=FinanceZustatek.TYP_FIO,
                        label=bal.get('account_label', 'fio'),
                        castka=bal['castka'],
                        mena=bal.get('mena', 'CZK'),
                    )
                    balance_saved += 1
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f'Balance snapshot selhal: {exc}'))

        summary = (
            f'staženo {len(rows)}, nových nákladů {created}, příchozích {incoming}, '
            f'přeskočeno {skipped}, zůstatků {balance_saved}'
        )
        if not dry_run:
            log_finance_system('fio_import', summary)

        self.stdout.write(self.style.SUCCESS(f'Hotovo: {summary}'))
