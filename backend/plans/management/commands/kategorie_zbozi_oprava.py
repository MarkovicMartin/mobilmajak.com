"""Noční přesun jistých položek ze stránky Kategorie zboží.

Bez --zapis jen vypíše plán. Nejisté kódy se nezapisují a na seznamu zůstávají.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from plans.kategorie_zbozi import produkty_mesice
from plans.kategorie_zbozi_noc import (
    drz_prodeje_lock,
    pockej_na_actory,
    prodejny_zavrene,
    pust_prodeje_lock,
)
from plans.kategorie_zbozi_zarazeni import nacti_katalog, rozhodni


class Command(BaseCommand):
    help = 'Přesune jisté položky Kategorie zboží do existujícího listu. Nejisté nechá.'

    def add_arguments(self, parser):
        parser.add_argument('--zapis', action='store_true', help='Zapsat jisté kategorie do Symplia.')
        parser.add_argument('--force', action='store_true', help='Bez čekání na zavření prodejen a locky.')
        parser.add_argument('--den', help='Jen kódy s posledním prodejem v tento den (RRRR-MM-DD).')

    def handle(self, *args, **options):
        zapis = bool(options['zapis'])
        if zapis and not options['force'] and not prodejny_zavrene():
            self.stdout.write('Prodejny ještě nejsou zavřené, oprava se odkládá.\n')
            return
        polozky = self._polozky(options.get('den'))
        katalog = nacti_katalog()
        jiste = []
        nejiste = []
        for row in polozky:
            rozhod = rozhodni(row['nazev'], row['kod'], katalog)
            rozhod['kod'] = row['kod']
            rozhod['nazev'] = row['nazev']
            (jiste if rozhod['stav'] == 'jiste' else nejiste).append(rozhod)

        self.stdout.write(f'Otevřených {len(polozky)}, jistých {len(jiste)}, nejistých {len(nejiste)}.\n')
        for row in jiste:
            cile = ', '.join(f"{k['id']} {k['nazev']}" for k in row['kategorie'])
            self.stdout.write(f"jisté {row['kod']} → {cile} | {row['nazev'][:90]}\n")
        for row in nejiste:
            self.stdout.write(f"nechávám {row['kod']} ({row['duvod']}) | {row['nazev'][:90]}\n")
        if not zapis:
            self.stdout.write('Bez --zapis se do Symplia nic nezapisuje.\n')
            return
        if not jiste:
            return
        if not options['force'] and not pockej_na_actory():
            self.stdout.write('Actor stále běží, jisté kódy zůstávají na seznamu.\n')
            return
        drz_prodeje_lock()
        try:
            vysledek = self._zapis(jiste)
        finally:
            pust_prodeje_lock()
        self.stdout.write(
            f"Zapsáno {vysledek['zapsano']}, přeskočeno {vysledek['preskoceno']}.\n"
        )

    def _polozky(self, den):
        dnes = timezone.localdate()
        vcera = dnes - timedelta(days=1)
        mesice = {(dnes.year, dnes.month), (vcera.year, vcera.month)}
        podle_kodu = {}
        for rok, mesic in mesice:
            for row in produkty_mesice(rok, mesic):
                if den and str(row.get('posledni_den') or '') != den:
                    continue
                podle_kodu[row['kod']] = row
        return list(podle_kodu.values())

    def _zapis(self, jiste):
        import json
        import subprocess
        from pathlib import Path

        from django.conf import settings

        script = Path(settings.BASE_DIR).parent / 'scripts' / 'symplio-poznamka-fix' / 'zaradit-kategorie.js'
        payload = {
            'polozky': [
                {
                    'kod': row['kod'],
                    'kategorie': [k['id'] for k in row['kategorie']],
                }
                for row in jiste
            ],
        }
        beh = subprocess.run(
            ['node', str(script)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
        )
        if beh.stderr:
            self.stderr.write(beh.stderr)
        if beh.returncode != 0:
            raise RuntimeError(f'Zápis kategorií selhal ({beh.returncode}).')
        data = json.loads(beh.stdout or '{}')
        return {
            'zapsano': int(data.get('zapsano') or 0),
            'preskoceno': int(data.get('preskoceno') or 0),
        }
