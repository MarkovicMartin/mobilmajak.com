"""Poměrný základ mzdy – shoda s Excel modelem."""
from decimal import Decimal

from django.test import TestCase

from shifts.labor_hours import fondu_hodin_mesic
from shifts.payroll_service import prescas_body_vypocet, zaklad_pomerovy_body
from users.models import WebUser


class PomerovyZakladTests(TestCase):
    def setUp(self):
        self.user = WebUser.objects.create(
            id=99002,
            uzivatelske_jmeno='test_pomer_zaklad',
            jmeno='Test',
            prijmeni='Prodejce',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            mzda_zaklad=Decimal('16000'),
            mzda_doplnky=[
                {'kod': 'a', 'nazev': 'Bonus', 'castka': 1000},
                {'kod': 'b', 'nazev': 'Vedoucí', 'castka': 2000},
            ],
        )

    def test_gabriel_june_model(self):
        """19000 × 163/176 ≈ 17597 jako v Excelu."""
        fond = fondu_hodin_mesic(2026, 6)
        body = zaklad_pomerovy_body(self.user, 163, fond)
        expected = (Decimal('19000') * Decimal('163') / Decimal(str(fond))).quantize(Decimal('1'))
        self.assertEqual(body, expected)
        self.assertEqual(body, Decimal('17597'))

    def test_pomerovy_plus_prescas_rovna_celkem(self):
        fond = fondu_hodin_mesic(2026, 3)
        h = Decimal('181')
        prescas_h = h - Decimal(str(fond))
        pomer = zaklad_pomerovy_body(self.user, float(h), fond)
        prescas_body, _, _ = prescas_body_vypocet(self.user, float(prescas_h), fond)
        celkem = pomer + prescas_body
        expected = (Decimal('19000') * h / Decimal(str(fond))).quantize(Decimal('1'))
        self.assertEqual(celkem, expected)
