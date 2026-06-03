from django.test import SimpleTestCase

from users.exclusions import (
    is_excluded_from_leaderboard,
    is_excluded_report_user,
    is_leaderboard_included_user,
)


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
