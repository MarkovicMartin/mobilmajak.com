"""Kalendář směn – mé směny a admin pohled na jednoho uživatele."""
from datetime import date, time

from django.test import TestCase
from rest_framework.test import APIClient

from shifts.models import Smena
from stores.models import Prodejna
from users.models import WebUser


class CalendarPersonScopeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.store_a = Prodejna.objects.create(
            id=9311, nazev='Přerov', nazev_kratkiy='PR', aktivni=True,
        )
        cls.store_b = Prodejna.objects.create(
            id=9312, nazev='Globus', nazev_kratkiy='GL', aktivni=True,
        )
        cls.prodejce = WebUser.objects.create(
            id=9311,
            uzivatelske_jmeno='cal_malek',
            jmeno='Jakub',
            prijmeni='Testmalek',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=cls.store_a.id,
        )
        cls.kolega = WebUser.objects.create(
            id=9312,
            uzivatelske_jmeno='cal_kolega',
            jmeno='Filip',
            prijmeni='Testrehak',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=cls.store_a.id,
        )
        cls.admin = WebUser.objects.create(
            id=9313,
            uzivatelske_jmeno='cal_admin',
            jmeno='Admin',
            prijmeni='Cal',
            heslo='x',
            role='ADMIN',
            aktivni=True,
        )
        cls.den = date(2026, 8, 10)
        cls.mesic = '2026-08'
        Smena.objects.create(
            user=cls.prodejce,
            prodejna=cls.store_a,
            datum=cls.den,
            cas_od=time(8, 0),
            cas_do=time(16, 0),
            typ_smeny='prace',
        )
        Smena.objects.create(
            user=cls.prodejce,
            prodejna=cls.store_b,
            datum=cls.den,
            cas_od=time(16, 0),
            cas_do=time(20, 0),
            typ_smeny='prace',
        )
        Smena.objects.create(
            user=cls.kolega,
            prodejna=cls.store_a,
            datum=cls.den,
            cas_od=time(8, 0),
            cas_do=time(16, 0),
            typ_smeny='prace',
        )

    def _ids(self, payload):
        rows = payload.get('kalendar_data', {}).get(self.den.isoformat(), [])
        return sorted(r['user_id'] for r in rows)

    def _stores(self, payload):
        rows = payload.get('kalendar_data', {}).get(self.den.isoformat(), [])
        return sorted(r.get('prodejna_id') for r in rows)

    def test_scope_mine_returns_own_shifts_across_stores(self):
        client = APIClient()
        client.force_authenticate(user=self.prodejce)
        res = client.get(f'/api/shifts/calendar/?mesic={self.mesic}&scope=mine')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self._ids(res.data), [self.prodejce.id, self.prodejce.id])
        self.assertEqual(set(self._stores(res.data)), {self.store_a.id, self.store_b.id})
        self.assertTrue(res.data['mine_only'])
        self.assertFalse(res.data['see_all_employees'])

    def test_scope_mine_ignores_store_filter(self):
        client = APIClient()
        client.force_authenticate(user=self.prodejce)
        res = client.get(
            f'/api/shifts/calendar/?mesic={self.mesic}&prodejna={self.store_a.id}&scope=mine'
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(set(self._stores(res.data)), {self.store_a.id, self.store_b.id})

    def test_admin_user_id_shows_that_user_across_stores(self):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        res = client.get(
            f'/api/shifts/calendar/?mesic={self.mesic}&user_id={self.prodejce.id}'
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self._ids(res.data), [self.prodejce.id, self.prodejce.id])
        self.assertEqual(set(self._stores(res.data)), {self.store_a.id, self.store_b.id})
        self.assertEqual(res.data['person_user_id'], self.prodejce.id)
        self.assertFalse(res.data['see_all_employees'])

    def test_seller_cannot_use_user_id_of_colleague(self):
        client = APIClient()
        client.force_authenticate(user=self.prodejce)
        res = client.get(
            f'/api/shifts/calendar/?mesic={self.mesic}&prodejna=vse&user_id={self.kolega.id}'
        )
        self.assertEqual(res.status_code, 200)
        self.assertNotIn(self.kolega.id, self._ids(res.data))
