"""Sunshine pod 100 Kč se nepočítá do provize ve výplatě."""
from datetime import date
from decimal import Decimal

from django.test import TestCase

from analytics.models import WebProdejeAll
from shifts.payroll_points_batch import batch_sales_metrics_for_month
from shifts.payroll_service import build_payroll_row
from stores.models import Prodejna
from users.models import WebUser


class SunshineUnder100PayrollTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.prodejna = Prodejna.objects.create(
            nazev='Test Sunshine', nazev_kratkiy='TSU', aktivni=True,
        )
        cls.user = WebUser.objects.create(
            uzivatelske_jmeno='sunshine_under_100',
            jmeno='Sun',
            prijmeni='Shine',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=cls.prodejna.id,
            mzda_zaklad=Decimal('14000'),
        )

    def _sale(self, nazev, cena, kusy=1, kod='P100'):
        WebProdejeAll.objects.create(
            typ=date(2026, 6, 15),
            doklad=f'UCT-{nazev}-{cena}-{kusy}',
            kod=kod,
            nazev=nazev,
            pocet_kusu=kusy,
            cena_ks_vcl_dph=Decimal(str(cena)),
            id_prodejce=self.user.id,
            stredisko='Test',
        )

    def test_under_100_not_in_sunshine_bonus_metrics(self):
        self._sale('SUNSHINE fólie', 50, kusy=2)
        self._sale('SUNSHINE fólie', 150, kusy=1)
        metrics = batch_sales_metrics_for_month(2026, 6, [self.user.id])
        self.assertEqual(metrics[self.user.id]['sunshine'], 1)

    def test_build_payroll_row_no_sunshine_points_for_under_100(self):
        self._sale('SUNSHINE fólie', 50, kusy=2)
        metrics = batch_sales_metrics_for_month(2026, 6, [self.user.id])
        row = build_payroll_row(
            self.user, 2026, 6,
            {self.user.id: {'odpracovano_h': 160, 'dovolena_h': 0, 'nemoc_h': 0, 'svatek_h': 0}},
            date(2026, 6, 1),
            {self.prodejna.id: 'Test Sunshine'},
            160,
            metrics, {}, {},
        )
        breakdown = row['provize_breakdown'] or {}
        self.assertEqual((breakdown.get('sunshine') or {}).get('count'), 0)
        self.assertEqual((breakdown.get('sunshine') or {}).get('points'), 0)
