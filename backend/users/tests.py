from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from users.activity import module_from_path, should_skip_path
from users.exclusions import (
    is_excluded_from_leaderboard,
    is_excluded_report_user,
    is_leaderboard_included_user,
)
from users.fields import SafeDateTimeField
from users.middleware import (
    ACTIVITY_HB_AT_KEY,
    ACTIVITY_HB_MODULE_KEY,
    ActivityHeartbeatMiddleware,
    SESSION_TOUCH_KEY,
    SlidingSessionTouchMiddleware,
)
from users.models import AppActivityLog, WebUser
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


class ActivityHelpersTests(SimpleTestCase):
    def test_module_from_path(self):
        self.assertEqual(module_from_path('/api/finance/naklady/'), 'finance')
        self.assertEqual(module_from_path('/api/shifts/attendance/today-board/'), 'shifts')
        self.assertEqual(module_from_path('/api/unknown/thing/'), 'other')
        self.assertEqual(module_from_path('/static/app.js'), '')

    def test_should_skip_path(self):
        self.assertTrue(should_skip_path('/api/users/current/'))
        self.assertTrue(should_skip_path('/api/csrf/'))
        self.assertTrue(should_skip_path('/health/'))
        self.assertTrue(should_skip_path('/api/shifts/camera-events/hikvision/1/tok/'))
        self.assertFalse(should_skip_path('/api/finance/naklady/analytika/'))
        self.assertFalse(should_skip_path('/api/shifts/attendance/absent-stores/'))


@override_settings(ACTIVITY_HEARTBEAT_ENABLED=True, ACTIVITY_HEARTBEAT_INTERVAL=600)
class ActivityHeartbeatMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = WebUser.objects.create(
            id=77001,
            uzivatelske_jmeno='activity_test',
            jmeno='Act',
            prijmeni='Test',
            heslo='x',
            role='ADMIN',
            aktivni=True,
            moduly=[],
        )

    def _run(self, path, session=None, user=None, now=1_000_000, method='GET'):
        request = self.factory.generic(method, path)
        request.user = self.user if user is None else user
        request.session = session if session is not None else _FakeSession()
        mw = ActivityHeartbeatMiddleware(lambda _req: HttpResponse('ok', status=200))
        with patch('users.middleware.time.time', return_value=now):
            response = mw(request)
        return request, response

    def test_first_api_request_logs(self):
        request, _ = self._run('/api/finance/naklady/analytika/')
        self.assertEqual(AppActivityLog.objects.count(), 1)
        row = AppActivityLog.objects.get()
        self.assertEqual(row.user_id, self.user.id)
        self.assertEqual(row.module, 'finance')
        self.assertEqual(row.method, 'GET')
        self.assertEqual(row.status_code, 200)
        self.assertTrue(request.session.modified)
        self.assertEqual(request.session[ACTIVITY_HB_MODULE_KEY], 'finance')

    def test_within_interval_same_module_skips(self):
        session = _FakeSession({
            ACTIVITY_HB_AT_KEY: 1_000_000,
            ACTIVITY_HB_MODULE_KEY: 'finance',
        })
        self._run('/api/finance/pravidla/', session=session, now=1_000_000 + 100)
        self.assertEqual(AppActivityLog.objects.count(), 0)
        self.assertFalse(session.modified)

    def test_after_interval_logs_again(self):
        session = _FakeSession({
            ACTIVITY_HB_AT_KEY: 1_000_000,
            ACTIVITY_HB_MODULE_KEY: 'finance',
        })
        self._run('/api/finance/pravidla/', session=session, now=1_000_000 + 600)
        self.assertEqual(AppActivityLog.objects.count(), 1)

    def test_module_change_logs_immediately(self):
        session = _FakeSession({
            ACTIVITY_HB_AT_KEY: 1_000_000,
            ACTIVITY_HB_MODULE_KEY: 'finance',
        })
        self._run('/api/shifts/attendance/today-board/', session=session, now=1_000_000 + 30)
        self.assertEqual(AppActivityLog.objects.count(), 1)
        self.assertEqual(AppActivityLog.objects.get().module, 'shifts')
        self.assertEqual(session[ACTIVITY_HB_MODULE_KEY], 'shifts')

    def test_excluded_current_user_skipped(self):
        self._run('/api/users/current/')
        self.assertEqual(AppActivityLog.objects.count(), 0)

    def test_anonymous_skipped(self):
        self._run('/api/finance/naklady/', user=AnonymousUser())
        self.assertEqual(AppActivityLog.objects.count(), 0)

    @override_settings(ACTIVITY_HEARTBEAT_ENABLED=False)
    def test_disabled_skips(self):
        self._run('/api/finance/naklady/')
        self.assertEqual(AppActivityLog.objects.count(), 0)
