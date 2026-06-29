"""Doplní id_prodejce u existujících řádků Packeta podle směn."""
from django.core.management.base import BaseCommand

from packeta.models import PacketaProvizePolozka
from packeta.shift_assign import resolve_prodejce_for_packeta


class Command(BaseCommand):
    help = 'Backfill id_prodejce u Packeta provizí podle nejbližší směny prodejce'

    def add_arguments(self, parser):
        parser.add_argument('--prodejna-id', type=int, help='Jen prodejna 1–6')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        qs = PacketaProvizePolozka.objects.filter(id_prodejce__isnull=True).order_by('cas')
        if options.get('prodejna_id'):
            qs = qs.filter(prodejna_id=options['prodejna_id'])

        total = qs.count()
        updated = 0
        dry_run = options['dry_run']

        self.stdout.write(f'Řádků bez prodejce: {total}')

        for row in qs.iterator(chunk_size=500):
            pid = resolve_prodejce_for_packeta(row.prodejna_id, row.cas)
            if not pid:
                continue
            if dry_run:
                updated += 1
                continue
            PacketaProvizePolozka.objects.filter(pk=row.pk).update(id_prodejce=pid)
            updated += 1

        suffix = ' [DRY RUN]' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(f'Přiřazeno: {updated}{suffix}'))
