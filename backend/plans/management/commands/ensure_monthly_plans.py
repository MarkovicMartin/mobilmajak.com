"""
Zajistí hybridní plány pro aktuální a příští měsíc (cron 1. den v měsíci).

Příklad crontab na VPS – viz docs/secrets-setup.md.
"""
from datetime import date

from django.core.management.base import BaseCommand

from plans.plan_service import ensure_plan_mesic, je_mesic_auto_povoleny
from users.models import WebUser


def _system_user():
    return WebUser.objects.filter(role='ADMIN', aktivni=True).order_by('id').first()


class Command(BaseCommand):
    help = 'Vytvoří hybridní plány pro aktuální + příští měsíc (idempotentní).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--rust',
            type=float,
            default=10,
            help='Růst v % oproti YoY baseline (výchozí 10)',
        )
        parser.add_argument(
            '--mesic',
            type=str,
            default=None,
            help='Jeden měsíc YYYY-MM (jinak aktuální + příští)',
        )

    def handle(self, *args, **options):
        user = _system_user()
        if not user:
            self.stderr.write('Chybí aktivní ADMIN uživatel.')
            return

        rust = options['rust']
        mesic_arg = options['mesic']

        if mesic_arg:
            parts = mesic_arg.strip().split('-')
            if len(parts) != 2:
                self.stderr.write('Neplatný formát --mesic (očekáváno YYYY-MM).')
                return
            targets = [(int(parts[0]), int(parts[1]))]
        else:
            today = date.today()
            r, m = today.year, today.month
            if m == 12:
                next_r, next_m = r + 1, 1
            else:
                next_r, next_m = r, m + 1
            targets = [(r, m), (next_r, next_m)]

        for rok, mesic in targets:
            if not je_mesic_auto_povoleny(rok, mesic):
                self.stdout.write(f'Přeskočeno {mesic}/{rok} (minulý měsíc).')
                continue
            res = ensure_plan_mesic(rok, mesic, user, rust_procent=rust)
            if res.get('created'):
                self.stdout.write(
                    self.style.SUCCESS(f'Vytvořen plán {mesic}/{rok} (id={res.get("plan_id")}).')
                )
                for w in res.get('warnings', []):
                    self.stdout.write(f'  ⚠ {w}')
            elif res.get('reason') == 'already_exists':
                self.stdout.write(f'Plán {mesic}/{rok} již existuje.')
            elif res.get('reason') == 'missing_data':
                self.stderr.write(f'{mesic}/{rok}: {res.get("error")}')
            else:
                self.stdout.write(f'{mesic}/{rok}: {res.get("reason", "přeskočeno")}')
