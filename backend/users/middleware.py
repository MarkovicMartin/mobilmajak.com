import time

from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware

SESSION_TOUCH_KEY = '_session_touched_at'


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
