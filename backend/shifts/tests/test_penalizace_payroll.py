"""Výpočet penalizací z provize."""
from decimal import Decimal

from django.test import TestCase

from shifts.models import MzdovaPenalizaceMesic
from shifts.payroll_service import provize_po_penalizaci


class _PenalizaceRow:
    def __init__(self, typ, hodnota, duvod=''):
        self.typ = typ
        self.hodnota = hodnota
        self.duvod = duvod


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
