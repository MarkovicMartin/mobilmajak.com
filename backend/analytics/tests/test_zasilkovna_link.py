"""Testy parseru a propojení Zásilkovna."""
from datetime import date, datetime
from decimal import Decimal

from django.test import TestCase

from analytics.zasilkovna_link import (
    LinkedSale,
    baliky_zpracovane_by_prodejce,
    is_plain_z_marker,
    is_z_oznaceno,
    parse_z_note_fields,
    parse_zasilka_from_note,
    prodeje_by_prodejce,
    typ_skupina,
)
from packeta.models import PacketaProvizePolozka


class BalikyZpracovaneTests(TestCase):
    def test_counts_vydane_and_prijate_distinct(self):
        den = date(2026, 7, 1)
        PacketaProvizePolozka.objects.create(
            prodejna_id=3, cas=datetime(2026, 7, 1, 9, 0),
            zasilka='Z1111111111', typ_provize='Podání C2C',
            castka=Decimal('10'), import_batch='t', id_prodejce=10,
        )
        PacketaProvizePolozka.objects.create(
            prodejna_id=3, cas=datetime(2026, 7, 1, 10, 0),
            zasilka='Z2222222222', typ_provize='Zpracování zásilky',
            castka=Decimal('10'), import_batch='t', id_prodejce=10,
        )
        PacketaProvizePolozka.objects.create(
            prodejna_id=3, cas=datetime(2026, 7, 1, 11, 0),
            zasilka='Z1111111111', typ_provize='Zpracování zásilky',
            castka=Decimal('10'), import_batch='t', id_prodejce=10,
        )
        counts = baliky_zpracovane_by_prodejce(den, den)
        self.assertEqual(counts[10], 2)


class ParseZasilkaNoteTests(TestCase):
    def test_plain_z_number(self):
        self.assertEqual(parse_zasilka_from_note('Z123456789'), 'Z123456789')

    def test_z_with_spaces(self):
        self.assertEqual(parse_zasilka_from_note('Z 236 9101 479'), 'Z2369101479')

    def test_zs_prefix(self):
        self.assertEqual(parse_zasilka_from_note('ZS: Z4413642733'), 'Z4413642733')

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
        self.assertEqual(z, 'Z2369101479')
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

    def test_plain_z_on_doklad_counts_as_oznaceno_not_prodej(self):
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
        self.assertEqual(stats[10]['zasilkovna_prodeje'], 0)
        self.assertEqual(stats[10]['zasilkovna_z_bez_cisla'], 1)

    def test_plain_z_never_auto_matches_packeta(self):
        from decimal import Decimal

        from analytics.models import WebProdejeAll
        from analytics.zasilkovna_link import link_sales_to_packeta
        from packeta.models import PacketaProvizePolozka

        den = date(2026, 7, 1)
        PacketaProvizePolozka.objects.create(
            prodejna_id=6,
            cas=datetime(2026, 7, 1, 12, 0),
            zasilka='Z9999999999',
            typ_provize='Zpracování zásilky',
            castka=Decimal('10'),
            import_batch='test',
        )
        WebProdejeAll.objects.create(
            typ=den,
            doklad='32607011005',
            kod='P100',
            nazev='Test',
            pocet_kusu=1,
            cena_ks_vcl_dph=Decimal('100'),
            id_prodejce=7,
            id_prodejny=6,
            stredisko='Test',
            poznamka_dokladu='Z',
        )
        linked, _ = link_sales_to_packeta(den, den, prodejna_id=6)
        self.assertEqual(len(linked), 1)
        self.assertFalse(linked[0].packeta_nalezeno)
        self.assertTrue(linked[0].z_marker)

    def test_sleva_bez_baliku_tracked_separately(self):
        linked = [
            LinkedSale(
                zasilka='', zasilka_raw='', typ_provize=None,
                typ_skupina=None, id_prodejce=10, id_prodejny=5,
                doklad='32607011007', datum_prodeje=date(2026, 7, 2),
                cas_baliku=None, match_source='sleva_fallback',
                packeta_nalezeno=False, z_marker=False,
            ),
        ]
        stats = prodeje_by_prodejce(linked)
        self.assertEqual(stats[10]['zasilkovna_prodeje'], 0)
        self.assertEqual(stats[10]['zasilkovna_sleva_bez_baliku'], 1)


