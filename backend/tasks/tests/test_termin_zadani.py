from datetime import date, timedelta

from django.test import TestCase
from rest_framework.test import APIClient

from stores.models import Prodejna
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


class TerminZadaniApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = _make_user(9101, "ADMIN")
        self.prodejce = _make_user(9102, "PRODEJCE", prodejna_id=201)
        self.store = Prodejna.objects.create(
            id=201,
            nazev="Prodejna TZ",
            nazev_kratkiy="TZ",
            vedouci_user_id=self.admin.id,
            aktivni=True,
        )

    def test_create_and_update_termin_zadani(self):
        self.client.force_authenticate(user=self.admin)
        zadani = (date.today() - timedelta(days=2)).isoformat()
        res = self.client.post(
            "/api/tasks/",
            {
                "vysledek": "Úkol s termínem zadání",
                "ukol": "Úkol s termínem zadání",
                "dod_polozky": [{"text": "Hotovo", "splneno": False}],
                "priorita": "stredni",
                "typ": "prirazeny",
                "deadline": date.today().isoformat(),
                "termin_zadani": zadani,
                "id_prodejny": self.store.id,
                "id_prodejce_ukol": self.prodejce.id,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["termin_zadani"], zadani)
        task_id = res.data["id"]

        new_zadani = (date.today() - timedelta(days=1)).isoformat()
        res = self.client.put(
            f"/api/tasks/{task_id}/",
            {"termin_zadani": new_zadani},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["termin_zadani"], new_zadani)
