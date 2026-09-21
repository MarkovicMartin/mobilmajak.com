from rest_framework.permissions import BasePermission

from users.exclusions import STAFF_ROLES, is_excluded_report_user
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


def _is_comparable_staff(seller) -> bool:
    if not seller or not getattr(seller, 'aktivni', False):
        return False
    if getattr(seller, 'role', None) not in STAFF_ROLES:
        return False
    return not is_excluded_report_user(user=seller)


def user_can_compare_sellers(viewer, seller_a, seller_b) -> bool:
    if can_access_coaching(viewer):
        return user_can_access_seller(viewer, seller_a) and user_can_access_seller(viewer, seller_b)
    if not viewer or not getattr(viewer, 'is_authenticated', False):
        return False
    if viewer.id not in (getattr(seller_a, 'id', None), getattr(seller_b, 'id', None)):
        return False
    return _is_comparable_staff(seller_a) and _is_comparable_staff(seller_b)


def user_can_access_own_timeline(viewer, seller) -> bool:
    if can_access_coaching(viewer) and user_can_access_seller(viewer, seller):
        return True
    return bool(
        viewer
        and getattr(viewer, 'is_authenticated', False)
        and seller
        and viewer.id == seller.id
    )


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
