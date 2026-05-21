"""
Vynechání systémových / demo účtů z výplaty, žebříčků a průměrů.

Nejsou to skuteční prodejci: administrátoři, účty „Prodejce Prodejce“, systémový, nový prodejce, …
"""
from django.db.models import Q

from .models import WebUser

STAFF_ROLES = ('PRODEJCE', 'VEDOUCI', 'BRIGADNIK')

# (jmeno, prijmeni) bez diakritiky / case-insensitive porovnání
_EXCLUDED_NAME_PAIRS = frozenset({
    ('prodejce', 'prodejce'),
    ('administrátor', 'systémový'),
    ('administrator', 'systemovy'),
    ('administrátor', 'systemovy'),
    ('nový', 'prodejce'),
    ('novy', 'prodejce'),
})

_excluded_ids_cache = None


def _normalize_pair(jmeno, prijmeni):
    return (
        (jmeno or '').strip().lower(),
        (prijmeni or '').strip().lower(),
    )


def is_excluded_report_user(role=None, jmeno=None, prijmeni=None, user=None):
    """True = nepatří do výpisů prodejců (výplata, žebříček, průměry)."""
    if user is not None:
        role = getattr(user, 'role', None)
        jmeno = getattr(user, 'jmeno', None)
        prijmeni = getattr(user, 'prijmeni', None)
    if role == 'ADMIN':
        return True
    if _normalize_pair(jmeno, prijmeni) in _EXCLUDED_NAME_PAIRS:
        return True
    return False


def get_excluded_report_user_ids():
    """ID všech uživatelů vynechaných z reportů (cache v procesu)."""
    global _excluded_ids_cache
    if _excluded_ids_cache is None:
        excluded = set()
        for uid, role, jmeno, prijmeni in WebUser.objects.values_list(
            'id', 'role', 'jmeno', 'prijmeni',
        ):
            if is_excluded_report_user(role=role, jmeno=jmeno, prijmeni=prijmeni):
                excluded.add(uid)
        _excluded_ids_cache = excluded
    return _excluded_ids_cache


def invalidate_excluded_user_ids_cache():
    global _excluded_ids_cache
    _excluded_ids_cache = None


def real_sales_staff_queryset():
    """Aktivní prodejci a vedoucí bez systémových účtů."""
    return (
        WebUser.objects.filter(aktivni=True, role__in=STAFF_ROLES)
        .exclude(id__in=get_excluded_report_user_ids())
    )


def excluded_users_q():
    """Q pro exclude v dotazech podle ID."""
    ids = get_excluded_report_user_ids()
    if not ids:
        return Q()
    return Q(id__in=ids)
