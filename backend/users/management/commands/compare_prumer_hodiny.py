"""Porovnání hodin z Excel override vs. směny v systému (průměr dovolené)."""
from django.core.management.base import BaseCommand
from django.db.models import Q

from shifts.payroll_service import _odpracovano_h_mesic, prumer_fixni_hodinove_detail
from shifts.prumer_mzdy_override import load_prumer_mzdy_overrides, prumer_override_for_user
from shifts.vacation_service import _reference_month_for_prumer, is_dovolena_eligible
from users.models import WebUser


class Command(BaseCommand):
    help = 'Vypíše rozdíl hodin: tabulka (override) vs. směny v MOBILMAJAK.'

    def add_arguments(self, parser):
        parser.add_argument('--rok', type=int, default=2025)
        parser.add_argument('--mesic', type=int, help='Referenční měsíc (výchozí: aktuální v roce)')
        parser.add_argument('--jen-rozdily', action='store_true', help='Jen řádky s |rozdíl| > 0.5 h')

    def handle(self, *args, **options):
        rok = options['rok']
        ref_mesic = options['mesic']
        if not ref_mesic:
            from datetime import date
            ref_mesic = _reference_month_for_prumer(rok, date.today())

        overrides = load_prumer_mzdy_overrides()
        if not overrides:
            self.stderr.write('Chybí shifts/data/prumer_mzdy_override.json')
            return

        qs = WebUser.objects.filter(aktivni=True).filter(
            Q(role__in=('PRODEJCE', 'VEDOUCI'))
            | Q(jmeno__iexact='Martin', prijmeni__iexact='Markovič')
        ).order_by('prijmeni')

        self.stdout.write(f'Průměr dovolené – kontrola hodin (rok {rok}, ref. měsíc {ref_mesic})')
        self.stdout.write('')

        for user in qs:
            if not is_dovolena_eligible(user):
                continue
            override = prumer_override_for_user(user)
            if not override:
                continue

            detail = prumer_fixni_hodinove_detail(user, rok, ref_mesic, override_mesice=override)
            lines = []
            for m in detail['mesice']:
                excel_h = m['odpracovano_h']
                smeny_h = m.get('odpracovano_h_smeny')
                if smeny_h is None:
                    smeny_h = float(_odpracovano_h_mesic(user.id, m['rok'], m['mesic']))
                diff = round(excel_h - smeny_h, 2)
                if options['jen_rozdily'] and abs(diff) <= 0.5:
                    continue
                status = 'OK' if abs(diff) <= 0.5 else 'ROZDÍL'
                lines.append(
                    f"  {m['mesic']:02d}/{m['rok']}: tabulka {excel_h:.1f} h, "
                    f"směny {smeny_h:.1f} h, Δ {diff:+.1f} h [{status}]"
                )

            if not lines:
                if options['jen_rozdily']:
                    continue
                lines.append('  (žádná data)')

            self.stdout.write(
                f"{user.prijmeni}: průměr {detail['prumer_fixni_h']:.0f} bodů/h "
                f"({detail['celkem_h']:.0f} h / {detail['celkem_fixni']:.0f} bodů fixní)"
            )
            for line in lines:
                self.stdout.write(line)
            self.stdout.write('')
