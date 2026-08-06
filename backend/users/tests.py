from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from users.exclusions import (
    is_excluded_from_leaderboard,
    is_excluded_report_user,
    is_leaderboard_included_user,
)
from users.fields import SafeDateTimeField
from users.middleware import SESSION_TOUCH_KEY, SlidingSessionTouchMiddleware
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


class _FakeSession(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.modified = False


@override_settings(SESSION_TOUCH_INTERVAL=900)
class SlidingSessionTouchMiddlewareTests(SimpleTestCase):
    def _run(self, session, now):
        request = RequestFactory().get('/api/users/current/')
        request.session = session
        mw = SlidingSessionTouchMiddleware(lambda _req: HttpResponse('ok'))
        with patch('users.middleware.time.time', return_value=now):
            mw(request)
        return request

    def test_first_authenticated_request_marks_modified(self):
        session = _FakeSession({'_auth_user_id': '29'})
        self._run(session, now=1_000_000)
        self.assertTrue(session.modified)
        self.assertEqual(session[SESSION_TOUCH_KEY], 1_000_000)

    def test_within_interval_does_not_mark_modified(self):
        session = _FakeSession({
            '_auth_user_id': '29',
            SESSION_TOUCH_KEY: 1_000_000,
        })
        self._run(session, now=1_000_000 + 100)
        self.assertFalse(session.modified)
        self.assertEqual(session[SESSION_TOUCH_KEY], 1_000_000)

    def test_after_interval_marks_modified_again(self):
        session = _FakeSession({
            '_auth_user_id': '29',
            SESSION_TOUCH_KEY: 1_000_000,
        })
        self._run(session, now=1_000_000 + 900)
        self.assertTrue(session.modified)
        self.assertEqual(session[SESSION_TOUCH_KEY], 1_000_900)

    def test_anonymous_session_untouched(self):
        session = _FakeSession()
        self._run(session, now=1_000_000)
        self.assertFalse(session.modified)
        self.assertNotIn(SESSION_TOUCH_KEY, session)
