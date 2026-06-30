"""Testy zabezpečení analytics API."""
import os
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

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

    def test_celkova_cisla_requires_login(self):
        res = self.client.get('/api/analytics/celkova-cisla/', {'period': 'monthly'})
        self.assertEqual(res.status_code, 401)

    def test_celkova_cisla_ok_when_authenticated(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get('/api/analytics/celkova-cisla/', {'period': 'monthly'})
        self.assertEqual(res.status_code, 200)

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
        self.assertIn(res.status_code, (200, 404))
