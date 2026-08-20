"""Slack účty pro notifikace objednávek (servis + prodejny)."""
from __future__ import annotations

from tasks.slack_notify import slack_user_id_for_web_user
from users.models import WebUser

# Servis Globus (servis@mobilmajak.cz)
SERVIS_GLOBUS_SLACK_ID = "U9MCYUWNN"

# Prodejny – Slack Member ID podle názvu v WEB_PRODEJNY
PRODEJNA_SLACK_BY_NAZEV: dict[str, str] = {
    "Globus": "UJEURV2G4",
    "Senimo": "U7X7ETS15",
    "Čepkov": "U026QUF0YAJ",
    "Přerov": "U04HDHCN7JT",
    "Vsetín": "U07V55LAEA0",
    "Šternberk": "U7VG523Q9",
}

BULANDRA_TECHNIK_ID = 103


def prodejna_slack_id_for_order(order) -> str | None:
    prodejna = getattr(order, "prodejna", None)
    if not prodejna:
        return None
    nazev = (getattr(prodejna, "nazev", None) or "").strip()
    if not nazev:
        return None
    return PRODEJNA_SLACK_BY_NAZEV.get(nazev)


def servis_and_prodejna_slack_ids(order) -> list[str]:
    """Servis Globus + účet prodejny objednávky (bez duplicit)."""
    ids: list[str] = []
    for sid in (SERVIS_GLOBUS_SLACK_ID, prodejna_slack_id_for_order(order)):
        if sid and sid not in ids:
            ids.append(sid)
    return ids


def bulandra_slack_id() -> str | None:
    """Radek Bulandra – admin eskalace (lookup přes WebUser e-mail)."""
    user = WebUser.objects.filter(technik_id=BULANDRA_TECHNIK_ID, aktivni=True).first()
    if not user:
        user = WebUser.objects.filter(prijmeni__iexact="Bulandra", aktivni=True).first()
    if not user:
        return None
    return slack_user_id_for_web_user(user)
