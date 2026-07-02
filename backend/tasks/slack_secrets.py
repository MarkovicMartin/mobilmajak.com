"""Načtení secrets/mobilmajak-slack.json – env proměnné mají přednost."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from django.conf import settings


@dataclass(frozen=True)
class SlackSecrets:
    bot_token: str = ""
    signing_secret: str = ""
    tasks_webhook_url: str = ""
    app_url: str = ""


def slack_secrets_path() -> Path:
    env_path = os.getenv("SLACK_SECRETS_FILE", "").strip()
    if env_path:
        p = Path(env_path)
        if not p.is_absolute():
            p = settings.BASE_DIR.parent / p
        return p
    return settings.BASE_DIR.parent / "secrets" / "mobilmajak-slack.json"


def _legacy_slacktoken_path() -> Path:
    return settings.BASE_DIR.parent / "secrets" / "slacktoken.json"


def _load_json_file(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _normalize_slack_dict(data: dict) -> dict:
    """Podporuje mobilmajak-slack.json i starší pojmenování klíčů."""
    return {
        "bot_token": (
            data.get("bot_token")
            or data.get("SLACK_BOT_TOKEN")
            or data.get("SLACK_ACCESS_BOT_TOKEN")
            or ""
        ).strip(),
        "signing_secret": (
            data.get("signing_secret")
            or data.get("SLACK_SIGNING_SECRET")
            or data.get("SIGNING_SECRET")
            or ""
        ).strip(),
        "tasks_webhook_url": (
            data.get("tasks_webhook_url")
            or data.get("SLACK_TASKS_WEBHOOK_URL")
            or ""
        ).strip(),
        "app_url": (
            data.get("app_url")
            or data.get("MOBILMAJAK_APP_URL")
            or ""
        ).strip(),
    }


def _file_secrets() -> SlackSecrets:
    data = _normalize_slack_dict(_load_json_file(slack_secrets_path()))
    if not data.get("bot_token") and not data.get("signing_secret"):
        legacy = _normalize_slack_dict(_load_json_file(_legacy_slacktoken_path()))
        if legacy.get("bot_token") or legacy.get("signing_secret"):
            data = legacy
    return SlackSecrets(
        bot_token=data.get("bot_token", ""),
        signing_secret=data.get("signing_secret", ""),
        tasks_webhook_url=data.get("tasks_webhook_url", ""),
        app_url=data.get("app_url", ""),
    )


@lru_cache(maxsize=1)
def slack_config() -> SlackSecrets:
    """Env má přednost před JSON souborem."""
    file_cfg = _file_secrets()
    return SlackSecrets(
        bot_token=os.getenv("SLACK_BOT_TOKEN", file_cfg.bot_token).strip(),
        signing_secret=os.getenv("SLACK_SIGNING_SECRET", file_cfg.signing_secret).strip(),
        tasks_webhook_url=os.getenv("SLACK_TASKS_WEBHOOK_URL", file_cfg.tasks_webhook_url).strip(),
        app_url=os.getenv("MOBILMAJAK_APP_URL", file_cfg.app_url or "https://mobilmajak.com").strip(),
    )
