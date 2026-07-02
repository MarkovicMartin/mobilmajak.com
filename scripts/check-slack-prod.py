#!/usr/bin/env python3
"""Ověří Slack konfiguraci na produkci – bez výpisu tokenů."""
import hashlib
import hmac
import json
import os
import sys
import time

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webapp.settings_production")
django.setup()

from django.conf import settings

import requests


def main() -> int:
    secret = settings.SLACK_SIGNING_SECRET or ""
    token = settings.SLACK_BOT_TOKEN or ""
    app_url = settings.MOBILMAJAK_APP_URL or ""

    print(f"bot_token_set={bool(token)}")
    print(f"signing_secret_set={bool(secret)}")
    print(f"app_url={app_url}")

    if not secret or not token:
        print("FAIL missing config")
        return 1

    body = json.dumps({"type": "url_verification", "challenge": "mm-challenge-ok"})
    ts = str(int(time.time()))
    sig = "v0=" + hmac.new(
        secret.encode(), f"v0:{ts}:{body}".encode(), hashlib.sha256
    ).hexdigest()
    r = requests.post(
        f"{app_url.rstrip('/')}/api/tasks/slack/events/",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Slack-Request-Timestamp": ts,
            "X-Slack-Signature": sig,
        },
        timeout=15,
    )
    print(f"challenge_status={r.status_code}")
    print(f"challenge_body={r.text}")
    if r.status_code != 200 or json.loads(r.text).get("challenge") != "mm-challenge-ok":
        print("FAIL challenge")
        return 1

    at = requests.get(
        "https://slack.com/api/auth.test",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    ).json()
    print(f"auth_ok={at.get('ok')}")
    print(f"team={at.get('team')}")
    if not at.get("ok"):
        print(f"auth_error={at.get('error')}")
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
