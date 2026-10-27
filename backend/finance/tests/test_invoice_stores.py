"""Faktury prodejce a brigádníka podle domácí prodejny a dnešní směny."""
from datetime import datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from finance import views
from finance.models import NakladPolozka
from finance.permissions import (
    current_shift_store_id,
    default_invoice_store_id,
    user_can_access_polozka,
    user_can_upload_doklad,
)
from shifts.models import Smena
from stores.models import Prodejna
from users.models import WebUser


class InvoiceStoreScopeTests(TestCase):
    def setUp(self):
        self.domaci = Prodejna.objects.create(nazev='Domaci FA', nazev_kratkiy='DF', aktivni=True)
        self.cizi = Prodejna.objects.create(nazev='Cizi FA', nazev_kratkiy='CF', aktivni=True)
        self.jina = Prodejna.objects.create(nazev='Jina FA', nazev_kratkiy='JF', aktivni=True)
        self.prodejce = WebUser.objects.create(
            id=9601,
            uzivatelske_jmeno='fa.prodejce',
            jmeno='Pro',
            prijmeni='Dejce',
            heslo='x',
            role='PRODEJCE',
            prodejna_id=self.domaci.id,
            aktivni=True,
        )
        self.brigadnik = WebUser.objects.create(
            id=9602,
            uzivatelske_jmeno='fa.brig',
            jmeno='Bri',
            prijmeni='Gadnik',
            heslo='x',
            role='BRIGADNIK',
            aktivni=True,
        )
        self.now = timezone.make_aware(datetime(2026, 10, 27, 12, 0))
        self.factory = APIRequestFactory()
        self.domaci_fa = self._polozka(self.domaci.id, 'symplio:fa:domaci')
        self.cizi_fa = self._polozka(self.cizi.id, 'symplio:fa:cizi')
        self.jina_fa = self._polozka(self.jina.id, 'symplio:fa:jina')

    def _polozka(self, prodejna_id, fio_id):
        return NakladPolozka.objects.create(
            datum=self.now.date(),
            rok=2026,
            mesic=10,
            castka=Decimal('-400'),
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            dph_stav=NakladPolozka.DPH_STAV_CEKA,
            zdroj=NakladPolozka.ZDROJ_SYMPLIO_POKLADNA,
            prodejna_id=prodejna_id,
            popis='Manuální výdej',
            fio_id=fio_id,
        )

    def _smena(self, user, prodejna, cas_od, cas_do, datum=None):
        return Smena.objects.create(
            user=user,
            prodejna=prodejna,
            datum=datum or self.now.date(),
            cas_od=cas_od,
            cas_do=cas_do,
            typ_smeny='prace',
            aktivni=True,
        )

    def _frozen_localtime(self, value=None):
        if value is None:
            return self.now
        return timezone.localtime(value)

    def _get(self, user, **params):
        request = self.factory.get('/finance/naklady/ceka-na-fakturu/', params)
        force_authenticate(request, user=user)
        with patch('finance.permissions.timezone.localtime', side_effect=self._frozen_localtime):
            return views.naklady_ceka_na_fakturu(request)

    def test_bez_smeny_je_default_domaci(self):
        self._smena(self.prodejce, self.cizi, time(18, 0), time(21, 0))
        self.assertIsNone(current_shift_store_id(self.prodejce, now=self.now))
        self.assertEqual(default_invoice_store_id(self.prodejce, now=self.now), self.domaci.id)
        resp = self._get(self.prodejce)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['prodejna_id'], self.domaci.id)
        self.assertEqual([row['id'] for row in resp.data['items']], [self.domaci_fa.id])
        ids = {row['id'] for row in resp.data['prodejny']}
        self.assertEqual(ids, {self.domaci.id, self.cizi.id})

    def test_probihajici_smena_prepne_default(self):
        self._smena(self.prodejce, self.cizi, time(9, 0), time(17, 0))
        self.assertEqual(current_shift_store_id(self.prodejce, now=self.now), self.cizi.id)
        resp = self._get(self.prodejce)
        self.assertEqual(resp.data['prodejna_id'], self.cizi.id)
        self.assertEqual(resp.data['aktualni_smena_prodejna_id'], self.cizi.id)
        self.assertEqual([row['id'] for row in resp.data['items']], [self.cizi_fa.id])
        with patch('finance.permissions.timezone.localtime', side_effect=self._frozen_localtime):
            self.assertTrue(user_can_upload_doklad(self.prodejce, self.cizi_fa))

    def test_rucne_vsechny_a_cizi_prodejna(self):
        self._smena(self.prodejce, self.cizi, time(9, 0), time(17, 0))
        vse = self._get(self.prodejce, prodejna_id='all')
        self.assertEqual(vse.status_code, 200)
        self.assertEqual(vse.data['prodejna_id'], 'all')
        self.assertEqual(
            {row['id'] for row in vse.data['items']},
            {self.domaci_fa.id, self.cizi_fa.id},
        )
        self.assertNotIn(self.jina_fa.id, {row['id'] for row in vse.data['items']})
        denied = self._get(self.prodejce, prodejna_id=self.jina.id)
        self.assertEqual(denied.status_code, 403)
        with patch('finance.permissions.timezone.localtime', side_effect=self._frozen_localtime):
            self.assertFalse(user_can_access_polozka(self.prodejce, self.jina_fa))

    def test_brigadnik_bez_domaci_vidi_smenu(self):
        self._smena(self.brigadnik, self.cizi, time(9, 0), time(17, 0))
        resp = self._get(self.brigadnik)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['prodejna_id'], self.cizi.id)
        self.assertEqual([row['id'] for row in resp.data['items']], [self.cizi_fa.id])
        with patch('finance.permissions.timezone.localtime', side_effect=self._frozen_localtime):
            self.assertTrue(user_can_upload_doklad(self.brigadnik, self.cizi_fa))

    def test_brigadnik_bez_smeny_nema_pristup(self):
        resp = self._get(self.brigadnik)
        self.assertEqual(resp.status_code, 403)

    def test_vedouci_vidi_vsechny_sve_prodejny(self):
        vedouci = WebUser.objects.create(
            id=9603,
            uzivatelske_jmeno='fa.vedouci',
            jmeno='Ve',
            prijmeni='Douci',
            heslo='x',
            role='VEDOUCI',
            prodejna_id=self.domaci.id,
            aktivni=True,
        )
        self.cizi.vedouci_user_id = vedouci.id
        self.cizi.save(update_fields=['vedouci_user_id'])
        self.assertIsNone(default_invoice_store_id(vedouci, now=self.now))
        resp = self._get(vedouci)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['prodejna_id'], 'all')
        self.assertEqual(
            {row['id'] for row in resp.data['items']},
            {self.domaci_fa.id, self.cizi_fa.id},
        )

    def test_nocni_smena_z_predchoziho_dne(self):
        self._smena(
            self.prodejce,
            self.cizi,
            time(22, 0),
            time(6, 0),
            datum=self.now.date() - timedelta(days=1),
        )
        rano = timezone.make_aware(datetime.combine(self.now.date(), time(2, 0)))
        self.assertEqual(current_shift_store_id(self.prodejce, now=rano), self.cizi.id)
        self.assertEqual(default_invoice_store_id(self.prodejce, now=rano), self.cizi.id)
