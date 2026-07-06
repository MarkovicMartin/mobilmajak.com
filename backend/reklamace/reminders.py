"""Připomínky k otevřeným reklamacím (10 dní in-app, 30 dní Slack)."""
from __future__ import annotations

import logging
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from stores.models import Prodejna
from tasks.slack_notify import send_slack_dm, slack_user_id_for_web_user
from users.models import WebUser

from .models import ReklamaceNotifikace, ReklamacePolozka, ReklamaceStatus

logger = logging.getLogger(__name__)

REMINDER_2D_TRACKING = timedelta(days=2)
REMINDER_10D = timedelta(days=10)
REMINDER_30D = timedelta(days=30)


def vedouci_user_id_for_prodejna_name(name: str) -> int | None:
    cleaned = (name or '').strip()
    if not cleaned:
        return None
    store = (
        Prodejna.objects.filter(
            Q(nazev__iexact=cleaned)
            | Q(nazev_kratkiy__iexact=cleaned)
            | Q(nazev_google_sheets__iexact=cleaned)
        )
        .order_by('id')
        .first()
    )
    return store.vedouci_user_id if store else None


def reminder_recipient_ids(item: ReklamacePolozka) -> list[int]:
    ids: list[int] = []
    if item.created_by_id:
        ids.append(item.created_by_id)
    vedouci_id = vedouci_user_id_for_prodejna_name(item.prodejna)
    if vedouci_id:
        ids.append(vedouci_id)
    return list(dict.fromkeys(ids))


def _open_items_past(cutoff, *, field_null: str):
    return ReklamacePolozka.objects.filter(
        is_active=True,
        created_at__lte=cutoff,
        **{f'{field_null}__isnull': True},
    ).exclude(status=ReklamaceStatus.VRIZENE)


def send_2d_tracking_reminders(now=None, *, dry_run: bool = False) -> int:
    """In-app připomínka, pokud 2+ dny chybí číslo balíčku."""
    now = now or timezone.now()
    cutoff = now - REMINDER_2D_TRACKING
    count = 0

    qs = (
        _open_items_past(cutoff, field_null='reminder_tracking_2d_sent_at')
        .filter(cislo_zasilky='')
    )
    for item in qs:
        message = f'Nepřidáno číslo balíčku – reklamace {item.nase_znacka}'
        recipients = reminder_recipient_ids(item)
        if dry_run:
            count += max(len(recipients), 1)
            continue

        for user_id in recipients:
            ReklamaceNotifikace.objects.create(
                reklamace=item,
                user_id=user_id,
                message=message,
                typ='reminder_tracking_2d',
            )
            count += 1

        item.reminder_tracking_2d_sent_at = now
        item.save(update_fields=['reminder_tracking_2d_sent_at', 'updated_at'])

    return count


def send_10d_reminders(now=None, *, dry_run: bool = False) -> int:
    """Vytvoří in-app notifikace pro reklamace starší 10 dní. Vrací počet notifikací."""
    now = now or timezone.now()
    cutoff = now - REMINDER_10D
    count = 0

    for item in _open_items_past(cutoff, field_null='reminder_10d_sent_at'):
        message = f'Je to 10 dní – zkontroluj stav reklamace {item.nase_znacka}'
        recipients = reminder_recipient_ids(item)
        if dry_run:
            count += max(len(recipients), 1)
            continue

        for user_id in recipients:
            ReklamaceNotifikace.objects.create(
                reklamace=item,
                user_id=user_id,
                message=message,
                typ='reminder_10d',
            )
            count += 1

        item.reminder_10d_sent_at = now
        item.save(update_fields=['reminder_10d_sent_at', 'updated_at'])

    return count


def _send_slack_to_user(user_id: int, text: str) -> bool:
    try:
        user = WebUser.objects.get(pk=user_id)
    except WebUser.DoesNotExist:
        return False
    slack_id = slack_user_id_for_web_user(user)
    if not slack_id:
        logger.debug('Slack připomínka reklamace – chybí Slack ID pro WebUser #%s', user_id)
        return False
    return send_slack_dm(slack_id, text)


def send_30d_slack_reminders(now=None, *, dry_run: bool = False) -> int:
    """Odešle Slack DM zadavateli a vedoucímu prodejny po 30 dnech. Vrací počet DM."""
    now = now or timezone.now()
    cutoff = now - REMINDER_30D
    count = 0

    for item in _open_items_past(cutoff, field_null='reminder_30d_slack_sent_at'):
        message = f'Zkontroluj stav – reklamace {item.nase_znacka} je 30 dní od založení'
        recipients = reminder_recipient_ids(item)
        if dry_run:
            count += max(len(recipients), 1)
            continue

        for user_id in recipients:
            if _send_slack_to_user(user_id, message):
                count += 1

        item.reminder_30d_slack_sent_at = now
        item.save(update_fields=['reminder_30d_slack_sent_at', 'updated_at'])

    return count


def run_reklamace_reminders(now=None, *, dry_run: bool = False) -> dict[str, int]:
    return {
        'in_app_tracking_2d': send_2d_tracking_reminders(now=now, dry_run=dry_run),
        'in_app_10d': send_10d_reminders(now=now, dry_run=dry_run),
        'slack_30d': send_30d_slack_reminders(now=now, dry_run=dry_run),
    }
