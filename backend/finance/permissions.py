"""Finance modul – všechny endpointy vyžadují ADMIN."""
from functools import wraps

from rest_framework import status
from rest_framework.response import Response


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def require_finance_admin(request):
    """Vrátí Response 403 nebo None pokud je uživatel ADMIN."""
    if getattr(request.user, 'role', None) != 'ADMIN':
        return Response({'error': 'Nemáte oprávnění'}, status=status.HTTP_403_FORBIDDEN)
    return None


def finance_admin_view(view_func):
    """Dekorátor pro DRF @api_view – kontrola ADMIN před handlerem."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        denied = require_finance_admin(request)
        if denied:
            return denied
        return view_func(request, *args, **kwargs)
    return wrapper
