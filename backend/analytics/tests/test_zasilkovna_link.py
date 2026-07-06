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
    typ_kategorie,
    typ_provize_label,
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
        self.assertEqual(typ_skupina('Podání'), 'prijate')
        self.assertEqual(typ_kategorie('Podání'), 'prijate')

    def test_c2c(self):
        self.assertEqual(typ_skupina('Podání C2C'), 'prijate_c2c')
        self.assertEqual(typ_kategorie('Podání C2C'), 'prijate_c2c')
        self.assertEqual(typ_provize_label('Podání C2C'), 'Příjem C2C')

    def test_cash_collection_vydane(self):
        self.assertEqual(typ_skupina('Cash collection'), 'vydane')
        self.assertEqual(typ_kategorie('Cash collection'), 'vydane_dobirka')
        self.assertEqual(typ_provize_label('Cash collection'), 'Výdej s dobírkou')

    def test_zpracovani_label(self):
        self.assertEqual(typ_provize_label('Zpracování zásilky'), 'Výdej zásilky')


class ProdejceAggTests(TestCase):
    def test_counts_distinct_doklady(self):
        linked = [
            LinkedSale(
                zasilka='Z1', zasilka_raw='Z1', typ_provize='Podání',
                typ_skupina='prijate', id_prodejce=10, id_prodejny=5,
                doklad='A', datum_prodeje=date(2026, 6, 1),
                cas_baliku=datetime(2026, 6, 1, 10), match_source='poznamka',
                packeta_nalezeno=True, packeta_zasilka_znamo=True,
            ),
            LinkedSale(
                zasilka='Z2', zasilka_raw='Z2', typ_provize='Podání C2C',
                typ_skupina='prijate_c2c', id_prodejce=10, id_prodejny=5,
                doklad='B', datum_prodeje=date(2026, 6, 2),
                cas_baliku=datetime(2026, 6, 2, 11), match_source='poznamka_dokladu',
                packeta_nalezeno=False, packeta_zasilka_znamo=True,
            ),
        ]
        stats = prodeje_by_prodejce(linked)
        self.assertEqual(stats[10]['zasilkovna_prodeje'], 2)

    def test_prodej_z_cislem_bez_slevy_a_packety(self):
        linked = [
            LinkedSale(
                zasilka='Z2344733062', zasilka_raw='Z2344733062',
                typ_provize=None, typ_skupina=None, id_prodejce=4, id_prodejny=2,
                doklad='32607022004', datum_prodeje=date(2026, 7, 2),
                cas_baliku=None, match_source='poznamka_dokladu',
                packeta_nalezeno=False, packeta_zasilka_znamo=True, z_marker=False,
            ),
        ]
        stats = prodeje_by_prodejce(linked)
        self.assertEqual(stats[4]['zasilkovna_prodeje'], 1)
        self.assertEqual(stats[4]['zasilkovna_packeta_potvrzene'], 0)

    def test_neexistujici_z_nepocita_se(self):
        linked = [
            LinkedSale(
                zasilka='Z31127521164', zasilka_raw='Z31127521164',
                typ_provize=None, typ_skupina=None, id_prodejce=2, id_prodejny=2,
                doklad='32607065014', datum_prodeje=date(2026, 7, 6),
                cas_baliku=None, match_source='poznamka_dokladu',
                packeta_nalezeno=False, packeta_zasilka_znamo=False, z_marker=False,
            ),
        ]
        stats = prodeje_by_prodejce(linked)
        self.assertEqual(stats.get(2, {}).get('zasilkovna_prodeje', 0), 0)

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
            zasilka='Z4325018333',
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


class CrossDayPacketaMatchTests(TestCase):
    def test_vydej_stejeny_den_jako_prodejka(self):
        """Krumpolc: příjem 30.6., výdej + prodejka 1.7. – páruje se jen provize z 1.7."""
        from decimal import Decimal

        from analytics.models import WebProdejeAll
        from analytics.zasilkovna_link import link_sales_to_packeta
        from packeta.models import PacketaProvizePolozka

        den_prodeje = date(2026, 7, 1)
        PacketaProvizePolozka.objects.create(
            prodejna_id=5,
            cas=datetime(2026, 6, 30, 14, 57),
            zasilka='Z4485275178',
            typ_provize='Podání',
            castka=Decimal('10'),
            import_batch='test',
        )
        PacketaProvizePolozka.objects.create(
            prodejna_id=5,
            cas=datetime(2026, 7, 1, 10, 9),
            zasilka='Z4485275178',
            typ_provize='Cash collection',
            castka=Decimal('4'),
            import_batch='test',
        )
        WebProdejeAll.objects.create(
            typ=den_prodeje,
            doklad='32607016008',
            kod='P132604',
            nazev='Test',
            pocet_kusu=1,
            cena_ks_vcl_dph=Decimal('449'),
            id_prodejce=9,
            id_prodejny=5,
            stredisko='Test',
            poznamka_dokladu='Z 448 5275 178',
            cas_prodeje=datetime.strptime('10:14:52', '%H:%M:%S').time(),
        )
        linked, invalid_z = link_sales_to_packeta(den_prodeje, den_prodeje, prodejna_id=5)
        doklad_links = [l for l in linked if l.doklad == '32607016008']
        self.assertEqual(invalid_z, [])
        self.assertEqual(len(doklad_links), 1)
        self.assertTrue(doklad_links[0].packeta_nalezeno)
        self.assertEqual(doklad_links[0].zasilka, 'Z4485275178')
        self.assertEqual(doklad_links[0].typ_provize, 'Cash collection')
        self.assertEqual(typ_provize_label(doklad_links[0].typ_provize), 'Výdej s dobírkou')

    def test_prijem_jiny_den_páruje_podle_zasilky(self):
        from decimal import Decimal

        from analytics.models import WebProdejeAll
        from analytics.zasilkovna_link import link_sales_to_packeta
        from packeta.models import PacketaProvizePolozka

        den_prodeje = date(2026, 7, 1)
        PacketaProvizePolozka.objects.create(
            prodejna_id=5,
            cas=datetime(2026, 6, 30, 14, 57),
            zasilka='Z4485275178',
            typ_provize='Podání',
            castka=Decimal('10'),
            import_batch='test',
        )
        WebProdejeAll.objects.create(
            typ=den_prodeje,
            doklad='32607016008',
            kod='P132604',
            nazev='Test',
            pocet_kusu=1,
            cena_ks_vcl_dph=Decimal('449'),
            id_prodejce=9,
            id_prodejny=5,
            stredisko='Test',
            poznamka_dokladu='Z 448 5275 178',
        )
        linked, invalid_z = link_sales_to_packeta(den_prodeje, den_prodeje, prodejna_id=5)
        doklad_links = [l for l in linked if l.doklad == '32607016008']
        self.assertEqual(len(doklad_links), 1)
        self.assertTrue(doklad_links[0].packeta_nalezeno)
        self.assertTrue(doklad_links[0].typ_inferovano)
        self.assertEqual(doklad_links[0].typ_provize, 'Zpracování zásilky')
        self.assertEqual(invalid_z, [])


