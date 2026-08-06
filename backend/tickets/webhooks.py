"""Odeslání notifikace na N8N webhook při novém ticketu nebo komentáři."""
import logging
import threading
from django.conf import settings
import requests

logger = logging.getLogger(__name__)
requests.packages.urllib3.disable_warnings()

# Krátký timeout – webhook nesmí blokovat HTTP odpověď klientovi.
WEBHOOK_TIMEOUT_SEC = 5


def _notify_webhooks(payload):
    """Odešle payload na všechny nakonfigurované webhooky (synchronně)."""
    urls = getattr(settings, 'TICKET_WEBHOOK_URLS', [])
    if not urls:
        logger.warning('TICKET_WEBHOOK_URLS není nastaveno')
        return

    for url in urls:
        try:
            r = requests.post(
                url,
                json=payload,
                timeout=WEBHOOK_TIMEOUT_SEC,
                verify=False,
                headers={'Content-Type': 'application/json'},
            )
            logger.info('Webhook %s: %s %s', url[:50], r.status_code, payload.get('event'))
        except Exception as e:
            logger.exception('Webhook %s selhal: %s', url[:50], e)


def _notify_webhooks_async(payload):
    """Spustí webhook na pozadí, aby create/comment API ihned vrátilo 201."""
    thread = threading.Thread(
        target=_notify_webhooks,
        args=(payload,),
        name='ticket-webhook',
        daemon=True,
    )
    thread.start()


def notify_ticket_created(ticket):
    """Zavolá se po vytvoření nového ticketu."""
    logger.info('notify_ticket_created: ticket_id=%s', ticket.id)
    payload = {
        'event': 'ticket_created',
        'ticket_id': ticket.id,
        'nazev': ticket.nazev,
        'popis': ticket.popis[:500] if ticket.popis else '',
        'autor_jmeno': ticket.autor_jmeno,
        'autor_id': ticket.autor_id,
        'url': ticket.url or '',
        'vytvoreno': ticket.vytvoreno.isoformat() if ticket.vytvoreno else None,
    }
    _notify_webhooks_async(payload)


def notify_comment_added(ticket, comment):
    """Zavolá se po přidání komentáře k ticketu."""
    logger.info('notify_comment_added: ticket_id=%s comment_id=%s', ticket.id, comment.id)
    payload = {
        'event': 'comment_added',
        'ticket_id': ticket.id,
        'comment_id': comment.id,
        'ticket_nazev': ticket.nazev,
        'autor_jmeno': comment.autor_jmeno,
        'text': comment.text[:500] if comment.text else '',
        'vytvoreno': comment.vytvoreno.isoformat() if comment.vytvoreno else None,
    }
    _notify_webhooks_async(payload)
