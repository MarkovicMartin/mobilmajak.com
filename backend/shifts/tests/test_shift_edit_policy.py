from datetime import date
from unittest import TestCase

from shifts.shift_helpers import earliest_editable_shift_date, seller_may_edit_shift_on_date


class ShiftEditPolicyTests(TestCase):
    def test_july_2026_allows_june_edits(self):
        today = date(2026, 7, 2)
        self.assertEqual(earliest_editable_shift_date(today), date(2026, 6, 1))
        self.assertTrue(seller_may_edit_shift_on_date(date(2026, 6, 15), today))
        self.assertTrue(seller_may_edit_shift_on_date(date(2026, 7, 1), today))
        self.assertFalse(seller_may_edit_shift_on_date(date(2026, 5, 31), today))

    def test_august_2026_closes_june_window(self):
        today = date(2026, 8, 1)
        self.assertEqual(earliest_editable_shift_date(today), date(2026, 8, 1))
        self.assertFalse(seller_may_edit_shift_on_date(date(2026, 6, 15), today))
