"""Odešle denní souhrn prodejů do Slacku (DM).

Cron (každý den 20:30):
    python manage.py send_daily_slack_report

Příjemci: aktivní uživatelé s zapnutým „Denní report“ v profilu
(výchozí: Radek Bulandra, Petr Valenta).

Vyžaduje SLACK_BOT_TOKEN v backend/.env a e-mail shodný se Slack účtem.
"""
from datetime import datetime
import os
import time

from django.core.management.base import BaseCommand, CommandError

from analytics.daily_report import build_daily_report, format_daily_report_slack
from analytics.daily_report_recipients import daily_report_recipient_queryset
from analytics.slack_report import resolve_daily_report_user, send_daily_report_dm
from tasks.slack_notify import _bot_token
from users.models import WebUser


ACTOR_LOCK_FILE = "/tmp/prodeje-actor.lock"
ACTOR_PID_FILE = "/tmp/prodeje-actor.pid"


def _actor_pid_from_lock() -> int | None:
    try:
        if not os.path.exists(ACTOR_PID_FILE):
            return None
        with open(ACTOR_PID_FILE, "r", encoding="utf-8", errors="replace") as f:
            raw = (f.read() or "").strip()
        return int(raw) if raw else None
    except Exception:
        return None


def _prodeje_actor_running() -> bool:
    """Zjistí, jestli běží prodeje actor (sdílený lock z wrapperu)."""
    if not os.path.exists(ACTOR_LOCK_FILE):
        return False

    pid = _actor_pid_from_lock()
    if pid is None:
        # Lock existuje, ale PID se nepodařilo přečíst => konzervativně považujeme za běžící.
        return True

    try:
        # signál 0 ověřuje existenci procesu.
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Nemáme práva, ale proces existuje.
        return True


def _wait_for_prodeje_actor(timeout_s: int = 180, poll_s: int = 5) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if not _prodeje_actor_running():
            return True
        time.sleep(poll_s)
    return not _prodeje_actor_running()


class Command(BaseCommand):
    help = 'Odešle denní report prodejů do Slacku jako DM (výchozí: dnešní den).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            help='Den reportu YYYY-MM-DD (výchozí: dnes)',
        )
        parser.add_argument(
            '--user',
            help='Odeslat jen jednomu uživateli (přihlašovací jméno nebo příjmení)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Jen vypsat text a seznam příjemců bez odeslání',
        )
        parser.add_argument(
            '--no-wait-actor',
            action='store_true',
            help='Nepočkat na doběhnutí prodejního actoru (riziko race / přepisu dat).',
        )

    def handle(self, *args, **options):
        report_day = None
        if options.get('date'):
            try:
                report_day = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError as exc:
                raise CommandError('Neplatný formát --date, použijte YYYY-MM-DD') from exc

        if not options.get('no_wait_actor'):
            # Actor zapisuje do WEB_PRODEJE_ALL (DELETE+INSERT), takže report nechceme pouštět uprostřed.
            if not _wait_for_prodeje_actor():
                raise CommandError('Prodejní actor stále běží – nepodařilo se bezpečně odeslat denní report.')

        report = build_daily_report(report_day)
        text = format_daily_report_slack(report)

        self.stdout.write(text)
        self.stdout.write('')

        if options.get('user'):
            recipients = [resolve_daily_report_user(options['user'])]
            if not recipients[0]:
                raise CommandError(f"Uživatel '{options['user']}' nenalezen.")
        else:
            recipients = list(daily_report_recipient_queryset())

        if not recipients:
            self.stdout.write(self.style.WARNING('Žádní příjemci (slack_daily_report=1).'))
            return

        self.stdout.write('Příjemci:')
        for user in recipients:
            self.stdout.write(f"  • {user.jmeno} {user.prijmeni} (#{user.id}, {user.uzivatelske_jmeno})")

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('Dry-run – nic se neodeslalo.'))
            return

        if not _bot_token():
            raise CommandError('SLACK_BOT_TOKEN není nastaven v backend/.env.')

        sent = 0
        failed = []
        for user in recipients:
            if send_daily_report_dm(user, text):
                sent += 1
            else:
                failed.append(user.uzivatelske_jmeno)

        if failed:
            self.stdout.write(
                self.style.WARNING(f"Nepodařilo se odeslat: {', '.join(failed)}")
            )
        self.stdout.write(self.style.SUCCESS(f"Odesláno {sent}/{len(recipients)} DM za {report['day']}."))
        if sent == 0:
            raise CommandError('Žádná DM se neodeslala – zkontroluj token a e-maily v profilu.')
