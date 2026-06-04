"""Vedoucí pobočky: systémová role VEDOUCI a/nebo přiřazení v Prodejna.vedouci_user_id."""

from __future__ import annotations

from stores.models import Prodejna
from users.models import WebUser


def vedouci_store_ids(user) -> list[int]:
    """ID poboček, kde je uživatel vedoucím (bez ohledu na roli v DB)."""
    if not user or not getattr(user, "id", None):
        return []
    return list(
        Prodejna.objects.filter(vedouci_user_id=user.id, aktivni=True).values_list("id", flat=True)
    )


def is_store_vedouci(user) -> bool:
    return bool(vedouci_store_ids(user))


def is_vedouci_role(user) -> bool:
    return getattr(user, "role", None) == "VEDOUCI"


def is_task_manager(user) -> bool:
    """Správa úkolů: admin, role Vedoucí, nebo vedoucí přiřazený u prodejny."""
    if not user:
        return False
    role = getattr(user, "role", None)
    if role == "ADMIN":
        return True
    if role == "VEDOUCI":
        return True
    return is_store_vedouci(user)


def ensure_vedouci_role_for_store_assignment(user: WebUser) -> None:
    """Po přiřazení jako vedoucí pobočky nastaví roli VEDOUCI (admina nemění)."""
    if user.role in ("ADMIN", "VEDOUCI"):
        return
    user.role = "VEDOUCI"
    user.save(update_fields=["role"])


def maybe_demote_vedouci_role_after_store_removal(user: WebUser) -> None:
    """Po odebrání z pobočky: pokud už nikde nevede a má roli VEDOUCI → Prodejce."""
    if user.role != "VEDOUCI":
        return
    if Prodejna.objects.filter(vedouci_user_id=user.id).exists():
        return
    user.role = "PRODEJCE"
    user.save(update_fields=["role"])


def sync_vedouci_roles_from_stores() -> int:
    """Jednorázová oprava: vedoucí u prodejny bez role VEDOUCI → nastaví VEDOUCI."""
    updated = 0
    for row in Prodejna.objects.filter(vedouci_user_id__isnull=False, aktivni=True).values(
        "vedouci_user_id",
    ):
        uid = row["vedouci_user_id"]
        try:
            user = WebUser.objects.get(pk=uid, aktivni=True)
        except WebUser.DoesNotExist:
            continue
        if user.role in ("ADMIN", "VEDOUCI"):
            continue
        user.role = "VEDOUCI"
        user.save(update_fields=["role"])
        updated += 1
    return updated
