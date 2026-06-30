"""Testy zabezpečení analytics API."""
import os
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from analytics.models import WebProdejeAll
from stores.models import Prodejna
from users.models import WebUser


class AnalyticsAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = WebUser.objects.create(
            id=9001,
            uzivatelske_jmeno='secadmin',
            jmeno='Sec',
            prijmeni='Admin',
            heslo='x',
            role='ADMIN',
            aktivni=True,
            moduly=[],
        )
        self.store = Prodejna.objects.create(id=901, nazev='Sec', nazev_kratkiy='S', aktivni=True)
        WebProdejeAll.objects.create(
            typ='2026-06-01',
            doklad='SEC-1',
            kod='P1',
            nazev='Test',
            pocet_kusu=1,
            cena_ks_vcl_dph=100,
            zisk=10,
            id_prodejce=9002,
            id_prodejny=self.store.id,
            stredisko='Sec',
        )
        WebUser.objects.create(
            id=9002,
            uzivatelske_jmeno='seller',
            jmeno='S',
            prijmeni='Eller',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            moduly=[],
            prodejna_id=self.store.id,
        )

    def test_polozky_requires_login(self):
        res = self.client.get(
            '/api/analytics/web-prodeje/polozky/',
            {'start_date': '2026-06-01', 'end_date': '2026-06-01'},
        )
        self.assertIn(res.status_code, (401, 403))

    def test_polozky_ok_when_authenticated(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(
            '/api/analytics/web-prodeje/polozky/',
            {'start_date': '2026-06-01', 'end_date': '2026-06-01'},
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data['success'])

    def test_zasilkovna_konverze_requires_login(self):
        res = self.client.get('/api/analytics/zasilkovna-konverze/')
        self.assertEqual(res.status_code, 401)

    @patch.dict(os.environ, {'WEBHOOK_MONTHLY_STATS_TOKEN': ''}, clear=False)
    def test_webhook_monthly_stats_denied_without_token_config(self):
        res = self.client.get('/api/analytics/webhook/monthly-stats/')
        self.assertEqual(res.status_code, 403)

    @patch.dict(os.environ, {'WEBHOOK_MONTHLY_STATS_TOKEN': 'test-secret-token'}, clear=False)
    def test_webhook_monthly_stats_denied_without_header(self):
        res = self.client.get('/api/analytics/webhook/monthly-stats/')
        self.assertEqual(res.status_code, 403)

    @patch.dict(os.environ, {'WEBHOOK_MONTHLY_STATS_TOKEN': 'test-secret-token'}, clear=False)
    def test_webhook_monthly_stats_ok_with_token(self):
        res = self.client.get(
            '/api/analytics/webhook/monthly-stats/',
            HTTP_X_WEBHOOK_TOKEN='test-secret-token',
        )
        self.assertNotEqual(res.status_code, 403)
