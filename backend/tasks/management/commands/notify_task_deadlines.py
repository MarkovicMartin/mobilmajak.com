"""Odešle Slack notifikace u úkolů s blížícím se nebo překročeným termínem.

Spouštění (cron, např. každou hodinu):
    python manage.py notify_task_deadlines

Preferuje DM přes SLACK_BOT_TOKEN; bez něj volitelně webhook SLACK_TASKS_WEBHOOK_URL.
Bez obou jen vypíše, co by odeslal (dry-run chování).
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from tasks.slack_notify import (
    _bot_token,
    _webhook_url,
    send_deadline_notifications,
    tasks_needing_slack_notify,
)


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
        bot = _bot_token()
        webhook = _webhook_url()

        if not pending:
            self.stdout.write("Žádné úkoly k notifikaci.")
            return

        self.stdout.write(f"Úkolů k notifikaci: {len(pending)}")
        if not bot and not webhook:
            self.stdout.write(
                self.style.WARNING(
                    "SLACK_BOT_TOKEN ani SLACK_TASKS_WEBHOOK_URL není nastaven – notifikace se neodesílají."
                )
            )

        sent = 0
        seen: set[tuple[int, str]] = set()
        for task, notify_typ, recipient_id in pending:
            title = (task.vysledek or task.ukol or "")[:60]
            recipient = f" → user #{recipient_id}" if recipient_id else ""
            self.stdout.write(f"  #{task.id} [{notify_typ}]{recipient} {title}")
            if options["dry_run"]:
                continue
            if not bot and not webhook:
                continue
            key = (task.id, notify_typ)
            if key in seen:
                continue
            seen.add(key)
            sent += send_deadline_notifications(task, notify_typ)

        if (bot or webhook) and not options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"Odesláno: {sent}/{len(pending)}"))
