"""Slack notifikace k interním objednávkám – fail-soft, bez e-mailu."""
from __future__ import annotations

import logging

from django.conf import settings

from tasks.slack_notify import send_slack_dm
from users.mzda_utils import is_vychodil_user

from .models import Order
from .slack_recipients import (
    SERVIS_GLOBUS_SLACK_ID,
    bulandra_slack_id,
    markovic_slack_id,
    servis_and_prodejna_slack_ids,
    slack_id_label,
)

logger = logging.getLogger(__name__)


def _app_base_url() -> str:
    return (getattr(settings, "MOBILMAJAK_APP_URL", None) or "https://mobilmajak.com").rstrip("/")


def _bot_token() -> str:
    return (getattr(settings, "SLACK_BOT_TOKEN", None) or "").strip()


def _orders_slack_test_mode() -> bool:
    return bool(getattr(settings, "ORDERS_SLACK_TEST_MODE", False))


def _order_link(order: Order) -> str:
    return f"{_app_base_url()}/orders?id={order.id}"


def _order_summary(order: Order) -> str:
    customer = f"{order.jmeno_zakaznika} {order.prijmeni_zakaznika}".strip()
    item = f"{order.typ_telefonu} – {order.dil}".strip(" –")
    return f"#{order.id} {customer}: {item}"


def _prodejna_label(order: Order) -> str:
    prodejna = getattr(order, "prodejna", None)
    if prodejna and getattr(prodejna, "nazev", None):
        return prodejna.nazev
    return "—"


def _creator_label(order: Order) -> str:
    try:
        user = order.zalozil
    except Exception:
        return "—"
    if not user:
        return "—"
    name = f"{user.jmeno} {user.prijmeni}".strip()
    return name or f"#{user.id}"


def build_order_message(
    order: Order,
    event: str,
    *,
    days_in_status: int | None = None,
    business_days: int | None = None,
) -> str:
    link = _order_link(order)
    summary = _order_summary(order)
    status_label = order.get_status_display()
    prodejna = _prodejna_label(order)

    if event == "created":
        return (
            f"Nová objednávka {summary}\n"
            f"Prodejna: {prodejna} | Stav: {status_label}\n"
            f"Založil: {_creator_label(order)}\n"
            f"{_escape(link)}"
        )
    if event == "stale":
        bd = business_days if business_days is not None else 1
        day_word = "den" if bd == 1 else "dny" if 2 <= bd <= 4 else "dní"
        return (
            f"Objednávka bez pohybu {bd} prac. {day_word}\n"
            f"{summary}\n"
            f"Prodejna: {prodejna} | Stav: {status_label}\n"
            f"{_escape(link)}"
        )
    if event == "escalation_admin":
        days = days_in_status if days_in_status is not None else order.days_in_current_status()
        return (
            f"Zaseknutá objednávka!\n"
            f"{summary}\n"
            f"Prodejna: {prodejna} | {days} dní ve stavu „{status_label}“\n"
            f"{_escape(link)}"
        )
    if event == "escalation_store":
        days = days_in_status if days_in_status is not None else order.days_in_current_status()
        return (
            f"Zaseklá objednávka\n"
            f"{summary}\n"
            f"Prodejna: {prodejna} | {days} dní ve stavu „{status_label}“\n"
            f"{_escape(link)}"
        )
    return f"Objednávka {summary}\n{_escape(link)}"


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _wrap_test_message(text: str, *, intended_target: str, event: str) -> str:
    return (
        f"[TEST objednávky – {_app_base_url()}]\n"
        f"Událost: {event}\n"
        f"Cíl (produkce): {intended_target}\n"
        f"---\n"
        f"{text}"
    )


def _send_to_slack_ids(
    slack_ids: list[str],
    text: str,
    *,
    order_id: int,
    event: str,
    intended_labels: list[str] | None = None,
) -> int:
    if not _bot_token():
        logger.debug("SLACK_BOT_TOKEN není nastaven – orders Slack přeskočeno (%s)", event)
        return 0

    labels = intended_labels or [slack_id_label(sid) for sid in slack_ids]

    if _orders_slack_test_mode():
        test_recipient = markovic_slack_id()
        if not test_recipient:
            logger.debug("Orders Slack test – chybí Slack ID Markoviče (#%s, %s)", order_id, event)
            return 0
        sent = 0
        pairs = [
            (sid, label)
            for sid, label in zip(slack_ids, labels)
            if label
        ]
        if not pairs and labels:
            pairs = [(slack_ids[0] if slack_ids else "", labels[0])]
        for _sid, label in pairs:
            payload = _wrap_test_message(text, intended_target=label, event=event)
            if send_slack_dm(test_recipient, payload):
                sent += 1
        return sent

    sent = 0
    for slack_id in slack_ids:
        if not slack_id:
            continue
        try:
            if send_slack_dm(slack_id, text):
                sent += 1
            else:
                logger.debug(
                    "Orders Slack selhalo pro %s (objednávka #%s, %s)",
                    slack_id,
                    order_id,
                    event,
                )
        except Exception:
            logger.exception(
                "Orders Slack selhalo pro %s (objednávka #%s, %s)",
                slack_id,
                order_id,
                event,
            )
    return sent


def notify_order_created(order: Order) -> int:
    if is_vychodil_user(order.zalozil):
        if not _orders_slack_test_mode():
            logger.debug("notify_order_created přeskočeno – založil Vychodil (#%s)", order.id)
            return 0
        text = build_order_message(order, "created")
        return _send_to_slack_ids(
            [SERVIS_GLOBUS_SLACK_ID],
            text,
            order_id=order.id,
            event="created",
            intended_labels=["Neposílat (založil František Vychodil)"],
        )

    text = build_order_message(order, "created")
    return _send_to_slack_ids(
        [SERVIS_GLOBUS_SLACK_ID],
        text,
        order_id=order.id,
        event="created",
    )


def notify_order_stale(order: Order, *, business_days: int | None = None) -> int:
    try:
        text = build_order_message(order, "stale", business_days=business_days)
        slack_ids = servis_and_prodejna_slack_ids(order)
        return _send_to_slack_ids(
            slack_ids,
            text,
            order_id=order.id,
            event="stale",
        )
    except Exception:
        logger.exception("notify_order_stale selhalo pro #%s", order.id)
        return 0


def notify_order_sla(order: Order, *, days_in_status: int | None = None) -> int:
    """7d eskalace: Bulandra (admin) + servis Globus + prodejna."""
    try:
        sent = 0
        admin_id = bulandra_slack_id()
        text_admin = build_order_message(order, "escalation_admin", days_in_status=days_in_status)
        if admin_id:
            sent += _send_to_slack_ids(
                [admin_id],
                text_admin,
                order_id=order.id,
                event="escalation_admin",
                intended_labels=["Radek Bulandra (admin)"],
            )
        elif _orders_slack_test_mode():
            sent += _send_to_slack_ids(
                [],
                text_admin,
                order_id=order.id,
                event="escalation_admin",
                intended_labels=["Radek Bulandra (admin – Slack ID nenalezeno)"],
            )
        else:
            logger.debug("Orders 7d eskalace – chybí Slack ID Bulandra (#%s)", order.id)

        text_store = build_order_message(order, "escalation_store", days_in_status=days_in_status)
        sent += _send_to_slack_ids(
            servis_and_prodejna_slack_ids(order),
            text_store,
            order_id=order.id,
            event="escalation_store",
        )
        return sent
    except Exception:
        logger.exception("notify_order_sla selhalo pro #%s", order.id)
        return 0
