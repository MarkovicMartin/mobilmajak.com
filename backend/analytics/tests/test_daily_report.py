"""Testy denního Slack reportu."""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from analytics.daily_report import build_daily_report, format_daily_report_slack
from analytics.daily_report_recipients import daily_report_recipient_queryset
from analytics.models import WebProdejeAll
from analytics.slack_report import send_daily_report_dm
from stores.models import Prodejna
from users.models import WebUser


class DailyReportTests(TestCase):
    def setUp(self):
        self.day = date(2026, 6, 15)
        self.store = Prodejna.objects.create(id=501, nazev='Testovna', nazev_kratkiy='T', aktivni=True)
        WebUser.objects.create(
            id=9501,
            uzivatelske_jmeno='seller1',
            jmeno='Jan',
            prijmeni='Novák',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            moduly=[],
            prodejna_id=self.store.id,
        )
        WebProdejeAll.objects.create(
            typ='2026-06-15',
            doklad='R-1',
            kod='P100',
            nazev='Telefon',
            pocet_kusu=2,
            cena_ks_bez_dph=Decimal('1000'),
            cena_ks_vcl_dph=Decimal('1210'),
            zisk=Decimal('400'),
            id_prodejce=9501,
            id_prodejny=self.store.id,
            stredisko='Testovna',
        )

    def test_build_daily_report_totals(self):
        report = build_daily_report(self.day)
        self.assertEqual(report['day'], self.day)
        self.assertEqual(report['totals']['doklady'], 1)
        self.assertEqual(report['totals']['obrat_bez_dph'], 2000.0)

    def test_format_contains_key_lines(self):
        report = build_daily_report(self.day)
        text = format_daily_report_slack(report)
        self.assertIn('Denní report MOBILMAJAK', text)
        self.assertIn('Testovna', text)

    def test_recipients_respect_opt_in(self):
        WebUser.objects.create(
            id=9502,
            uzivatelske_jmeno='radek',
            jmeno='Radek',
            prijmeni='Bulandra',
            heslo='x',
            role='ADMIN',
            aktivni=True,
            moduly=[],
            slack_daily_report=True,
        )
        WebUser.objects.create(
            id=9503,
            uzivatelske_jmeno='petr',
            jmeno='Petr',
            prijmeni='Valenta',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            moduly=[],
            slack_daily_report=False,
        )
        ids = list(daily_report_recipient_queryset().values_list('id', flat=True))
        self.assertEqual(ids, [9502])

    @patch('analytics.slack_report.send_slack_dm', return_value=True)
    @patch('analytics.slack_report.slack_user_id_for_web_user', return_value='U123')
    def test_send_daily_report_dm(self, _lookup, _send):
        user = WebUser.objects.get(id=9501)
        self.assertTrue(send_daily_report_dm(user, 'ahoj'))
