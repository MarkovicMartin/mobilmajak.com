"""Doplní id_prodejce u existujících řádků Packeta podle směn."""
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date

from packeta.models import PacketaProvizePolozka
from packeta.shift_assign import resolve_prodejce_for_packeta


class Command(BaseCommand):
    help = 'Backfill id_prodejce u Packeta provizí podle nejbližší směny prodejce'

    def add_arguments(self, parser):
        parser.add_argument('--prodejna-id', type=int, help='Jen prodejna 1–6')
        parser.add_argument('--date-from', type=str, help='YYYY-MM-DD')
        parser.add_argument('--date-to', type=str, help='YYYY-MM-DD')
        parser.add_argument(
            '--force',
            action='store_true',
            help='Přepočítat i řádky, které už id_prodejce mají',
        )
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        qs = PacketaProvizePolozka.objects.all().order_by('cas')
        if not options.get('force'):
            qs = qs.filter(id_prodejce__isnull=True)
        if options.get('prodejna_id'):
            qs = qs.filter(prodejna_id=options['prodejna_id'])
        if options.get('date_from'):
            qs = qs.filter(cas__date__gte=parse_date(options['date_from']))
        if options.get('date_to'):
            qs = qs.filter(cas__date__lte=parse_date(options['date_to']))

        total = qs.count()
        updated = 0
        unchanged = 0
        dry_run = options['dry_run']

        self.stdout.write(f'Řádků k přiřazení: {total}')

        for row in qs.iterator(chunk_size=500):
            pid = resolve_prodejce_for_packeta(row.prodejna_id, row.cas)
            if not pid:
                continue
            if row.id_prodejce == pid:
                unchanged += 1
                continue
            if dry_run:
                updated += 1
                continue
            PacketaProvizePolozka.objects.filter(pk=row.pk).update(id_prodejce=pid)
            updated += 1

        suffix = ' [DRY RUN]' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'Přiřazeno/změněno: {updated}, beze změny: {unchanged}{suffix}'
        ))
