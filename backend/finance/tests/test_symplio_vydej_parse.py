"""Testy parsování dodavatele a čísla FA z popisu výdeje pokladny."""
from decimal import Decimal

from django.test import TestCase

from finance.symplio_vydej_parse import parse_symplio_vydej_faktura


class SymplioVydejParseTests(TestCase):
    def test_manualni_vydej_panfico(self):
        r = parse_symplio_vydej_faktura('Manuální výdej PANFICO - servis 202601234', Decimal('-500'))
        self.assertEqual(r['dodavatel_nazev'], 'PANFICO')
        self.assertEqual(r['cislo_faktury'], '202601234')
        self.assertEqual(r['castka_celkem'], '500')

    def test_aswo_zbozi(self):
        r = parse_symplio_vydej_faktura('ASWO Czech - zbozi FA2026/001', Decimal('-1234.50'))
        self.assertEqual(r['dodavatel_nazev'], 'ASWO Czech')
        self.assertEqual(r['cislo_faktury'], 'FA2026/001')
        self.assertEqual(r['castka_celkem'], '1234.50')

    def test_dily_na_konci(self):
        r = parse_symplio_vydej_faktura('MobilParts Olomouc - díly servis 998877', Decimal('-349'))
        self.assertEqual(r['dodavatel_nazev'], 'MobilParts Olomouc')
        self.assertEqual(r['cislo_faktury'], '998877')

    def test_bez_zbozi_klice_none(self):
        self.assertIsNone(parse_symplio_vydej_faktura('Úhrada výkupky V26070012', Decimal('-5000')))

    def test_spotreba_none(self):
        self.assertIsNone(parse_symplio_vydej_faktura('spotřeba kancelář', Decimal('-200')))
