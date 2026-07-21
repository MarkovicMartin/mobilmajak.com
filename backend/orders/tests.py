"""Testy Objednávky O1 (Slack), O2 (symplio_id), O3 (SLA bez auto statusu)."""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from orders.models import Order, OrderStatusHistory
from orders.sla import orders_past_sla, run_orders_sla_reminders, sla_days_threshold
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


@override_settings(SLACK_BOT_TOKEN="xoxb-test", MOBILMAJAK_APP_URL="https://mobilmajak.com")
class OrdersO1SlackTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.vedouci = _make_user(9302, "VEDOUCI", prodejna_id=202, email="vedouci-ord@example.com")
        self.creator = _make_user(9303, "PRODEJCE", prodejna_id=202, email="creator-ord@example.com")
        Prodejna.objects.create(
            id=202,
            nazev="Ord Store",
            nazev_kratkiy="OS",
            vedouci_user_id=self.vedouci.id,
            aktivni=True,
        )
        self.client.force_authenticate(user=self.creator)

    @patch("orders.slack_notify.send_slack_dm", return_value=True)
    @patch("orders.slack_notify.slack_user_id_for_web_user", side_effect=lambda u: f"U{u.id}" if u else None)
    def test_create_notifies_creator_and_vedouci(self, _lookup, mock_dm):
        resp = self.client.post("/api/orders/orders/", _order_payload(), format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(mock_dm.call_count, 2)
        texts = [c.args[1] for c in mock_dm.call_args_list]
        self.assertTrue(any("Nová objednávka" in t for t in texts))

    @patch("orders.slack_notify.send_slack_dm", return_value=True)
    @patch("orders.slack_notify.slack_user_id_for_web_user", side_effect=lambda u: f"U{u.id}" if u else None)
    def test_status_dorazilo_ceka_notifies(self, _lookup, mock_dm):
        with patch("orders.serializers.notify_order_created", return_value=0):
            resp = self.client.post("/api/orders/orders/", _order_payload(), format="json")
        order_id = resp.data["id"]
        mock_dm.reset_mock()

        resp2 = self.client.patch(
            f"/api/orders/orders/{order_id}/update_status/",
            {"novy_status": "dorazilo_ceka"},
            format="json",
        )
        self.assertEqual(resp2.status_code, 200, resp2.content)
        self.assertEqual(resp2.data["status"], "dorazilo_ceka")
        self.assertEqual(mock_dm.call_count, 2)
        texts = [c.args[1] for c in mock_dm.call_args_list]
        self.assertTrue(any("dorazila" in t.lower() or "Dorazila" in t or "dorazilo" in t.lower() for t in texts))

    @patch("orders.slack_notify.send_slack_dm", return_value=True)
    @patch("orders.slack_notify.slack_user_id_for_web_user", return_value=None)
    def test_missing_slack_id_fail_soft(self, _lookup, mock_dm):
        resp = self.client.post("/api/orders/orders/", _order_payload(), format="json")
        self.assertEqual(resp.status_code, 201)
        mock_dm.assert_not_called()


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
        self.assertEqual(order.status, "objednano")
        self.assertIsNotNone(order.sla_reminder_sent_at)
        self.assertGreaterEqual(result["candidates"], 1)
        mock_notify.assert_called()

    def test_serializer_sla_overdue_flag(self):
        client = APIClient()
        client.force_authenticate(user=self.user)
        order = self._make_order(status="objednano", days_ago=10)
        with patch("orders.serializers.notify_order_created", return_value=0):
            pass
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
