"""Zpětné uplatnění kategorizačních pravidel na nezařazené platby."""
from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from finance import views
from finance.models import FioKategorizacniPravidlo, NakladKategorie, NakladPolozka
from finance.services import apply_pravidlo_to_nezarazene, preview_pravidlo
from users.models import WebUser


def _polozka(**kwargs):
    defaults = dict(
        datum=date(2026, 8, 1),
        rok=2026,
        mesic=8,
        castka=Decimal('-100'),
        typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
        stav=NakladPolozka.STAV_NEZARAZENO,
        zdroj=NakladPolozka.ZDROJ_FIO,
    )
    defaults.update(kwargs)
    return NakladPolozka.objects.create(**defaults)


class ApplyPravidloTests(TestCase):
    def setUp(self):
        self.kat = NakladKategorie.objects.create(nazev='Energie apply')
        self.rule = FioKategorizacniPravidlo.objects.create(
            protiucet='123/0100',
            kategorie=self.kat,
            aktivni=True,
        )

    def test_categorizes_matching_nezarazeno(self):
        p = _polozka(protiucet='123/0100', fio_id='fio:ap1')
        result = apply_pravidlo_to_nezarazene(self.rule)
        self.assertEqual(result['updated'], 1)
        p.refresh_from_db()
        self.assertEqual(p.stav, NakladPolozka.STAV_ZARAZENO)
        self.assertEqual(p.kategorie_id, self.kat.id)
        self.assertTrue(p.zarazeno_automaticky)
        self.assertEqual(p.auto_pravidlo, 'db_pravidlo')

    def test_skips_already_categorized(self):
        _polozka(
            protiucet='123/0100',
            fio_id='fio:ap2',
            stav=NakladPolozka.STAV_ZARAZENO,
            kategorie=self.kat,
        )
        result = apply_pravidlo_to_nezarazene(self.rule)
        self.assertEqual(result['updated'], 0)

    def test_skips_incoming(self):
        _polozka(
            protiucet='123/0100',
            fio_id='fio:ap-in',
            castka=Decimal('2000'),
            typ_platby=NakladPolozka.TYP_PLATBY_PRICHOZI,
            stav=NakladPolozka.STAV_IGNOROVAT,
            ignorovat=True,
        )
        result = apply_pravidlo_to_nezarazene(self.rule)
        self.assertEqual(result['updated'], 0)

    def test_ignore_rule(self):
        rule = FioKategorizacniPravidlo.objects.create(
            zprava_obsahuje='prevod',
            ignorovat=True,
            aktivni=True,
        )
        p = _polozka(zprava='interni prevod', fio_id='fio:ap-ign')
        result = apply_pravidlo_to_nezarazene(rule)
        self.assertEqual(result['updated'], 1)
        p.refresh_from_db()
        self.assertEqual(p.stav, NakladPolozka.STAV_IGNOROVAT)
        self.assertTrue(p.ignorovat)

    def test_empty_key_does_nothing(self):
        rule = FioKategorizacniPravidlo.objects.create(
            kategorie=self.kat, aktivni=True,
        )
        _polozka(fio_id='fio:ap-empty')
        result = apply_pravidlo_to_nezarazene(rule)
        self.assertEqual(result['updated'], 0)

    def test_presne_nechyti_najem_s_codaruina_ve_zprave(self):
        rule = FioKategorizacniPravidlo.objects.create(
            zprava_obsahuje='Codaruina s.r.o.',
            text_shoda=FioKategorizacniPravidlo.TEXT_SHODA_PRESNE,
            ignorovat=True,
            aktivni=True,
        )
        prevod = _polozka(
            zprava='Codaruina s.r.o.',
            popis='Codaruina s.r.o.',
            fio_id='fio:ap-cod-prevod',
        )
        najem = _polozka(
            zprava='Codaruina s.r.o.',
            popis='Vsetín - nájem',
            fio_id='fio:ap-cod-najem',
        )
        result = apply_pravidlo_to_nezarazene(rule)
        self.assertEqual(result['updated'], 1)
        prevod.refresh_from_db()
        najem.refresh_from_db()
        self.assertTrue(prevod.ignorovat)
        self.assertEqual(najem.stav, NakladPolozka.STAV_NEZARAZENO)

    def test_preview_nezarazene(self):
        rule = FioKategorizacniPravidlo.objects.create(
            zprava_obsahuje='ossz',
            kategorie=self.kat,
            aktivni=True,
        )
        _polozka(popis='OSSZ splátka', fio_id='fio:pv1')
        _polozka(
            popis='OSSZ splátka',
            fio_id='fio:pv2',
            stav=NakladPolozka.STAV_ZARAZENO,
            kategorie=self.kat,
        )
        result = preview_pravidlo(rule, scope='nezarazene', limit=10)
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['total_vse_odchozi'], 2)
        self.assertEqual(len(result['polozky']), 1)


class ApplyPravidloApiTests(TestCase):
    def setUp(self):
        self.admin = WebUser.objects.create(
            id=9310,
            uzivatelske_jmeno='finapply',
            jmeno='Admin',
            prijmeni='Fin',
            heslo='x',
            role='ADMIN',
            aktivni=True,
            moduly=[],
        )
        self.factory = APIRequestFactory()
        self.kat = NakladKategorie.objects.create(nazev='IT apply api')
        self.rule = FioKategorizacniPravidlo.objects.create(
            vs='4242',
            kategorie=self.kat,
            aktivni=True,
        )
        _polozka(vs='4242', fio_id='fio:api-ap1')

    def _auth(self, request):
        force_authenticate(request, user=self.admin)
        return request

    def test_apply_one(self):
        request = self._auth(self.factory.post(f'/finance/pravidla/{self.rule.id}/apply/'))
        resp = views.pravidlo_apply(request, pravidlo_id=self.rule.id)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['updated'], 1)
        p = NakladPolozka.objects.get(fio_id='fio:api-ap1')
        self.assertEqual(p.kategorie_id, self.kat.id)

    def test_apply_empty_rule_400(self):
        rule = FioKategorizacniPravidlo.objects.create(kategorie=self.kat, aktivni=True)
        request = self._auth(self.factory.post(f'/finance/pravidla/{rule.id}/apply/'))
        resp = views.pravidlo_apply(request, pravidlo_id=rule.id)
        self.assertEqual(resp.status_code, 400)

    def test_preview_api(self):
        request = self._auth(self.factory.post(
            '/finance/pravidla/preview/',
            {'pravidlo_id': self.rule.id, 'scope': 'nezarazene'},
            format='json',
        ))
        resp = views.pravidlo_preview(request)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['total'], 1)
        self.assertEqual(resp.data['polozky'][0]['vs'], '4242')

    def test_apply_all(self):
        request = self._auth(self.factory.post('/finance/pravidla/apply-all/'))
        resp = views.pravidla_apply_all(request)
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.data['updated'], 1)
