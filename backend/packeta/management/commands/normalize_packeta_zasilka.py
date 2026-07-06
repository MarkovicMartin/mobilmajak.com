"""Normalizuje zasilka v DB – odstraní mezery (jednorázový backfill po změně importu)."""
from django.core.management.base import BaseCommand
from django.db import transaction

from packeta.models import PacketaProvizePolozka
from packeta.packeta_parser import normalize_zasilka


class Command(BaseCommand):
    help = 'Odstraní mezery ze sloupce zasilka u všech Packeta provizí'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Jen vypsat změny')
        parser.add_argument('--batch-size', type=int, default=500, help='Velikost dávky bulk_update')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = max(50, options['batch_size'])
        updated = deleted = skipped = 0
        to_update: list[PacketaProvizePolozka] = []

        for obj in PacketaProvizePolozka.objects.iterator(chunk_size=batch_size):
            norm = normalize_zasilka(obj.zasilka)
            if norm == obj.zasilka:
                skipped += 1
                continue
            if dry_run:
                updated += 1
                if updated <= 20:
                    self.stdout.write(f'  {obj.pk}: {obj.zasilka!r} → {norm!r}')
                continue
            obj.zasilka = norm
            to_update.append(obj)
            if len(to_update) >= batch_size:
                updated += self._flush_updates(to_update)
                to_update = []

        if to_update and not dry_run:
            updated += self._flush_updates(to_update)

        if not dry_run:
            deleted = self._remove_duplicates()

        suffix = ' [DRY RUN]' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'Hotovo{suffix}: upraveno {updated}, smazáno duplicit {deleted}, '
            f'beze změny {skipped}'
        ))

    def _flush_updates(self, objs: list[PacketaProvizePolozka]) -> int:
        with transaction.atomic():
            PacketaProvizePolozka.objects.bulk_update(objs, ['zasilka'])
        return len(objs)

    def _remove_duplicates(self) -> int:
        deleted = 0
        seen: set[tuple[int, str, str, object]] = set()
        for obj in PacketaProvizePolozka.objects.order_by('pk').iterator(chunk_size=1000):
            key = (obj.prodejna_id, obj.zasilka, obj.typ_provize, obj.cas)
            if key in seen:
                obj.delete()
                deleted += 1
            else:
                seen.add(key)
        return deleted
