"""Testy osiřelé FA a auto-přiřazení podle VS."""
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from finance.doklady import create_orphan_doklad, try_auto_link_doklad, try_auto_link_polozka
from finance.faktura_extract import _parse_text_fields
from finance.models import FinanceDoklad, NakladPolozka
from finance.services import upsert_fio_row


@override_settings(MEDIA_ROOT='/tmp/mobilmajak-finance-orphan-test-media')
class OrphanDokladTests(TestCase):
    def setUp(self):
        Path('/tmp/mobilmajak-finance-orphan-test-media').mkdir(parents=True, exist_ok=True)

    def _pdf(self, name='fa.pdf'):
        return SimpleUploadedFile(name, b'%PDF-1.4 test', content_type='application/pdf')

    def test_ocr_vs_fallback_from_cislo_faktury(self):
        r = _parse_text_fields('Faktura č. 20260099\nCelkem k úhradě 1 210,00')
        self.assertEqual(r.cislo_faktury, '20260099')
        self.assertEqual(r.vs, '20260099')

    def test_create_orphan_then_auto_link_on_fio(self):
        doklad = FinanceDoklad.objects.create(
            soubor='finance/doklady/x.pdf',
            vs='173982026',
            cislo_faktury='173982026',
            castka_celkem=Decimal('980'),
            stav=FinanceDoklad.STAV_KE_KONTROLE,
        )
        result = upsert_fio_row({
            'fio_id': 'fio-orphan-1',
            'datum': date(2026, 8, 1),
            'castka': Decimal('-980'),
            'popis': 'Dativery',
            'protiucet': '123',
            'vs': '173982026',
            'zprava': 'platba',
        })
        self.assertEqual(result, 'created')
        doklad.refresh_from_db()
        self.assertTrue(doklad.prirazeno_automaticky)
        self.assertIsNotNone(doklad.naklad_polozka_id)
        polozka = doklad.naklad_polozka
        self.assertEqual(polozka.doklad_id, doklad.id)
        self.assertEqual(doklad.stav, FinanceDoklad.STAV_KE_KONTROLE)

    def test_try_auto_link_polozka_direct(self):
        doklad = FinanceDoklad.objects.create(
            soubor='finance/doklady/y.pdf',
            vs='555666',
            stav=FinanceDoklad.STAV_KE_KONTROLE,
        )
        polozka = NakladPolozka.objects.create(
            datum=date(2026, 8, 2),
            rok=2026,
            mesic=8,
            castka=Decimal('-100'),
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            dph_stav=NakladPolozka.DPH_STAV_CEKA,
            zdroj=NakladPolozka.ZDROJ_FIO,
            vs='555666',
            fio_id='fio-orphan-2',
        )
        self.assertTrue(try_auto_link_polozka(polozka))
        doklad.refresh_from_db()
        self.assertTrue(doklad.prirazeno_automaticky)
        self.assertEqual(doklad.naklad_polozka_id, polozka.id)

    def test_create_orphan_doklad_persists(self):
        doklad = create_orphan_doklad(self._pdf())
        self.assertTrue(doklad.soubor)
        self.assertIn(doklad.stav, (
            FinanceDoklad.STAV_CEKA_NA_OCR,
            FinanceDoklad.STAV_KE_KONTROLE,
        ))

    def test_pokladna_links_by_fa_and_popis(self):
        doklad = FinanceDoklad.objects.create(
            soubor='finance/doklady/kasa.pdf',
            cislo_faktury='202601234',
            dodavatel_nazev='PANFICO',
            stav=FinanceDoklad.STAV_KE_KONTROLE,
        )
        polozka = NakladPolozka.objects.create(
            datum=date(2026, 8, 3),
            rok=2026,
            mesic=8,
            castka=Decimal('-500'),
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            dph_stav=NakladPolozka.DPH_STAV_CEKA,
            zdroj=NakladPolozka.ZDROJ_SYMPLIO_POKLADNA,
            popis='Manuální výdej PANFICO - servis 202601234',
            vs='',
            protiucet='',
            fio_id='symplio:orphan-kasa',
        )
        self.assertTrue(try_auto_link_doklad(doklad))
        doklad.refresh_from_db()
        self.assertEqual(doklad.naklad_polozka_id, polozka.id)

    def test_pokladna_no_vs_does_not_use_fio_vs(self):
        doklad = FinanceDoklad.objects.create(
            soubor='finance/doklady/kasa2.pdf',
            cislo_faktury='FA-99',
            stav=FinanceDoklad.STAV_KE_KONTROLE,
        )
        NakladPolozka.objects.create(
            datum=date(2026, 8, 4),
            rok=2026,
            mesic=8,
            castka=Decimal('-99'),
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            zdroj=NakladPolozka.ZDROJ_FIO,
            vs='99',
            fio_id='fio:not-kasa',
        )
        self.assertFalse(try_auto_link_doklad(doklad))
        doklad.refresh_from_db()
        self.assertIsNone(doklad.naklad_polozka_id)
