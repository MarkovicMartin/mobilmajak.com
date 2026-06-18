from decimal import Decimal

from django.test import TestCase

from analytics.service_commission import (
    catalog_price_for_kod,
    min_commission_unit_price,
    row_qualifies_for_service_extra,
)


class ServiceCommissionTests(TestCase):
    def test_catalog_from_kod_number(self):
        self.assertEqual(catalog_price_for_kod('CT1200'), Decimal('1200'))
        self.assertEqual(catalog_price_for_kod('KOP500'), Decimal('500'))

    def test_x99_prices_qualify(self):
        self.assertTrue(row_qualifies_for_service_extra('CT600', 599))
        self.assertTrue(row_qualifies_for_service_extra('KOP500', 499))
        self.assertTrue(row_qualifies_for_service_extra('ZAH250', 249))

    def test_ten_percent_off_qualifies(self):
        self.assertTrue(row_qualifies_for_service_extra('CT1200', 1080))

    def test_twenty_percent_off_excluded(self):
        min_p = min_commission_unit_price(Decimal('1200'))
        self.assertEqual(min_p, Decimal('960.00'))
        self.assertFalse(row_qualifies_for_service_extra('CT1200', 960))
        self.assertFalse(row_qualifies_for_service_extra('CT1200', 959))

    def test_half_price_excluded(self):
        self.assertFalse(row_qualifies_for_service_extra('CT600', 300))
        self.assertFalse(row_qualifies_for_service_extra('KOP500', 100))

    def test_akt_nap_catalog(self):
        self.assertTrue(row_qualifies_for_service_extra('AKT', 249))
        self.assertFalse(row_qualifies_for_service_extra('AKT', 100))
        self.assertFalse(row_qualifies_for_service_extra('NAP', 1))
