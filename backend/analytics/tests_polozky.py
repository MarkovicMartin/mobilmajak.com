"""Testy rozšířeného API Položky."""
from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from analytics.models import WebProdejeAll
from analytics.polozky_aggregate import (
    aggregate_polozky_by_salesperson,
    parse_polozky_params,
)
from analytics.receipt_metrics import qualifying_polozka_q
from analytics.viceprace_config import polozky_nad_100_q
from shifts.models import Smena
from stores.models import Prodejna
from tasks.models import Ukol
from users.models import WebUser


def _sale(day, prodejce_id, prodejna_id, kod='P100', cena=150, kusy=1):
    return WebProdejeAll.objects.create(
        typ=day,
        doklad=f'D{prodejce_id}-{day}-{kod}',
        kod=kod,
        nazev='Test',
        pocet_kusu=kusy,
        cena_ks_vcl_dph=Decimal(str(cena)),
        id_prodejce=prodejce_id,
        id_prodejny=prodejna_id,
        stredisko='Test',
    )


class PolozkyAggregateTests(TestCase):
    def setUp(self):
        self.store_home = Prodejna.objects.create(id=201, nazev='Domácí', nazev_kratkiy='D', aktivni=True)
        self.store_host = Prodejna.objects.create(id=202, nazev='Host', nazev_kratkiy='H', aktivni=True)
        self.domaci = WebUser.objects.create(
            id=8101,
            uzivatelske_jmeno='domaci',
            jmeno='Dom',
            prijmeni='Ací',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            moduly=[],
            prodejna_id=self.store_home.id,
        )
        self.brigadnik = WebUser.objects.create(
            id=8102,
            uzivatelske_jmeno='brig',
            jmeno='Brig',
            prijmeni='Adník',
            heslo='x',
            role='BRIGADNIK',
            aktivni=True,
            moduly=[],
            prodejna_id=None,
        )
        self.day = '2026-05-10'
        _sale(self.day, self.domaci.id, self.store_home.id)
        _sale(self.day, self.domaci.id, self.store_host.id, kod='P200')
        _sale(self.day, self.brigadnik.id, self.store_host.id, kod='P300')

    def test_segment_host_excludes_home_store_sales(self):
        params = parse_polozky_params({
            'start_date': self.day,
            'end_date': self.day,
            'segment': 'host',
        })
        rows = aggregate_polozky_by_salesperson(params, limit=50)
        ids = {r['id_prodejce'] for r in rows}
        self.assertIn(self.domaci.id, ids)
        dom_row = next(r for r in rows if r['id_prodejce'] == self.domaci.id)
        self.assertEqual(dom_row['polozky_nad_100'], 1)

    def test_segment_brigadnik(self):
        params = parse_polozky_params({
            'start_date': self.day,
            'end_date': self.day,
            'segment': 'brigadnik',
        })
        rows = aggregate_polozky_by_salesperson(params, limit=50)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['id_prodejce'], self.brigadnik.id)

    def test_segment_docasni_host_and_brigadnik(self):
        params = parse_polozky_params({
            'start_date': self.day,
            'end_date': self.day,
            'segment': 'docasni',
        })
        rows = aggregate_polozky_by_salesperson(params, limit=50)
        ids = {r['id_prodejce'] for r in rows}
        self.assertIn(self.domaci.id, ids)
        self.assertIn(self.brigadnik.id, ids)
        dom_row = next(r for r in rows if r['id_prodejce'] == self.domaci.id)
        self.assertEqual(dom_row['polozky_nad_100'], 1)

    def test_include_hours_empty_shifts(self):
        params = parse_polozky_params({
            'start_date': self.day,
            'end_date': self.day,
            'include_hours': '1',
        })
        rows = aggregate_polozky_by_salesperson(params, limit=50)
        row = next(r for r in rows if r['id_prodejce'] == self.domaci.id)
        self.assertIsNone(row.get('odpracovane_hodiny'))
        self.assertIsNone(row.get('polozky_nad_100_za_hodinu'))

    def test_include_hours_with_shift(self):
        Smena.objects.create(
            user=self.domaci,
            prodejna=self.store_home,
            datum=date(2026, 5, 10),
            cas_od='09:00',
            cas_do='17:00',
            typ_smeny='prace',
            aktivni=True,
        )
        params = parse_polozky_params({
            'start_date': self.day,
            'end_date': self.day,
            'include_hours': '1',
        })
        rows = aggregate_polozky_by_salesperson(params, limit=50)
        row = next(r for r in rows if r['id_prodejce'] == self.domaci.id)
        self.assertEqual(row['odpracovane_hodiny'], 8.0)
        self.assertAlmostEqual(row['polozky_nad_100_za_hodinu'], 0.25, places=2)


class PolozkyApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = WebUser.objects.create(
            id=8200,
            uzivatelske_jmeno='api',
            jmeno='Api',
            prijmeni='Test',
            heslo='x',
            role='ADMIN',
            aktivni=True,
            moduly=[],
        )
        self.client.force_authenticate(user=self.user)
        self.store = Prodejna.objects.create(id=301, nazev='API', nazev_kratkiy='A', aktivni=True)
        self.day = '2026-06-01'
        _sale(self.day, 8201, self.store.id)
        WebUser.objects.create(
            id=8201,
            uzivatelske_jmeno='p1',
            jmeno='P',
            prijmeni='One',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            moduly=[],
            prodejna_id=self.store.id,
        )

    def test_polozky_endpoint_backward_compatible(self):
        res = self.client.get(
            '/api/analytics/web-prodeje/polozky/',
            {'start_date': self.day, 'end_date': self.day},
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data['success'])
        self.assertIsInstance(res.data['data'], list)
        if res.data['data']:
            row = res.data['data'][0]
            self.assertIn('polozky_nad_100', row)
            self.assertIn('sluzby_celkem', row)

    def test_timeline_endpoint(self):
        res = self.client.get(
            '/api/analytics/web-prodeje/polozky/timeline/',
            {'user_id': 8201, 'metric': 'polozky_nad_100', 'rok': 2026},
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data['success'])
        self.assertTrue(len(res.data['points']) >= 1)

    def test_timeline_compare_period(self):
        res = self.client.get(
            '/api/analytics/web-prodeje/polozky/timeline/',
            {
                'user_id': 8201,
                'metric': 'polozky_nad_100',
                'period': 'custom',
                'start_date': '2026-01-01',
                'end_date': '2026-03-31',
                'compare_period': 'prev_year',
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data['success'])
        self.assertEqual(res.data['compare_period'], 'prev_year')
        if res.data['points']:
            pt = res.data['points'][0]
            self.assertIn('compare_value', pt)
            self.assertIn('compare_month', pt)
            self.assertEqual(pt['compare_month'], '2025-01')
