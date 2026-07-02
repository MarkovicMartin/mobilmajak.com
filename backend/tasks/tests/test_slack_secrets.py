"""Test načítání Slack secrets ze souboru."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from tasks.slack_secrets import SlackSecrets, slack_config


class SlackSecretsLoadTests(SimpleTestCase):
    def test_env_overrides_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "slack.json"
            path.write_text(
                '{"bot_token": "xoxb-file", "signing_secret": "sec-file"}',
                encoding="utf-8",
            )
            with patch.dict(os.environ, {
                "SLACK_SECRETS_FILE": str(path),
                "SLACK_BOT_TOKEN": "xoxb-env",
            }, clear=False):
                slack_config.cache_clear()
                cfg = slack_config()
                self.assertEqual(cfg.bot_token, "xoxb-env")
                self.assertEqual(cfg.signing_secret, "sec-file")
                slack_config.cache_clear()

    def test_legacy_slacktoken_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "slacktoken.json"
            path.write_text(
                '{"SLACK_ACCESS_BOT_TOKEN": "xoxb-legacy", "MOBILMAJAK_APP_URL": "https://example.com"}',
                encoding="utf-8",
            )
            missing = Path(tmp) / "mobilmajak-slack.json"
            with patch("tasks.slack_secrets.slack_secrets_path", return_value=missing), \
                 patch("tasks.slack_secrets._legacy_slacktoken_path", return_value=path), \
                 patch.dict(os.environ, {}, clear=True):
                os.environ.pop("SLACK_BOT_TOKEN", None)
                os.environ.pop("SLACK_SIGNING_SECRET", None)
                slack_config.cache_clear()
                cfg = slack_config()
                self.assertEqual(cfg.bot_token, "xoxb-legacy")
                self.assertEqual(cfg.app_url, "https://example.com")
                slack_config.cache_clear()

    def test_alias_keys_in_slack_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mobilmajak-slack.json"
            path.write_text(
                '{"SLACK_ACCESS_BOT_TOKEN": "xoxb-a", "SIGNING_SECRET": "sec-a"}',
                encoding="utf-8",
            )
            with patch("tasks.slack_secrets.slack_secrets_path", return_value=path), \
                 patch.dict(os.environ, {}, clear=True):
                os.environ.pop("SLACK_BOT_TOKEN", None)
                os.environ.pop("SLACK_SIGNING_SECRET", None)
                slack_config.cache_clear()
                cfg = slack_config()
                self.assertEqual(cfg.bot_token, "xoxb-a")
                self.assertEqual(cfg.signing_secret, "sec-a")
                slack_config.cache_clear()
