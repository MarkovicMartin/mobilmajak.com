"""Denní SLA připomínky k objednávkám (Slack only – nikdy nemění status).

    ./scripts/backend-run.sh manage.py check_orders_sla_reminders
    ./scripts/backend-run.sh manage.py check_orders_sla_reminders --dry-run
"""
from django.core.management.base import BaseCommand

from orders.sla import run_orders_sla_reminders


class Command(BaseCommand):
    help = (
        "7d eskalace objednávek – Bulandra + servis/prodejna "
        "(ORDERS_SLA_DAYS, bez změny statusu)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Jen spočítat kandidáty bez odeslání',
        )

    def handle(self, *args, **options):
        result = run_orders_sla_reminders(dry_run=options['dry_run'])
        self.stdout.write(
            f"SLA threshold={result['threshold_days']}d, "
            f"candidates={result['candidates']}, reminded={result['reminded']}"
            + (" (dry-run)" if result['dry_run'] else "")
        )
