"""Denní kontrola připomínek k otevřeným reklamacím.

Spouštění (cron, např. 1× denně ráno):
    ./scripts/backend-run.sh manage.py check_reklamace_reminders
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from reklamace.reminders import run_reklamace_reminders


class Command(BaseCommand):
    help = 'Odešle 2d/10d in-app a 30d Slack připomínky k otevřeným reklamacím.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Jen spočítat kandidáty bez odeslání',
        )

    def handle(self, *args, **options):
        now = timezone.now()
        result = run_reklamace_reminders(now=now, dry_run=options['dry_run'])
        self.stdout.write(
            f"In-app tracking 2d: {result['in_app_tracking_2d']}, "
            f"in-app 10d: {result['in_app_10d']}, Slack 30d: {result['slack_30d']}"
        )
