"""Testy Objednávky: Slack O1, Symplio O2, SLA O3, redesign (prodejna/serviska/dodavatel)."""
from __future__ import annotations

from datetime import time, timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from orders.business_days import business_days_elapsed
from orders.models import Order, OrderStatusHistory
from orders.sla import orders_past_sla, run_orders_sla_reminders, sla_days_threshold
from orders.slack_recipients import SERVIS_GLOBUS_SLACK_ID
from orders.stale import orders_stale_candidates, run_orders_stale_reminders
from orders.status_config import MAIN_STATUS_KEYS
from shifts.models import Smena
from stores.models import Prodejna
from users.models import WebUser


def _make_user(pk, role="PRODEJCE", prodejna_id=None, email=None):
    return WebUser.objects.create(
        id=pk,
        uzivatelske_jmeno=f"orduser{pk}",
        jmeno=f"Jméno{pk}",
        prijmeni=f"Příjmení{pk}",
        heslo="x",
        role=role,
        aktivni=True,
        email=email or f"ord{pk}@example.com",
        prodejna_id=prodejna_id,
        moduly=[],
    )


def _order_payload(**overrides):
    data = {
        "jmeno_zakaznika": "Jan",
        "prijmeni_zakaznika": "Novák",
        "telefon_zakaznika": "+420777123456",
        "typ_telefonu": "iPhone 13",
        "dil": "baterie",
        "barva": "černá",
        "servisni_cislo": "952501099",
    }
    data.update(overrides)
    return data


