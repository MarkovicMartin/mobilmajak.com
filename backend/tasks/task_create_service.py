"""Vytvoření úkolu – sdílená logika pro REST API a Slack (bez úprav chování API)."""
from __future__ import annotations

from users.vedouci_utils import is_task_manager, vedouci_store_ids

from .models import Ukol
from .permissions import validate_task_create
from .serializers import UkolSerializer
from .slack_notify import notify_task_lifecycle_change


def create_ukol_for_user(user, data: dict) -> tuple[Ukol | None, str | None]:
    """
    Stejná validace a vedlejší efekty jako POST /api/tasks/.
    Vrací (úkol, None) nebo (None, chybová zpráva).
    """
    payload = dict(data)
    role = getattr(user, "role", None)

    if not is_task_manager(user):
        payload["typ"] = "osobni"
        payload.setdefault("id_prodejce_ukol", user.id)
        payload.setdefault("id_prodejce_zadal", user.id)
    else:
        payload.setdefault("id_prodejce_zadal", user.id)
        if payload.get("typ") == "prirazeny" and not payload.get("id_prodejce_ukol"):
            return None, "U přiřazeného úkolu je povinný přiřazený uživatel."

    err = validate_task_create(user, payload)
    if err:
        return None, err

    if payload.get("typ") != "prirazeny":
        payload.setdefault("id_prodejce_ukol", user.id)
        payload.setdefault("id_prodejce_zadal", user.id)
        if not is_task_manager(user) or payload.get("typ") == "osobni":
            payload["id_prodejny"] = None
        elif role == "VEDOUCI" and not payload.get("id_prodejny"):
            store_ids = vedouci_store_ids(user)
            if len(store_ids) == 1:
                payload["id_prodejny"] = store_ids[0]

    from .permissions import sync_ukol_from_vysledek
    sync_ukol_from_vysledek(payload)

    serializer = UkolSerializer(data=payload)
    if not serializer.is_valid():
        first_key = next(iter(serializer.errors.keys()), "")
        first = serializer.errors.get(first_key, ["Neplatná data"])
        msg = first[0] if isinstance(first, list) else str(first)
        if first_key:
            msg = f"{first_key}: {msg}"
        return None, str(msg)

    task = serializer.save()
    if task.typ == "prirazeny" and task.id_prodejce_ukol != user.id:
        task.precteno_v = None
        task.save(update_fields=["precteno_v"])
    notify_task_lifecycle_change(task, is_new=True)
    return task, None
