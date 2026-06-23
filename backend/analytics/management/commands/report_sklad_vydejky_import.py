"""Ticket při selhání / varování importu skladových výdejek (cron actor)."""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from tickets.models import Ticket
from tickets.webhooks import notify_ticket_created

IMPORT_AUTOR_ID = 1
IMPORT_AUTOR_JMENO = 'Import sklad-vydejky'
DEDUP_HOURS = 24


class Command(BaseCommand):
    help = 'Vytvoří ticket při chybě nebo varování importu skladových výdejek'

    def add_arguments(self, parser):
        parser.add_argument('--kind', choices=['failure', 'warning'], required=True)
        parser.add_argument('--message', required=True)
        parser.add_argument('--from-date', default='')
        parser.add_argument('--to-date', default='')

    def handle(self, *args, **options):
        kind = options['kind']
        message = (options['message'] or '').strip()[:2000]
        from_date = (options['from_date'] or '').strip()
        to_date = (options['to_date'] or '').strip()
        range_label = f'{from_date} .. {to_date}' if from_date and to_date else '—'

        fingerprint = f'sklad-vydejky-{kind}-{from_date}-{to_date}'
        since = timezone.now() - timedelta(hours=DEDUP_HOURS)
        if Ticket.objects.filter(popis__contains=f'fp:{fingerprint}', vytvoreno__gte=since).exists():
            self.stdout.write('Ticket přeskočen (duplikát)')
            return

        if kind == 'failure':
            nazev = '[Import] Skladové výdejky – neproběhl'
        else:
            nazev = '[Import] Skladové výdejky – varování'

        popis = '\n'.join([
            f'fp:{fingerprint}',
            f'Období: {range_label}',
            message,
            '',
            'Automaticky z nočního importu skladových výdejek (VPS actor).',
        ])

        ticket = Ticket.objects.create(
            nazev=nazev[:200],
            popis=popis,
            autor_id=IMPORT_AUTOR_ID,
            autor_jmeno=IMPORT_AUTOR_JMENO,
        )
        notify_ticket_created(ticket)
        self.stdout.write(self.style.SUCCESS(f'Ticket #{ticket.id} vytvořen'))
