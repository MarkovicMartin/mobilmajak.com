"""Testy merge manuálních úprav výplaty."""
from datetime import date
from decimal import Decimal

from django.test import TestCase

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
        self.assertEqual(row['celkem_body'], 24000.0)

    def test_apply_manual_odmena(self):
        from shifts.models import MzdovaOdmenaMesic

        odmena = MzdovaOdmenaMesic.objects.create(
            user=self.user,
            mesic=self.mesic,
            castka=Decimal('500'),
            poznamka='bonus',
        )
        row = apply_manual_adjustments_to_row(self.base_row, odmena_row=odmena)
        self.assertEqual(row['odmena_mesic_body'], 500.0)
        self.assertEqual(row['celkem_body'], 26500.0)
