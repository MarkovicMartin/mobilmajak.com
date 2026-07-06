"""Finance modul – admin vs. přístup k fakturám na prodejně."""
from functools import wraps

from rest_framework import status
from rest_framework.response import Response


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def accessible_store_ids(user) -> list[int] | None:
    """None = všechny prodejny (admin), jinak seznam ID."""
    if getattr(user, 'role', None) == 'ADMIN':
        return None
    ids = []
    if getattr(user, 'prodejna_id', None):
        ids.append(int(user.prodejna_id))
    try:
        from users.vedouci_utils import vedouci_store_ids
        ids.extend(int(x) for x in vedouci_store_ids(user))
    except Exception:
        pass
    return list(dict.fromkeys(ids))


def user_can_access_polozka(user, polozka) -> bool:
    store_ids = accessible_store_ids(user)
    if store_ids is None:
        return True
    if not store_ids:
        return False
    return polozka.prodejna_id in store_ids


def require_finance_admin(request):
    """Vrátí Response 403 nebo None pokud je uživatel ADMIN."""
    if getattr(request.user, 'role', None) != 'ADMIN':
        return Response({'error': 'Nemáte oprávnění'}, status=status.HTTP_403_FORBIDDEN)
    return None


def require_finance_invoice_access(request):
    """Admin, vedoucí nebo prodejce s domovskou prodejnou."""
    role = getattr(request.user, 'role', None)
    if role == 'ADMIN':
        return None
    if accessible_store_ids(request.user):
        return None
    return Response({'error': 'Nemáte oprávnění k fakturám'}, status=status.HTTP_403_FORBIDDEN)


def finance_admin_view(view_func):
    """Dekorátor pro DRF @api_view – kontrola ADMIN před handlerem."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        denied = require_finance_admin(request)
        if denied:
            return denied
        return view_func(request, *args, **kwargs)
    return wrapper


def finance_invoice_view(view_func):
    """Admin nebo uživatel s přístupem k prodejně."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        denied = require_finance_invoice_access(request)
        if denied:
            return denied
        return view_func(request, *args, **kwargs)
    return wrapper
