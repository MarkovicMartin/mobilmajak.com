"""Testy merge manuálních úprav výplaty."""
from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from shifts.models import MzdovaPenalizaceMesic
from shifts.payroll_manual import (
    apply_manual_adjustments_to_row,
    merge_manual_into_rows,
    strip_manual_adjustments_from_row,
)
from users.models import WebUser


class PayrollManualMergeTests(TestCase):
    def setUp(self):
        self.user = WebUser.objects.create(
            id=99001,
            uzivatelske_jmeno='test_manual_payroll',
            jmeno='Test',
            prijmeni='Prodejce',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            mzda_zaklad=Decimal('14000'),
            mzda_doplnky=[],
        )
        self.mesic = date(2026, 6, 1)
        self.base_row = {
            'user_id': self.user.id,
            'mzda_fixni_body': 16000.0,
            'provize_body_brutto': 10000.0,
            'provize_body': 10000.0,
            'dovolena_body': 0.0,
            'prescas_body': 0.0,
            'cestovne_body': 0.0,
            'dyska_body': 0.0,
            'pol_dok_odmena_body': 0.0,
            'celkem_body': 26000.0,
        }

    def test_strip_then_merge_penalizace(self):
        MzdovaPenalizaceMesic.objects.create(
            user=self.user,
            mesic=self.mesic,
            typ=MzdovaPenalizaceMesic.TYP_PROCENTA,
            hodnota=Decimal('20'),
            duvod='Test srážka',
        )
        stripped = strip_manual_adjustments_from_row(self.base_row)
        self.assertEqual(stripped['provize_body'], 10000.0)
        self.assertEqual(stripped['penalizace_srazka_body'], 0.0)
        self.assertEqual(stripped['celkem_body'], 26000.0)

        merged, revision = merge_manual_into_rows([stripped], '2026-06')
        self.assertTrue(revision)
        row = merged[0]
        self.assertEqual(row['penalizace_srazka_body'], 2000.0)
        self.assertEqual(row['provize_body'], 8000.0)
        self.assertEqual(row['penalizace'][0]['srazka_body'], 2000.0)
        self.assertEqual(row['celkem_body'], 24000.0)

    def test_apply_manual_odmena(self):
        from shifts.models import MzdovaOdmenaMesic

        odmena = MzdovaOdmenaMesic.objects.create(
            user=self.user,
            mesic=self.mesic,
            castka=Decimal('500'),
            poznamka='bonus',
        )
        row = apply_manual_adjustments_to_row(self.base_row, odmeny_rows=[odmena])
        self.assertEqual(row['odmena_mesic_body'], 500.0)
        self.assertEqual(len(row['odmeny']), 1)
        self.assertEqual(row['odmeny'][0]['poznamka'], 'bonus')
        self.assertEqual(row['celkem_body'], 26500.0)


class PayrollPenalizaceApiTests(TestCase):
    def setUp(self):
        self.admin = WebUser.objects.create(
            id=99002,
            uzivatelske_jmeno='admin_penalizace_test',
            jmeno='Admin',
            prijmeni='Test',
            heslo='x',
            role='ADMIN',
            aktivni=True,
        )
        self.prodejce = WebUser.objects.create(
            id=99003,
            uzivatelske_jmeno='prodejce_penalizace_test',
            jmeno='Jan',
            prijmeni='Létal',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            mzda_zaklad=Decimal('14000'),
            mzda_doplnky=[],
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_post_penalizace_past_month_sets_vytvoril_webuser(self):
        res = self.client.post(
            '/api/shifts/payroll/penalizace/',
            {
                'user_id': self.prodejce.id,
                'mesic': '2026-06',
                'polozky': [{'typ': 'procenta', 'hodnota': 20, 'duvod': 'výkupy'}],
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.content)
        row = MzdovaPenalizaceMesic.objects.get(user=self.prodejce, mesic=date(2026, 6, 1), duvod='výkupy')
        self.assertEqual(row.vytvoril_id, self.admin.id)
        self.assertEqual(res.json()['count'], 1)

    def test_post_odmena_creates_row_with_vytvoril(self):
        from shifts.models import MzdovaOdmenaMesic

        res = self.client.post(
            '/api/shifts/payroll/odmena/',
            {
                'user_id': self.prodejce.id,
                'mesic': '2026-06',
                'castka': 500,
                'poznamka': 'Nevyčerpaná dovolená',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.content)
        row = MzdovaOdmenaMesic.objects.get(user=self.prodejce, mesic=date(2026, 6, 1), poznamka='Nevyčerpaná dovolená')
        self.assertEqual(row.vytvoril_id, self.admin.id)
        self.assertEqual(float(row.castka), 500.0)
