"""Testy nahrávání faktur."""
from datetime import date
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from finance.doklady import link_doklad_to_polozka
from finance.models import FinanceDoklad, NakladPolozka
from finance.permissions import user_can_access_polozka
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
