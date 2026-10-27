from datetime import date, time

from django.test import TestCase
from rest_framework.test import APIClient

from shifts.czech_holidays import get_ceske_svatky, get_nazev_svatku
from shifts.mall_closure import (
    closure_kind_for_date,
    easter_monday,
    is_retail_ban_day,
)
from shifts.models import Smena
from stores.models import Prodejna
from users.models import WebUser


class MallClosureTests(TestCase):
    def test_always_closed(self):
        self.assertEqual(closure_kind_for_date(date(2026, 1, 1)), 'always_closed')
        self.assertEqual(closure_kind_for_date(date(2026, 5, 8)), 'always_closed')
        self.assertEqual(closure_kind_for_date(date(2026, 9, 28)), 'always_closed')
        self.assertEqual(closure_kind_for_date(date(2026, 10, 28)), 'always_closed')
        self.assertEqual(closure_kind_for_date(date(2026, 12, 25)), 'always_closed')
        self.assertEqual(closure_kind_for_date(date(2026, 12, 26)), 'always_closed')
        self.assertEqual(easter_monday(2026), date(2026, 4, 6))
        self.assertTrue(is_retail_ban_day(date(2026, 4, 6)))
        self.assertEqual(easter_monday(2025), date(2025, 4, 21))

    def test_open_holidays_and_christmas_eve(self):
        self.assertIsNone(closure_kind_for_date(date(2026, 5, 1)))
        self.assertIsNone(closure_kind_for_date(date(2026, 7, 5)))
        self.assertIsNone(closure_kind_for_date(date(2026, 7, 6)))
        self.assertIsNone(closure_kind_for_date(date(2026, 11, 17)))
        self.assertIsNone(closure_kind_for_date(date(2026, 4, 3)))
        self.assertIsNone(closure_kind_for_date(date(2026, 12, 24)))
        self.assertIsNone(closure_kind_for_date(date(2026, 12, 31)))

    def test_svatky_obsahuji_velikonoce(self):
        svatky = set(get_ceske_svatky(2026))
        self.assertIn((2026, 4, 3), svatky)
        self.assertIn((2026, 4, 6), svatky)
        self.assertEqual(get_nazev_svatku(4, 3, 2026), 'Velký pátek')
        self.assertEqual(get_nazev_svatku(4, 6, 2026), 'Velikonoční pondělí')


class MallClosureShiftApiTests(TestCase):
    def setUp(self):
        self.mall = Prodejna.objects.create(nazev='Globus', nazev_kratkiy='Globus', aktivni=True)
        self.senimo = Prodejna.objects.create(nazev='Senimo', nazev_kratkiy='Senimo', aktivni=True)
        self.prodejce = WebUser.objects.create(
            id=98011,
            uzivatelske_jmeno='mall.prod',
            jmeno='Petr',
            prijmeni='Prodejce',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=self.mall.id,
        )
        self.vedouci = WebUser.objects.create(
            id=98012,
            uzivatelske_jmeno='mall.ved',
            jmeno='Věra',
            prijmeni='Vedouci',
            heslo='x',
            role='VEDOUCI',
            aktivni=True,
            prodejna_id=self.mall.id,
        )
        self.admin = WebUser.objects.create(
            id=98013,
            uzivatelske_jmeno='mall.admin',
            jmeno='Ada',
            prijmeni='Admin',
            heslo='x',
            role='ADMIN',
            aktivni=True,
        )

    def _post(self, actor, **extra):
        client = APIClient()
        client.force_authenticate(user=actor)
        payload = {
            'user_id': self.prodejce.id,
            'prodejna': self.mall.id,
            'datum': '2026-10-28',
            'cas_od': '09:00',
            'cas_do': '17:00',
            'typ_smeny': 'prace',
        }
        payload.update(extra)
        return client.post('/api/shifts/', payload, format='json')

    def test_vedouci_nemuze_smnu_na_zavreny_den(self):
        res = self._post(self.vedouci)
        self.assertEqual(res.status_code, 403)
        self.assertIn('administrátor', res.data['error'])

    def test_admin_muze_smnu_na_zavreny_den(self):
        res = self._post(self.admin)
        self.assertEqual(res.status_code, 201)

    def test_senimo_na_zavreny_den_nejde(self):
        res = self._post(self.vedouci, prodejna=self.senimo.id, datum='2026-05-08')
        self.assertEqual(res.status_code, 403)

    def test_stedry_den_po_poledni_je_zakazany(self):
        res = self._post(
            self.admin,
            datum='2026-12-24',
            cas_od='08:00',
            cas_do='18:00',
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn('12:00', res.data['error'])

    def test_stedry_den_do_poledne_projde(self):
        res = self._post(
            self.vedouci,
            datum='2026-12-24',
            cas_od='08:00',
            cas_do='12:00',
        )
        self.assertEqual(res.status_code, 201)
        smena = Smena.objects.get(id=res.data['id'])
        self.assertEqual(smena.cas_do, time(12, 0))

    def test_senimo_stedry_den_jen_do_poledne(self):
        res = self._post(
            self.vedouci,
            prodejna=self.senimo.id,
            datum='2026-12-24',
            cas_od='09:00',
            cas_do='18:00',
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn('12:00', res.data['error'])
