from __future__ import annotations

from django.db.models import Q

from users.exclusions import get_excluded_report_user_ids, real_sales_staff_queryset
from users.models import WebUser
from users.vedouci_utils import is_task_manager, vedouci_store_ids

from .models import Ukol


def tasks_queryset_for_user(user):
    role = getattr(user, "role", None)
    if role == "ADMIN":
        return Ukol.objects.all()
    store_ids = vedouci_store_ids(user)
    if store_ids:
        return Ukol.objects.filter(id_prodejny__in=store_ids)
    return Ukol.objects.filter(
        Q(id_prodejce_ukol=user.id)
        | (Q(typ="osobni") & Q(id_prodejce_zadal=user.id))
    )


def user_can_access_task(user, task: Ukol) -> bool:
    return tasks_queryset_for_user(user).filter(pk=task.pk).exists()


def user_can_edit_task(user, task: Ukol) -> bool:
    role = getattr(user, "role", None)
    if role == "ADMIN":
        return True
    if task.id_prodejny and task.id_prodejny in vedouci_store_ids(user):
        return True
    return task.id_prodejce_ukol == user.id or (
        task.typ == "osobni" and task.id_prodejce_zadal == user.id
    )


def _user_display(u: WebUser | None, skupina: str | None = None) -> dict | None:
    if not u:
        return None
    out = {
        "id": u.id,
        "jmeno": u.jmeno,
        "prijmeni": u.prijmeni,
        "jmeno_plne": f"{u.jmeno} {u.prijmeni}".strip(),
    }
    if skupina:
        out["skupina"] = skupina
    return out


def validate_task_create(user, data: dict) -> str | None:
    typ = data.get("typ") or "osobni"
    if typ not in ("prirazeny", "osobni"):
        return "Neplatný typ úkolu."

    assignee_id = data.get("id_prodejce_ukol")
    store_id = data.get("id_prodejny")

    if typ == "prirazeny":
        if not store_id:
            return "U přiřazeného úkolu je povinná prodejna (id_prodejny)."
        if not assignee_id:
            return "U přiřazeného úkolu je povinný přiřazený uživatel."
        try:
            assignee = WebUser.objects.get(id=int(assignee_id), aktivni=True)
        except (WebUser.DoesNotExist, TypeError, ValueError):
            return "Přiřazený uživatel neexistuje nebo není aktivní."

        role = getattr(user, "role", None)
        if role == "ADMIN":
            pass
        elif is_task_manager(user):
            manager_stores = vedouci_store_ids(user)
            if int(store_id) not in manager_stores:
                return "Nemáte oprávnění vytvářet úkoly na této prodejně."
            if not _assignee_allowed_on_store(assignee, int(store_id)):
                return "Uživatele nelze přiřadit na tuto prodejnu."
        else:
            return "Nemáte oprávnění vytvářet přiřazené úkoly."
    else:
        if is_task_manager(user):
            pass
        else:
            data["id_prodejce_ukol"] = user.id
            data["id_prodejce_zadal"] = user.id
            data["id_prodejny"] = None

    priorita = data.get("priorita", "stredni")
    if priorita not in dict(Ukol.PRIORITY):
        return "Neplatná priorita."

    return None


def _assignee_allowed_on_store(assignee: WebUser, _store_id: int) -> bool:
    if not assignee.aktivni:
        return False
    if assignee.role not in ("PRODEJCE", "VEDOUCI", "BRIGADNIK"):
        return False
    return assignee.id not in get_excluded_report_user_ids()


def assignees_for_store(store_id: int, user) -> list[dict]:
    role = getattr(user, "role", None)
    if role != "ADMIN":
        if store_id not in vedouci_store_ids(user):
            return []
    if not is_task_manager(user):
        return []

    excluded = get_excluded_report_user_ids()
    domovska = (
        WebUser.objects.filter(prodejna_id=store_id, aktivni=True)
        .exclude(id__in=excluded)
        .order_by("jmeno", "prijmeni")
    )
    brigadnici = (
        WebUser.objects.filter(role="BRIGADNIK", aktivni=True)
        .exclude(id__in=excluded)
        .order_by("jmeno", "prijmeni")
    )
    ostatni = (
        real_sales_staff_queryset()
        .exclude(prodejna_id=store_id)
        .exclude(role="BRIGADNIK")
        .order_by("jmeno", "prijmeni")
    )
    seen = set()
    result = []
    for u in domovska:
        if u.id in seen:
            continue
        seen.add(u.id)
        result.append(_user_display(u, "domaci"))
    for u in brigadnici:
        if u.id in seen:
            continue
        seen.add(u.id)
        result.append(_user_display(u, "brigadnik"))
    for u in ostatni:
        if u.id in seen:
            continue
        seen.add(u.id)
        result.append(_user_display(u, "ostatni"))
    return result
