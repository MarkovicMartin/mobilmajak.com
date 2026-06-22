"""Spáruje e-maily WebUser podle jména s aktivními uživateli ve Slacku."""
from __future__ import annotations

import unicodedata

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from users.models import WebUser


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").strip().lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _fetch_slack_members(token: str) -> list[dict]:
    members: list[dict] = []
    cursor = None
    headers = {"Authorization": f"Bearer {token}"}
    while True:
        params: dict = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        r = requests.get("https://slack.com/api/users.list", params=params, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("error", "users.list failed"))
        members.extend(data.get("members", []))
        cursor = (data.get("response_metadata") or {}).get("next_cursor")
        if not cursor:
            break

    out = []
    for m in members:
        if m.get("deleted") or m.get("is_bot") or m.get("id") == "USLACKBOT":
            continue
        profile = m.get("profile") or {}
        email = (profile.get("email") or "").strip()
        if not email:
            continue
        real_name = (profile.get("real_name") or profile.get("display_name") or m.get("name") or "").strip()
        out.append({
            "slack_id": m["id"],
            "email": email,
            "real_name": real_name,
            "norm_name": _norm(real_name),
        })
    return out


# Ruční mapování MOBILMAJAK jméno → Slack real_name (když se liší)
_MANUAL_SLACK_NAMES: dict[str, str] = {
    "artur babusik": "benny babusik",
    "frantisek vychodil": "franta vychodil servis",
    "honza bajtek": "jan bajtek",
}


def _match_slack_user(web_user: WebUser, slack_users: list[dict]) -> dict | None:
    full = _norm(f"{web_user.jmeno} {web_user.prijmeni}".strip())
    if not full or full in {"novy prodejce", "administrator systemovy", "administrátor systémový"}:
        return None

    alias = _MANUAL_SLACK_NAMES.get(full)
    if alias:
        manual = [s for s in slack_users if s["norm_name"] == alias]
        if len(manual) == 1:
            return manual[0]

    exact = [s for s in slack_users if s["norm_name"] == full]
    if len(exact) == 1:
        return exact[0]

    jmeno_n = _norm(web_user.jmeno)
    prijmeni_n = _norm(web_user.prijmeni)
    if not jmeno_n or not prijmeni_n:
        return None

    partial = [
        s for s in slack_users
        if jmeno_n in s["norm_name"] and prijmeni_n in s["norm_name"]
    ]
    if len(partial) == 1:
        return partial[0]
    return None


class Command(BaseCommand):
    help = "Spáruje e-mail WebUser podle jména s uživateli ve Slacku (users.list + users:read.email)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Uloží nové e-maily do DB (výchozí je jen náhled).",
        )

    def handle(self, *args, **options):
        token = (getattr(settings, "SLACK_BOT_TOKEN", None) or "").strip()
        if not token:
            self.stderr.write(self.style.ERROR("SLACK_BOT_TOKEN není nastaven."))
            return

        slack_users = _fetch_slack_members(token)
        self.stdout.write(f"Slack: {len(slack_users)} aktivních uživatelů s e-mailem")

        matched = 0
        updated = 0
        skipped = 0
        unmatched = []

        for user in WebUser.objects.filter(aktivni=True).order_by("prijmeni", "jmeno"):
            slack = _match_slack_user(user, slack_users)
            if not slack:
                if user.jmeno and user.prijmeni:
                    unmatched.append(f"  #{user.id} {user.jmeno} {user.prijmeni} (email: {user.email or '—'})")
                continue

            matched += 1
            old = (user.email or "").strip()
            new = slack["email"]
            if old.lower() == new.lower():
                skipped += 1
                self.stdout.write(f"  OK #{user.id} {user.jmeno} {user.prijmeni} – e-mail už sedí ({new})")
                continue

            self.stdout.write(
                f"  → #{user.id} {user.jmeno} {user.prijmeni}: "
                f"{old or '—'} → {new}  (Slack: {slack['real_name']})"
            )
            if options["apply"]:
                user.email = new
                user.save(update_fields=["email"])
                updated += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Spárováno: {matched}, už OK: {skipped}, "
            f"{'aktualizováno' if options['apply'] else 'k aktualizaci'}: "
            f"{updated if options['apply'] else matched - skipped}"
        ))
        if unmatched:
            self.stdout.write(self.style.WARNING(f"Bez páru ve Slacku ({len(unmatched)}):"))
            for line in unmatched:
                self.stdout.write(line)
