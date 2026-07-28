from django.test import SimpleTestCase

from users.exclusions import (
    is_excluded_from_leaderboard,
    is_excluded_report_user,
    is_leaderboard_included_user,
)
from users.fields import SafeDateTimeField
from users.mysql_datetime_patch import _normalize_db_datetime, patch_mysql_datetime_conversion


class LeaderboardExclusionsTests(SimpleTestCase):
    def test_radek_bulandra_included_in_leaderboard_despite_admin(self):
        self.assertTrue(is_leaderboard_included_user(jmeno='Radek', prijmeni='Bulandra'))
        self.assertTrue(is_excluded_report_user(role='ADMIN', jmeno='Radek', prijmeni='Bulandra'))
        self.assertFalse(
            is_excluded_from_leaderboard(role='ADMIN', jmeno='Radek', prijmeni='Bulandra')
        )

    def test_other_admin_still_excluded_from_leaderboard(self):
        self.assertTrue(
            is_excluded_from_leaderboard(role='ADMIN', jmeno='Martin', prijmeni='Markovič')
        )


class SafeDateTimeFieldTests(SimpleTestCase):
    def test_internal_type_is_not_datetimefield(self):
        # DateTimeField → MySQL convert_datetimefield_value běží před from_db_value
        # a padá na legacy zero-datetime string ('… utcoffset').
        self.assertEqual(SafeDateTimeField().get_internal_type(), 'SafeDateTimeField')

    def test_zero_datetime_string_becomes_none(self):
        field = SafeDateTimeField()
        self.assertIsNone(field.to_python('0000-00-00 00:00:00'))
        self.assertIsNone(field.to_python('0000-00-00 00:00:00.000000'))
        self.assertIsNone(field.from_db_value('0000-00-00 00:00:00.000000', None, None))

    def test_mysql_patch_normalizes_zero_strings(self):
        self.assertIsNone(_normalize_db_datetime('0000-00-00 00:00:00.000000'))
        self.assertIsNone(_normalize_db_datetime(''))
        parsed = _normalize_db_datetime('2024-06-15 10:30:00')
        self.assertIsNotNone(parsed)
        self.assertFalse(isinstance(parsed, str))

    def test_mysql_patch_is_idempotent(self):
        patch_mysql_datetime_conversion()
        patch_mysql_datetime_conversion()
        from django.db.backends.mysql.operations import DatabaseOperations

        self.assertTrue(getattr(DatabaseOperations, '_mobilmajak_safe_datetime_patched', False))
