"""Import objednávek z Mastersheet (list Díly) – bootstrap JSON."""

import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from orders.models import Order, OrderStatusHistory
from stores.models import Prodejna
from users.models import WebUser

BOOTSTRAP_JSON = Path(__file__).resolve().parents[2] / 'bootstrap' / 'mastersheet_dily.json'
TZ = ZoneInfo('Europe/Prague')
FALLBACK_USER_ID = 999  # Markovič – jen když CSV nemá „Zadal“

PRODEJNA_ALIASES = {
    'globus': 'Globus',
    'senimo': 'Senimo',
    'senimou': 'Senimo',
    'čepkov': 'Čepkov',
    'cepkov': 'Čepkov',
    'zlín - čepkov': 'Čepkov',
    'zlin - cepkov': 'Čepkov',
    'přerov': 'Přerov',
    'prerov': 'Přerov',
    'vsetín': 'Vsetín',
    'vsetin': 'Vsetín',
    'šternberk': 'Šternberk',
    'sternberk': 'Šternberk',
}

# „Valenta“ v Mastersheetu = Tomáš Valenta (ne Petr)
ZADAL_USER_ID = {
    'karas': 24,
    'létal': 5,
    'letal': 5,
    'valenta': 4,
    'krumpolc': 9,
    'křížková': 20,
    'krizkova': 20,
    'málek': 3,
    'malek': 3,
    'gabriel': 2,
}


def _norm(s):
    return (s or '').strip()


def _parse_cena(val):
    if val is None or val == '':
        return None
    try:
        return Decimal(str(val).replace(',', '.').strip())
    except (InvalidOperation, ValueError):
        return None


def _resolve_prodejna(name, cache):
    key = _norm(name).lower()
    if not key:
        return None
    alias = PRODEJNA_ALIASES.get(key, _norm(name))
    if alias in cache:
        return cache[alias]
    for p in Prodejna.objects.all():
        labels = {
            _norm(p.nazev).lower(),
            _norm(getattr(p, 'nazev_kratkiy', '') or '').lower(),
            _norm(getattr(p, 'nazev_google_sheets', '') or '').lower(),
        }
        if alias.lower() in labels or alias.lower() in ' '.join(labels):
            cache[alias] = p
            return p
        if 'čepkov' in alias.lower() and 'čepkov' in (p.nazev or '').lower():
            cache[alias] = p
            return p
    return None


def _resolve_user(zadal, users_by_prijmeni):
    key = _norm(zadal).lower()
    if not key:
        return WebUser.objects.get(pk=FALLBACK_USER_ID)
    if key in ZADAL_USER_ID:
        return WebUser.objects.get(pk=ZADAL_USER_ID[key])
    matches = users_by_prijmeni.get(key, [])
    if len(matches) == 1:
        return matches[0]
    if matches:
        # Prefer aktivní ne-ADMIN při shodě příjmení
        preferred = [u for u in matches if u.aktivni and u.role != 'ADMIN']
        return preferred[0] if preferred else matches[0]
    return WebUser.objects.get(pk=FALLBACK_USER_ID)


def _build_poznamka(item):
    parts = []
    if item.get('cena_poznamka'):
        parts.append(f"Cena z listu: {item['cena_poznamka']}")
    note = _norm(item.get('poznamka'))
    if note:
        parts.append(note)
    return '; '.join(parts) if parts else ''


class Command(BaseCommand):
    help = 'Import objednávek z Mastersheet listu Díly (bootstrap JSON).'

    def add_arguments(self, parser):
        parser.add_argument('--json', type=str, default='')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Před importem smaže všechny objednávky (a historii).',
        )

    def handle(self, *args, **options):
        json_path = Path(options['json']) if options['json'] else BOOTSTRAP_JSON
        if not json_path.is_file():
            self.stderr.write(self.style.ERROR(f'Nenalezen JSON: {json_path}'))
            return

        items = json.loads(json_path.read_text(encoding='utf-8'))
        self.stdout.write(f'Čtu {json_path} ({len(items)} řádků)')

        users_by_prijmeni = {}
        for u in WebUser.objects.all():
            users_by_prijmeni.setdefault(_norm(u.prijmeni).lower(), []).append(u)
        prodejna_cache = {}

        prepared = []
        for i, item in enumerate(items, start=1):
            user = _resolve_user(item.get('zadal'), users_by_prijmeni)
            prodejna = _resolve_prodejna(item.get('prodejna'), prodejna_cache)
            datum_raw = item.get('datum')
            if datum_raw:
                dt = datetime.strptime(datum_raw, '%Y-%m-%d').replace(
                    hour=12, minute=0, second=0, tzinfo=TZ,
                )
            else:
                dt = timezone.now()
            prepared.append({
                'idx': i,
                'user': user,
                'prodejna': prodejna,
                'datum': dt,
                'status': item.get('status') or 'nove',
                'fields': {
                    'jmeno_zakaznika': _norm(item.get('jmeno_zakaznika')),
                    'prijmeni_zakaznika': _norm(item.get('prijmeni_zakaznika')),
                    'telefon_zakaznika': _norm(item.get('telefon_zakaznika')),
                    'typ_telefonu': _norm(item.get('typ_telefonu'))[:100],
                    'dil': _norm(item.get('dil'))[:100],
                    'barva': _norm(item.get('barva'))[:50] or None,
                    'servisni_cislo': _norm(item.get('servisni_cislo'))[:50] or None,
                    'cena': _parse_cena(item.get('cena')),
                    'dodavatel': _norm(item.get('dodavatel'))[:100] or None,
                    'poznamka': _build_poznamka(item) or None,
                    'status': item.get('status') or 'nove',
                },
            })

        if options['dry_run']:
            for row in prepared:
                p = row['prodejna']
                self.stdout.write(
                    f"  {row['idx']:02d} {row['fields']['status']:14s} "
                    f"{row['fields']['typ_telefonu'][:28]:28s} "
                    f"zadal={row['user'].prijmeni} "
                    f"prodejna={p.nazev if p else '-'}"
                )
            self.stdout.write(self.style.WARNING('DRY RUN – nic nezapsáno'))
            return

        existing = Order.objects.count()
        if existing and not options['clear']:
            self.stderr.write(self.style.ERROR(
                f'DB už má {existing} objednávek. Použij --clear nebo nejdřív vyčisti.'
            ))
            return

        with transaction.atomic():
            if options['clear']:
                deleted_h, _ = OrderStatusHistory.objects.all().delete()
                deleted_o, _ = Order.objects.all().delete()
                self.stdout.write(f'Smazáno objednávek={deleted_o}, historie={deleted_h}')

            created = 0
            for row in prepared:
                order = Order(
                    zalozil=row['user'],
                    posledni_zmena_uzivatel=row['user'],
                    prodejna=row['prodejna'],
                    **row['fields'],
                )
                order.save()
                Order.objects.filter(pk=order.pk).update(
                    datum_vytvoreni=row['datum'],
                    datum_aktualizace=row['datum'],
                )
                OrderStatusHistory.objects.create(
                    objednavka=order,
                    puvodni_status='',
                    novy_status=row['status'],
                    uzivatel=row['user'],
                    poznamka='Import z Mastersheet (Díly)',
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Hotovo: {created} objednávek (celkem {Order.objects.count()})'
        ))
