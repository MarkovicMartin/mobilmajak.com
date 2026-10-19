"""Výpis a mazání ručních nákladů."""
from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from finance import views
from finance.models import FinanceDoklad, NakladPolozka
from users.models import WebUser


class ManualNakladApiTests(TestCase):
    def setUp(self):
        self.admin = WebUser.objects.create(
            id=9320,
            uzivatelske_jmeno='finmanual',
            jmeno='Admin',
            prijmeni='Fin',
            heslo='x',
            role='ADMIN',
            aktivni=True,
            moduly=[],
        )
        self.factory = APIRequestFactory()
        self.older = NakladPolozka.objects.create(
            datum=date(2026, 8, 1),
            rok=2026,
            mesic=8,
            castka=Decimal('-100'),
            zdroj=NakladPolozka.ZDROJ_MANUAL,
            popis='starší',
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
        )
        self.newer = NakladPolozka.objects.create(
            datum=date(2026, 10, 2),
            rok=2026,
            mesic=10,
            castka=Decimal('-250'),
            zdroj=NakladPolozka.ZDROJ_MANUAL,
            popis='novější',
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
        )
        self.fio = NakladPolozka.objects.create(
            datum=date(2026, 10, 3),
            rok=2026,
            mesic=10,
            castka=Decimal('-80'),
            zdroj=NakladPolozka.ZDROJ_FIO,
            fio_id='fio:manual-test',
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
        )

    def _auth(self, request):
        force_authenticate(request, user=self.admin)
        return request

    def test_positive_amount_stored_as_expense(self):
        request = self._auth(self.factory.post(
            '/finance/naklady/manual/',
            {'datum': '2026-10-12', 'castka': '8000', 'popis': 'nájem'},
            format='json',
        ))
        resp = views.naklad_manual_create(request)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['castka'], '-8000')
        self.assertEqual(resp.data['typ_platby'], NakladPolozka.TYP_PLATBY_ODCHOZI)

    def test_minus_amount_stays_expense(self):
        request = self._auth(self.factory.post(
            '/finance/naklady/manual/',
            {'datum': '2026-10-12', 'castka': '-1500'},
            format='json',
        ))
        resp = views.naklad_manual_create(request)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['castka'], '-1500')

    def test_list_only_manual_newest_first(self):
        request = self._auth(self.factory.get('/finance/naklady/manual/'))
        resp = views.naklad_manual_create(request)
        self.assertEqual(resp.status_code, 200)
        ids = [row['id'] for row in resp.data]
        self.assertEqual(ids, [self.newer.id, self.older.id])

    def test_delete_manual(self):
        request = self._auth(self.factory.delete(f'/finance/naklady/{self.older.id}/'))
        resp = views.naklad_update(request, polozka_id=self.older.id)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(NakladPolozka.objects.filter(pk=self.older.id).exists())

    def test_delete_fio_refused(self):
        request = self._auth(self.factory.delete(f'/finance/naklady/{self.fio.id}/'))
        resp = views.naklad_update(request, polozka_id=self.fio.id)
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(NakladPolozka.objects.filter(pk=self.fio.id).exists())

    def test_delete_unlinks_doklad(self):
        doklad = FinanceDoklad.objects.create(naklad_polozka=self.newer, cislo_faktury='FA-1')
        self.newer.doklad = doklad
        self.newer.save(update_fields=['doklad'])
        request = self._auth(self.factory.delete(f'/finance/naklady/{self.newer.id}/'))
        resp = views.naklad_update(request, polozka_id=self.newer.id)
        self.assertEqual(resp.status_code, 200)
        doklad.refresh_from_db()
        self.assertIsNone(doklad.naklad_polozka_id)
        self.assertTrue(FinanceDoklad.objects.filter(pk=doklad.id).exists())
