"""Testy nahrávání faktur."""
from datetime import date
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from finance import views
from finance.doklady import link_doklad_to_polozka
from finance.models import FinanceDoklad, NakladPolozka
from finance.permissions import user_can_access_polozka, user_can_edit_doklad
from users.models import WebUser


@override_settings(MEDIA_ROOT='/tmp/mobilmajak-finance-test-media')
class DokladUploadTests(TestCase):
    def setUp(self):
        self.prodejce = WebUser.objects.create(
            id=9102,
            uzivatelske_jmeno='prodejce1',
            jmeno='Pro',
            prijmeni='Dejce',
            heslo='x',
            role='PRODEJCE',
            prodejna_id=6,
            aktivni=True,
            moduly=[],
        )
        self.polozka = NakladPolozka.objects.create(
            datum=date(2026, 6, 10),
            rok=2026,
            mesic=6,
            castka=Decimal('-500'),
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            dph_stav=NakladPolozka.DPH_STAV_CEKA,
            zdroj=NakladPolozka.ZDROJ_SYMPLIO_POKLADNA,
            prodejna_id=6,
            popis='Manuální výdej PANFICO',
            fio_id='symplio:test:1',
        )

    def _pdf(self):
        return SimpleUploadedFile('fa.pdf', b'%PDF-1.4 test', content_type='application/pdf')

    def test_link_doklad_to_polozka(self):
        doklad = link_doklad_to_polozka(
            self.polozka,
            self._pdf(),
            cislo_faktury='FA001',
            castka_bez_dph='400',
            dph_castka='100',
            user_id=self.prodejce.id,
        )
        self.polozka.refresh_from_db()
        self.assertEqual(doklad.cislo_faktury, 'FA001')
        self.assertEqual(self.polozka.dph_stav, NakladPolozka.DPH_STAV_SPAROVANO)
        self.assertEqual(self.polozka.castka_bez_dph, Decimal('400'))

    def test_prodejce_access_own_store(self):
        self.assertTrue(user_can_access_polozka(self.prodejce, self.polozka))

    def test_prodejce_denied_other_store(self):
        other = NakladPolozka.objects.create(
            datum=date(2026, 6, 11),
            rok=2026,
            mesic=6,
            castka=Decimal('-100'),
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            dph_stav=NakladPolozka.DPH_STAV_CEKA,
            zdroj=NakladPolozka.ZDROJ_SYMPLIO_POKLADNA,
            prodejna_id=1,
            popis='test',
            fio_id='symplio:test:2',
        )
        self.assertFalse(user_can_access_polozka(self.prodejce, other))

    def test_duplicate_upload_rejected(self):
        link_doklad_to_polozka(self.polozka, self._pdf())
        with self.assertRaises(ValueError):
            link_doklad_to_polozka(self.polozka, self._pdf())


