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
_leaderboard_excluded_ids_cache = None

# Aktivní prodej na pultu – ve žebříčku i při roli ADMIN (výplata dál podle is_excluded_report_user)
_LEADERBOARD_INCLUDED_NAME_PAIRS = frozenset({
    ('radek', 'bulandra'),
})


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
    invalidate_leaderboard_excluded_ids_cache()


def is_leaderboard_included_user(jmeno=None, prijmeni=None, user=None):
    """Uživatel, který má být ve žebříčku i když je jinak vynechaný (typicky ADMIN)."""
    if user is not None:
        jmeno = getattr(user, 'jmeno', None)
        prijmeni = getattr(user, 'prijmeni', None)
    return _normalize_pair(jmeno, prijmeni) in _LEADERBOARD_INCLUDED_NAME_PAIRS


def is_excluded_from_leaderboard(role=None, jmeno=None, prijmeni=None, user=None):
    """True = nepatří do žebříčků (s výjimkou _LEADERBOARD_INCLUDED_NAME_PAIRS)."""
    if is_leaderboard_included_user(jmeno=jmeno, prijmeni=prijmeni, user=user):
        return False
    return is_excluded_report_user(role=role, jmeno=jmeno, prijmeni=prijmeni, user=user)


def get_leaderboard_excluded_prodejce_ids():
    """
    ID vynechaná z žebříčku – WebUser.id i technik_id (v prodejních datech bývá technik_id).
    """
    global _leaderboard_excluded_ids_cache
    if _leaderboard_excluded_ids_cache is None:
        excluded = set(get_excluded_report_user_ids())
        for uid, technik_id, jmeno, prijmeni in WebUser.objects.values_list(
            'id', 'technik_id', 'jmeno', 'prijmeni',
        ):
            if _normalize_pair(jmeno, prijmeni) in _LEADERBOARD_INCLUDED_NAME_PAIRS:
                excluded.discard(uid)
                if technik_id:
                    excluded.discard(technik_id)
        _leaderboard_excluded_ids_cache = excluded
    return _leaderboard_excluded_ids_cache


def invalidate_leaderboard_excluded_ids_cache():
    global _leaderboard_excluded_ids_cache
    _leaderboard_excluded_ids_cache = None


def real_sales_staff_queryset():
    """Aktivní prodejci a vedoucí bez systémových účtů."""
    return (
        WebUser.objects.filter(aktivni=True, role__in=STAFF_ROLES)
        .exclude(id__in=get_excluded_report_user_ids())
    )


def vacation_overview_users_queryset():
    """Staff pro přehled dovolené – prodejci/vedoucí + aktivní admini (bez demo účtů)."""
    staff_qs = real_sales_staff_queryset()
    staff_ids = set(staff_qs.values_list('id', flat=True))
    admin_ids = [
        uid
        for uid, jmeno, prijmeni in WebUser.objects.filter(
            aktivni=True, role='ADMIN',
        ).exclude(id__in=staff_ids).values_list('id', 'jmeno', 'prijmeni')
        if _normalize_pair(jmeno, prijmeni) not in _EXCLUDED_NAME_PAIRS
    ]
    if not admin_ids:
        return staff_qs.order_by('jmeno', 'prijmeni')
    return (
        WebUser.objects.filter(Q(id__in=staff_ids) | Q(id__in=admin_ids))
        .order_by('jmeno', 'prijmeni')
    )


def excluded_users_q():
    """Q pro exclude v dotazech podle ID."""
    ids = get_excluded_report_user_ids()
    if not ids:
        return Q()
    return Q(id__in=ids)
