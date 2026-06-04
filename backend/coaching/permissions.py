from rest_framework.permissions import BasePermission

from users.vedouci_utils import is_task_manager, vedouci_store_ids


def can_access_coaching(user) -> bool:
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    return is_task_manager(user)


def allowed_store_ids(user) -> list[int] | None:
    """None = všechny prodejny (ADMIN). Jinak seznam ID."""
    if not user:
        return []
    if user.role == 'ADMIN':
        return None
    if is_task_manager(user):
        return vedouci_store_ids(user)
    return []


def user_can_access_seller(user, seller) -> bool:
    if not can_access_coaching(user):
        return False
    stores = allowed_store_ids(user)
    if stores is None:
        return True
    if not stores:
        return False
    sid = getattr(seller, 'prodejna_id', None)
    return sid in stores


def filter_prodejna_id_param(user, prodejna_id):
    """Vrátí prodejna_id omezené na oprávnění vedoucího."""
    stores = allowed_store_ids(user)
    if stores is None:
        return prodejna_id
    if not stores:
        return -1
    if prodejna_id:
        try:
            pid = int(prodejna_id)
            return pid if pid in stores else -1
        except (TypeError, ValueError):
            return -1
    return stores[0] if len(stores) == 1 else prodejna_id


class CoachingAccessPermission(BasePermission):
    def has_permission(self, request, view):
        return can_access_coaching(request.user)