@override_settings(SLACK_BOT_TOKEN="xoxb-test", MOBILMAJAK_APP_URL="https://mobilmajak.com")
class OrdersO2SymplioTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user(9301, "PRODEJCE", prodejna_id=201)
        self.client.force_authenticate(user=self.user)

    def test_create_and_read_symplio_objednavka_id(self):
        with patch("orders.serializers.notify_order_created", return_value=0):
            resp = self.client.post(
                "/api/orders/orders/",
                _order_payload(symplio_objednavka_id="98765"),
                format="json",
            )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data["symplio_objednavka_id"], "98765")
        self.assertEqual(
            resp.data["symplio_url"],
            "https://www.mobilmajak.cz/admin/objednavky/objednavka-98765",
        )

    def test_symplio_url_null_without_id(self):
        with patch("orders.serializers.notify_order_created", return_value=0):
            resp = self.client.post("/api/orders/orders/", _order_payload(), format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertIsNone(resp.data.get("symplio_url"))


@override_settings(
    SLACK_BOT_TOKEN="xoxb-test",
    MOBILMAJAK_APP_URL="https://mobilmajak.com",
    ORDERS_SLACK_TEST_MODE=False,
)
class OrdersO1SlackTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.creator = _make_user(9303, "PRODEJCE", prodejna_id=202, email="creator-ord@example.com")
        self.vychodil = WebUser.objects.create(
            id=9305,
            uzivatelske_jmeno="vychodil",
            jmeno="František",
            prijmeni="Vychodil",
            heslo="x",
            role="PRODEJCE",
            aktivni=True,
            email="vychodil@example.com",
            technik_id=121,
            prodejna_id=202,
            moduly=[],
        )
        self.store = Prodejna.objects.create(
            id=202,
            nazev="Senimo",
            nazev_kratkiy="Sen",
            aktivni=True,
        )
        self.client.force_authenticate(user=self.creator)

    @patch("orders.slack_notify.send_slack_dm", return_value=True)
    def test_create_notifies_servis_globus(self, mock_dm):
        resp = self.client.post("/api/orders/orders/", _order_payload(), format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        mock_dm.assert_called_once()
        self.assertEqual(mock_dm.call_args[0][0], SERVIS_GLOBUS_SLACK_ID)
        self.assertIn("Nová objednávka", mock_dm.call_args[0][1])

    @patch("orders.slack_notify.send_slack_dm", return_value=True)
    def test_create_skips_when_vychodil(self, mock_dm):
        self.client.force_authenticate(user=self.vychodil)
        resp = self.client.post("/api/orders/orders/", _order_payload(), format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        mock_dm.assert_not_called()

    @patch("orders.slack_notify.send_slack_dm", return_value=True)
    def test_status_dorazilo_ceka_does_not_notify(self, mock_dm):
        resp = self.client.post("/api/orders/orders/", _order_payload(), format="json")
        order_id = resp.data["id"]
        mock_dm.reset_mock()

        resp2 = self.client.patch(
            f"/api/orders/orders/{order_id}/update_status/",
            {"novy_status": "dorazilo_ceka"},
            format="json",
        )
        self.assertEqual(resp2.status_code, 200, resp2.content)
        mock_dm.assert_not_called()

    @patch("orders.slack_notify.send_slack_dm", return_value=False)
    def test_missing_slack_fail_soft(self, mock_dm):
        resp = self.client.post("/api/orders/orders/", _order_payload(), format="json")
        self.assertEqual(resp.status_code, 201)


@override_settings(ORDERS_SLA_DAYS=7, SLACK_BOT_TOKEN="xoxb-test")
class OrdersO3SlaTests(TestCase):
    def setUp(self):
        self.user = _make_user(9304, "PRODEJCE", prodejna_id=203)
        Prodejna.objects.create(
            id=203,
            nazev="SLA Store",
            nazev_kratkiy="SS",
            vedouci_user_id=self.user.id,
            aktivni=True,
        )

    def _make_order(self, status="objednano", days_ago=10, **kwargs):
        now = timezone.now()
        order = Order.objects.create(
            jmeno_zakaznika="A",
            prijmeni_zakaznika="B",
            telefon_zakaznika="777",
            typ_telefonu="iPhone",
            dil="LCD",
            servisni_cislo="111",
            status=status,
            zalozil=self.user,
            posledni_zmena_uzivatel=self.user,
            **kwargs,
        )
        Order.objects.filter(pk=order.pk).update(datum_vytvoreni=now - timedelta(days=days_ago + 1))
        hist = OrderStatusHistory.objects.create(
            objednavka=order,
            puvodni_status="nove",
            novy_status=status,
            uzivatel=self.user,
        )
        OrderStatusHistory.objects.filter(pk=hist.pk).update(
            datum_zmeny=now - timedelta(days=days_ago)
        )
        order.refresh_from_db()
        return order

    def test_sla_threshold_from_settings(self):
        self.assertEqual(sla_days_threshold(), 7)

    def test_overdue_orders_exclude_hotovo_storno(self):
        overdue = self._make_order(status="objednano", days_ago=10)
        self._make_order(status="hotovo", days_ago=10)
        self._make_order(status="storno", days_ago=10)
        fresh = self._make_order(status="nove", days_ago=2)
        candidates = {o.id for o in orders_past_sla()}
        self.assertIn(overdue.id, candidates)
        self.assertNotIn(fresh.id, candidates)
        self.assertEqual(len(candidates), 1)

    @patch("orders.sla.notify_order_sla", return_value=1)
    def test_sla_reminder_does_not_change_status(self, mock_notify):
        order = self._make_order(status="objednano", days_ago=10)
        status_before = order.status
        result = run_orders_sla_reminders(dry_run=False)
        order.refresh_from_db()
        self.assertEqual(order.status, status_before)
        self.assertIsNotNone(order.sla_reminder_sent_at)
        self.assertGreaterEqual(result["candidates"], 1)
        mock_notify.assert_called()

    def test_serializer_sla_overdue_flag(self):
        order = self._make_order(status="objednano", days_ago=10)
        from orders.serializers import OrderSerializer

        data = OrderSerializer(order).data
        self.assertTrue(data["sla_overdue"])
        self.assertGreaterEqual(data["dni_ve_stavu"], 7)

    def test_management_command_dry_run(self):
        from django.core.management import call_command
        from io import StringIO

        self._make_order(status="objednano", days_ago=10)
        out = StringIO()
        call_command("check_orders_sla_reminders", "--dry-run", stdout=out)
        self.assertIn("candidates=1", out.getvalue())
        order = Order.objects.get(status="objednano")
        self.assertIsNone(order.sla_reminder_sent_at)
        self.assertEqual(order.status, "objednano")


@override_settings(SLACK_BOT_TOKEN="xoxb-test", ORDERS_SLACK_TEST_MODE=False)
class OrdersStaleTests(TestCase):
    def setUp(self):
        self.user = _make_user(9306, "PRODEJCE", prodejna_id=204)
        self.store = Prodejna.objects.create(
            id=204,
            nazev="Globus",
            nazev_kratkiy="GL",
            aktivni=True,
        )

    def test_business_days_skip_weekend(self):
        from datetime import datetime

        # Pátek → pondělí = 1 pracovní den
        fri = timezone.make_aware(datetime(2026, 8, 14, 10, 0))
        mon = timezone.make_aware(datetime(2026, 8, 17, 10, 0))
        self.assertEqual(business_days_elapsed(fri, mon), 1)

        # Pátek → sobota = 0
        sat = timezone.make_aware(datetime(2026, 8, 15, 10, 0))
        self.assertEqual(business_days_elapsed(fri, sat), 0)

    def _make_order_at(self, status_since, **kwargs):
        order = Order.objects.create(
            jmeno_zakaznika="A",
            prijmeni_zakaznika="B",
            telefon_zakaznika="777",
            typ_telefonu="iPhone",
            dil="LCD",
            servisni_cislo="111",
            status="nove",
            zalozil=self.user,
            posledni_zmena_uzivatel=self.user,
            prodejna=self.store,
            **kwargs,
        )
        hist = OrderStatusHistory.objects.create(
            objednavka=order,
            puvodni_status="",
            novy_status="nove",
            uzivatel=self.user,
        )
        OrderStatusHistory.objects.filter(pk=hist.pk).update(datum_zmeny=status_since)
        order.refresh_from_db()
        return order

    def test_stale_candidate_after_one_business_day(self):
        from datetime import datetime

        now = timezone.make_aware(datetime(2026, 8, 17, 9, 0))  # Monday
        since = timezone.make_aware(datetime(2026, 8, 14, 15, 0))  # Friday
        order = self._make_order_at(since)
        candidates = orders_stale_candidates(now=now)
        self.assertIn(order, candidates)

    @patch("orders.stale.notify_order_stale", return_value=2)
    def test_stale_reminder_marks_sent_at(self, mock_notify):
        from datetime import datetime

        now = timezone.make_aware(datetime(2026, 8, 17, 9, 0))
        since = timezone.make_aware(datetime(2026, 8, 14, 15, 0))
        order = self._make_order_at(since)
        result = run_orders_stale_reminders(now=now, dry_run=False)
        order.refresh_from_db()
        self.assertIsNotNone(order.stale_reminder_sent_at)
        self.assertGreaterEqual(result["candidates"], 1)
        mock_notify.assert_called()

    @patch("orders.slack_notify.bulandra_slack_id", return_value="UBULANDRA")
    @patch("orders.slack_notify.send_slack_dm", return_value=True)
    def test_sla_escalation_messages(self, mock_dm, _bulandra):
        from orders.slack_notify import notify_order_sla

        order = Order.objects.create(
            jmeno_zakaznika="A",
            prijmeni_zakaznika="B",
            telefon_zakaznika="777",
            typ_telefonu="iPhone",
            dil="LCD",
            servisni_cislo="111",
            status="objednano",
            zalozil=self.user,
            posledni_zmena_uzivatel=self.user,
            prodejna=self.store,
        )
        sent = notify_order_sla(order, days_in_status=7)
        self.assertGreaterEqual(sent, 2)
        texts = [call.args[1] for call in mock_dm.call_args_list]
        self.assertTrue(any("Zaseknutá objednávka!" in t for t in texts))
        self.assertTrue(any("Zaseklá objednávka" in t for t in texts))


@override_settings(
    SLACK_BOT_TOKEN="xoxb-test",
    MOBILMAJAK_APP_URL="https://staging.mobilmajak.com",
    ORDERS_SLACK_TEST_MODE=True,
)
class OrdersSlackTestModeTests(TestCase):
    def setUp(self):
        self.user = _make_user(9311, "PRODEJCE", prodejna_id=205)
        self.store = Prodejna.objects.create(
            id=205,
            nazev="Senimo",
            nazev_kratkiy="Sen",
            aktivni=True,
        )

    @patch("orders.slack_notify.markovic_slack_id", return_value="UMARKOVIC")
    @patch("orders.slack_notify.send_slack_dm", return_value=True)
    def test_created_redirects_to_markovic_with_target(self, mock_dm, _markovic):
        from orders.slack_notify import notify_order_created

        order = Order.objects.create(
            jmeno_zakaznika="Jan",
            prijmeni_zakaznika="Novák",
            telefon_zakaznika="777123456",
            typ_telefonu="iPhone",
            dil="LCD",
            servisni_cislo="123",
            status="nove",
            zalozil=self.user,
            posledni_zmena_uzivatel=self.user,
            prodejna=self.store,
        )
        sent = notify_order_created(order)
        self.assertEqual(sent, 1)
        self.assertEqual(mock_dm.call_args[0][0], "UMARKOVIC")
        body = mock_dm.call_args[0][1]
        self.assertIn("[TEST objednávky", body)
        self.assertIn("Servis Globus", body)
        self.assertIn("Nová objednávka", body)


@override_settings(SLACK_BOT_TOKEN="xoxb-test", MOBILMAJAK_APP_URL="https://mobilmajak.com")
class OrdersRedesignTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.store = Prodejna.objects.create(
            id=210,
            nazev="Čepkov Test",
            nazev_kratkiy="Čepkov",
            aktivni=True,
        )
        self.shift_store = Prodejna.objects.create(
            id=211,
            nazev="Přerov Test",
            nazev_kratkiy="Přerov",
            aktivni=True,
        )
        self.user = _make_user(9310, "PRODEJCE", prodejna_id=self.store.id)
        self.client.force_authenticate(user=self.user)

    def test_create_requires_servisni_cislo_and_autofills(self):
        with patch("orders.serializers.notify_order_created", return_value=0):
            missing_both = self.client.post(
                "/api/orders/orders/",
                _order_payload(
                    servisni_cislo="",
                    jmeno_zakaznika="",
                    prijmeni_zakaznika="",
                    telefon_zakaznika="",
                ),
                format="json",
            )
        self.assertEqual(missing_both.status_code, 400)

        with patch("orders.serializers.notify_order_created", return_value=0):
            by_serviska = self.client.post(
                "/api/orders/orders/",
                _order_payload(
                    jmeno_zakaznika="",
                    prijmeni_zakaznika="",
                    telefon_zakaznika="",
                ),
                format="json",
            )
        self.assertEqual(by_serviska.status_code, 201, by_serviska.content)
        self.assertEqual(by_serviska.data["servisni_cislo"], "952501099")

        with patch("orders.serializers.notify_order_created", return_value=0):
            resp = self.client.post("/api/orders/orders/", _order_payload(), format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data["zalozil"]["id"], self.user.id)
        self.assertEqual(resp.data["status"], "nove")
        self.assertEqual(resp.data["servisni_cislo"], "952501099")
        self.assertEqual(resp.data["barva"], "černá")
        self.assertIsNotNone(resp.data["datum_vytvoreni"])
        # fallback na domovskou prodejnu bez směny
        self.assertEqual(resp.data["prodejna"]["id"], self.store.id)
        self.assertEqual(resp.data["status_display"], "Nové")

    def test_create_by_customer_without_serviska(self):
        with patch("orders.serializers.notify_order_created", return_value=0):
            resp = self.client.post(
                "/api/orders/orders/",
                _order_payload(servisni_cislo=""),
                format="json",
            )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data["jmeno_zakaznika"], "Jan")
        self.assertEqual(resp.data["servisni_cislo"], "")

    def test_create_requires_barva(self):
        with patch("orders.serializers.notify_order_created", return_value=0):
            resp = self.client.post(
                "/api/orders/orders/",
                _order_payload(barva=""),
                format="json",
            )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("barva", resp.data)

    def test_create_prodejna_from_today_shift(self):
        today = timezone.localdate()
        Smena.objects.create(
            user=self.user,
            prodejna=self.shift_store,
            datum=today,
            cas_od=time(8, 0),
            cas_do=time(16, 0),
            typ_smeny="prace",
            aktivni=True,
        )
        with patch("orders.serializers.notify_order_created", return_value=0):
            resp = self.client.post("/api/orders/orders/", _order_payload(), format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data["prodejna"]["id"], self.shift_store.id)

    def test_default_prodejna_endpoint(self):
        today = timezone.localdate()
        Smena.objects.create(
            user=self.user,
            prodejna=self.shift_store,
            datum=today,
            cas_od=time(8, 0),
            cas_do=time(16, 0),
            typ_smeny="prace",
            aktivni=True,
        )
        resp = self.client.get("/api/orders/orders/default-prodejna/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["prodejna"]["id"], self.shift_store.id)

    def test_create_accepts_explicit_prodejna(self):
        with patch("orders.serializers.notify_order_created", return_value=0):
            resp = self.client.post(
                "/api/orders/orders/",
                _order_payload(prodejna=self.shift_store.id),
                format="json",
            )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data["prodejna"]["id"], self.shift_store.id)

    def test_create_requires_typ_and_dil(self):
        with patch("orders.serializers.notify_order_created", return_value=0):
            resp = self.client.post(
                "/api/orders/orders/",
                _order_payload(typ_telefonu="", dil=""),
                format="json",
            )
        self.assertEqual(resp.status_code, 400)
        self.assertTrue("typ_telefonu" in resp.data or "dil" in resp.data)

    def test_dodavatel_required_for_v_kosiku_and_objednano(self):
        with patch("orders.serializers.notify_order_created", return_value=0):
            resp = self.client.post("/api/orders/orders/", _order_payload(), format="json")
        order_id = resp.data["id"]

        bad = self.client.patch(
            f"/api/orders/orders/{order_id}/update_status/",
            {"novy_status": "v_kosiku"},
            format="json",
        )
        self.assertEqual(bad.status_code, 400)
        self.assertIn("dodavatel", bad.data)

        ok = self.client.patch(
            f"/api/orders/orders/{order_id}/update_status/",
            {"novy_status": "v_kosiku", "dodavatel": "ASWO"},
            format="json",
        )
        self.assertEqual(ok.status_code, 200, ok.content)
        self.assertEqual(ok.data["status"], "v_kosiku")
        self.assertEqual(ok.data["dodavatel"], "ASWO")

        bad2 = self.client.patch(
            f"/api/orders/orders/{order_id}/update_status/",
            {"novy_status": "objednano", "dodavatel": ""},
            format="json",
        )
        # empty dodavatel in payload clears / fails — must reject
        self.assertEqual(bad2.status_code, 400)

        ok2 = self.client.patch(
            f"/api/orders/orders/{order_id}/update_status/",
            {"novy_status": "objednano"},
            format="json",
        )
        # already has ASWO on order → OK without re-sending
        self.assertEqual(ok2.status_code, 200, ok2.content)
        self.assertEqual(ok2.data["status"], "objednano")
        self.assertEqual(ok2.data["status_display"], "objednáno")

    def test_kanban_main_columns_and_labels(self):
        with patch("orders.serializers.notify_order_created", return_value=0):
            created = self.client.post("/api/orders/orders/", _order_payload(), format="json")
        order_id = created.data["id"]
        self.client.patch(
            f"/api/orders/orders/{order_id}/update_status/",
            {"novy_status": "hotovo"},
            format="json",
        )

        # legacy predobjednano folded into objednano column
        Order.objects.create(
            jmeno_zakaznika="X",
            prijmeni_zakaznika="Y",
            telefon_zakaznika="1",
            typ_telefonu="iP",
            dil="LCD",
            servisni_cislo="999",
            status="predobjednano",
            zalozil=self.user,
            posledni_zmena_uzivatel=self.user,
        )

        resp = self.client.get("/api/orders/orders/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["main_columns"], MAIN_STATUS_KEYS)
        kd = resp.data["kanban_data"]
        self.assertEqual(kd["nove"]["label"], "Nové")
        self.assertEqual(kd["v_kosiku"]["label"], "v košíku")
        self.assertEqual(kd["objednano"]["label"], "objednáno")
        self.assertEqual(kd["dorazilo_ceka"]["label"], "připraveno")
        self.assertEqual(kd["hotovo"]["label"], "vyřízeno")
        self.assertEqual(kd["hotovo"]["orders"], [])
        self.assertTrue(kd["hotovo"].get("lazy"))
        self.assertGreaterEqual(kd["hotovo"]["count"], 1)
        for col in kd.values():
            for order in col.get("orders") or []:
                self.assertNotIn("historie_stavu", order)

        searched = self.client.get("/api/orders/orders/", {"search": "Jan"})
        self.assertEqual(searched.status_code, 200)
        hotovo_orders = searched.data["kanban_data"]["hotovo"]["orders"]
        self.assertTrue(any(o["id"] == order_id for o in hotovo_orders))
        self.assertTrue(any(o["status"] == "predobjednano" for o in kd["objednano"]["orders"]))
        self.assertNotIn("storno", kd)
        self.assertNotIn("neni_skladem", kd)

    def test_telefon_validation(self):
        with patch("orders.serializers.notify_order_created", return_value=0):
            short = self.client.post(
                "/api/orders/orders/",
                _order_payload(telefon_zakaznika="12345678", servisni_cislo=""),
                format="json",
            )
        self.assertEqual(short.status_code, 400)
        self.assertIn("telefon_zakaznika", short.data)

        with patch("orders.serializers.notify_order_created", return_value=0):
            long = self.client.post(
                "/api/orders/orders/",
                _order_payload(telefon_zakaznika="+420 777 123 456 7890", servisni_cislo=""),
                format="json",
            )
        self.assertEqual(long.status_code, 400)
        self.assertIn("telefon_zakaznika", long.data)

        with patch("orders.serializers.notify_order_created", return_value=0):
            ok_local = self.client.post(
                "/api/orders/orders/",
                _order_payload(telefon_zakaznika="777 123 456", servisni_cislo=""),
                format="json",
            )
        self.assertEqual(ok_local.status_code, 201, ok_local.content)

        with patch("orders.serializers.notify_order_created", return_value=0):
            ok_intl = self.client.post(
                "/api/orders/orders/",
                _order_payload(telefon_zakaznika="+421912345678", servisni_cislo=""),
                format="json",
            )
        self.assertEqual(ok_intl.status_code, 201, ok_intl.content)

    def test_patch_updates_fields(self):
        with patch("orders.serializers.notify_order_created", return_value=0):
            created = self.client.post("/api/orders/orders/", _order_payload(), format="json")
        order_id = created.data["id"]

        resp = self.client.patch(
            f"/api/orders/orders/{order_id}/",
            {"telefon_zakaznika": "777 111 222", "barva": "černá"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["telefon_zakaznika"], "777 111 222")
        self.assertEqual(resp.data["barva"], "černá")
        self.assertEqual(resp.data["posledni_zmena_uzivatel"]["id"], self.user.id)

        blank = self.client.patch(
            f"/api/orders/orders/{order_id}/",
            {"barva": ""},
            format="json",
        )
        self.assertEqual(blank.status_code, 400)
        self.assertIn("barva", blank.data)

    def test_patch_updates_prodejna(self):
        with patch("orders.serializers.notify_order_created", return_value=0):
            created = self.client.post("/api/orders/orders/", _order_payload(), format="json")
        order_id = created.data["id"]
        self.assertEqual(created.data["prodejna"]["id"], self.store.id)

        resp = self.client.patch(
            f"/api/orders/orders/{order_id}/",
            {"prodejna": self.shift_store.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["prodejna"]["id"], self.shift_store.id)
        order = Order.objects.get(pk=order_id)
        self.assertEqual(order.prodejna_id, self.shift_store.id)

    def test_prodejce_can_delete_order(self):
        with patch("orders.serializers.notify_order_created", return_value=0):
            created = self.client.post("/api/orders/orders/", _order_payload(), format="json")
        order_id = created.data["id"]
        self.assertEqual(self.user.role, "PRODEJCE")
        resp = self.client.delete(f"/api/orders/orders/{order_id}/")
        self.assertIn(resp.status_code, (200, 204), resp.content)
        self.assertFalse(Order.objects.filter(pk=order_id).exists())
