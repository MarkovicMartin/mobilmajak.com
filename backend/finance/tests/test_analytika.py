"""Testy analytiky nákladů, POST kategorie a auto-pravidel."""
from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from analytics.models import WebProdejeAll
from finance import views
from finance.models import FioKategorizacniPravidlo, NakladKategorie, NakladPolozka
from finance.services import (
    _matches_rule,
    compute_stav_rozdilu,
    upsert_pravidlo_from_polozka,
)
from users.models import WebUser


class StavRozdiluTests(TestCase):
    def test_minus(self):
        self.assertEqual(compute_stav_rozdilu(100, 150), 'minus')

    def test_vyrovnano_under_5pct(self):
        self.assertEqual(compute_stav_rozdilu(1000, 960), 'vyrovnano')

    def test_plus(self):
        self.assertEqual(compute_stav_rozdilu(1000, 800), 'plus')

    def test_zero_prijmy_with_naklady(self):
        self.assertEqual(compute_stav_rozdilu(0, 50), 'minus')


class MatchesRulePopisTests(TestCase):
    def test_zprava_obsahuje_matches_popis(self):
        rule = FioKategorizacniPravidlo(
            protiucet='',
            vs='',
            zprava_obsahuje='Symplio výdej',
        )
        self.assertTrue(_matches_rule(rule, {'zprava': '', 'popis': 'Symplio výdej kancelář'}))
        self.assertFalse(_matches_rule(rule, {'zprava': '', 'popis': 'jiný text'}))


class UpsertPravidloTests(TestCase):
    def setUp(self):
        self.kat = NakladKategorie.objects.create(nazev='Test kat analytika', poradi=1)
        self.kat2 = NakladKategorie.objects.create(nazev='Test kat 2', poradi=2)

    def test_create_from_protiucet(self):
        p = NakladPolozka.objects.create(
            datum=date(2026, 8, 1),
            rok=2026,
            mesic=8,
            castka=Decimal('-100'),
            kategorie=self.kat,
            protiucet='1234567890',
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            zdroj=NakladPolozka.ZDROJ_FIO,
            fio_id='fio:upsert1',
        )
        meta = upsert_pravidlo_from_polozka(p, user_id=1)
        self.assertTrue(meta['pravidlo_created'])
        rule = FioKategorizacniPravidlo.objects.get(pk=meta['pravidlo_id'])
        self.assertEqual(rule.protiucet, '1234567890')
        self.assertEqual(rule.kategorie_id, self.kat.id)

    def test_update_existing(self):
        FioKategorizacniPravidlo.objects.create(
            protiucet='999',
            kategorie=self.kat,
            aktivni=True,
        )
        p = NakladPolozka.objects.create(
            datum=date(2026, 8, 2),
            rok=2026,
            mesic=8,
            castka=Decimal('-50'),
            kategorie=self.kat2,
            protiucet='999',
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            zdroj=NakladPolozka.ZDROJ_FIO,
            fio_id='fio:upsert2',
        )
        meta = upsert_pravidlo_from_polozka(p)
        self.assertTrue(meta['pravidlo_updated'])
        self.assertEqual(
            FioKategorizacniPravidlo.objects.get(protiucet='999').kategorie_id,
            self.kat2.id,
        )


class FinanceAnalytikaApiTests(TestCase):
    """API přes RequestFactory – finance URLs jsou za FINANCE_MODULE_ENABLED."""

    def setUp(self):
        self.admin = WebUser.objects.create(
            id=9301,
            uzivatelske_jmeno='finanalytika',
            jmeno='Admin',
            prijmeni='Fin',
            heslo='x',
            role='ADMIN',
            aktivni=True,
            moduly=[],
        )
        self.factory = APIRequestFactory()
        self.kat = NakladKategorie.objects.create(nazev='Reklama test', poradi=10)

        WebProdejeAll.objects.create(
            typ=date(2026, 8, 5),
            doklad='U1',
            kod='P1',
            nazev='Telefon',
            pocet_kusu=2,
            cena_ks_vcl_dph=Decimal('1000'),
            id_prodejny=1,
            stredisko='Test',
        )
        NakladPolozka.objects.create(
            datum=date(2026, 8, 6),
            rok=2026,
            mesic=8,
            castka=Decimal('-500'),
            kategorie=self.kat,
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            ignorovat=False,
            stav=NakladPolozka.STAV_ZARAZENO,
            zdroj=NakladPolozka.ZDROJ_FIO,
            fio_id='fio:an1',
            popis='FB ads',
            protiucet='111',
        )
        NakladPolozka.objects.create(
            datum=date(2026, 8, 7),
            rok=2026,
            mesic=8,
            castka=Decimal('-100'),
            kategorie=None,
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            ignorovat=False,
            stav=NakladPolozka.STAV_NEZARAZENO,
            zdroj=NakladPolozka.ZDROJ_MANUAL,
            popis='nezarazeno',
        )
        NakladPolozka.objects.create(
            datum=date(2026, 8, 8),
            rok=2026,
            mesic=8,
            castka=Decimal('-999'),
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            ignorovat=True,
            stav=NakladPolozka.STAV_IGNOROVAT,
            zdroj=NakladPolozka.ZDROJ_FIO,
            fio_id='fio:an-ign',
        )

    def _auth(self, request):
        force_authenticate(request, user=self.admin)
        return request

    def test_analytika_aggregation(self):
        request = self._auth(self.factory.get(
            '/finance/naklady/analytika/',
            {'start_date': '2026-08-01', 'end_date': '2026-08-31'},
        ))
        resp = views.naklady_analytika(request)
        self.assertEqual(resp.status_code, 200)
        data = resp.data
        self.assertEqual(data['prijmy_s_dph'], 2000.0)
        self.assertEqual(data['naklady_s_dph'], 600.0)
        self.assertEqual(data['rozdil'], 1400.0)
        self.assertEqual(data['stav_rozdilu'], 'plus')
        ids = {c['id'] for c in data['kategorie']}
        self.assertIn(self.kat.id, ids)
        self.assertIn(None, ids)
        self.assertGreaterEqual(len(data['polozky']), 2)

    def test_post_kategorie(self):
        request = self._auth(self.factory.post(
            '/finance/kategorie/',
            {'nazev': 'Nová analytika kat', 'typ_dph': 'bez', 'poradi': 50},
            format='json',
        ))
        resp = views.naklad_kategorie_list(request)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['nazev'], 'Nová analytika kat')
        self.assertEqual(resp.data['typ_dph'], 'bez')

    def test_post_kategorie_duplicate(self):
        request = self._auth(self.factory.post(
            '/finance/kategorie/',
            {'nazev': 'Reklama test', 'typ_dph': 'z_faktury'},
            format='json',
        ))
        resp = views.naklad_kategorie_list(request)
        self.assertEqual(resp.status_code, 400)

    def test_patch_creates_pravidlo(self):
        p = NakladPolozka.objects.get(fio_id='fio:an1')
        request = self._auth(self.factory.patch(
            f'/finance/naklady/{p.id}/',
            {'kategorie_id': self.kat.id, 'zaradit': True},
            format='json',
        ))
        resp = views.naklad_update(request, polozka_id=p.id)
        self.assertEqual(resp.status_code, 200)
        body = resp.data
        self.assertTrue(body.get('pravidlo_created') or body.get('pravidlo_updated'))
        self.assertTrue(
            FioKategorizacniPravidlo.objects.filter(protiucet='111', kategorie=self.kat).exists()
        )
