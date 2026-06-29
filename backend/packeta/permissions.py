from functools import wraps

from rest_framework import status
from rest_framework.response import Response


def require_packeta_admin(request):
    if getattr(request.user, 'role', None) != 'ADMIN':
        return Response({'error': 'Nemáte oprávnění'}, status=status.HTTP_403_FORBIDDEN)
    return None


def packeta_admin_view(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        denied = require_packeta_admin(request)
        if denied:
            return denied
        return view_func(request, *args, **kwargs)
    return wrapper
