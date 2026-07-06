"""Testy extrakce textu z faktur."""
from django.test import TestCase

from finance.faktura_extract import _parse_text_fields


class FakturaExtractTests(TestCase):
    def test_parse_czech_invoice_text(self):
        text = """
        PANFICO s.r.o.
        IČO: 12345678
        DIČ: CZ12345678
        Faktura č. FA2026/0042
        Základ daně 10 000,00
        DPH 21% 2 100,00
        Celkem k úhradě 12 100,00 Kč
        """
        r = _parse_text_fields(text)
        self.assertEqual(r.dodavatel_ico, '12345678')
        self.assertIn('FA2026', r.cislo_faktury)
        self.assertEqual(r.castka_bez_dph, '10000.00')
        self.assertEqual(r.dph_castka, '2100.00')
        self.assertEqual(r.castka_celkem, '12100.00')
