from collections import Counter

from django.core.management.base import BaseCommand

from finance.kategorizace import apply_rules_to_polozka
from finance.models import NakladPolozka


class Command(BaseCommand):
    help = 'Aplikuje vestavěná + DB pravidla na nezařazené položky nákladů'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--limit', type=int, default=0, help='Max položek (0 = vše)')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        qs = NakladPolozka.objects.filter(stav=NakladPolozka.STAV_NEZARAZENO).order_by('datum', 'id')
        if options['limit']:
            qs = qs[: options['limit']]

        stats = Counter()
        for p in qs:
            rule = apply_rules_to_polozka(p, dry_run=dry_run)
            if rule:
                stats[rule] += 1
            else:
                stats['nezarazeno'] += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'{"[DRY RUN] " if dry_run else ""}zpracováno {sum(stats.values())}: '
                + ', '.join(f'{k}={v}' for k, v in sorted(stats.items(), key=lambda x: -x[1]))
            )
        )
