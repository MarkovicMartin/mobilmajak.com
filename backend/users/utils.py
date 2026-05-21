from django.db import IntegrityError
from django.db.models import Max

from .exclusions import STAFF_ROLES  # noqa: F401 – re-export
from .models import WebUser

# Systémové / admin účty mají vysoká ID (777, 99999, …) – řada pro běžné uživatele je 1, 2, …


def get_next_web_user_id():
    """
    Další volné ID v řadě běžných uživatelů (prodejce, vedoucí).
    Vychází z max ID mezi staff účty, pak přeskočí každé číslo,
    které už v tabulce existuje (např. ručně zadané admin ID 69).
    """
    current_max = WebUser.objects.filter(role__in=STAFF_ROLES).aggregate(m=Max('id'))['m'] or 0
    candidate = current_max + 1
    while WebUser.objects.filter(id=candidate).exists():
        candidate += 1
    return candidate


def create_web_user_with_auto_id(validated_data, raw_heslo, max_attempts=20):
    """
    Vytvoří uživatele s automaticky přiděleným ID.
    Při kolizi primárního klíče (souběžné vytvoření) zkusí další volné ID.
    """
    heslo = raw_heslo
    user_id = get_next_web_user_id()
    last_error = None
    for _ in range(max_attempts):
        if WebUser.objects.filter(id=user_id).exists():
            user_id += 1
            continue
        user = WebUser(id=user_id, **validated_data)
        user.set_heslo(heslo)
        try:
            user.save()
            return user
        except IntegrityError as exc:
            last_error = exc
            if 'id' not in str(exc).lower() and 'primary' not in str(exc).lower():
                raise
            user_id += 1
    raise IntegrityError(last_error or 'Nepodařilo se přidělit unikátní ID uživatele.')
