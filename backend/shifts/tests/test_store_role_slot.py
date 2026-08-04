"""Na prodejně max. jeden prodejce / servis / výpomoc ve stejném čase; školení bez limitu."""
from datetime import date, time

from django.test import TestCase
from rest_framework.test import APIClient

from shifts.models import Smena
from shifts.shift_helpers import (
    find_store_role_slot_conflict,
    shift_store_role_slot,
    store_role_slot_conflict_message,
)
from stores.models import Prodejna
from users.models import WebUser


class StoreRoleSlotHelperTests(TestCase):
    def test_slot_mapping(self):
        self.assertEqual(shift_store_role_slot('prodej'), 'prodej')
        self.assertEqual(shift_store_role_slot('prodej', 'vypomoc'), 'vypomoc')
        self.assertEqual(shift_store_role_slot('servis'), 'servis')
        self.assertIsNone(shift_store_role_slot('skoleni'))
        self.assertIsNone(shift_store_role_slot('backoffice'))
        self.assertIsNone(shift_store_role_slot('home_office'))

    def test_message_guides_resolution(self):
        from types import SimpleNamespace
        store = Prodejna(nazev='Test', nazev_kratkiy='TST')
        conflict = SimpleNamespace(
            cas_od=time(9, 0),
            cas_do=time(17, 0),
            user=SimpleNamespace(jmeno='Jan', prijmeni='Novák'),
        )
        msg = store_role_slot_conflict_message(conflict, store, 'prodej')
        self.assertIn('Dva prodejci!', msg)
        self.assertIn('Novák Jan', msg)
        self.assertIn('zrušte nebo upravte stávající směnu', msg)
        self.assertIn('nového prodejce', msg)


class StoreRoleSlotConflictTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.store = Prodejna.objects.create(
            nazev='Test Šternberk',
            nazev_kratkiy='ŠTR',
            aktivni=True,
            povolena_pozice_servis=True,
        )
        cls.senimo = Prodejna.objects.create(
            nazev='Senimo',
            nazev_kratkiy='SEN',
            aktivni=True,
        )
        cls.a = WebUser.objects.create(
            id=9401,
            uzivatelske_jmeno='slot.a',
            jmeno='Anna',
            prijmeni='Alpha',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=cls.store.id,
        )
        cls.b = WebUser.objects.create(
            id=9402,
            uzivatelske_jmeno='slot.b',
            jmeno='Bob',
            prijmeni='Beta',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=cls.store.id,
        )
        cls.brig = WebUser.objects.create(
            id=9403,
            uzivatelske_jmeno='slot.brig',
            jmeno='Brig',
            prijmeni='Charlie',
            heslo='x',
            role='BRIGADNIK',
            aktivni=True,
            prodejna_id=cls.store.id,
        )
        cls.admin = WebUser.objects.create(
            id=9404,
            uzivatelske_jmeno='slot.admin',
            jmeno='Ada',
            prijmeni='Admin',
            heslo='x',
            role='ADMIN',
            aktivni=True,
        )

    def _prace(self, user, store, d, od, do, pozice='prodej', rezim='prodejce'):
        return Smena.objects.create(
            user=user,
            prodejna=store,
            datum=d,
            cas_od=od,
            cas_do=do,
            typ_smeny='prace',
            pozice_smeny=pozice,
            brigadnik_rezim=rezim,
        )

    def test_two_prodejci_overlapping_blocked(self):
        d = date(2026, 9, 10)
        self._prace(self.a, self.store, d, time(9, 0), time(17, 0))
        conflict = find_store_role_slot_conflict(
            d, self.store, 'prace', time(10, 0), time(18, 0), 'prodej',
        )
        self.assertIsNotNone(conflict)
        self.assertEqual(conflict.user_id, self.a.id)

    def test_prodejce_and_vypomoc_same_time_ok(self):
        d = date(2026, 9, 11)
        self._prace(self.a, self.store, d, time(9, 0), time(17, 0))
        conflict = find_store_role_slot_conflict(
            d, self.store, 'prace', time(9, 0), time(17, 0), 'prodej', 'vypomoc',
        )
        self.assertIsNone(conflict)

    def test_prodejce_and_servis_same_time_ok(self):
        d = date(2026, 9, 12)
        self._prace(self.a, self.store, d, time(9, 0), time(17, 0))
        conflict = find_store_role_slot_conflict(
            d, self.store, 'prace', time(9, 0), time(17, 0), 'servis',
        )
        self.assertIsNone(conflict)

    def test_two_servis_overlapping_blocked(self):
        d = date(2026, 9, 13)
        self._prace(self.a, self.store, d, time(9, 0), time(17, 0), pozice='servis')
        conflict = find_store_role_slot_conflict(
            d, self.store, 'prace', time(12, 0), time(20, 0), 'servis',
        )
        self.assertIsNotNone(conflict)

    def test_non_overlapping_same_slot_ok(self):
        d = date(2026, 9, 14)
        self._prace(self.a, self.store, d, time(8, 0), time(14, 0))
        conflict = find_store_role_slot_conflict(
            d, self.store, 'prace', time(14, 0), time(20, 0), 'prodej',
        )
        self.assertIsNone(conflict)

    def test_skoleni_senimo_unlimited(self):
        d = date(2026, 9, 15)
        self._prace(self.a, self.senimo, d, time(9, 0), time(17, 0), pozice='skoleni')
        conflict = find_store_role_slot_conflict(
            d, self.senimo, 'prace', time(9, 0), time(17, 0), 'skoleni',
        )
        self.assertIsNone(conflict)

    def test_api_create_second_prodejce_returns_guide(self):
        d = date(2026, 9, 16)
        self._prace(self.a, self.store, d, time(9, 0), time(17, 0))
        client = APIClient()
        client.force_authenticate(user=self.admin)
        resp = client.post('/api/shifts/', {
            'user_id': self.b.id,
            'prodejna': self.store.id,
            'datum': d.isoformat(),
            'cas_od': '10:00',
            'cas_do': '18:00',
            'typ_smeny': 'prace',
            'pozice_smeny': 'prodej',
        }, format='json')
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data.get('conflict_type'), 'store_role_slot')
        self.assertIn('Dva prodejci!', resp.data['error'])
        self.assertIn('zrušte nebo upravte stávající směnu', resp.data['error'])
        self.assertIn('nového prodejce', resp.data['error'])

    def test_api_create_skoleni_second_ok(self):
        d = date(2026, 9, 17)
        self._prace(self.a, self.senimo, d, time(9, 0), time(17, 0), pozice='skoleni')
        client = APIClient()
        client.force_authenticate(user=self.admin)
        resp = client.post('/api/shifts/', {
            'user_id': self.b.id,
            'prodejna': self.senimo.id,
            'datum': d.isoformat(),
            'cas_od': '09:00',
            'cas_do': '17:00',
            'typ_smeny': 'prace',
            'pozice_smeny': 'skoleni',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
