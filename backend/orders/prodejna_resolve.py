"""Resolve store for a new order from today's shift, else home store."""
from __future__ import annotations

from django.utils import timezone

from stores.models import Prodejna


def resolve_order_prodejna(user):
    """Active work shift store for today, else user's home prodejna."""
    if not user or not getattr(user, "id", None):
        return None

    try:
        from shifts.models import Smena
    except Exception:
        Smena = None  # noqa: N806

    if Smena is not None:
        today = timezone.localdate()
        smena = (
            Smena.objects.filter(
                user_id=user.id,
                datum=today,
                aktivni=True,
                typ_smeny="prace",
                prodejna_id__isnull=False,
            )
            .select_related("prodejna")
            .order_by("-cas_od")
            .first()
        )
        if smena and smena.prodejna_id:
            return smena.prodejna

    home_id = getattr(user, "prodejna_id", None)
    if home_id:
        return Prodejna.objects.filter(pk=home_id, aktivni=True).first() or Prodejna.objects.filter(
            pk=home_id
        ).first()
    return None
