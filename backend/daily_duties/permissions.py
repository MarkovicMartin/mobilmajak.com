from django.conf import settings
from rest_framework.permissions import BasePermission


class DailyDutiesModuleGate(BasePermission):
    message = 'Modul denních povinností není zapnutý.'

    def has_permission(self, request, view):
        return bool(getattr(settings, 'DAILY_DUTIES_MODULE_ENABLED', False))


class IsAdminRole(BasePermission):
    message = 'Jen administrátor může spravovat šablony.'

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and getattr(user, 'is_authenticated', False)
            and getattr(user, 'role', None) == 'ADMIN'
        )


def user_matches_template(user, template) -> bool:
    if template.uzivatel_id and template.uzivatel_id == user.id:
        return True
    if template.prodejna_id and getattr(user, 'prodejna_id', None) == template.prodejna_id:
        return True
    return False


def user_label(user) -> str:
    if not user:
        return ''
    name = f'{user.jmeno} {user.prijmeni}'.strip()
    return name or user.uzivatelske_jmeno
