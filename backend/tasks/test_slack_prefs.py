"""Testy preferencí Slack notifikací k úkolům."""
from datetime import date

from django.test import TestCase, override_settings
from unittest.mock import patch

from tasks.models import Ukol, UkolKomentar
from tasks.slack_notify import (
    _recipient_user_ids,
    _recipient_user_ids_for_comment,
    notify_task_comment,
)
from tasks.slack_prefs import (
    PREF_COMMENT_ALL,
    PREF_CREATED_ALL,
    PREF_DUE_SOON_ALL,
    PREF_DUE_SOON_MINE,
    PREF_OVERDUE_MINE,
    get_slack_ukoly_prefs,
    invalidate_global_watcher_cache,
    normalize_slack_ukoly_prefs,
)
from users.models import WebUser


def _make_user(uid, role="PRODEJCE", **kwargs):
    defaults = {
        "uzivatelske_jmeno": f"user{uid}",
        "jmeno": "Test",
        "prijmeni": str(uid),
        "heslo": "x",
        "role": role,
        "aktivni": True,
        "email": f"user{uid}@example.com",
    }
    defaults.update(kwargs)
    return WebUser.objects.create(id=uid, **defaults)


@override_settings(SLACK_BOT_TOKEN="xoxb-test")
class SlackUkolyPrefsTests(TestCase):
    def setUp(self):
        invalidate_global_watcher_cache()
        self.supervisor = _make_user(
            9201,
            "ADMIN",
            jmeno="Radek",
            prijmeni="Supervisor",
            slack_ukoly_prefs={
                PREF_CREATED_ALL: True,
                PREF_DUE_SOON_ALL: True,
                PREF_DUE_SOON_MINE: False,
                PREF_OVERDUE_MINE: False,
                PREF_COMMENT_ALL: True,
            },
        )
        self.manager = _make_user(
            9202,
            "ADMIN",
            jmeno="Martin",
            prijmeni="Manager",
            slack_ukoly_prefs={PREF_DUE_SOON_MINE: False},
        )
        self.assignee = _make_user(9203, email="assignee@example.com")
        self.store = Prodejna.objects.create(
            id=9201,
            nazev="Prefs Store",
            nazev_kratkiy="P",
            vedouci_user_id=self.manager.id,
            aktivni=True,
        )
        invalidate_global_watcher_cache()

    def _task(self, **kwargs):
        defaults = {
            "ukol": "Úkol",
            "vysledek": "Úkol",
            "dod_polozky": [],
            "priorita": "stredni",
            "typ": "prirazeny",
            "deadline": date.today(),
            "id_prodejce_ukol": self.assignee.id,
            "id_prodejce_zadal": self.manager.id,
            "id_prodejny": self.store.id,
        }
        defaults.update(kwargs)
        return Ukol.objects.create(**defaults)

    def test_normalize_prefs_merges_defaults(self):
        prefs = normalize_slack_ukoly_prefs({PREF_CREATED_ALL: True})
        self.assertTrue(prefs[PREF_CREATED_ALL])
        self.assertTrue(prefs["assigned_mine"])

    def test_supervisor_gets_created_for_foreign_task(self):
        task = self._task()
        recipients = _recipient_user_ids(task, "created")
        self.assertIn(self.supervisor.id, recipients)
        self.assertIn(self.manager.id, recipients)

    def test_manager_skips_due_soon_for_own_task(self):
        task = self._task()
        recipients = _recipient_user_ids(task, "due_soon")
        self.assertIn(self.assignee.id, recipients)
        self.assertNotIn(self.manager.id, recipients)
        self.assertIn(self.supervisor.id, recipients)

    def test_manager_still_gets_overdue_for_own_task(self):
        task = self._task()
        recipients = _recipient_user_ids(task, "overdue")
        self.assertIn(self.manager.id, recipients)
        self.assertIn(self.assignee.id, recipients)

    def test_get_slack_ukoly_prefs_from_db(self):
        prefs = get_slack_ukoly_prefs(self.supervisor)
        self.assertTrue(prefs[PREF_CREATED_ALL])
        self.assertFalse(prefs[PREF_DUE_SOON_MINE])

    def test_assignee_always_gets_comment_from_admin(self):
        task = self._task()
        comment = UkolKomentar.objects.create(
            ukol=task,
            autor_id=self.manager.id,
            autor_jmeno="Martin Manager",
            text="Prosím doplňte foto.",
        )
        recipients = _recipient_user_ids_for_comment(task, comment)
        self.assertIn(self.assignee.id, recipients)
        self.assertNotIn(self.manager.id, recipients)

    def test_assignee_not_notified_for_own_comment(self):
        task = self._task()
        comment = UkolKomentar.objects.create(
            ukol=task,
            autor_id=self.assignee.id,
            autor_jmeno="Assignee",
            text="Moje odpověď",
        )
        recipients = _recipient_user_ids_for_comment(task, comment)
        self.assertNotIn(self.assignee.id, recipients)

    def test_supervisor_gets_all_comments(self):
        task = self._task()
        comment = UkolKomentar.objects.create(
            ukol=task,
            autor_id=self.assignee.id,
            autor_jmeno="Assignee",
            text="Hotovo",
        )
        recipients = _recipient_user_ids_for_comment(task, comment)
        self.assertIn(self.supervisor.id, recipients)

    @patch("tasks.slack_notify._slack_api")
    def test_notify_task_comment_sends_dm(self, mock_api):
        def side_effect(method, payload):
            if method == "users.lookupByEmail":
                return {"ok": True, "user": {"id": "UASSIGNEE"}}
            if method == "chat.postMessage":
                return {"ok": True}
            return {"ok": False}

        mock_api.side_effect = side_effect
        task = self._task()
        comment = UkolKomentar.objects.create(
            ukol=task,
            autor_id=self.manager.id,
            autor_jmeno="Martin Manager",
            text="Kontrola",
        )
        sent = notify_task_comment(task, comment)
        self.assertGreaterEqual(sent, 1)
