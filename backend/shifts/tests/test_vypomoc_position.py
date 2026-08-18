from datetime import date, time

from django.test import TestCase
from rest_framework.test import APIClient

from shifts.models import Smena
from shifts.views import _normalize_pozice_smeny
from stores.models import Prodejna
from users.models import WebUser


class ServisAllStoresAndVypomocPositionTests(TestCase):
    def setUp(self):
        self.store = Prodejna.objects.create(
            nazev='Nova Pobocka',
            nazev_kratkiy='NP',
            aktivni=True,
        )
        self.prodejce = WebUser.objects.create(
            id=9421,
            uzivatelske_jmeno='vyp.prod',
            jmeno='Petr',
            prijmeni='Prodejce',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=self.store.id,
        )
        self.brig = WebUser.objects.create(
            id=9422,
            uzivatelske_jmeno='vyp.brig',
            jmeno='Bára',
            prijmeni='Brig',
            heslo='x',
            role='BRIGADNIK',
            aktivni=True,
            prodejna_id=self.store.id,
        )
        self.admin = WebUser.objects.create(
            id=9423,
            uzivatelske_jmeno='vyp.admin',
            jmeno='Ada',
            prijmeni='Admin',
            heslo='x',
            role='ADMIN',
            aktivni=True,
        )

    def test_nova_prodejna_ma_servis_pozici(self):
        self.assertTrue(self.store.povolena_pozice_servis)
        self.assertEqual(
            _normalize_pozice_smeny(self.store, 'prace', 'servis'),
            'servis',
        )

    def test_zamestnanec_muze_vypomoc(self):
        self.assertEqual(
            _normalize_pozice_smeny(
                self.store, 'prace', 'vypomoc', user=self.prodejce,
            ),
            'vypomoc',
        )

    def test_brigadnik_vypomoc_pozice_je_prodej(self):
        self.assertEqual(
            _normalize_pozice_smeny(
                self.store, 'prace', 'vypomoc', user=self.brig,
            ),
            'prodej',
        )

    def test_api_servis_na_nove_prodejne(self):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        resp = client.post('/api/shifts/', {
            'user_id': self.prodejce.id,
            'prodejna': self.store.id,
            'datum': '2026-09-23',
            'cas_od': '09:00',
            'cas_do': '17:00',
            'typ_smeny': 'prace',
            'pozice_smeny': 'servis',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        smena = Smena.objects.get(id=resp.data['id'])
        self.assertEqual(smena.pozice_smeny, 'servis')

    def test_api_zamestnanec_vypomoc_vedle_prodejce(self):
        Smena.objects.create(
            user=self.brig,
            prodejna=self.store,
            datum=date(2026, 9, 24),
            cas_od=time(9, 0),
            cas_do=time(17, 0),
            typ_smeny='prace',
            pozice_smeny='prodej',
            brigadnik_rezim='prodejce',
        )
        client = APIClient()
        client.force_authenticate(user=self.admin)
        resp = client.post('/api/shifts/', {
            'user_id': self.prodejce.id,
            'prodejna': self.store.id,
            'datum': '2026-09-24',
            'cas_od': '09:00',
            'cas_do': '17:00',
            'typ_smeny': 'prace',
            'pozice_smeny': 'vypomoc',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        smena = Smena.objects.get(id=resp.data['id'])
        self.assertEqual(smena.pozice_smeny, 'vypomoc')
        self.assertEqual(smena.brigadnik_rezim, 'prodejce')
