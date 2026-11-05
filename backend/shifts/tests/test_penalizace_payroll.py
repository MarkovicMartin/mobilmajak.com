"""Výpočet penalizací z provize."""
from decimal import Decimal

from django.test import TestCase

from shifts.models import MzdovaPenalizaceMesic
from shifts.payroll_service import provize_po_penalizaci


class _PenalizaceRow:
    def __init__(self, typ, hodnota, duvod='', zruseno_stitem=False):
        self.typ = typ
        self.hodnota = hodnota
        self.duvod = duvod
        self.zruseno_stitem = zruseno_stitem


class ProvizePenalizaceTests(TestCase):
    def test_legacy_dva_krat_deset_procent(self):
        rows = [_PenalizaceRow('procenta', 10), _PenalizaceRow('procenta', 10)]
        netto, srazka, pct, _detail = provize_po_penalizaci(1000, rows)
        self.assertEqual(netto, Decimal('800'))
        self.assertEqual(srazka, Decimal('200'))
        self.assertEqual(pct, Decimal('20'))

    def test_fixni_body(self):
        rows = [_PenalizaceRow('fixni', 150)]
        netto, srazka, pct, _detail = provize_po_penalizaci(1000, rows)
        self.assertEqual(netto, Decimal('850'))
        self.assertEqual(srazka, Decimal('150'))
        self.assertEqual(pct, Decimal('0'))

    def test_procenta_a_fixni_kombinace(self):
        rows = [
            _PenalizaceRow('procenta', 10),
            _PenalizaceRow('fixni', 100),
        ]
        netto, srazka, pct, _detail = provize_po_penalizaci(1000, rows)
        self.assertEqual(pct, Decimal('10'))
        self.assertEqual(netto, Decimal('800'))
        self.assertEqual(srazka, Decimal('200'))

    def test_model_defaults(self):
        self.assertEqual(MzdovaPenalizaceMesic.TYP_PROCENTA, 'procenta')
        self.assertEqual(MzdovaPenalizaceMesic._meta.get_field('hodnota').default, 10)

    def test_stit_zrusi_deset_procent(self):
        rows = [_PenalizaceRow('procenta', 10, zruseno_stitem=True)]
        netto, srazka, pct, detail = provize_po_penalizaci(1000, rows)
        self.assertEqual(netto, Decimal('1000'))
        self.assertEqual(srazka, Decimal('0'))
        self.assertEqual(pct, Decimal('0'))
        self.assertTrue(detail[0]['zruseno_stitem'])
        self.assertEqual(detail[0]['srazka_body'], 0.0)

    def test_stit_zrusi_jen_prvni_deset_procent(self):
        rows = [
            _PenalizaceRow('procenta', 10, zruseno_stitem=True),
            _PenalizaceRow('procenta', 10),
        ]
        netto, srazka, pct, detail = provize_po_penalizaci(1000, rows)
        self.assertEqual(netto, Decimal('900'))
        self.assertEqual(srazka, Decimal('100'))
        self.assertEqual(pct, Decimal('10'))
        self.assertTrue(detail[0]['zruseno_stitem'])
        self.assertFalse(detail[1]['zruseno_stitem'])

    def test_stit_necha_jinou_srazku(self):
        rows = [
            _PenalizaceRow('procenta', 20, zruseno_stitem=True),
            _PenalizaceRow('fixni', 100, zruseno_stitem=True),
        ]
        netto, srazka, pct, _detail = provize_po_penalizaci(1000, rows)
        self.assertEqual(pct, Decimal('20'))
        self.assertEqual(netto, Decimal('700'))
        self.assertEqual(srazka, Decimal('300'))
