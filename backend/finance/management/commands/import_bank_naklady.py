from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError

from finance.bank_import import _summary, run_bank_import


class Command(BaseCommand):
    help = 'Import nákladů z Fio a Raiffeisen. Převody mezi vlastními účty se ignorují.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7, help='Počet dní zpět (výchozí 7)')
        parser.add_argument('--date-from', default='', help='YYYY-MM-DD (místo --days)')
        parser.add_argument('--date-to', default='', help='YYYY-MM-DD (výchozí dnes)')
        parser.add_argument('--dry-run', action='store_true', help='Bez zápisu do DB')
        parser.add_argument('--skip-balance', action='store_true', help='Neukládat snapshot zůstatku')
        parser.add_argument('--bank', default='both', choices=('both', 'fio', 'rb'))

    def handle(self, *args, **options):
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

        self.stdout.write(
            f'Import účtů {date_from} – {date_to}' + (' [DRY RUN]' if dry_run else '')
        )
        result = run_bank_import(
            date_from,
            date_to,
            dry_run=dry_run,
            skip_balance=options['skip_balance'],
            banks=options['bank'],
        )
        for key, label in (('fio_skipped', 'Fio'), ('rb_skipped', 'Raiffeisen')):
            if result[key]:
                self.stdout.write(self.style.WARNING(f'{label}: {result[key]}'))
        for key, label in (('fio', 'Fio'), ('rb', 'Raiffeisen')):
            if result[key]:
                self.stdout.write(self.style.SUCCESS(_summary(label, result[key])))
        errors = [msg for msg in (result['fio_error'], result['rb_error']) if msg]
        if errors:
            raise CommandError(' '.join(errors))
