"""
Přepočet plánů prodejců po změně jedné směny (ne hromadně).

Volá se z shifts/views po single create/update/delete. Selhání přepočtu
neblokuje uložení směny.
"""
from __future__ import annotations

import logging
from datetime import date

from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)


def _as_date(value):
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        from datetime import datetime
        return datetime.strptime(value[:10], '%Y-%m-%d').date()
    return value


def _je_bezici_mesic(datum: date) -> bool:
    d = _as_date(datum)
    if not d:
        return False
    today = date.today()
    return d.year == today.year and d.month == today.month


def _resolve_prodejna_id(smena, prodejna_id, user):
    if prodejna_id:
        return prodejna_id
    if smena and smena.prodejna_id:
        return smena.prodejna_id
    u = user or (smena.user if smena else None)
    if u and getattr(u, 'prodejna_id', None):
        return u.prodejna_id
    return None


def naplanuj_prepocet_po_smene(
    smena=None,
    *,
    zdroj: str = 'single',
    datum=None,
    prodejna_id=None,
    user=None,
):
    """
    Naplánuje přepočet plánu prodejny po commitu transakce směny.

    zdroj: 'single' | 'bulk' | 'import' – přepočet jen u 'single'.
    """
    if zdroj != 'single':
        return
    if not getattr(settings, 'PLAN_PREPOCET_ON_SHIFT', True):
        return

    shift_datum = _as_date(datum or (smena.datum if smena else None))
    if not shift_datum or not _je_bezici_mesic(shift_datum):
        return

    store_id = _resolve_prodejna_id(smena, prodejna_id, user)
    if not store_id:
        return

    rok, mesic = shift_datum.year, shift_datum.month

    def _prepocet():
        try:
            from plans.models import PlanMonth, PlanStore
            from plans.prodejci_auto import prirad_prodejce_automaticky

            plan = PlanMonth.objects.filter(
                rok=rok, mesic=mesic, je_aktualni=True,
            ).first()
            if not plan:
                return
            ps = PlanStore.objects.filter(
                plan_mesic=plan, prodejna_id=store_id,
            ).first()
            if not ps:
                return
            prirad_prodejce_automaticky(plan, plan_prodejna_id=ps.id)
        except Exception:
            logger.exception(
                'Přepočet plánu po směně selhal (směna uložena), prodejna=%s %s/%s',
                store_id, mesic, rok,
            )

    transaction.on_commit(_prepocet)
