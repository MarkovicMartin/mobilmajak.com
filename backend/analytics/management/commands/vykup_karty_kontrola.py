"""Denní kontrola karet výkupů. Cron v 8:00."""
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from analytics.vykup_karty import spustit


class Command(BaseCommand):
    help = (
        'Druhý den po výkupu založí úkol na nedokončenou kartu skladem. '
        '1. den v měsíci pošle Radkovi Bulandrovi souhrn za minulý měsíc.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Nic nezakládat ani neposílat.')
        parser.add_argument('--datum', help='Dnešní datum YYYY-MM-DD, jinak skutečné dnes.')

    def handle(self, *args, **options):
        ted = timezone.now()
        dnes = None
        if options.get('datum'):
            try:
                dnes = datetime.strptime(options['datum'], '%Y-%m-%d').date()
            except ValueError as exc:
                raise CommandError('--datum musí být YYYY-MM-DD') from exc
            ted = timezone.make_aware(datetime.combine(dnes, datetime.min.time().replace(hour=8)))
        try:
            spustit(dnes=dnes, ted=ted, dry_run=bool(options['dry_run']), stdout=self.stdout)
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc
