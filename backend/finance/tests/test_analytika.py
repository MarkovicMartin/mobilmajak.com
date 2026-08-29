"""Testy analytiky nákladů, POST kategorie a auto-pravidel."""
from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from analytics.models import WebProdejeAll
from finance import views
from finance.models import FinanceDoklad, FioKategorizacniPravidlo, NakladKategorie, NakladPolozka
from finance.services import (
    _matches_rule,
    compute_stav_rozdilu,
    is_fio_account_number,
    navrh_pravidla_from_polozka,
    rule_key_from_polozka,
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

    def test_ignore_codaruina_jen_cisty_prevod(self):
        rule = FioKategorizacniPravidlo(
            protiucet='',
            vs='',
            zprava_obsahuje='Codaruina s.r.o.',
            text_shoda=FioKategorizacniPravidlo.TEXT_SHODA_PRESNE,
            ignorovat=True,
        )
        row_prevod = {'zprava': 'Codaruina s.r.o.', 'popis': 'Codaruina s.r.o.'}
        row_najem = {'zprava': 'Codaruina s.r.o.', 'popis': 'Vsetín - nájem'}
        row_splatka = {'zprava': 'Codaruina s.r.o. - Splátka úvěru', 'popis': 'ČSOB-Splátka úvěru auto'}
        self.assertTrue(_matches_rule(rule, row_prevod))
        self.assertFalse(_matches_rule(rule, row_najem))
        self.assertFalse(_matches_rule(rule, row_splatka))


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
            protiucet='2540180968',
            kategorie=self.kat,
            aktivni=True,
        )
        p = NakladPolozka.objects.create(
            datum=date(2026, 8, 2),
            rok=2026,
            mesic=8,
            castka=Decimal('-50'),
            kategorie=self.kat2,
            protiucet='2540180968',
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            zdroj=NakladPolozka.ZDROJ_FIO,
            fio_id='fio:upsert2',
        )
        meta = upsert_pravidlo_from_polozka(p)
        self.assertTrue(meta['pravidlo_updated'])
        self.assertEqual(
            FioKategorizacniPravidlo.objects.get(protiucet='2540180968').kategorie_id,
            self.kat2.id,
        )

    def test_fio_rejects_vs_as_account(self):
        self.assertFalse(is_fio_account_number('20260008'))
        self.assertTrue(is_fio_account_number('270640235'))
        p = NakladPolozka.objects.create(
            datum=date(2026, 8, 17),
            rok=2026,
            mesic=8,
            castka=Decimal('-5000'),
            kategorie=self.kat,
            protiucet='20260008',
            zprava='Ing. Lucie Polednova - administrati',
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            zdroj=NakladPolozka.ZDROJ_FIO,
            fio_id='fio:lucie',
        )
        self.assertIsNone(rule_key_from_polozka(p))
        navrh = navrh_pravidla_from_polozka(p)
        self.assertEqual(navrh['varovani'], 'fio_bez_uctu')
        self.assertEqual(navrh['navrh']['protiucet'], '')
        self.assertFalse(upsert_pravidlo_from_polozka(p)['pravidlo_created'])

    def test_pokladna_uses_popis(self):
        p = NakladPolozka.objects.create(
            datum=date(2026, 8, 3),
            rok=2026,
            mesic=8,
            castka=Decimal('-200'),
            kategorie=self.kat,
            popis='Manuální výdej PANFICO - servis 202601234',
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            zdroj=NakladPolozka.ZDROJ_SYMPLIO_POKLADNA,
            fio_id='symplio:upsert-kasa',
        )
        key = rule_key_from_polozka(p)
        self.assertEqual(key['protiucet'], '')
        self.assertIn('PANFICO', key['zprava_obsahuje'])
        meta = upsert_pravidlo_from_polozka(p)
        self.assertTrue(meta['pravidlo_created'])


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

    def test_patch_returns_navrh_without_creating_pravidlo(self):
        p = NakladPolozka.objects.get(fio_id='fio:an1')
        request = self._auth(self.factory.patch(
            f'/finance/naklady/{p.id}/',
            {'kategorie_id': self.kat.id, 'zaradit': True},
            format='json',
        ))
        resp = views.naklad_update(request, polozka_id=p.id)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data.get('pravidlo_created'))
        self.assertIn('pravidlo_navrh', resp.data)
        self.assertFalse(
            FioKategorizacniPravidlo.objects.filter(protiucet='111', kategorie=self.kat).exists()
        )

    def test_from_polozka_creates_pravidlo(self):
        p = NakladPolozka.objects.get(fio_id='fio:an1')
        p.protiucet = '270640235'
        p.save(update_fields=['protiucet'])
        request = self._auth(self.factory.post(
            '/finance/pravidla/from-polozka/',
            {'polozka_id': p.id, 'protiucet': '270640235', 'kategorie_id': self.kat.id},
            format='json',
        ))
        resp = views.pravidlo_from_polozka(request)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get('pravidlo_created'))
        self.assertTrue(
            FioKategorizacniPravidlo.objects.filter(protiucet='270640235', kategorie=self.kat).exists()
        )

    def test_ignore_keeps_kategorie(self):
        p = NakladPolozka.objects.get(fio_id='fio:an1')
        request = self._auth(self.factory.patch(
            f'/finance/naklady/{p.id}/',
            {'ignorovat': True, 'zachovat_kategorii': True, 'kategorie_id': self.kat.id},
            format='json',
        ))
        resp = views.naklad_update(request, polozka_id=p.id)
        self.assertEqual(resp.status_code, 200)
        p.refresh_from_db()
        self.assertTrue(p.ignorovat)
        self.assertEqual(p.stav, NakladPolozka.STAV_IGNOROVAT)
        self.assertEqual(p.kategorie_id, self.kat.id)
        self.assertTrue(resp.data.get('pravidlo_navrh', {}).get('navrh', {}).get('ignorovat'))

    def test_patch_kategorie_and_delete(self):
        request = self._auth(self.factory.patch(
            f'/finance/kategorie/{self.kat.id}/',
            {'nazev': 'Reklama upravena', 'poradi': 3},
            format='json',
        ))
        resp = views.naklad_kategorie_detail(request, kategorie_id=self.kat.id)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['nazev'], 'Reklama upravena')
        del_req = self._auth(self.factory.delete(f'/finance/kategorie/{self.kat.id}/'))
        del_resp = views.naklad_kategorie_detail(del_req, kategorie_id=self.kat.id)
        self.assertEqual(del_resp.status_code, 200)
        p = NakladPolozka.objects.get(fio_id='fio:an1')
        self.assertIsNone(p.kategorie_id)
        self.assertEqual(p.stav, NakladPolozka.STAV_NEZARAZENO)

    def test_doklad_patch_keeps_cislo_faktury(self):
        d = FinanceDoklad.objects.create(stav=FinanceDoklad.STAV_KE_KONTROLE)
        request = self._auth(self.factory.patch(
            f'/finance/doklady/{d.id}/',
            {'cislo_faktury': 'FA2026/001'},
            format='json',
        ))
        resp = views.doklad_update(request, doklad_id=d.id)
        self.assertEqual(resp.status_code, 200)
        d.refresh_from_db()
        self.assertEqual(d.cislo_faktury, 'FA2026/001')
        get_req = self._auth(self.factory.get('/finance/doklady/ke-kontrole/'))
        get_resp = views.doklady_ke_kontrole(get_req)
        found = next(x for x in get_resp.data if x['id'] == d.id)
        self.assertEqual(found['cislo_faktury'], 'FA2026/001')
