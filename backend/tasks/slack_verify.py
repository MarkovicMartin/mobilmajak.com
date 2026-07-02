"""Ověření podpisu požadavků ze Slack API."""
from __future__ import annotations

import hashlib
import hmac
import time

from django.conf import settings


def slack_signing_secret() -> str:
    return (getattr(settings, "SLACK_SIGNING_SECRET", None) or "").strip()


def verify_slack_request(request) -> bool:
    secret = slack_signing_secret()
    if not secret:
        return False

    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    if not timestamp or not signature:
        return False

    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False

    if abs(time.time() - ts) > 60 * 5:
        return False

    body = request.body
    if isinstance(body, bytes):
        body_text = body.decode("utf-8")
    else:
        body_text = str(body)

    base = f"v0:{timestamp}:{body_text}"
    digest = hmac.new(secret.encode("utf-8"), base.encode("utf-8"), hashlib.sha256).hexdigest()
    expected = f"v0={digest}"
    return hmac.compare_digest(expected, signature)
