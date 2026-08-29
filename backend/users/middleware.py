import logging
import time

from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware

from .activity import client_ip, module_from_path, normalize_path, should_skip_path

SESSION_TOUCH_KEY = '_session_touched_at'
ACTIVITY_HB_AT_KEY = '_activity_hb_at'
ACTIVITY_HB_MODULE_KEY = '_activity_hb_module'

logger = logging.getLogger(__name__)


class ApiCsrfMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Pro API endpointy ignorujeme CSRF
        if request.path.startswith('/api/'):
            # Přeskočíme CSRF kontrolu pro API
            return self.get_response(request)

        # Pro ostatní endpointy použijeme standardní CSRF middleware
        csrf_middleware = CsrfViewMiddleware(self.get_response)
        return csrf_middleware(request)


class SlidingSessionTouchMiddleware:
    """
    Lehký sliding: prodluž session max jednou za SESSION_TOUCH_INTERVAL.
    SESSION_SAVE_EVERY_REQUEST zůstává False — poll každých 90 s session nezapisuje.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session = getattr(request, 'session', None)
        if session is not None and session.get('_auth_user_id'):
            interval = int(getattr(settings, 'SESSION_TOUCH_INTERVAL', 900))
            now = int(time.time())
            last = session.get(SESSION_TOUCH_KEY)
            try:
                last_ts = int(last) if last is not None else 0
            except (TypeError, ValueError):
                last_ts = 0
            if last_ts <= 0 or (now - last_ts) >= interval:
                session[SESSION_TOUCH_KEY] = now
                session.modified = True

        return self.get_response(request)


class ActivityHeartbeatMiddleware:
    """
    Throttled zápis app_activity_log: max 1× / interval na usera,
    nebo při změně API modulu. Nezapisuje poll/csrf/health.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._maybe_log(request, response)
        except Exception:
            logger.exception('Activity heartbeat failed')
        return response

    def _maybe_log(self, request, response):
        if not getattr(settings, 'ACTIVITY_HEARTBEAT_ENABLED', True):
            return

        user = getattr(request, 'user', None)
        if user is None or not getattr(user, 'is_authenticated', False):
            return
        user_id = getattr(user, 'id', None)
        if user_id is None:
            return

        path = normalize_path(getattr(request, 'path', '') or '')
        if should_skip_path(path):
            return

        module = module_from_path(path)
        if not module:
            return

        session = getattr(request, 'session', None)
        interval = int(getattr(settings, 'ACTIVITY_HEARTBEAT_INTERVAL', 600))
        now = int(time.time())
        last_ts = 0
        last_module = ''
        if session is not None:
            try:
                last_ts = int(session.get(ACTIVITY_HB_AT_KEY) or 0)
            except (TypeError, ValueError):
                last_ts = 0
            last_module = str(session.get(ACTIVITY_HB_MODULE_KEY) or '')

        due = last_ts <= 0 or (now - last_ts) >= interval or last_module != module
        if not due:
            return

        from .models import AppActivityLog

        AppActivityLog.objects.create(
            user_id=int(user_id),
            ip=client_ip(request),
            module=module[:32],
            path=path[:200],
            method=(getattr(request, 'method', '') or '')[:8],
            status_code=getattr(response, 'status_code', None),
        )

        if session is not None:
            session[ACTIVITY_HB_AT_KEY] = now
            session[ACTIVITY_HB_MODULE_KEY] = module
            session.modified = True
