from collections import Counter

from django.core.management.base import BaseCommand

from finance.kategorizace import apply_builtin_rules, apply_rules_to_polozka, polozka_as_row
from finance.models import NakladPolozka


class Command(BaseCommand):
    help = 'Aplikuje vestavěná + DB pravidla na nezařazené položky nákladů'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--limit', type=int, default=0, help='Max položek (0 = vše)')
        parser.add_argument(
            '--backfill-pravidla',
            action='store_true',
            help='Doplní auto_pravidlo u už automaticky zařazených položek',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if options['backfill_pravidla']:
            self._backfill_pravidla(dry_run)
            return

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

    def _backfill_pravidla(self, dry_run: bool):
        stats = Counter()
        qs = NakladPolozka.objects.filter(
            zarazeno_automaticky=True,
            auto_pravidlo='',
        ).order_by('datum', 'id')
        for p in qs:
            builtin = apply_builtin_rules(
                polozka_as_row(p), zdroj=p.zdroj, prodejna_id=p.prodejna_id,
            )
            if not builtin or not builtin.pravidlo:
                stats['bez_match'] += 1
                continue
            if not dry_run:
                p.auto_pravidlo = builtin.pravidlo[:64]
                p.save(update_fields=['auto_pravidlo'])
            stats[builtin.pravidlo] += 1
        self.stdout.write(
            self.style.SUCCESS(
                f'{"[DRY RUN] " if dry_run else ""}backfill: '
                + ', '.join(f'{k}={v}' for k, v in sorted(stats.items(), key=lambda x: -x[1]))
            )
        )
