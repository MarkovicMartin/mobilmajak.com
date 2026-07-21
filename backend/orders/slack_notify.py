"""Slack notifikace k interním objednávkám – fail-soft, bez e-mailu."""
from __future__ import annotations

import logging

from django.conf import settings

from stores.models import Prodejna
from tasks.slack_notify import send_slack_dm, slack_user_id_for_web_user
from users.models import WebUser

from .models import Order

logger = logging.getLogger(__name__)


def _app_base_url() -> str:
    return (getattr(settings, "MOBILMAJAK_APP_URL", None) or "https://mobilmajak.com").rstrip("/")


def _bot_token() -> str:
    return (getattr(settings, "SLACK_BOT_TOKEN", None) or "").strip()


def vedouci_user_id_for_order(order: Order) -> int | None:
    """Vedoucí prodejny tvůrce objednávky (zalozil.prodejna_id)."""
    try:
        creator = order.zalozil
    except Exception:
        return None
    prodejna_id = getattr(creator, "prodejna_id", None)
    if not prodejna_id:
        return None
    store = Prodejna.objects.filter(pk=prodejna_id).only("vedouci_user_id").first()
    return store.vedouci_user_id if store else None


def order_recipient_ids(order: Order) -> list[int]:
    ids: list[int] = []
    if order.zalozil_id:
        ids.append(order.zalozil_id)
    vedouci_id = vedouci_user_id_for_order(order)
    if vedouci_id:
        ids.append(vedouci_id)
    return list(dict.fromkeys(ids))


def _order_link(order: Order) -> str:
    return f"{_app_base_url()}/orders?id={order.id}"


def _order_summary(order: Order) -> str:
    customer = f"{order.jmeno_zakaznika} {order.prijmeni_zakaznika}".strip()
    item = f"{order.typ_telefonu} – {order.dil}".strip(" –")
    return f"#{order.id} {customer}: {item}"


def build_order_message(order: Order, event: str, *, days_in_status: int | None = None) -> str:
    link = _order_link(order)
    summary = _order_summary(order)
    status_label = order.get_status_display()
    if event == "created":
        return f"Nová objednávka {summary}\nStav: {status_label}\n{_escape(link)}"
    if event == "sla":
        days = days_in_status if days_in_status is not None else order.days_in_current_status()
        return (
            f"Připomínka: objednávka {days} dní ve stavu „{status_label}“\n"
            f"{summary}\n{_escape(link)}"
        )
    return f"Objednávka {summary}\n{_escape(link)}"


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def send_order_slack_to_recipients(order: Order, event: str, *, days_in_status: int | None = None) -> int:
    """Odešle DM příjemcům. Fail-soft: chybějící Slack ID / token = skip. Vrací počet odeslaných."""
    if not _bot_token():
        logger.debug("SLACK_BOT_TOKEN není nastaven – orders Slack přeskočeno (%s)", event)
        return 0

    text = build_order_message(order, event, days_in_status=days_in_status)
    sent = 0
    for user_id in order_recipient_ids(order):
        try:
            user = WebUser.objects.filter(pk=user_id).first()
            slack_id = slack_user_id_for_web_user(user)
            if not slack_id:
                logger.debug(
                    "Orders Slack přeskočeno – chybí Slack ID WebUser #%s (objednávka #%s, %s)",
                    user_id,
                    order.id,
                    event,
                )
                continue
            if send_slack_dm(slack_id, text):
                sent += 1
        except Exception:
            logger.exception(
                "Orders Slack selhalo pro WebUser #%s (objednávka #%s, %s)",
                user_id,
                order.id,
                event,
            )
    return sent


def notify_order_created(order: Order) -> int:
    try:
        return send_order_slack_to_recipients(order, "created")
    except Exception:
        logger.exception("notify_order_created selhalo pro #%s", order.id)
        return 0


def notify_order_sla(order: Order, *, days_in_status: int | None = None) -> int:
    try:
        return send_order_slack_to_recipients(order, "sla", days_in_status=days_in_status)
    except Exception:
        logger.exception("notify_order_sla selhalo pro #%s", order.id)
        return 0
