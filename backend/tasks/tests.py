from datetime import date, time

from django.test import TestCase
from django.utils import timezone
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


class TasksApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = _make_user(9001, "ADMIN")
        self.vedouci_a = _make_user(9002, "VEDOUCI")
        self.vedouci_b = _make_user(9003, "VEDOUCI")
        self.prodejce = _make_user(9004, "PRODEJCE", prodejna_id=101)
        self.brigadnik = _make_user(9005, "BRIGADNIK", prodejna_id=None)

        self.store_a = Prodejna.objects.create(
            id=101,
            nazev="Prodejna A",
            nazev_kratkiy="A",
            vedouci_user_id=self.vedouci_a.id,
            aktivni=True,
        )
        self.store_b = Prodejna.objects.create(
            id=102,
            nazev="Prodejna B",
            nazev_kratkiy="B",
            vedouci_user_id=self.vedouci_b.id,
            aktivni=True,
        )

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def test_vedouci_sees_only_own_store_tasks(self):
        Ukol.objects.create(
            ukol="Úkol A",
            priorita="stredni",
            typ="prirazeny",
            id_prodejce_ukol=self.prodejce.id,
            id_prodejce_zadal=self.vedouci_a.id,
            id_prodejny=self.store_a.id,
        )
        Ukol.objects.create(
            ukol="Úkol B",
            priorita="stredni",
            typ="prirazeny",
            id_prodejce_ukol=self.prodejce.id,
            id_prodejce_zadal=self.vedouci_b.id,
            id_prodejny=self.store_b.id,
        )

        self._auth(self.vedouci_a)
        res = self.client.get("/api/tasks/")
        self.assertEqual(res.status_code, 200)
        ids = {t["id"] for t in res.data}
        self.assertEqual(len(ids), 1)

        self._auth(self.admin)
        res_admin = self.client.get("/api/tasks/")
        self.assertEqual(len(res_admin.data), 2)

    def test_prodejce_as_store_vedouci_can_manage_tasks(self):
        """Vedoucí přiřazený u prodejny (i s rolí PRODEJCE) vidí úkoly pobočky."""
        prodejce_vedouci = _make_user(9011, "PRODEJCE", prodejna_id=101)
        Prodejna.objects.filter(pk=self.store_a.id).update(vedouci_user_id=prodejce_vedouci.id)
        Ukol.objects.create(
            ukol="Úkol na A",
            priorita="stredni",
            typ="prirazeny",
            id_prodejce_ukol=self.prodejce.id,
            id_prodejce_zadal=self.admin.id,
            id_prodejny=self.store_a.id,
        )
        self._auth(prodejce_vedouci)
        res = self.client.get("/api/tasks/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)

    def test_prirazeny_requires_id_prodejny(self):
        self._auth(self.vedouci_a)
        res = self.client.post(
            "/api/tasks/",
            {
                "ukol": "Bez pobočky",
                "priorita": "stredni",
                "typ": "prirazeny",
                "id_prodejce_ukol": self.prodejce.id,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 400)

        res_ok = self.client.post(
            "/api/tasks/",
            {
                "ukol": "S pobočkou",
                "priorita": "stredni",
                "typ": "prirazeny",
                "id_prodejce_ukol": self.prodejce.id,
                "id_prodejny": self.store_a.id,
            },
            format="json",
        )
        self.assertEqual(res_ok.status_code, 201)
        self.assertEqual(res_ok.data["id_prodejny"], self.store_a.id)

    def test_scope_mine_for_employee(self):
        Ukol.objects.create(
            ukol="Cizí",
            priorita="stredni",
            typ="prirazeny",
            id_prodejce_ukol=self.brigadnik.id,
            id_prodejce_zadal=self.vedouci_a.id,
            id_prodejny=self.store_a.id,
        )
        Ukol.objects.create(
            ukol="Můj",
            priorita="stredni",
            typ="prirazeny",
            id_prodejce_ukol=self.prodejce.id,
            id_prodejce_zadal=self.vedouci_a.id,
            id_prodejny=self.store_a.id,
        )

        self._auth(self.prodejce)
        res = self.client.get("/api/tasks/", {"scope": "mine"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["ukol"], "Můj")

    def test_notifications_unread_only_prirazeny(self):
        Ukol.objects.create(
            ukol="Od vedoucího",
            priorita="stredni",
            typ="prirazeny",
            id_prodejce_ukol=self.prodejce.id,
            id_prodejce_zadal=self.vedouci_a.id,
            id_prodejny=self.store_a.id,
        )
        Ukol.objects.create(
            ukol="Osobní",
            priorita="stredni",
            typ="osobni",
            stav="novy",
            id_prodejce_ukol=self.prodejce.id,
            id_prodejce_zadal=self.prodejce.id,
        )

        self._auth(self.prodejce)
        res = self.client.get("/api/tasks/notifications-summary/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["tasks_unread"], 1)

    def test_shifts_calendar_scope_mine_for_admin(self):
        from shifts.models import Smena

        other = _make_user(9010, "PRODEJCE", prodejna_id=101)
        Smena.objects.create(
            user=self.admin,
            prodejna=self.store_a,
            datum=date.today(),
            cas_od=time(8, 0),
            cas_do=time(16, 0),
            typ_smeny="prace",
            aktivni=True,
        )
        Smena.objects.create(
            user=other,
            prodejna=self.store_a,
            datum=date.today(),
            cas_od=time(9, 0),
            cas_do=time(17, 0),
            typ_smeny="prace",
            aktivni=True,
        )

        mesic = date.today().strftime("%Y-%m")
        self._auth(self.admin)
        res_all = self.client.get(f"/api/shifts/calendar/?mesic={mesic}&prodejna=vse")
        count_all = sum(len(v) for v in res_all.data.get("kalendar_data", {}).values())

        res_mine = self.client.get(f"/api/shifts/calendar/?mesic={mesic}&scope=mine")
        count_mine = sum(len(v) for v in res_mine.data.get("kalendar_data", {}).values())

        self.assertGreaterEqual(count_all, 2)
        self.assertEqual(count_mine, 1)

    def test_assignees_lists_home_brigadnik_then_others(self):
        prodejce_b = _make_user(9012, "PRODEJCE", prodejna_id=102)
        self._auth(self.vedouci_a)
        res = self.client.get("/api/tasks/assignees/", {"prodejna_id": self.store_a.id})
        self.assertEqual(res.status_code, 200)
        assignees = res.data["assignees"]
        ids = [a["id"] for a in assignees]
        skupiny = [a.get("skupina") for a in assignees]
        self.assertIn(self.prodejce.id, ids)
        self.assertIn(self.brigadnik.id, ids)
        self.assertIn(prodejce_b.id, ids)
        self.assertEqual(skupiny[ids.index(self.prodejce.id)], "domaci")
        self.assertEqual(skupiny[ids.index(self.brigadnik.id)], "brigadnik")
        self.assertEqual(skupiny[ids.index(prodejce_b.id)], "ostatni")
        self.assertLess(ids.index(self.prodejce.id), ids.index(prodejce_b.id))
        self.assertLess(ids.index(self.brigadnik.id), ids.index(prodejce_b.id))

    def test_assignee_from_other_store_can_receive_task(self):
        prodejce_b = _make_user(9013, "PRODEJCE", prodejna_id=102)
        self._auth(self.vedouci_a)
        res = self.client.post(
            "/api/tasks/",
            {
                "ukol": "Výpomoc na A",
                "priorita": "stredni",
                "typ": "prirazeny",
                "id_prodejce_ukol": prodejce_b.id,
                "id_prodejny": self.store_a.id,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["id_prodejce_ukol"], prodejce_b.id)

    def test_admin_can_assign_task_to_other_admin(self):
        admin_b = _make_user(9014, "ADMIN", jmeno="Admin", prijmeni="Dva")
        self._auth(self.admin)
        res_list = self.client.get("/api/tasks/assignees/", {"prodejna_id": self.store_a.id})
        self.assertEqual(res_list.status_code, 200)
        ids = [a["id"] for a in res_list.data["assignees"]]
        self.assertIn(admin_b.id, ids)
        self.assertEqual(
            res_list.data["assignees"][ids.index(admin_b.id)]["skupina"],
            "admini",
        )

        res = self.client.post(
            "/api/tasks/",
            {
                "ukol": "Úkol pro admina",
                "priorita": "stredni",
                "typ": "prirazeny",
                "id_prodejce_ukol": admin_b.id,
                "id_prodejny": self.store_a.id,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["id_prodejce_ukol"], admin_b.id)

    def test_vedouci_assignees_exclude_admins(self):
        _make_user(9015, "ADMIN", jmeno="Admin", prijmeni="Skryty")
        self._auth(self.vedouci_a)
        res = self.client.get("/api/tasks/assignees/", {"prodejna_id": self.store_a.id})
        self.assertEqual(res.status_code, 200)
        roles_present = {a["id"] for a in res.data["assignees"]}
        self.assertNotIn(9015, roles_present)

    def test_dokonceno_v_set_on_hotovo(self):
        task = Ukol.objects.create(
            ukol="Dokončit",
            priorita="stredni",
            typ="osobni",
            stav="novy",
            id_prodejce_ukol=self.prodejce.id,
            id_prodejce_zadal=self.prodejce.id,
        )
        self.assertIsNone(task.dokonceno_v)
        self._auth(self.prodejce)
        res = self.client.patch(
            f"/api/tasks/{task.id}/",
            {"stav": "hotovo"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        task.refresh_from_db()
        self.assertIsNotNone(task.dokonceno_v)
        self.assertLessEqual(task.dokonceno_v, timezone.now())
