"""Testy modelů finance modulu."""
from datetime import date
from decimal import Decimal

from django.test import TestCase

from finance.models import FinanceDoklad, FinanceZustatek, NakladKategorie, NakladPolozka


class NakladPolozkaModelTests(TestCase):
    def test_create_outgoing_with_dph_stav(self):
        p = NakladPolozka.objects.create(
            datum=date(2026, 1, 15),
            rok=2026,
            mesic=1,
            castka=Decimal('-1000'),
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            dph_stav=NakladPolozka.DPH_STAV_CEKA,
            zdroj=NakladPolozka.ZDROJ_FIO,
            fio_id='test-fio-1',
        )
        self.assertEqual(p.dph_stav, NakladPolozka.DPH_STAV_CEKA)
        self.assertIsNone(p.castka_bez_dph)

    def test_symplio_zdroj_choice(self):
        self.assertIn(
            NakladPolozka.ZDROJ_SYMPLIO_POKLADNA,
            [c[0] for c in NakladPolozka.ZDROJ_CHOICES],
        )


class NakladKategorieTypDphTests(TestCase):
    def test_mzdy_bez_dph(self):
        kat = NakladKategorie.objects.create(
            nazev='Test Mzdy',
            typ_dph=NakladKategorie.TYP_DPH_BEZ,
        )
        self.assertEqual(kat.typ_dph, NakladKategorie.TYP_DPH_BEZ)


class FinanceDokladScaffoldTests(TestCase):
    def test_create_nova_doklad(self):
        d = FinanceDoklad.objects.create(
            dodavatel_nazev='Dodavatel s.r.o.',
            cislo_faktury='FA2026001',
            stav=FinanceDoklad.STAV_NOVA,
        )
        self.assertEqual(d.stav, FinanceDoklad.STAV_NOVA)


class FinanceZustatekTests(TestCase):
    def test_fio_snapshot(self):
        z = FinanceZustatek.objects.create(
            datum=date.today(),
            typ=FinanceZustatek.TYP_FIO,
            label='main',
            castka=Decimal('150000.50'),
        )
        self.assertEqual(z.typ, FinanceZustatek.TYP_FIO)
