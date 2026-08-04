from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from stores.models import Prodejna
from tasks.models import Ukol
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


class TaskStartWithoutPrvniKrokTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = _make_user(9201, "ADMIN")
        self.prodejce = _make_user(9202, "PRODEJCE", prodejna_id=301)
        self.store = Prodejna.objects.create(
            id=301,
            nazev="Prodejna Start",
            nazev_kratkiy="ST",
            vedouci_user_id=self.admin.id,
            aktivni=True,
        )
        self.task = Ukol.objects.create(
            ukol="Start bez kroku",
            vysledek="Start bez kroku",
            dod_polozky=[{"text": "Hotovo", "splneno": False}],
            priorita="stredni",
            typ="prirazeny",
            stav="novy",
            deadline=date.today(),
            id_prodejce_ukol=self.prodejce.id,
            id_prodejce_zadal=self.admin.id,
            id_prodejny=self.store.id,
        )

    def test_assignee_can_start_without_prvni_krok(self):
        self.client.force_authenticate(user=self.prodejce)
        res = self.client.put(
            f"/api/tasks/{self.task.id}/",
            {"stav": "v_procesu"},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.task.refresh_from_db()
        self.assertEqual(self.task.stav, "v_procesu")
        self.assertIsNotNone(self.task.start_potvrzeno_v)
