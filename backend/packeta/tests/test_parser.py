from django.test import TestCase

from packeta.packeta_parser import normalize_zasilka, parse_packeta_csv


class NormalizeZasilkaTests(TestCase):
    def test_removes_all_spaces(self):
        self.assertEqual(normalize_zasilka('Z 432 5018 333'), 'Z4325018333')
        self.assertEqual(normalize_zasilka('Z4325018333'), 'Z4325018333')
        self.assertEqual(normalize_zasilka('  Z 123 456 789  '), 'Z123456789')


class ParsePacketaCsvTests(TestCase):
    def test_import_normalizes_zasilka(self):
        csv = (
            'Datum a čas;Zásilka;Typ provize;Částka;Měna;Poznámka\n'
            '3. 7. 2026, 08:43;"Z 432 5018 333";Podání C2C;10,00;Kč;\n'
        )
        rows = parse_packeta_csv(csv)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['zasilka'], 'Z4325018333')
        self.assertEqual(rows[0]['zasilka_raw'], 'Z 432 5018 333')
