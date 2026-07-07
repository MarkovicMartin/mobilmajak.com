"""Odešle denní souhrn prodejů do Slacku (DM).

Cron (každý den 20:30):
    python manage.py send_daily_slack_report

Příjemci: aktivní uživatelé s zapnutým „Denní report“ v profilu
(výchozí: Radek Bulandra, Petr Valenta).

Vyžaduje SLACK_BOT_TOKEN v backend/.env a e-mail shodný se Slack účtem.
"""
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from analytics.daily_report import build_daily_report, format_daily_report_slack
from analytics.daily_report_recipients import daily_report_recipient_queryset
from analytics.slack_report import resolve_daily_report_user, send_daily_report_dm
from tasks.slack_notify import _bot_token
from users.models import WebUser


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

    def handle(self, *args, **options):
        report_day = None
        if options.get('date'):
            try:
                report_day = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError as exc:
                raise CommandError('Neplatný formát --date, použijte YYYY-MM-DD') from exc

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
