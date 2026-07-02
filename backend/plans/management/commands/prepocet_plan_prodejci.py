"""
Denní přepočet přiřazení prodejců podle směn (hodiny).

Běžící měsíc; poslední den měsíce navíc příští (cron 7:00).

Příklad cron (staging/produkce, 7:00):
  python manage.py prepocet_plan_prodejci

Vynucení všech měsíců roku:
  python manage.py prepocet_plan_prodejci --rok 2026

Vynucení jednoho měsíce:
  python manage.py prepocet_plan_prodejci --mesic 2026-07
"""
from datetime import date

from django.core.management.base import BaseCommand

from plans.prodejci_prepocet import (
    mesice_pro_denni_prepocet,
    prepocet_prodejci_mesice,
)
class Command(BaseCommand):
    help = 'Přepočítá plány prodejců podle směn (hodiny) – denně běžící měsíc.'

    def add_arguments(self, parser):
        parser.add_argument('--rok', type=int, help='Přepočítat všech 12 měsíců daného roku')
        parser.add_argument('--mesic', type=str, help='Jeden měsíc YYYY-MM')
        parser.add_argument(
            '--force',
            action='store_true',
            help='Přepočítat běžící i příští měsíc (i mimo poslední den)',
        )

    def handle(self, *args, **options):
        today = date.today()
        targets = []

        if options.get('mesic'):
            parts = options['mesic'].strip().split('-')
            if len(parts) != 2:
                self.stderr.write('Neplatný formát --mesic (YYYY-MM).')
                return
            targets = [(int(parts[0]), int(parts[1]))]
        elif options.get('rok'):
            rok = int(options['rok'])
            targets = [(rok, m) for m in range(1, 13)]
        elif options.get('force'):
            r, m = today.year, today.month
            targets = [(r, m)]
            if m == 12:
                targets.append((r + 1, 1))
            else:
                targets.append((r, m + 1))
        else:
            targets = mesice_pro_denni_prepocet(today)

        if not targets:
            self.stdout.write('Žádný měsíc k přepočtu.')
            return

        self.stdout.write(
            f'Přepočet prodejců ({today.isoformat()}, den {today.day}): '
            + ', '.join(f'{mm}/{rr}' for rr, mm in targets)
        )

        pr = prepocet_prodejci_mesice(targets, reference=today)
        for v in pr['vysledky']:
            if v.get('prepocet'):
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  {v['mesic']:02d}/{v['rok']}: "
                        f"{v.get('prirazeno_prodejen', 0)} přiřazení"
                    )
                )
                for w in v.get('warnings', []):
                    self.stdout.write(f'    ⚠ {w}')
            else:
                self.stdout.write(f"  {v['mesic']:02d}/{v['rok']}: přeskočeno ({v.get('reason')})")

        self.stdout.write(self.style.SUCCESS(f"Hotovo: {pr['pocet_prepocet']} měsíců přepočteno."))
