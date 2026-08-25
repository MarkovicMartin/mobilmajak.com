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
        Variabilní symbol: 20260042
        Základ daně 10 000,00
        DPH 21% 2 100,00
        Celkem k úhradě 12 100,00 Kč
        """
        r = _parse_text_fields(text)
        self.assertEqual(r.dodavatel_ico, '12345678')
        self.assertIn('FA2026', r.cislo_faktury)
        self.assertEqual(r.vs, '20260042')
        self.assertEqual(r.castka_bez_dph, '10000.00')
        self.assertEqual(r.dph_castka, '2100.00')
        self.assertEqual(r.castka_celkem, '12100.00')

    def test_parse_vs_variants(self):
        self.assertEqual(_parse_text_fields('VS: 998877').vs, '998877')
        self.assertEqual(_parse_text_fields('Var. symbol 12345').vs, '12345')

    def test_parse_vs_multiline(self):
        text = 'Variabilní symbol\n1234567890\nCelkem k úhradě 1 210,00'
        self.assertEqual(_parse_text_fields(text).vs, '1234567890')

    def test_parse_globus_like_invoice(self):
        """Vzor Globus FA (textová vrstva z PDF)."""
        text = """
        Dodavatel / Lieferant
        Globus ČR, v.o.s.
        DIČ / MWStNr.:  CZ63473291
        IČO:  63473291
        Faktura / Rechnung 30001940
        Variabilní symbol / Zahlungsreferenz 30001940
        Datum splatnosti / Fälligkeitsdatum 07.09.2026
        - období 7/2026
        21% 2 360,66
        Základ
        2 360,66 CZK 21 % 495,74 CZK
        Celkem bez DPH / ohne MWSt.
        Celkem DPH / MWSt.
        2 360,66
        495,74
        Celkem k úhradě
        Zur Zahlung
        CZK
        2 856,40
        """
        r = _parse_text_fields(text)
        self.assertEqual(r.vs, '30001940')
        self.assertEqual(r.cislo_faktury, '30001940')
        self.assertEqual(r.dodavatel_ico, '63473291')
        self.assertEqual(r.dodavatel_dic, 'CZ63473291')
        self.assertEqual(r.castka_bez_dph, '2360.66')
        self.assertEqual(r.dph_castka, '495.74')
        self.assertEqual(r.castka_celkem, '2856.40')
        self.assertIn('Globus', r.dodavatel_nazev)

    def test_parse_faktura_heading_without_number_then_number(self):
        text = (
            'Faktura / Rechnung\nDodavatel / Lieferant\nGlobus ČR, v.o.s.\n'
            'Faktura / Rechnung 30001940\nVariabilní symbol 30001940\n'
            'Celkem k úhradě 2 856,40'
        )
        self.assertEqual(_parse_text_fields(text).cislo_faktury, '30001940')

    def test_parse_amount_thousand_dots(self):
        from finance.faktura_extract import _normalize_amount_str
        self.assertEqual(_normalize_amount_str('1.210,50'), '1210.50')

    def test_ocr_deps_module(self):
        from finance.ocr_deps import check_finance_ocr_deps
        status = check_finance_ocr_deps()
        self.assertIn('text_pdf_ready', status)
        self.assertIn('scan_ocr_ready', status)
