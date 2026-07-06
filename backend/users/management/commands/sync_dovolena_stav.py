"""Synchronizace skutečného stavu dovolené z JSON souboru."""
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from shifts.dovolena_sync import apply_dovolena_targets, normalize_prijmeni
from users.models import WebUser

DEFAULT_DATA = Path(__file__).resolve().parents[3] / 'shifts' / 'data' / 'dovolena_stav_2026-06.json'


class Command(BaseCommand):
    help = 'Nastaví fond a čerpání dovolené dle JSON tabulky (fond_h / cerpano_h / zbyva_h).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data',
            default=str(DEFAULT_DATA),
            help='Cesta k JSON (výchozí: shifts/data/dovolena_stav_2026-06.json)',
        )
        parser.add_argument('--rok', type=int, help='Rok (výchozí: z JSON nebo aktuální)')
        parser.add_argument('--dry-run', action='store_true', help='Jen vypsat změny')

    def handle(self, *args, **options):
        data_path = Path(options['data'])
        with data_path.open(encoding='utf-8') as f:
            payload = json.load(f)

        rok = options['rok'] or payload.get('rok')
        targets = payload.get('uzivatele') or {}
        dry = options['dry_run']
        missing = []
        skipped = []

        qs = WebUser.objects.filter(aktivni=True, role__in=('PRODEJCE', 'VEDOUCI'))

        by_prijmeni = {}
        for user in qs:
            by_prijmeni[normalize_prijmeni(user.prijmeni)] = user

        for prijmeni, row in targets.items():
            user = by_prijmeni.get(normalize_prijmeni(prijmeni))
            if not user:
                missing.append(prijmeni)
                continue

            try:
                result = apply_dovolena_targets(
                    user,
                    rok,
                    row['fond_h'],
                    row['cerpano_h'],
                    zbyva_h=row.get('zbyva_h'),
                    dry_run=dry,
                )
            except ValueError as exc:
                self.stderr.write(self.style.ERROR(str(exc)))
                continue

            b, a = result['before'], result['after']
            if (
                b.get('fond_h') == a['fond_h']
                and b.get('cerpano_h') == a['cerpano_h']
                and b.get('zbyva_h') == a['zbyva_h']
            ):
                skipped.append(prijmeni)
                self.stdout.write(f"  {prijmeni}: beze změny ({a['zbyva_h']} h zbývá)")
                continue

            self.stdout.write(
                f"  {prijmeni}: fond {b.get('fond_h')}→{a['fond_h']} h, "
                f"čerpáno {b.get('cerpano_h')}→{a['cerpano_h']} h, "
                f"zbývá {b.get('zbyva_h')}→{a['zbyva_h']} h "
                f"(extra fond {result['fond_extra']:+.0f}, korekce čerpání {result['korekce_cerpano']:+.0f})"
            )

        if missing:
            self.stderr.write(self.style.WARNING(f'Nenalezeni: {", ".join(missing)}'))
        if skipped and not dry:
            self.stdout.write(f'Beze změny: {len(skipped)}')
        if dry:
            self.stdout.write(self.style.WARNING('Dry-run – nic neuloženo'))
        else:
            self.stdout.write(self.style.SUCCESS('Hotovo'))
