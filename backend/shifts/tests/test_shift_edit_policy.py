from datetime import date
from unittest import TestCase

from shifts.shift_helpers import (
    earliest_editable_shift_date,
    seller_may_edit_shift_on_date,
    user_may_edit_shift_on_date,
)


class _User:
    def __init__(self, role):
        self.role = role


class ShiftEditPolicyTests(TestCase):
    def test_seller_current_and_future_months(self):
        today = date(2026, 7, 15)
        self.assertEqual(earliest_editable_shift_date(today), date(2026, 7, 1))
        self.assertTrue(seller_may_edit_shift_on_date(date(2026, 7, 1), today))
        self.assertTrue(seller_may_edit_shift_on_date(date(2026, 7, 31), today))
        self.assertTrue(seller_may_edit_shift_on_date(date(2026, 8, 1), today))
        self.assertTrue(seller_may_edit_shift_on_date(date(2026, 12, 31), today))
        self.assertFalse(seller_may_edit_shift_on_date(date(2026, 6, 30), today))

    def test_admin_any_month(self):
        today = date(2026, 7, 15)
        admin = _User('ADMIN')
        self.assertTrue(user_may_edit_shift_on_date(admin, date(2025, 1, 1), today))
        self.assertTrue(user_may_edit_shift_on_date(admin, date(2026, 7, 1), today))

    def test_vedouci_any_month(self):
        today = date(2026, 7, 15)
        vedouci = _User('VEDOUCI')
        self.assertTrue(user_may_edit_shift_on_date(vedouci, date(2026, 7, 10), today))
        self.assertTrue(user_may_edit_shift_on_date(vedouci, date(2026, 6, 1), today))
        self.assertTrue(user_may_edit_shift_on_date(vedouci, date(2026, 8, 1), today))
