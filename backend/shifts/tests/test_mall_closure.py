from datetime import date

from django.test import SimpleTestCase

from shifts.mall_closure import closure_kind_for_date


class MallClosureTests(SimpleTestCase):
    def test_always_closed(self):
        self.assertEqual(closure_kind_for_date(date(2026, 1, 1)), 'always_closed')
        self.assertEqual(closure_kind_for_date(date(2026, 12, 25)), 'always_closed')
        self.assertEqual(closure_kind_for_date(date(2026, 12, 26)), 'always_closed')

    def test_nc_verify_closed(self):
        self.assertEqual(closure_kind_for_date(date(2026, 5, 8)), 'nc_verify_closed')
        self.assertEqual(closure_kind_for_date(date(2026, 9, 28)), 'nc_verify_closed')
        self.assertEqual(closure_kind_for_date(date(2026, 10, 28)), 'nc_verify_closed')

    def test_regular_holiday_open_for_check(self):
        self.assertIsNone(closure_kind_for_date(date(2026, 7, 5)))
        self.assertIsNone(closure_kind_for_date(date(2026, 3, 15)))
