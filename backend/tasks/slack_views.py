"""HTTP endpointy pro Slack Events, slash command a interactivity."""
from __future__ import annotations

import json
import logging

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .slack_notify import web_user_for_slack_id
from .slack_verify import slack_signing_secret, verify_slack_request
from .slack_wizard import (
    handle_slack_interaction,
    handle_slack_text_message,
    handle_slack_view_submission,
    parse_interaction_payload,
    start_slack_task_wizard,
)

logger = logging.getLogger(__name__)


def _slack_disabled_response() -> HttpResponse:
    return JsonResponse({"ok": False, "error": "slack_not_configured"}, status=503)


def _verify_or_403(request) -> bool:
    if not slack_signing_secret():
        return False
    return verify_slack_request(request)


@csrf_exempt
@require_POST
def slack_events(request):
    if not slack_signing_secret():
        return _slack_disabled_response()
    if not _verify_or_403(request):
        return HttpResponse(status=403)

    try:
        body = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return HttpResponse(status=400)

    if body.get("type") == "url_verification":
        return JsonResponse({"challenge": body.get("challenge", "")})

    if body.get("type") != "event_callback":
        return HttpResponse(status=200)

    event = body.get("event") or {}
    if event.get("type") != "message":
        return HttpResponse(status=200)
    if event.get("subtype") or event.get("bot_id"):
        return HttpResponse(status=200)

    channel_type = event.get("channel_type")
    if channel_type not in ("im", "mpim"):
        return HttpResponse(status=200)

    slack_user_id = event.get("user") or ""
    text = event.get("text") or ""
    channel_id = event.get("channel") or ""

    try:
        handle_slack_text_message(slack_user_id, text, channel_id=channel_id)
    except Exception:
        logger.exception("Slack message handler selhal")

    return HttpResponse(status=200)


@csrf_exempt
@require_POST
def slack_interactions(request):
    if not slack_signing_secret():
        return _slack_disabled_response()
    if not _verify_or_403(request):
        return HttpResponse(status=403)

    raw_payload = request.POST.get("payload", "")
    if not raw_payload:
        return HttpResponse(status=400)

    try:
        payload = parse_interaction_payload(raw_payload)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    try:
        if payload.get("type") == "view_submission":
            handle_slack_view_submission(payload)
        else:
            handle_slack_interaction(payload)
    except Exception:
        logger.exception("Slack interaction handler selhal")

    return HttpResponse(status=200)


@csrf_exempt
@require_POST
def slack_slash_ukol(request):
    if not slack_signing_secret():
        return _slack_disabled_response()
    if not _verify_or_403(request):
        return HttpResponse(status=403)

    slack_user_id = request.POST.get("user_id", "")
    channel_id = request.POST.get("channel_id", "")
    initial_text = (request.POST.get("text") or "").strip()

    web_user = web_user_for_slack_id(slack_user_id)
    if not web_user:
        return JsonResponse({
            "response_type": "ephemeral",
            "text": (
                "Tvůj Slack účet není propojený s MOBILMAJAK. "
                "Vyplň stejný e-mail v profilu aplikace."
            ),
        })

    try:
        msg, ok = start_slack_task_wizard(
            slack_user_id,
            web_user,
            channel_id=channel_id,
            initial_text=initial_text,
        )
    except Exception:
        logger.exception("Slack /ukol selhal")
        return JsonResponse({
            "response_type": "ephemeral",
            "text": "Zakládání úkolu selhalo. Zkus to znovu nebo použij web.",
        })

    return JsonResponse({
        "response_type": "ephemeral",
        "text": msg if ok else "Zakládání úkolu se nepodařilo spustit.",
    })
