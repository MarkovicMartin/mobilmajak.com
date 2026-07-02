"""Testy Slack zakládání úkolů – wizard a podpis."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from unittest.mock import patch

from django.test import Client, TestCase, override_settings

from stores.models import Prodejna
from tasks.models import SlackTaskDraft, Ukol
from tasks.slack_wizard import (
    STEP_CHOOSE_DEADLINE,
    STEP_CONFIRM,
    handle_slack_interaction,
    handle_slack_text_message,
    handle_slack_view_submission,
    start_slack_task_wizard,
)
from tasks.task_create_service import create_ukol_for_user
from users.models import WebUser


def _make_user(pk, role="PRODEJCE", email=None, prodejna_id=None):
    return WebUser.objects.create(
        id=pk,
        uzivatelske_jmeno=f"user{pk}",
        jmeno=f"Jméno{pk}",
        prijmeni=f"Příjmení{pk}",
        heslo="x",
        role=role,
        aktivni=True,
        email=email or f"user{pk}@example.com",
        prodejna_id=prodejna_id,
    )


def _sign_body(secret: str, body: bytes) -> dict:
    ts = str(int(time.time()))
    base = f"v0:{ts}:{body.decode('utf-8')}"
    sig = "v0=" + hmac.new(secret.encode(), base.encode(), hashlib.sha256).hexdigest()
    return {
        "HTTP_X_SLACK_REQUEST_TIMESTAMP": ts,
        "HTTP_X_SLACK_SIGNATURE": sig,
        "CONTENT_TYPE": "application/json",
    }


@override_settings(SLACK_SIGNING_SECRET="test-signing-secret")
class SlackVerifyTests(TestCase):
    def test_verify_valid_signature(self):
        body = b'{"type":"url_verification","challenge":"abc"}'
        headers = _sign_body("test-signing-secret", body)
        client = Client()
        response = client.post(
            "/api/tasks/slack/events/",
            data=body,
            content_type="application/json",
            **headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["challenge"], "abc")


@override_settings(
    SLACK_BOT_TOKEN="xoxb-test",
    SLACK_SIGNING_SECRET="test-signing-secret",
)
class SlackWizardTests(TestCase):
    def setUp(self):
        self.prodejce = _make_user(9201, "PRODEJCE", "prodejce@example.com", prodejna_id=101)
        self.vedouci = _make_user(9202, "VEDOUCI", "vedouci@example.com", prodejna_id=101)
        self.admin = _make_user(9203, "ADMIN", "admin@example.com")
        self.store = Prodejna.objects.create(
            id=101,
            nazev="Test Prodejna",
            nazev_kratkiy="Test",
            aktivni=True,
            vedouci_user_id=self.vedouci.id,
        )

    @patch("tasks.slack_notify.notify_task_lifecycle_change")
    @patch("tasks.slack_notify.web_user_for_slack_id")
    @patch("tasks.slack_wizard.send_slack_dm", return_value=True)
    def test_prodejce_osobni_flow_creates_task(self, mock_dm, mock_lookup, mock_notify):
        mock_lookup.return_value = self.prodejce
        start_slack_task_wizard("U_SLACK", self.prodejce, initial_text="Uklidit vitrínu")
        draft = SlackTaskDraft.objects.get(slack_user_id="U_SLACK")
        self.assertEqual(draft.step, STEP_CHOOSE_DEADLINE)

        handle_slack_interaction({
            "user": {"id": "U_SLACK"},
            "actions": [{"action_id": "slack_ukol:deadline:today", "value": "today"}],
        })
        draft.refresh_from_db()
        self.assertEqual(draft.step, "choose_priority")

        handle_slack_interaction({
            "user": {"id": "U_SLACK"},
            "actions": [{"action_id": "slack_ukol:priority:stredni", "value": "stredni"}],
        })
        draft.refresh_from_db()
        self.assertEqual(draft.step, STEP_CONFIRM)

        handle_slack_interaction({
            "user": {"id": "U_SLACK"},
            "actions": [{"action_id": "slack_ukol:confirm:create", "value": "create"}],
        })

        self.assertFalse(SlackTaskDraft.objects.filter(slack_user_id="U_SLACK").exists())
        task = Ukol.objects.filter(id_prodejce_ukol=self.prodejce.id, typ="osobni").first()
        self.assertIsNotNone(task)
        self.assertIn("vitrínu", (task.vysledek or "").lower())

    def test_create_service_prodejce_forces_osobni(self):
        task, err = create_ukol_for_user(self.prodejce, {
            "typ": "prirazeny",
            "vysledek": "Test",
            "ukol": "Test",
            "id_prodejce_ukol": self.vedouci.id,
            "id_prodejny": self.store.id,
            "deadline": "2026-12-31",
            "dod_polozky": [{"text": "krok 1", "splneno": False}],
        })
        self.assertIsNone(err)
        self.assertEqual(task.typ, "osobni")
        self.assertEqual(task.id_prodejce_ukol, self.prodejce.id)

    def test_create_service_admin_osobni_sets_assignee(self):
        task, err = create_ukol_for_user(self.admin, {
            "typ": "osobni",
            "vysledek": "test self úkolů do appky",
            "priorita": "nizka",
            "stav": "novy",
            "deadline": "2026-07-01",
        })
        self.assertIsNone(err, err)
        self.assertIsNotNone(task)
        self.assertEqual(task.typ, "osobni")
        self.assertEqual(task.id_prodejce_ukol, self.admin.id)
        self.assertEqual(task.id_prodejce_zadal, self.admin.id)

    @patch("tasks.slack_wizard.send_slack_dm", return_value=True)
    @patch("tasks.slack_notify.web_user_for_slack_id")
    def test_admin_prirazeny_dod_default_button(self, mock_lookup, mock_dm):
        mock_lookup.return_value = self.admin
        start_slack_task_wizard(
            "U_ADMIN",
            self.admin,
            initial_text="Kontrola výlohy",
        )
        handle_slack_interaction({
            "user": {"id": "U_ADMIN"},
            "actions": [{"action_id": "slack_ukol:typ:prirazeny", "value": "prirazeny"}],
        })
        handle_slack_interaction({
            "user": {"id": "U_ADMIN"},
            "actions": [{"action_id": f"slack_ukol:store:{self.store.id}", "value": str(self.store.id)}],
        })
        handle_slack_interaction({
            "user": {"id": "U_ADMIN"},
            "actions": [{"action_id": f"slack_ukol:assignee:{self.prodejce.id}", "value": str(self.prodejce.id)}],
        })
        handle_slack_interaction({
            "user": {"id": "U_ADMIN"},
            "actions": [{"action_id": "slack_ukol:dod:default", "value": "default"}],
        })
        draft = SlackTaskDraft.objects.get(slack_user_id="U_ADMIN")
        self.assertEqual(draft.step, STEP_CHOOSE_DEADLINE)
        self.assertEqual(len(draft.data.get("dod_polozky") or []), 1)
        self.assertIn("výlohy", draft.data["dod_polozky"][0]["text"].lower())

    @patch("tasks.slack_wizard.send_slack_dm", return_value=True)
    @patch("tasks.slack_notify.web_user_for_slack_id")
    def test_admin_sees_all_six_stores_in_wizard(self, mock_lookup, mock_dm):
        mock_lookup.return_value = self.admin
        Prodejna.objects.filter(pk=self.store.id).delete()
        for i, name in enumerate(
            ["Globus", "Přerov", "Senimo", "Šternberk", "Vsetín", "Zlín"],
            start=201,
        ):
            Prodejna.objects.create(
                id=i,
                nazev=name,
                nazev_kratkiy=name,
                aktivni=True,
            )
        draft = SlackTaskDraft.objects.create(
            slack_user_id="U_STORES",
            web_user_id=self.admin.id,
            step="choose_store",
            data={"typ": "prirazeny", "vysledek": "Test"},
        )
        from tasks.slack_wizard import _step_blocks
        _, blocks = _step_blocks(draft, self.admin)
        action_blocks = [b for b in blocks if b.get("type") == "actions"]
        store_ids = set()
        store_row_sizes = []
        for block in action_blocks:
            row = []
            for el in block.get("elements") or []:
                aid = el.get("action_id") or ""
                if aid.startswith("slack_ukol:store:") and not aid.endswith(":none"):
                    store_ids.add(aid.split(":")[-1])
                    row.append(el)
            if row:
                store_row_sizes.append(len(row))
        self.assertEqual(len(store_ids), 6)
        self.assertEqual(store_row_sizes, [3, 3])

    @patch("tasks.slack_wizard.send_slack_dm", return_value=True)
    @patch("tasks.slack_notify.web_user_for_slack_id")
    def test_view_submission_dod_modal(self, mock_lookup, mock_dm):
        mock_lookup.return_value = self.admin
        SlackTaskDraft.objects.create(
            slack_user_id="U_MODAL",
            web_user_id=self.admin.id,
            step="enter_dod",
            data={
                "typ": "prirazeny",
                "vysledek": "Outcome",
                "id_prodejce_ukol": self.prodejce.id,
            },
        )
        handled = handle_slack_view_submission({
            "type": "view_submission",
            "user": {"id": "U_MODAL"},
            "view": {
                "callback_id": "slack_ukol_modal:dod",
                "private_metadata": "U_MODAL",
                "state": {
                    "values": {
                        "text_input": {"value": {"value": "Zkontrolovat sklad"}},
                    },
                },
            },
        })
        self.assertTrue(handled)
        draft = SlackTaskDraft.objects.get(slack_user_id="U_MODAL")
        self.assertEqual(len(draft.data.get("dod_polozky") or []), 1)
        self.assertEqual(draft.data["dod_polozky"][0]["text"], "Zkontrolovat sklad")

    @patch("tasks.slack_wizard.send_slack_dm", return_value=True)
    @patch("tasks.slack_notify.web_user_for_slack_id")
    def test_dm_trigger_starts_wizard(self, mock_lookup, mock_dm):
        mock_lookup.return_value = self.prodejce
        handled = handle_slack_text_message("U_SLACK2", "úkol: doplnit sklo", channel_id="D1")
        self.assertTrue(handled)
        self.assertTrue(SlackTaskDraft.objects.filter(slack_user_id="U_SLACK2").exists())

    @patch("tasks.slack_views.web_user_for_slack_id")
    def test_slash_command_unknown_user(self, mock_lookup):
        mock_lookup.return_value = None
        body = "user_id=U999&channel_id=D1&text="
        headers = _sign_body("test-signing-secret", body.encode())
        client = Client()
        response = client.post(
            "/api/tasks/slack/commands/ukol/",
            data=body,
            content_type="application/x-www-form-urlencoded",
            **headers,
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("propojený", data["text"])