@override_settings(MEDIA_ROOT='/tmp/mobilmajak-finance-test-media')
class DokladOpravaTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.prodejce = WebUser.objects.create(
            id=9103,
            uzivatelske_jmeno='prodejce-oprava',
            jmeno='Pro',
            prijmeni='Dejce',
            heslo='x',
            role='PRODEJCE',
            prodejna_id=6,
            aktivni=True,
            moduly=[],
        )
        self.admin = WebUser.objects.create(
            id=9104,
            uzivatelske_jmeno='admin-oprava',
            jmeno='Ad',
            prijmeni='Min',
            heslo='x',
            role='ADMIN',
            aktivni=True,
            moduly=[],
        )
        self.polozka = self._polozka(6, 'symplio:oprava:1', NakladPolozka.ZDROJ_SYMPLIO_POKLADNA)
        self.cizi = self._polozka(1, 'symplio:oprava:2', NakladPolozka.ZDROJ_SYMPLIO_POKLADNA)
        self.fio = self._polozka(6, 'fio:oprava:1', NakladPolozka.ZDROJ_FIO)
        self.doklad = self._doklad(self.polozka, FinanceDoklad.STAV_KE_KONTROLE, cislo='FA-1')
        self.schvaleny = self._doklad(self.polozka, FinanceDoklad.STAV_SCHVALENO, cislo='FA-SCH')
        self.zamitnuty = self._doklad(self.polozka, FinanceDoklad.STAV_ZAMITNUTO, cislo='FA-ZAM')
        self.cizi_doklad = self._doklad(self.cizi, FinanceDoklad.STAV_KE_KONTROLE, cislo='FA-CIZI')
        self.fio_doklad = self._doklad(self.fio, FinanceDoklad.STAV_KE_KONTROLE, cislo='FA-FIO')

    def _polozka(self, prodejna_id, fio_id, zdroj):
        return NakladPolozka.objects.create(
            datum=date(2026, 6, 12),
            rok=2026,
            mesic=6,
            castka=Decimal('-200'),
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            dph_stav=NakladPolozka.DPH_STAV_SPAROVANO,
            zdroj=zdroj,
            prodejna_id=prodejna_id,
            popis='Manuální výdej',
            fio_id=fio_id,
        )

    def _doklad(self, polozka, stav, cislo):
        doklad = FinanceDoklad.objects.create(
            stav=stav,
            cislo_faktury=cislo,
            naklad_polozka=polozka,
            soubor='finance/doklady/test.pdf',
        )
        return doklad

    def _auth(self, request, user):
        force_authenticate(request, user=user)
        return request

    def test_prodejce_vidi_sve_neschvalene_a_ne_cizi(self):
        request = self._auth(self.factory.get('/finance/doklady/'), self.prodejce)
        resp = views.doklady_list(request)
        self.assertEqual(resp.status_code, 200)
        ids = {row['id'] for row in resp.data}
        self.assertIn(self.doklad.id, ids)
        self.assertIn(self.zamitnuty.id, ids)
        self.assertNotIn(self.schvaleny.id, ids)
        self.assertNotIn(self.cizi_doklad.id, ids)
        self.assertNotIn(self.fio_doklad.id, ids)
        own = next(row for row in resp.data if row['id'] == self.doklad.id)
        self.assertTrue(own['lze_upravit'])
        self.assertEqual(own['naklad_polozka']['id'], self.polozka.id)

    def test_prodejce_upravi_dokud_neni_schvaleno(self):
        request = self._auth(self.factory.patch(
            f'/finance/doklady/{self.doklad.id}/',
            {'cislo_faktury': 'FA-OPRAVA', 'dodavatel_nazev': 'Panfico'},
            format='json',
        ), self.prodejce)
        resp = views.doklad_update(request, doklad_id=self.doklad.id)
        self.assertEqual(resp.status_code, 200)
        self.doklad.refresh_from_db()
        self.assertEqual(self.doklad.cislo_faktury, 'FA-OPRAVA')
        self.assertEqual(self.doklad.dodavatel_nazev, 'Panfico')
        self.assertTrue(resp.data['lze_upravit'])

    def test_prodejce_neupravi_schvalenou(self):
        self.assertFalse(user_can_edit_doklad(self.prodejce, self.schvaleny))
        request = self._auth(self.factory.patch(
            f'/finance/doklady/{self.schvaleny.id}/',
            {'cislo_faktury': 'HACK'},
            format='json',
        ), self.prodejce)
        resp = views.doklad_update(request, doklad_id=self.schvaleny.id)
        self.assertEqual(resp.status_code, 403)
        self.schvaleny.refresh_from_db()
        self.assertEqual(self.schvaleny.cislo_faktury, 'FA-SCH')

    def test_prodejce_neupravi_cizi_ani_fio(self):
        for doklad in (self.cizi_doklad, self.fio_doklad):
            request = self._auth(self.factory.patch(
                f'/finance/doklady/{doklad.id}/',
                {'cislo_faktury': 'HACK'},
                format='json',
            ), self.prodejce)
            resp = views.doklad_update(request, doklad_id=doklad.id)
            self.assertEqual(resp.status_code, 403)

    def test_admin_neupravi_po_schvaleni(self):
        request = self._auth(self.factory.patch(
            f'/finance/doklady/{self.schvaleny.id}/',
            {'cislo_faktury': 'ADMIN'},
            format='json',
        ), self.admin)
        resp = views.doklad_update(request, doklad_id=self.schvaleny.id)
        self.assertEqual(resp.status_code, 403)

    def test_nahrazeni_souboru_jen_pred_schvalenim(self):
        pdf = SimpleUploadedFile('nova.pdf', b'%PDF-1.4 nova', content_type='application/pdf')
        request = self._auth(self.factory.post(
            f'/finance/doklady/{self.doklad.id}/soubor/',
            {'file': pdf},
            format='multipart',
        ), self.prodejce)
        resp = views.doklad_replace_file(request, doklad_id=self.doklad.id)
        self.assertEqual(resp.status_code, 200)
        self.doklad.refresh_from_db()
        self.assertTrue(self.doklad.soubor.endswith('nova.pdf') or 'nova' in self.doklad.soubor)

        locked = self._auth(self.factory.post(
            f'/finance/doklady/{self.schvaleny.id}/soubor/',
            {'file': SimpleUploadedFile('x.pdf', b'%PDF-1.4', content_type='application/pdf')},
            format='multipart',
        ), self.prodejce)
        denied = views.doklad_replace_file(locked, doklad_id=self.schvaleny.id)
        self.assertEqual(denied.status_code, 403)
