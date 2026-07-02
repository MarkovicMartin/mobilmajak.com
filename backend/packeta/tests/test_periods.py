"""Testy období Packeta importu."""
from datetime import date, timedelta

from django.test import TestCase

from packeta.packeta_fetch import date_range_for_period, date_range_today, date_range_yesterday


class DateRangePeriodTests(TestCase):
    def test_today(self):
        start, end = date_range_today()
        self.assertEqual(start, end)
        self.assertEqual(start, date.today())

    def test_yesterday(self):
        start, end = date_range_yesterday()
        expected = date.today() - timedelta(days=1)
        self.assertEqual(start, expected)
        self.assertEqual(end, expected)

    def test_for_period_today(self):
        self.assertEqual(date_range_for_period('today'), date_range_today())