class LinkPacketaFormatTests(TestCase):
    """Párování poznámky a Packeta CSV i při rozdílném formátu mezer."""

    def test_matches_spaced_packeta_to_compact_note(self):
        from decimal import Decimal

        from analytics.models import WebProdejeAll
        from analytics.zasilkovna_link import link_sales_to_packeta
        from packeta.models import PacketaProvizePolozka

        den = date(2026, 7, 3)
        PacketaProvizePolozka.objects.create(
            prodejna_id=3,
            cas=datetime(2026, 7, 3, 8, 43),
            zasilka='Z 432 5018 333',
            zasilka_raw='Z 432 5018 333',
            typ_provize='Podání C2C',
            castka=Decimal('10'),
            import_batch='test',
        )
        WebProdejeAll.objects.create(
            typ=den,
            doklad='32607037001',
            kod='P100',
            nazev='Test',
            pocet_kusu=1,
            cena_ks_vcl_dph=Decimal('100'),
            id_prodejce=42,
            id_prodejny=3,
            stredisko='Test',
            poznamka_dokladu='Z4325018333',
        )
        linked, invalid_z = link_sales_to_packeta(den, den, prodejna_id=3)
        self.assertEqual(invalid_z, [])
        self.assertEqual(len(linked), 1)
        self.assertTrue(linked[0].packeta_nalezeno)
        self.assertEqual(linked[0].zasilka, 'Z4325018333')
        self.assertEqual(linked[0].doklad, '32607037001')


class SpacedZNoteFilterTests(TestCase):
    def test_z_with_space_before_digits_pairs_packeta(self):
        from decimal import Decimal

        from analytics.models import WebProdejeAll
        from analytics.zasilkovna_link import link_sales_to_packeta
        from packeta.models import PacketaProvizePolozka

        den = date(2026, 7, 2)
        PacketaProvizePolozka.objects.create(
            prodejna_id=4,
            cas=datetime(2026, 7, 2, 15, 46),
            zasilka='Z2003703604',
            typ_provize='Podání C2C',
            castka=Decimal('10'),
            import_batch='test',
        )
        WebProdejeAll.objects.create(
            typ=den,
            doklad='32607029008',
            kod='P135760',
            nazev='Test',
            pocet_kusu=1,
            cena_ks_vcl_dph=Decimal('100'),
            id_prodejce=22,
            id_prodejny=4,
            stredisko='Test',
            poznamka_dokladu='Z 200 3703 604',
        )
        WebProdejeAll.objects.create(
            typ=den,
            doklad='32607029008',
            kod='SLEVA',
            nazev='zasilkovna20 20%',
            pocet_kusu=1,
            cena_ks_vcl_dph=Decimal('-20'),
            id_prodejce=22,
            id_prodejny=4,
            stredisko='Test',
            poznamka_dokladu='Z 200 3703 604',
        )
        linked, invalid_z = link_sales_to_packeta(den, den, prodejna_id=4)
        doklad_links = [l for l in linked if l.doklad == '32607029008']
        self.assertEqual(len(doklad_links), 1)
        self.assertEqual(doklad_links[0].match_source, 'poznamka_dokladu')
        self.assertTrue(doklad_links[0].packeta_nalezeno)
        self.assertEqual(doklad_links[0].zasilka, 'Z2003703604')
        self.assertEqual(invalid_z, [])

    def test_spaced_z_vydany_balik(self):
        from decimal import Decimal

        from analytics.models import WebProdejeAll
        from analytics.zasilkovna_link import link_sales_to_packeta
        from packeta.models import PacketaProvizePolozka

        den = date(2026, 7, 5)
        PacketaProvizePolozka.objects.create(
            prodejna_id=4,
            cas=datetime(2026, 7, 5, 10, 16),
            zasilka='Z3836610126',
            typ_provize='Zpracování zásilky',
            castka=Decimal('10'),
            import_batch='test',
        )
        for kod, nazev, cena in (
            ('P140996', 'Obal', Decimal('100')),
            ('SLEVA', 'ZASILKOVNA ZASILKOVNA20', Decimal('-20')),
        ):
            WebProdejeAll.objects.create(
                typ=den,
                doklad='32607059006',
                kod=kod,
                nazev=nazev,
                pocet_kusu=1,
                cena_ks_vcl_dph=cena,
                id_prodejce=22,
                id_prodejny=4,
                stredisko='Test',
                poznamka_dokladu='Z 383 6610 126',
            )
        linked, invalid_z = link_sales_to_packeta(den, den, prodejna_id=4)
        doklad_links = [l for l in linked if l.doklad == '32607059006']
        self.assertEqual(len(doklad_links), 1)
        self.assertEqual(doklad_links[0].match_source, 'poznamka_dokladu')
        self.assertTrue(doklad_links[0].packeta_nalezeno)
        self.assertEqual(doklad_links[0].zasilka, 'Z3836610126')
        self.assertEqual(invalid_z, [])
