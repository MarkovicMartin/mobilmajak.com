"""Oprávnění pro analytics API."""
import os
import secrets
from functools import wraps

from django.http import JsonResponse
from rest_framework.permissions import BasePermission


def _unauthorized_response():
    return JsonResponse(
        {'success': False, 'error': 'Přihlášení vyžadováno'},
        status=401,
    )


def require_analytics_login(view_func):
    """Django function view – vyžaduje aktivní session."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'is_authenticated', False):
            return _unauthorized_response()
        return view_func(request, *args, **kwargs)
    return wrapper


def analytics_login_required(cls):
    """Class-based Django view – vyžaduje aktivní session."""
    original_dispatch = cls.dispatch

    def dispatch(self, request, *args, **kwargs):
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'is_authenticated', False):
            return _unauthorized_response()
        return original_dispatch(self, request, *args, **kwargs)

    cls.dispatch = dispatch
    return cls


def verify_webhook_monthly_stats_token(request) -> bool:
    expected = os.getenv('WEBHOOK_MONTHLY_STATS_TOKEN', '').strip()
    if not expected:
        return False
    provided = (
        request.headers.get('X-Webhook-Token')
        or request.META.get('HTTP_X_WEBHOOK_TOKEN')
        or request.GET.get('token')
        or ''
    ).strip()
    if not provided:
        return False
    return secrets.compare_digest(provided, expected)


class WebhookMonthlyStatsPermission(BasePermission):
    """Externí webhook (N8N) – token v hlavičce X-Webhook-Token nebo ?token=."""

    message = 'Neplatný nebo chybějící webhook token'

    def has_permission(self, request, view):
        return verify_webhook_monthly_stats_token(request)
