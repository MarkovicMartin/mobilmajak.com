"""Příjemci denního Slack reportu – výběr z WebUser.slack_daily_report."""
from __future__ import annotations

from users.models import WebUser

# Výchozí příjemci (data migrace); další lze zapnout v profilu nebo adminem.
DEFAULT_DAILY_REPORT_NAMES = (
    ('Radek', 'Bulandra'),
    ('Petr', 'Valenta'),
)


def daily_report_recipient_queryset():
    return WebUser.objects.filter(aktivni=True, slack_daily_report=True).order_by('prijmeni', 'jmeno')
