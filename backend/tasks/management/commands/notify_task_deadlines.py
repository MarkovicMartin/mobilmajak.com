"""Odešle Slack notifikace u úkolů s blížícím se nebo překročeným termínem.

Spouštění (cron, např. každou hodinu):
    python manage.py notify_task_deadlines

Bez SLACK_TASKS_WEBHOOK_URL v .env příkaz jen vypíše, co by odeslal (dry-run chování).
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from tasks.slack_notify import _webhook_url, send_slack_message, tasks_needing_slack_notify


class Command(BaseCommand):
    help = "Odešle Slack notifikace k termínům úkolů (due_soon / overdue)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Jen vypsat úkoly bez odeslání",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        pending = tasks_needing_slack_notify(now)
        webhook = _webhook_url()

        if not pending:
            self.stdout.write("Žádné úkoly k notifikaci.")
            return

        self.stdout.write(f"Úkolů k notifikaci: {len(pending)}")
        if not webhook:
            self.stdout.write(
                self.style.WARNING(
                    "SLACK_TASKS_WEBHOOK_URL není nastaven – notifikace se neodesílají."
                )
            )

        sent = 0
        for task, notify_typ in pending:
            title = (task.vysledek or task.ukol or "")[:60]
            self.stdout.write(f"  #{task.id} [{notify_typ}] {title}")
            if options["dry_run"]:
                continue
            if not webhook:
                continue
            if send_slack_message(task, notify_typ):
                sent += 1

        if webhook and not options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"Odesláno: {sent}/{len(pending)}"))