class ProdejZCislemIntegrationTests(TestCase):
    def test_32607022004_nepocita_bez_packety(self):
        from analytics.models import WebProdejeAll
        from analytics.zasilkovna_link import link_sales_to_packeta, prodeje_by_prodejce

        den = date(2026, 7, 2)
        WebProdejeAll.objects.create(
            typ=den,
            doklad='32607022004',
            kod='P137806',
            nazev='Test',
            pocet_kusu=1,
            cena_ks_vcl_dph=Decimal('350'),
            id_prodejce=4,
            id_prodejny=2,
            stredisko='Test',
            poznamka_dokladu='Z 234 4733 062',
        )
        linked, invalid_z = link_sales_to_packeta(den, den, prodejna_id=2)
        stats = prodeje_by_prodejce(linked)
        self.assertEqual(stats.get(4, {}).get('zasilkovna_prodeje', 0), 0)
        self.assertEqual(len(invalid_z), 1)

    def test_32607022004_infers_vydany_typ_z_jineho_dne(self):
        from analytics.models import WebProdejeAll
        from packeta.models import PacketaProvizePolozka

        from analytics.zasilkovna_link import link_sales_to_packeta

        den_prodeje = date(2026, 7, 2)
        PacketaProvizePolozka.objects.create(
            prodejna_id=2,
            cas=datetime(2026, 7, 1, 11, 0),
            zasilka='Z2344733062',
            typ_provize='Zpracování zásilky',
            castka=Decimal('4'),
            import_batch='test',
        )
        WebProdejeAll.objects.create(
            typ=den_prodeje,
            doklad='32607022004',
            kod='P137806',
            nazev='Test',
            pocet_kusu=1,
            cena_ks_vcl_dph=Decimal('350'),
            id_prodejce=4,
            id_prodejny=2,
            stredisko='Test',
            poznamka_dokladu='Z 234 4733 062',
        )
        linked, invalid_z = link_sales_to_packeta(den_prodeje, den_prodeje, prodejna_id=2)
        doklad = [l for l in linked if l.doklad == '32607022004'][0]
        self.assertTrue(doklad.packeta_nalezeno)
        self.assertFalse(doklad.typ_inferovano)
        self.assertEqual(doklad.typ_provize, 'Zpracování zásilky')
        self.assertEqual(typ_provize_label(doklad.typ_provize), 'Výdej zásilky')
        self.assertEqual(invalid_z, [])

    def test_32607022004_podani_pred_prodejkou_inferuje_vydej(self):
        from analytics.models import WebProdejeAll
        from packeta.models import PacketaProvizePolozka

        from analytics.zasilkovna_link import link_sales_to_packeta, prodeje_by_prodejce

        den_prodeje = date(2026, 7, 2)
        PacketaProvizePolozka.objects.create(
            prodejna_id=2,
            cas=datetime(2026, 7, 1, 14, 38),
            zasilka='Z2344733062',
            typ_provize='Podání',
            castka=Decimal('10'),
            import_batch='test',
        )
        WebProdejeAll.objects.create(
            typ=den_prodeje,
            doklad='32607022004',
            kod='P137806',
            nazev='Test',
            pocet_kusu=1,
            cena_ks_vcl_dph=Decimal('350'),
            id_prodejce=4,
            id_prodejny=2,
            stredisko='Test',
            poznamka_dokladu='Z 234 4733 062',
            cas_prodeje=datetime.strptime('11:52:20', '%H:%M:%S').time(),
        )
        linked, invalid_z = link_sales_to_packeta(den_prodeje, den_prodeje, prodejna_id=2)
        doklad = [l for l in linked if l.doklad == '32607022004'][0]
        stats = prodeje_by_prodejce(linked)
        self.assertTrue(doklad.packeta_nalezeno)
        self.assertTrue(doklad.typ_inferovano)
        self.assertEqual(doklad.typ_provize, 'Zpracování zásilky')
        self.assertEqual(typ_provize_label(doklad.typ_provize), 'Výdej zásilky')
        self.assertEqual(stats[4]['zasilkovna_prodeje'], 1)
        self.assertEqual(invalid_z, [])
