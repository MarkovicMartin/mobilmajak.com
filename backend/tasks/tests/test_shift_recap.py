"""Testy ranního Slack recapu úkolů ke směně."""
from datetime import date, datetime, time, timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from shifts.models import Smena
from stores.models import Prodejna
from tasks.models import Ukol, UkolShiftRecapNotifikace
from tasks.shift_recap import (
    build_shift_recap_message,
    send_shift_recap,
    shifts_due_for_recap,
)
from users.models import WebUser


def _make_user(uid, **kwargs):
    defaults = {
        "uzivatelske_jmeno": f"recap{uid}",
        "jmeno": "Recap",
        "prijmeni": str(uid),
        "heslo": "x",
        "role": "PRODEJCE",
        "aktivni": True,
        "email": f"recap{uid}@example.com",
    }
    defaults.update(kwargs)
    return WebUser.objects.create(id=uid, **defaults)


@override_settings(SLACK_BOT_TOKEN="xoxb-test")
class ShiftRecapTests(TestCase):
    def setUp(self):
        self.user = _make_user(9301, jmeno="Jan", email="jan@example.com")
        self.store = Prodejna.objects.create(
            id=9301,
            nazev="Recap Store",
            nazev_kratkiy="R",
            aktivni=True,
        )
        today = timezone.localdate()
        self.smena = Smena.objects.create(
            user=self.user,
            prodejna=self.store,
            datum=today,
            cas_od=time(8, 0),
            cas_do=time(16, 0),
            typ_smeny="prace",
        )

    def test_build_message_highlights_due_today(self):
        today = timezone.localdate()
        task = Ukol.objects.create(
            ukol="Dnes",
            vysledek="Dnes hotovo",
            dod_polozky=[{"text": "x", "splneno": False}],
            priorita="stredni",
            typ="prirazeny",
            stav="v_procesu",
            deadline=today,
            id_prodejce_ukol=self.user.id,
            id_prodejce_zadal=999,
            id_prodejny=self.store.id,
        )
        text = build_shift_recap_message(self.user, self.smena, [task])
        self.assertIn("Dnes musí být hotovo", text)
        self.assertIn("Dnes hotovo", text)

    def test_shifts_due_in_recap_window(self):
        tz = timezone.get_current_timezone()
        today = timezone.localdate()
        recap_moment = timezone.make_aware(
            datetime.combine(today, time(8, 10)),
            tz,
        )
        due = shifts_due_for_recap(recap_moment)
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0].id, self.smena.id)

    def test_shifts_not_due_before_window(self):
        tz = timezone.get_current_timezone()
        today = timezone.localdate()
        early = timezone.make_aware(
            datetime.combine(today, time(8, 5)),
            tz,
        )
        self.assertEqual(shifts_due_for_recap(early), [])

    @override_settings(SLACK_BOT_TOKEN="xoxb-test")
    def test_send_shift_recap_records_notification(self):
        from unittest.mock import patch

        tz = timezone.get_current_timezone()
        today = timezone.localdate()
        now = timezone.make_aware(datetime.combine(today, time(8, 11)), tz)

        def side_effect(method, payload):
            if method == "users.lookupByEmail":
                return {"ok": True, "user": {"id": "URECAP"}}
            if method == "chat.postMessage":
                return {"ok": True}
            return {"ok": False}

        with patch("tasks.slack_notify._slack_api", side_effect=side_effect):
            self.assertTrue(send_shift_recap(self.smena, now=now))
        self.assertTrue(UkolShiftRecapNotifikace.objects.filter(smena_id=self.smena.id).exists())

        with patch("tasks.slack_notify._slack_api", side_effect=side_effect):
            self.assertFalse(send_shift_recap(self.smena, now=now))
