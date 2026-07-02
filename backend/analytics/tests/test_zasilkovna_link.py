"""Testy parseru a propojení Zásilkovna."""
from datetime import date, datetime

from django.test import TestCase

from analytics.zasilkovna_link import (
    LinkedSale,
    is_plain_z_marker,
    is_z_oznaceno,
    parse_z_note_fields,
    parse_zasilka_from_note,
    prodeje_by_prodejce,
    typ_skupina,
)


class ParseZasilkaNoteTests(TestCase):
    def test_plain_z_number(self):
        self.assertEqual(parse_zasilka_from_note('Z123456789'), 'Z 123456789')

    def test_z_with_spaces(self):
        self.assertEqual(parse_zasilka_from_note('Z 236 9101 479'), 'Z 2369101479')

    def test_zs_prefix(self):
        self.assertEqual(parse_zasilka_from_note('ZS: Z4413642733'), 'Z 4413642733')

    def test_rejects_zzs_false_positive(self):
        self.assertIsNone(parse_zasilka_from_note('ZZS Zlínského kraje'))

    def test_empty(self):
        self.assertIsNone(parse_zasilka_from_note(None))
        self.assertIsNone(parse_zasilka_from_note(''))


class PlainZMarkerTests(TestCase):
    def test_plain_z(self):
        self.assertTrue(is_plain_z_marker('Z'))
        self.assertTrue(is_plain_z_marker(' z '))
        self.assertTrue(is_plain_z_marker('ZS: Z'))

    def test_not_plain_z(self):
        self.assertFalse(is_plain_z_marker('Záruka'))
        self.assertFalse(is_plain_z_marker('Z123456789'))

    def test_parse_fields_doklad_priority(self):
        z, source, marker = parse_z_note_fields('Z', 'Z123456789', None)
        self.assertEqual(source, 'poznamka_dokladu')
        self.assertTrue(marker)
        self.assertIsNone(z)

    def test_parse_fields_zasilka_on_doklad(self):
        z, source, marker = parse_z_note_fields('Z 236 9101 479', None, None)
        self.assertEqual(source, 'poznamka_dokladu')
        self.assertEqual(z, 'Z 2369101479')
        self.assertFalse(marker)


class TypSkupinaTests(TestCase):
    def test_vydane(self):
        self.assertEqual(typ_skupina('Zpracování zásilky'), 'vydane')

    def test_prijate(self):
        self.assertEqual(typ_skupina('Podání C2C'), 'prijate')


class ProdejceAggTests(TestCase):
    def test_counts_distinct_doklady(self):
        linked = [
            LinkedSale(
                zasilka='Z 1', zasilka_raw='Z 1', typ_provize='Podání',
                typ_skupina='prijate', id_prodejce=10, id_prodejny=5,
                doklad='A', datum_prodeje=date(2026, 6, 1),
                cas_baliku=datetime(2026, 6, 1, 10), match_source='poznamka',
            ),
            LinkedSale(
                zasilka='Z 2', zasilka_raw='Z 2', typ_provize='Podání',
                typ_skupina='prijate', id_prodejce=10, id_prodejny=5,
                doklad='B', datum_prodeje=date(2026, 6, 2),
                cas_baliku=datetime(2026, 6, 2, 11), match_source='poznamka',
            ),
        ]
        stats = prodeje_by_prodejce(linked)
        self.assertEqual(stats[10]['zasilkovna_prodeje'], 2)
        self.assertEqual(stats[10]['zasilkovna_oznaceno'], 2)

    def test_plain_z_on_doklad_counts_as_oznaceno(self):
        linked = [
            LinkedSale(
                zasilka='', zasilka_raw='', typ_provize=None,
                typ_skupina=None, id_prodejce=10, id_prodejny=5,
                doklad='32607011005', datum_prodeje=date(2026, 7, 1),
                cas_baliku=None, match_source='poznamka_dokladu',
                packeta_nalezeno=False, z_marker=True,
            ),
        ]
        self.assertTrue(is_z_oznaceno(linked[0]))
        stats = prodeje_by_prodejce(linked)
        self.assertEqual(stats[10]['zasilkovna_oznaceno'], 1)
        self.assertEqual(stats[10]['zasilkovna_prodeje'], 1)
