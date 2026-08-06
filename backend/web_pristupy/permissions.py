"""Oprávnění pro modul Přístupy (web_pristupy)."""

from django.db.models import Q

from users.models import WebUser

ADMIN_CATEGORY = 'Admin'


def is_web_user(user):
    return user if isinstance(user, WebUser) else None


def is_admin_user(user):
    webuser = is_web_user(user)
    return bool(webuser and webuser.role == 'ADMIN')


def is_admin_category(category):
    return (category or '').strip().casefold() == ADMIN_CATEGORY.casefold()


def exclude_admin_category_q():
    """Vyloučí kategorii Admin (case-insensitive)."""
    return ~Q(category__iexact=ADMIN_CATEGORY)
