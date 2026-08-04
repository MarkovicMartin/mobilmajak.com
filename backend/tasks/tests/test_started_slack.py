from datetime import date
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from stores.models import Prodejna
from tasks.models import Ukol, UkolSlackNotifikace
from tasks.slack_notify import notify_task_event, notify_task_lifecycle_change
from users.models import WebUser


def _make_user(pk, role, prodejna_id=None, **kwargs):
    defaults = {
        "uzivatelske_jmeno": f"user{pk}",
        "jmeno": "Test",
        "prijmeni": f"User{pk}",
        "heslo": "x",
        "role": role,
        "aktivni": True,
        "moduly": [],
    }
    defaults.update(kwargs)
    user, _ = WebUser.objects.update_or_create(id=pk, defaults=defaults)
    if prodejna_id is not None:
        user.prodejna_id = prodejna_id
        user.save(update_fields=["prodejna_id"])
    return user


@override_settings(SLACK_BOT_TOKEN="xoxb-test")
class TaskStartedSlackTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = _make_user(9301, "ADMIN", jmeno="Zadavatel", prijmeni="Admin")
        self.prodejce = _make_user(
            9302, "PRODEJCE", prodejna_id=401, jmeno="Rešitel", prijmeni="Prodejce"
        )
        self.store = Prodejna.objects.create(
            id=401,
            nazev="Prodejna Start DM",
            nazev_kratkiy="SD",
            vedouci_user_id=self.admin.id,
            aktivni=True,
        )
        self.task = Ukol.objects.create(
            ukol="Začni pracovat",
            vysledek="Začni pracovat",
            dod_polozky=[{"text": "Hotovo", "splneno": False}],
            priorita="stredni",
            typ="prirazeny",
            stav="novy",
            deadline=date.today(),
            id_prodejce_ukol=self.prodejce.id,
            id_prodejce_zadal=self.admin.id,
            id_prodejny=self.store.id,
        )

    @patch("tasks.slack_notify.slack_user_id_for_web_user", return_value="U_ZADAVATEL")
    @patch("tasks.slack_notify._slack_api", return_value={"ok": True})
    def test_started_event_notifies_zadavatel(self, _mock_api, _mock_lookup):
        sent = notify_task_event(self.task, "started")
        self.assertEqual(sent, 1)
        self.assertTrue(
            UkolSlackNotifikace.objects.filter(
                ukol=self.task,
                typ="dm_started",
                recipient_user_id=self.admin.id,
            ).exists()
        )

    def test_lifecycle_started_only_when_assignee_acts(self):
        started = Ukol.objects.get(pk=self.task.id)
        started.stav = "v_procesu"

        with patch("tasks.slack_notify.notify_task_event") as mock_notify:
            notify_task_lifecycle_change(
                started,
                old_stav="novy",
                actor_id=self.admin.id,
            )
            mock_notify.assert_not_called()

            notify_task_lifecycle_change(
                started,
                old_stav="novy",
                actor_id=self.prodejce.id,
            )
            mock_notify.assert_called_once_with(started, "started")

    def test_api_start_by_assignee_triggers_started_dm(self):
        with patch("tasks.slack_notify.notify_task_event") as mock_notify:
            self.client.force_authenticate(user=self.prodejce)
            res = self.client.put(
                f"/api/tasks/{self.task.id}/",
                {"stav": "v_procesu"},
                format="json",
            )
            self.assertEqual(res.status_code, 200, res.data)
            events = [c.args[1] for c in mock_notify.call_args_list]
            self.assertIn("started", events)
