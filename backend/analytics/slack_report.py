"""Odeslání denního reportu do Slacku (DM přes bota)."""
from __future__ import annotations

import logging

from tasks.slack_notify import send_slack_dm, slack_user_id_for_web_user
from users.models import WebUser

logger = logging.getLogger(__name__)


def resolve_daily_report_user(identifier: str) -> WebUser | None:
    """Ruční cílení podle přihlašovacího jména nebo příjmení (--user)."""
    ident = (identifier or '').strip()
    if not ident:
        return None
    user = WebUser.objects.filter(uzivatelske_jmeno__iexact=ident, aktivni=True).first()
    if user:
        return user
    return WebUser.objects.filter(prijmeni__iexact=ident, aktivni=True).first()


def send_daily_report_dm(user: WebUser, text: str) -> bool:
    slack_id = slack_user_id_for_web_user(user)
    if not slack_id:
        logger.warning(
            'Slack DM pro denní report – chybí Slack ID (WebUser #%s, email=%s)',
            user.id,
            user.email or '',
        )
        return False
    return send_slack_dm(slack_id, text)
