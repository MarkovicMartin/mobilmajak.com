from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from users.models import AppActivityLog


class Command(BaseCommand):
    help = 'Smaže app_activity_log starší než N dní (default 90).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Retence ve dnech (default 90)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Jen spočítat, nemazat',
        )

    def handle(self, *args, **options):
        days = max(1, int(options['days']))
        cutoff = timezone.now() - timedelta(days=days)
        qs = AppActivityLog.objects.filter(vytvoreno__lt=cutoff)
        count = qs.count()
        if options['dry_run']:
            self.stdout.write(f'dry-run: smazalo by se {count} řádků starších než {days} dní')
            return
        deleted, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(f'smazáno {deleted} řádků (retence {days} dní)'))
