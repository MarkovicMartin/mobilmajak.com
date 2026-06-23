"""Ranní recap úkolů ke směně (start + 10 min).

Cron (každých 5–10 min v pracovní dny):
    */5 * * * * cd .../backend && ... python manage.py notify_shift_task_recap
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from tasks.shift_recap import RECAP_OFFSET_MINUTES, send_shift_recap, shifts_due_for_recap
from tasks.slack_notify import _bot_token


class Command(BaseCommand):
    help = "Odešle Slack recap úkolů uživatelům se směnou (začátek směny + 10 min)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Jen vypsat, komu by se odeslalo",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        due = shifts_due_for_recap(now)

        if not due:
            self.stdout.write("Žádné směny pro recap v tomto okně.")
            return

        self.stdout.write(
            f"Směn k recapu (start+{RECAP_OFFSET_MINUTES} min): {len(due)}"
        )

        if not _bot_token():
            self.stdout.write(
                self.style.WARNING("SLACK_BOT_TOKEN není nastaven – nic se neodešle.")
            )

        sent = 0
        for smena in due:
            user = smena.user
            label = f"  směna #{smena.id} {user.jmeno} {user.prijmeni} od {smena.cas_od}"
            self.stdout.write(label)
            if options["dry_run"] or not _bot_token():
                continue
            if send_shift_recap(smena, now=now):
                sent += 1

        if not options["dry_run"] and _bot_token():
            self.stdout.write(self.style.SUCCESS(f"Odesláno: {sent}/{len(due)}"))
