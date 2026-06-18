"""Bonus/penalizace za průměr položek/účtenku ve výplatě."""
from datetime import date
from decimal import Decimal

from django.test import TestCase

from analytics.models import WebProdejeAll
from shifts.payroll_points_batch import batch_pol_dok_for_month
from shifts.payroll_service import build_payroll_row, pol_dok_odmena_body
from stores.models import Prodejna
from users.models import WebUser


class PolDokOdmenaTests(TestCase):
    def test_nad_dva_bonus(self):
        self.assertEqual(pol_dok_odmena_body(2.5, 10), Decimal('1000'))

    def test_pod_dva_penalizace(self):
        self.assertEqual(pol_dok_odmena_body(1.9, 10), Decimal('-1000'))

    def test_presne_dva_nula(self):
        self.assertEqual(pol_dok_odmena_body(2.0, 10), Decimal('0'))

    def test_bez_uctenek_nula(self):
        self.assertEqual(pol_dok_odmena_body(0, 0), Decimal('0'))


class PolDokPayrollRowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.prodejna = Prodejna.objects.create(
            nazev='Test PolDok', nazev_kratkiy='TPD', aktivni=True,
        )
        cls.user = WebUser.objects.create(
            uzivatelske_jmeno='pol_dok_pay',
            jmeno='Pol',
            prijmeni='Dok',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=cls.prodejna.id,
            mzda_zaklad=Decimal('14000'),
        )

    def _sale(self, doklad, kod='P100', cena=199, kusy=1):
        WebProdejeAll.objects.create(
            typ=date(2026, 6, 15),
            doklad=doklad,
            kod=kod,
            nazev='Položka',
            pocet_kusu=kusy,
            cena_ks_vcl_dph=Decimal(str(cena)),
            id_prodejce=self.user.id,
            stredisko='Test',
        )

    def test_build_payroll_row_includes_pol_dok_bonus(self):
        self._sale('UCT1', kusy=3)
        pol_dok_map = batch_pol_dok_for_month(2026, 6, [self.user.id])
        row = build_payroll_row(
            self.user, 2026, 6,
            {self.user.id: {'odpracovano_h': 160, 'dovolena_h': 0, 'nemoc_h': 0, 'svatek_h': 0}},
            date(2026, 6, 1),
            {self.prodejna.id: 'Test PolDok'},
            160,
            {}, {}, {},
            pol_dok_map=pol_dok_map,
        )
        self.assertGreater(row['pol_dok'], 2)
        self.assertEqual(row['pol_dok_odmena_body'], 1000.0)
        self.assertEqual(
            row['celkem_body'],
            row['mzda_fixni_body'] + row['provize_body'] + row['odmena_mesic_body']
            + row['dovolena_body'] + row['prescas_body'] + row['cestovne_body']
            + row.get('dyska_body', 0) + row['pol_dok_odmena_body'],
        )

    def test_build_payroll_row_includes_pol_dok_penalizace(self):
        self._sale('UCT1', kusy=1)
        pol_dok_map = batch_pol_dok_for_month(2026, 6, [self.user.id])
        row = build_payroll_row(
            self.user, 2026, 6,
            {self.user.id: {'odpracovano_h': 160, 'dovolena_h': 0, 'nemoc_h': 0, 'svatek_h': 0}},
            date(2026, 6, 1),
            {self.prodejna.id: 'Test PolDok'},
            160,
            {}, {}, {},
            pol_dok_map=pol_dok_map,
        )
        self.assertLess(row['pol_dok'], 2)
        self.assertEqual(row['pol_dok_odmena_body'], -1000.0)
