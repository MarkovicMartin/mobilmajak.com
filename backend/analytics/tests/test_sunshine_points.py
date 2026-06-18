"""Testy bodů za SUNSHINE fólie."""
from django.test import SimpleTestCase

from analytics.points_config import calculate_product_points, build_product_points_breakdown
from analytics.sunshine_config import (
    SUNSHINE_POINTS_PER_UNIT,
    calculate_sunshine_points,
    prolepenost_pct,
    prolepenost_zaklad_kusy,
    sunshine_bonus_row_q,
    sunshine_row_q,
)


class SunshinePointsTests(SimpleTestCase):
    def test_calculate_sunshine_points(self):
        self.assertEqual(calculate_sunshine_points(0), 0)
        self.assertEqual(calculate_sunshine_points(4), 4 * SUNSHINE_POINTS_PER_UNIT)

    def test_calculate_product_points_includes_sunshine(self):
        data = {
            'polozky_nad_100': 2,
            'ct600': 0,
            'ct1200': 0,
            'akt': 0,
            'zah250': 0,
            'zah500': 0,
            'kop250': 0,
            'kop500': 0,
            'nap': 0,
            'pz1': 0,
            'knz': 0,
            'aligator': 0,
            'sunshine': 4,
        }
        # 2×15 položky + 4×15 sunshine
        self.assertEqual(calculate_product_points(data), 30 + 60)

    def test_breakdown_sunshine_line(self):
        data = {'sunshine': 3, 'polozky_nad_100': 0}
        breakdown = build_product_points_breakdown(data)
        self.assertEqual(breakdown['sunshine']['count'], 3)
        self.assertEqual(breakdown['sunshine']['points'], 45)

    def test_sunshine_row_q_matches_name(self):
        self.assertIn('SUNSHINE', str(sunshine_row_q()))

    def test_sunshine_bonus_row_q_requires_price_at_least_100(self):
        self.assertIn('gte', str(sunshine_bonus_row_q()).lower())

    def test_prolepenost_includes_sunshine_in_denominator(self):
        self.assertEqual(prolepenost_zaklad_kusy(10, 5), 15)
        self.assertEqual(prolepenost_pct(6, 10, 5), 40.0)
        self.assertEqual(prolepenost_pct(12, 10, 0), 120.0)
        self.assertEqual(prolepenost_pct(12, 10, 5), 80.0)
        self.assertIsNone(prolepenost_pct(5, 0, 0))
