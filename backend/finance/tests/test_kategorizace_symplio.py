"""Testy vestavěných pravidel kategorizace pokladny."""
from django.test import TestCase

from finance.kategorizace import apply_builtin_rules
from finance.models import NakladKategorie, NakladPolozka


class SymplioKategorizaceTests(TestCase):
    def setUp(self):
        parent, _ = NakladKategorie.objects.get_or_create(
            nazev='Zboží / sklad', defaults={'poradi': 900, 'typ_dph': 'z_faktury'},
        )
        NakladKategorie.objects.get_or_create(
            nazev='Zboží – nákup sklad',
            defaults={'poradi': 901, 'typ_dph': 'z_faktury', 'parent': parent},
        )
        NakladKategorie.objects.get_or_create(
            nazev='Spotřeba prodejny', defaults={'poradi': 800, 'typ_dph': 'z_faktury'},
        )

    def _apply(self, popis, prodejna_id=6):
        row = {'popis': popis, 'zprava': 'Admin'}
        return apply_builtin_rules(
            row, zdroj=NakladPolozka.ZDROJ_SYMPLIO_POKLADNA, prodejna_id=prodejna_id,
        )

    def test_zbozi_manualni_vydej(self):
        r = self._apply('Manuální výdej PANFICO s.r.o. Zboží 26220383')
        self.assertEqual(r.pravidlo, 'symplio:zbozi')
        self.assertEqual(r.prodejna_id, 6)
        self.assertEqual(r.kategorie_id, NakladKategorie.objects.get(nazev='Zboží – nákup sklad').id)

    def test_dily(self):
        r = self._apply('Manuální výdej Bakr s.r.o díly/zboží 2126020761')
        self.assertEqual(r.pravidlo, 'symplio:zbozi')

    def test_spotreba(self):
        r = self._apply('Manuální výdej Tesco Stores ČR a.s. spotřeba')
        self.assertEqual(r.pravidlo, 'symplio:spotreba')
        self.assertEqual(r.kategorie_id, NakladKategorie.objects.get(nazev='Spotřeba prodejny').id)

    def test_prevod_pokladny_ignore(self):
        r = self._apply('Převod do pokladny Pokladna Lucka (id8)')
        self.assertTrue(r.ignorovat)
        self.assertEqual(r.pravidlo, 'symplio:prevod_pokladna')

    def test_vklad_na_ucet_ignore(self):
        r = self._apply('Manuální výdej vklad hotovosti na účet')
        self.assertTrue(r.ignorovat)
        self.assertEqual(r.pravidlo, 'symplio:vklad_na_ucet')

    def test_manualni_vydej_vykup(self):
        NakladKategorie.objects.get_or_create(
            nazev='Výkup',
            defaults={'poradi': 903, 'typ_dph': 'bez'},
        )
        r = self._apply('Manuální výdej V26070023 Výkup')
        self.assertEqual(r.pravidlo, 'symplio:vykup')
        self.assertEqual(r.kategorie_id, NakladKategorie.objects.get(nazev='Výkup').id)
        self.assertEqual(r.prodejna_id, 6)
