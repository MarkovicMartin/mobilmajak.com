from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Import nákladů z Raiffeisen Premium API. Převody na vlastní účty Fio a Raiffeisen se ignorují.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7)
        parser.add_argument('--date-from', default='')
        parser.add_argument('--date-to', default='')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--skip-balance', action='store_true')

    def handle(self, *args, **options):
        call_command(
            'import_bank_naklady',
            days=options['days'],
            date_from=options['date_from'],
            date_to=options['date_to'],
            dry_run=options['dry_run'],
            skip_balance=options['skip_balance'],
            bank='rb',
        )
