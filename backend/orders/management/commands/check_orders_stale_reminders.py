"""Denní připomínky objednávek bez pohybu (≥1 pracovní den, Po–Pá).

    ./scripts/backend-run.sh manage.py check_orders_stale_reminders
    ./scripts/backend-run.sh manage.py check_orders_stale_reminders --dry-run
"""
from django.core.management.base import BaseCommand

from orders.stale import run_orders_stale_reminders


class Command(BaseCommand):
    help = "Slack připomínky u objednávek ≥1 pracovní den ve stejném stavu (bez víkendů)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Jen spočítat kandidáty bez odeslání",
        )

    def handle(self, *args, **options):
        result = run_orders_stale_reminders(dry_run=options["dry_run"])
        self.stdout.write(
            f"Stale threshold={result['threshold_business_days']} business day(s), "
            f"candidates={result['candidates']}, reminded={result['reminded']}"
            + (" (dry-run)" if result["dry_run"] else "")
        )
