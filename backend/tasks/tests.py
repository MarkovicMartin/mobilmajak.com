from datetime import date, time, timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from stores.models import Prodejna
from tasks.models import Ukol, UkolSlackNotifikace
from tasks.slack_notify import (
    _slack_user_cache,
    notify_task_event,
    slack_user_id_for_web_user,
    tasks_needing_slack_notify,
)
from tasks.urgency import is_at_risk
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


def _prirazeny_payload(**overrides):
    data = {
        "vysledek": "Připravit výlohu",
        "ukol": "Připravit výlohu",
        "dod_polozky": [{"text": "Výloha hotová", "splneno": False}],
        "priorita": "stredni",
        "typ": "prirazeny",
        "deadline": date.today().isoformat(),
    }
    data.update(overrides)
    return data


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

    def _create_prirazeny(self, **kwargs):
        defaults = {
            "ukol": "Připravit výlohu",
            "vysledek": "Připravit výlohu",
            "dod_polozky": [{"text": "Výloha hotová", "splneno": False}],
            "priorita": "stredni",
            "typ": "prirazeny",
            "deadline": date.today(),
            "id_prodejce_ukol": self.prodejce.id,
            "id_prodejce_zadal": self.vedouci_a.id,
            "id_prodejny": self.store_a.id,
        }
        defaults.update(kwargs)
        return Ukol.objects.create(**defaults)

    def test_vedouci_sees_only_own_store_tasks(self):
        self._create_prirazeny(ukol="Úkol A", vysledek="Úkol A")
        Ukol.objects.create(
            ukol="Úkol B",
            vysledek="Úkol B",
            dod_polozky=[{"text": "x", "splneno": False}],
            priorita="stredni",
            typ="prirazeny",
            deadline=date.today(),
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
        prodejce_vedouci = _make_user(9011, "PRODEJCE", prodejna_id=101)
        Prodejna.objects.filter(pk=self.store_a.id).update(vedouci_user_id=prodejce_vedouci.id)
        self._create_prirazeny(ukol="Úkol na A", vysledek="Úkol na A")
        self._auth(prodejce_vedouci)
        res = self.client.get("/api/tasks/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)

    def test_prirazeny_requires_sop_fields(self):
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

        res_no_dod = self.client.post(
            "/api/tasks/",
            {
                **_prirazeny_payload(),
                "id_prodejce_ukol": self.prodejce.id,
                "id_prodejny": self.store_a.id,
                "dod_polozky": [],
            },
            format="json",
        )
        self.assertEqual(res_no_dod.status_code, 400)

        res_ok = self.client.post(
            "/api/tasks/",
            {
                **_prirazeny_payload(),
                "id_prodejce_ukol": self.prodejce.id,
                "id_prodejny": self.store_a.id,
            },
            format="json",
        )
        self.assertEqual(res_ok.status_code, 201)
        self.assertEqual(res_ok.data["id_prodejny"], self.store_a.id)
        self.assertEqual(res_ok.data["vysledek"], "Připravit výlohu")

    def test_scope_mine_for_employee(self):
        self._create_prirazeny(ukol="Cizí", vysledek="Cizí", id_prodejce_ukol=self.brigadnik.id)
        self._create_prirazeny(ukol="Můj", vysledek="Můj")

        self._auth(self.prodejce)
        res = self.client.get("/api/tasks/", {"scope": "mine"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["ukol"], "Můj")

    def test_notifications_unread_only_prirazeny(self):
        self._create_prirazeny(ukol="Od vedoucího", vysledek="Od vedoucího")
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

    def test_manager_notifications_include_at_risk_and_approval(self):
        self._create_prirazeny(
            stav="ceka_schvaleni",
            vyzaduje_schvaleni=True,
            dod_polozky=[{"text": "Hotovo", "splneno": True}],
        )
        overdue = self._create_prirazeny(stav="v_procesu", prvni_krok="x", ukol="Po termínu", vysledek="Po termínu")
        overdue.deadline = date.today() - timedelta(days=1)
        overdue.save(update_fields=["deadline"])

        self._auth(self.vedouci_a)
        res = self.client.get("/api/tasks/notifications-summary/")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(res.data["cekajici_schvaleni_count"], 1)
        self.assertGreaterEqual(res.data["at_risk_count"], 1)

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
                **_prirazeny_payload(),
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
        assignees = res_list.data["assignees"]
        ids = [a["id"] for a in assignees]
        self.assertIn(admin_b.id, ids)
        self.assertEqual(assignees[ids.index(admin_b.id)]["skupina"], "admini")

        res = self.client.post(
            "/api/tasks/",
            {
                **_prirazeny_payload(vysledek="Úkol pro admina", ukol="Úkol pro admina"),
                "id_prodejce_ukol": admin_b.id,
                "id_prodejny": self.store_a.id,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["id_prodejce_ukol"], admin_b.id)

    def test_assignees_hide_system_and_named_accounts(self):
        system_admin = _make_user(9020, "ADMIN", jmeno="Administrátor", prijmeni="Systémový")
        _make_user(9021, "PRODEJCE", prodejna_id=101, jmeno="Prodejce", prijmeni="Prodejce")
        petr = _make_user(9022, "PRODEJCE", prodejna_id=101, jmeno="Petr", prijmeni="Valenta")
        self._auth(self.admin)
        res = self.client.get("/api/tasks/assignees/", {"prodejna_id": self.store_a.id})
        self.assertEqual(res.status_code, 200)
        ids = {a["id"] for a in res.data["assignees"]}
        self.assertNotIn(system_admin.id, ids)
        self.assertNotIn(9021, ids)
        self.assertNotIn(petr.id, ids)

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
        res = self.client.put(
            f"/api/tasks/{task.id}/",
            {"stav": "hotovo"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        task.refresh_from_db()
        self.assertIsNotNone(task.dokonceno_v)
        self.assertLessEqual(task.dokonceno_v, timezone.now())

    def test_prirazeny_requires_prvni_krok_to_start(self):
        task = self._create_prirazeny()
        self._auth(self.prodejce)
        res = self.client.put(
            f"/api/tasks/{task.id}/",
            {"stav": "v_procesu"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

        res_ok = self.client.put(
            f"/api/tasks/{task.id}/",
            {"stav": "v_procesu", "prvni_krok": "Zkontroluju sklad"},
            format="json",
        )
        self.assertEqual(res_ok.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.stav, "v_procesu")
        self.assertIsNotNone(task.start_potvrzeno_v)

    def test_assignee_can_toggle_dod_polozky(self):
        task = self._create_prirazeny(stav="v_procesu", prvni_krok="Start")
        self._auth(self.prodejce)
        res = self.client.put(
            f"/api/tasks/{task.id}/",
            {"dod_polozky": [{"text": "Výloha hotová", "splneno": True}]},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["dod_polozky"][0]["splneno"])
        task.refresh_from_db()
        self.assertTrue(task.dod_polozky[0]["splneno"])

    def test_assignee_cannot_edit_task_details(self):
        task = self._create_prirazeny()
        self._auth(self.prodejce)
        res = self.client.put(
            f"/api/tasks/{task.id}/",
            {"vysledek": "Změněný výsledek"},
            format="json",
        )
        self.assertEqual(res.status_code, 403)

    def test_hotovo_requires_complete_dod(self):
        task = self._create_prirazeny(stav="v_procesu", prvni_krok="Start")
        self._auth(self.prodejce)
        res = self.client.put(
            f"/api/tasks/{task.id}/",
            {"stav": "hotovo"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

        res_ok = self.client.put(
            f"/api/tasks/{task.id}/",
            {
                "stav": "hotovo",
                "dod_polozky": [{"text": "Výloha hotová", "splneno": True}],
            },
            format="json",
        )
        self.assertEqual(res_ok.status_code, 200)
        self.assertEqual(res_ok.data["stav"], "hotovo")

    def test_approval_flow_ceka_schvaleni(self):
        task = self._create_prirazeny(
            stav="v_procesu",
            prvni_krok="Start",
            vyzaduje_schvaleni=True,
        )
        self._auth(self.prodejce)
        res = self.client.put(
            f"/api/tasks/{task.id}/",
            {
                "stav": "hotovo",
                "dod_polozky": [{"text": "Výloha hotová", "splneno": True}],
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["stav"], "ceka_schvaleni")

        self._auth(self.vedouci_a)
        res_approve = self.client.put(
            f"/api/tasks/{task.id}/",
            {"stav": "hotovo"},
            format="json",
        )
        self.assertEqual(res_approve.status_code, 200)
        self.assertEqual(res_approve.data["stav"], "hotovo")
        self.assertIsNotNone(res_approve.data["schvaleno_v"])

    def test_wip_warning_on_create(self):
        for i in range(3):
            self._create_prirazeny(ukol=f"Úkol {i}", vysledek=f"Úkol {i}")
        self._auth(self.vedouci_a)
        res = self.client.post(
            "/api/tasks/",
            {
                **_prirazeny_payload(vysledek="Čtvrtý", ukol="Čtvrtý"),
                "id_prodejce_ukol": self.prodejce.id,
                "id_prodejny": self.store_a.id,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertIn("wip_warning", res.data)

    def test_at_risk_overdue(self):
        task = self._create_prirazeny(stav="v_procesu", prvni_krok="x")
        task.deadline = date.today() - timedelta(days=1)
        task.save(update_fields=["deadline"])
        self.assertTrue(is_at_risk(task))

    def test_filter_at_risk(self):
        task = self._create_prirazeny(stav="v_procesu", prvni_krok="x")
        task.deadline = date.today() - timedelta(days=1)
        task.save(update_fields=["deadline"])
        self._auth(self.vedouci_a)
        res = self.client.get("/api/tasks/", {"filter": "at_risk", "typ": "prirazeny"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertTrue(res.data[0]["at_risk"])

    def test_admin_can_create_storeless_prirazeny_task(self):
        backoffice = _make_user(9030, "VEDOUCI", prodejna_id=None, jmeno="Back", prijmeni="Office")
        self._auth(self.admin)
        res = self.client.post(
            "/api/tasks/",
            {
                **_prirazeny_payload(vysledek="Centrální úkol", ukol="Centrální úkol"),
                "id_prodejce_ukol": backoffice.id,
                "id_prodejny": None,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertIsNone(res.data["id_prodejny"])
        self.assertEqual(res.data["id_prodejce_ukol"], backoffice.id)

    def test_vedouci_cannot_create_storeless_prirazeny_task(self):
        admin_b = _make_user(9031, "ADMIN", jmeno="Admin", prijmeni="Dva")
        self._auth(self.vedouci_a)
        res = self.client.post(
            "/api/tasks/",
            {
                **_prirazeny_payload(),
                "id_prodejce_ukol": admin_b.id,
                "id_prodejny": None,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("administrátor", res.data["error"].lower())

    def test_storeless_assignee_sees_own_task(self):
        backoffice = _make_user(9032, "PRODEJCE", prodejna_id=None, jmeno="Centr", prijmeni="Staff")
        task = Ukol.objects.create(
            ukol="Bez pobočky",
            vysledek="Bez pobočky",
            dod_polozky=[{"text": "Hotovo", "splneno": False}],
            priorita="stredni",
            typ="prirazeny",
            deadline=date.today(),
            id_prodejce_ukol=backoffice.id,
            id_prodejce_zadal=self.admin.id,
            id_prodejny=None,
        )
        self._auth(backoffice)
        res = self.client.get("/api/tasks/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], task.id)

    def test_storeless_assignees_endpoint(self):
        backoffice = _make_user(9033, "PRODEJCE", prodejna_id=None, jmeno="Centr", prijmeni="Dva")
        self._auth(self.admin)
        res = self.client.get("/api/tasks/assignees/", {"storeless": "1"})
        self.assertEqual(res.status_code, 200)
        ids = {a["id"] for a in res.data["assignees"]}
        self.assertIn(self.admin.id, ids)
        self.assertIn(backoffice.id, ids)
        self.assertIn(self.prodejce.id, ids)

        admin_entry = next(a for a in res.data["assignees"] if a["id"] == self.admin.id)
        self.assertEqual(admin_entry["skupina"], "admini")
        backoffice_entry = next(a for a in res.data["assignees"] if a["id"] == backoffice.id)
        self.assertEqual(backoffice_entry["skupina"], "backoffice")
        prodejce_entry = next(a for a in res.data["assignees"] if a["id"] == self.prodejce.id)
        self.assertEqual(prodejce_entry["skupina"], "prodejna")
        self.assertEqual(prodejce_entry["prodejna_id"], self.store_a.id)

        assignees = res.data["assignees"]
        admin_idx = next(i for i, a in enumerate(assignees) if a["id"] == self.admin.id)
        prodejce_idx = next(i for i, a in enumerate(assignees) if a["id"] == self.prodejce.id)
        self.assertLess(admin_idx, prodejce_idx)

    def test_admin_can_create_storeless_task_for_store_employee(self):
        self._auth(self.admin)
        res = self.client.post(
            "/api/tasks/",
            {
                **_prirazeny_payload(vysledek="Úkol na prodejci", ukol="Úkol na prodejci"),
                "id_prodejce_ukol": self.prodejce.id,
                "id_prodejny": None,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertIsNone(res.data["id_prodejny"])
        self.assertEqual(res.data["id_prodejce_ukol"], self.prodejce.id)

    def test_admin_can_update_storeless_task(self):
        backoffice = _make_user(9034, "PRODEJCE", prodejna_id=None)
        task = Ukol.objects.create(
            ukol="Původní",
            vysledek="Původní",
            dod_polozky=[{"text": "Krok", "splneno": False}],
            priorita="stredni",
            typ="prirazeny",
            deadline=date.today(),
            id_prodejce_ukol=backoffice.id,
            id_prodejce_zadal=self.admin.id,
            id_prodejny=None,
        )
        self._auth(self.admin)
        res = self.client.put(
            f"/api/tasks/{task.id}/",
            {"vysledek": "Upravený výsledek", "deadline": date.today().isoformat()},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["vysledek"], "Upravený výsledek")

    def test_admin_can_toggle_dod_on_assigned_task(self):
        task = self._create_prirazeny()
        self._auth(self.admin)
        res = self.client.put(
            f"/api/tasks/{task.id}/",
            {"dod_polozky": [{"text": "Výloha hotová", "splneno": True}]},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["dod_polozky"][0]["splneno"])

    def test_vedouci_can_toggle_dod_on_store_task(self):
        task = self._create_prirazeny()
        self._auth(self.vedouci_a)
        res = self.client.put(
            f"/api/tasks/{task.id}/",
            {"dod_polozky": [{"text": "Výloha hotová", "splneno": True}]},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["dod_polozky"][0]["splneno"])

    def test_prodejce_cannot_toggle_dod_on_others_task(self):
        task = self._create_prirazeny()
        other = _make_user(9050, "PRODEJCE", prodejna_id=101)
        self._auth(other)
        res = self.client.put(
            f"/api/tasks/{task.id}/",
            {"dod_polozky": [{"text": "Výloha hotová", "splneno": True}]},
            format="json",
        )
        self.assertEqual(res.status_code, 403)


@override_settings(
    SLACK_BOT_TOKEN="xoxb-test",
    MOBILMAJAK_APP_URL="https://staging.mobilmajak.com",
)
class TasksSlackNotifyTests(TestCase):
    def setUp(self):
        _slack_user_cache.clear()
        self.client = APIClient()
        self.admin = _make_user(9101, "ADMIN", email="admin@example.com")
        self.vedouci = _make_user(9102, "VEDOUCI", email="vedouci@example.com")
        self.prodejce = _make_user(9103, "PRODEJCE", prodejna_id=201, email="prodejce@example.com")
        self.store = Prodejna.objects.create(
            id=201,
            nazev="Prodejna Slack",
            nazev_kratkiy="S",
            vedouci_user_id=self.vedouci.id,
            aktivni=True,
        )

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def _mock_slack_api(self, lookup_id="UASSIGNEE", post_ok=True):
        def side_effect(method, payload):
            if method == "users.lookupByEmail":
                return {"ok": True, "user": {"id": lookup_id}}
            if method == "chat.postMessage":
                return {"ok": post_ok}
            return {"ok": False, "error": "unknown_method"}

        return patch("tasks.slack_notify._slack_api", side_effect=side_effect)

    def test_slack_user_lookup_caches_by_web_user_id(self):
        with self._mock_slack_api(lookup_id="UCACHED"):
            first = slack_user_id_for_web_user(self.prodejce)
            second = slack_user_id_for_web_user(self.prodejce)
        self.assertEqual(first, "UCACHED")
        self.assertEqual(second, "UCACHED")

    def test_notify_assigned_sends_dm_to_assignee(self):
        task = Ukol.objects.create(
            ukol="Úkol",
            vysledek="Úkol",
            dod_polozky=[],
            priorita="stredni",
            typ="prirazeny",
            deadline=date.today(),
            id_prodejce_ukol=self.prodejce.id,
            id_prodejce_zadal=self.vedouci.id,
            id_prodejny=self.store.id,
        )
        with self._mock_slack_api(lookup_id="UASSIGNEE"):
            sent = notify_task_event(task, "assigned")
        self.assertEqual(sent, 1)
        self.assertTrue(
            UkolSlackNotifikace.objects.filter(
                ukol=task,
                typ="dm_assigned",
                recipient_user_id=self.prodejce.id,
            ).exists()
        )

    def test_notify_due_soon_dm_to_assignee_and_zadavatel(self):
        task = Ukol.objects.create(
            ukol="Termín",
            vysledek="Termín",
            dod_polozky=[],
            priorita="stredni",
            typ="prirazeny",
            stav="v_procesu",
            deadline=date.today(),
            id_prodejce_ukol=self.prodejce.id,
            id_prodejce_zadal=self.vedouci.id,
            id_prodejny=self.store.id,
        )
        with self._mock_slack_api(lookup_id="URECIPIENT"):
            sent = notify_task_event(task, "due_soon")
        self.assertEqual(sent, 2)
        self.assertEqual(
            UkolSlackNotifikace.objects.filter(ukol=task, typ="dm_due_soon").count(),
            2,
        )

    def test_notify_dedup_per_recipient(self):
        task = Ukol.objects.create(
            ukol="Dedup",
            vysledek="Dedup",
            dod_polozky=[],
            priorita="stredni",
            typ="prirazeny",
            deadline=date.today(),
            id_prodejce_ukol=self.prodejce.id,
            id_prodejce_zadal=self.vedouci.id,
            id_prodejny=self.store.id,
        )
        with self._mock_slack_api():
            self.assertEqual(notify_task_event(task, "assigned"), 1)
            self.assertEqual(notify_task_event(task, "assigned"), 0)

    def test_create_prirazeny_task_triggers_assigned_dm(self):
        with self._mock_slack_api(lookup_id="UASSIGNEE"):
            self._auth(self.vedouci)
            res = self.client.post(
                "/api/tasks/",
                {
                    **_prirazeny_payload(),
                    "id_prodejce_ukol": self.prodejce.id,
                    "id_prodejny": self.store.id,
                },
                format="json",
            )
        self.assertEqual(res.status_code, 201)
        task_id = res.data["id"]
        self.assertTrue(
            UkolSlackNotifikace.objects.filter(
                ukol_id=task_id,
                typ="dm_assigned",
                recipient_user_id=self.prodejce.id,
            ).exists()
        )

    def test_completed_state_triggers_dm_to_zadavatel(self):
        task = Ukol.objects.create(
            ukol="Hotovo",
            vysledek="Hotovo",
            dod_polozky=[{"text": "x", "splneno": True}],
            priorita="stredni",
            typ="prirazeny",
            stav="v_procesu",
            vyzaduje_schvaleni=True,
            deadline=date.today(),
            id_prodejce_ukol=self.prodejce.id,
            id_prodejce_zadal=self.vedouci.id,
            id_prodejny=self.store.id,
        )
        with self._mock_slack_api(lookup_id="UZADAVATEL"):
            self._auth(self.prodejce)
            res = self.client.put(
                f"/api/tasks/{task.id}/",
                {"stav": "ceka_schvaleni"},
                format="json",
            )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(
            UkolSlackNotifikace.objects.filter(
                ukol=task,
                typ="dm_awaiting_approval",
                recipient_user_id=self.vedouci.id,
            ).exists()
        )

        with self._mock_slack_api(lookup_id="UZADAVATEL"):
            self._auth(self.vedouci)
            res = self.client.put(
                f"/api/tasks/{task.id}/",
                {"stav": "hotovo"},
                format="json",
            )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(
            UkolSlackNotifikace.objects.filter(
                ukol=task,
                typ="dm_completed",
                recipient_user_id=self.vedouci.id,
            ).exists()
        )

    def test_awaiting_approval_dm_includes_store_vedouci(self):
        task = Ukol.objects.create(
            ukol="Schválení",
            vysledek="Schválení",
            dod_polozky=[],
            priorita="stredni",
            typ="prirazeny",
            stav="v_procesu",
            deadline=date.today(),
            id_prodejce_ukol=self.prodejce.id,
            id_prodejce_zadal=self.admin.id,
            id_prodejny=self.store.id,
        )
        with self._mock_slack_api(lookup_id="UVED"):
            sent = notify_task_event(task, "awaiting_approval")
        self.assertEqual(sent, 2)
        recipient_ids = set(
            UkolSlackNotifikace.objects.filter(
                ukol=task,
                typ="dm_awaiting_approval",
            ).values_list("recipient_user_id", flat=True)
        )
        self.assertEqual(recipient_ids, {self.admin.id, self.vedouci.id})

    def test_tasks_needing_slack_notify_per_recipient(self):
        task = Ukol.objects.create(
            ukol="Brzy",
            vysledek="Brzy",
            dod_polozky=[],
            priorita="stredni",
            typ="prirazeny",
            stav="novy",
            deadline=timezone.localdate(),
            id_prodejce_ukol=self.prodejce.id,
            id_prodejce_zadal=self.vedouci.id,
            id_prodejny=self.store.id,
        )
        pending = tasks_needing_slack_notify()
        pairs = {(t.id, rid) for t, _typ, rid in pending}
        self.assertIn((task.id, self.prodejce.id), pairs)
        self.assertIn((task.id, self.vedouci.id), pairs)

    def test_notify_task_deadlines_command_sends_dm(self):
        task = Ukol.objects.create(
            ukol="Cron",
            vysledek="Cron",
            dod_polozky=[],
            priorita="stredni",
            typ="prirazeny",
            stav="novy",
            deadline=timezone.localdate(),
            id_prodejce_ukol=self.prodejce.id,
            id_prodejce_zadal=self.vedouci.id,
            id_prodejny=self.store.id,
        )
        with self._mock_slack_api(lookup_id="UCRON"):
            out = StringIO()
            call_command("notify_task_deadlines", stdout=out)
        self.assertIn("Odesláno", out.getvalue())
        self.assertTrue(
            UkolSlackNotifikace.objects.filter(ukol=task, typ="dm_due_soon").exists()
        )

    @override_settings(SLACK_BOT_TOKEN="", SLACK_TASKS_WEBHOOK_URL="https://hooks.example.com")
    @patch("tasks.slack_notify.requests.post")
    def test_webhook_fallback_when_no_bot_token(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, raise_for_status=MagicMock())
        task = Ukol.objects.create(
            ukol="Webhook",
            vysledek="Webhook",
            dod_polozky=[],
            priorita="stredni",
            typ="prirazeny",
            stav="novy",
            deadline=timezone.localdate(),
            id_prodejce_ukol=self.prodejce.id,
            id_prodejce_zadal=self.vedouci.id,
            id_prodejny=self.store.id,
        )
        out = StringIO()
        call_command("notify_task_deadlines", stdout=out)
        mock_post.assert_called_once()
        self.assertTrue(
            UkolSlackNotifikace.objects.filter(ukol=task, typ="due_soon").exists()
        )
