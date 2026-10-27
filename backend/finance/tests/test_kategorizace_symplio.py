"""Testy vestavěných pravidel kategorizace pokladny."""
from datetime import date
from decimal import Decimal

from django.test import TestCase

from finance.kategorizace import apply_builtin_rules
from finance.models import NakladKategorie, NakladPolozka
from finance.services import qs_ceka_na_fakturu


class SymplioKategorizaceTests(TestCase):
    def setUp(self):
        parent, _ = NakladKategorie.objects.get_or_create(
            nazev='Zboží / sklad', defaults={'poradi': 900, 'typ_dph': 'z_faktury'},
        )
        NakladKategorie.objects.get_or_create(
            nazev='Nákup zboží / výkup',
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
        self.assertEqual(r.kategorie_id, NakladKategorie.objects.get(nazev='Nákup zboží / výkup').id)

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
        r = self._apply('Manuální výdej V26070023 Výkup')
        self.assertEqual(r.pravidlo, 'symplio:vykup')
        self.assertFalse(r.ignorovat)
        self.assertEqual(r.stav, NakladPolozka.STAV_ZARAZENO)
        self.assertEqual(r.kategorie_id, NakladKategorie.objects.get(nazev='Nákup zboží / výkup').id)

    def test_uhrada_vykupky(self):
        r = self._apply('Úhrada výkupky V26070012')
        self.assertEqual(r.pravidlo, 'symplio:vykup')
        self.assertFalse(r.ignorovat)
        self.assertEqual(r.kategorie_id, NakladKategorie.objects.get(nazev='Nákup zboží / výkup').id)

    def test_vykup_neni_ve_fronte_faktur(self):
        kat = NakladKategorie.objects.get(nazev='Nákup zboží / výkup')
        NakladPolozka.objects.create(
            datum=date(2026, 10, 21),
            rok=2026,
            mesic=10,
            castka=Decimal('-1500'),
            kategorie=kat,
            stav=NakladPolozka.STAV_ZARAZENO,
            zdroj=NakladPolozka.ZDROJ_SYMPLIO_POKLADNA,
            fio_id='symplio:test:vykup-fa',
            ignorovat=False,
            auto_pravidlo='symplio:vykup',
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            dph_stav=NakladPolozka.DPH_STAV_CEKA,
        )
        NakladPolozka.objects.create(
            datum=date(2026, 10, 21),
            rok=2026,
            mesic=10,
            castka=Decimal('-400'),
            stav=NakladPolozka.STAV_ZARAZENO,
            zdroj=NakladPolozka.ZDROJ_SYMPLIO_POKLADNA,
            fio_id='symplio:test:zbozi-stare',
            ignorovat=False,
            auto_pravidlo='symplio:zbozi',
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            dph_stav=NakladPolozka.DPH_STAV_CEKA,
        )
        NakladPolozka.objects.create(
            datum=date(2026, 10, 23),
            rok=2026,
            mesic=10,
            castka=Decimal('-400'),
            stav=NakladPolozka.STAV_ZARAZENO,
            zdroj=NakladPolozka.ZDROJ_SYMPLIO_POKLADNA,
            fio_id='symplio:test:zbozi-fa',
            ignorovat=False,
            auto_pravidlo='symplio:zbozi',
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            dph_stav=NakladPolozka.DPH_STAV_CEKA,
        )
        ids = set(qs_ceka_na_fakturu().values_list('fio_id', flat=True))
        self.assertNotIn('symplio:test:vykup-fa', ids)
        self.assertNotIn('symplio:test:zbozi-stare', ids)
        self.assertIn('symplio:test:zbozi-fa', ids)
