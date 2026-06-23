from decimal import Decimal

from django.test import TestCase

from analytics.models import SkladVydejka, SkladVydejkaPolozka, WebProdejeAll
from analytics.sklad_vydejky_parse import (
    parse_doklad_xlsx_row,
    parse_polozka_html_cells,
    resolve_subtype,
)
from analytics.vydejky import list_vydejky, vydejky_queryset_for_month, vydejky_totals


class SkladVydejkyParseTests(TestCase):
    def test_resolve_subtype_rucni_hlavni(self):
        self.assertEqual(resolve_subtype('Vyskladnění z hlavního skladu - ruční'), 20)

    def test_resolve_subtype_spotreba_komisni(self):
        self.assertEqual(resolve_subtype('Vyskladnění z komisního skladu - spotřeba'), 254)

    def test_parse_doklad_xlsx_row(self):
        row = [
            'Výdejka S202681000108',
            'Vyskladnění z hlavního skladu - ruční',
            '32601256003',
            'Krumpolc Jan',
            '7. 1. 2026',
            None,
            None,
            '-65,09',
            '-53,79',
        ]
        parsed = parse_doklad_xlsx_row(row)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['doklad'], 'S202681000108')
        self.assertEqual(parsed['symplio_subtype'], 20)
        self.assertEqual(parsed['duvod_kategorie'], 'rucni')
        self.assertEqual(parsed['sklad_typ'], 'hlavni')
        self.assertEqual(parsed['spravce'], 'Krumpolc Jan')
        self.assertEqual(parsed['vazba'], '32601256003')

    def test_parse_doklad_xlsx_skips_other_subtype(self):
        row = [
            'Výdejka S999',
            'Vyskladnění z hlavního skladu - pokladna',
            '',
            'X',
            '1. 1. 2026',
        ]
        self.assertIsNone(parse_doklad_xlsx_row(row))

    def test_parse_polozka_html_cells(self):
        cells = [
            '7. 1. 2026',
            'P141931',
            'Pouzdro',
            'S202681000108',
            '',
            '',
            '2',
            '21 %',
            '10,00',
            '8,26',
            '16,52',
        ]
        parsed = parse_polozka_html_cells(cells)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['doklad'], 'S202681000108')
        self.assertEqual(parsed['kod'], 'P141931')
        self.assertEqual(parsed['pocet_kusu'], 2)


class VydejkyServiceTests(TestCase):
    def setUp(self):
        SkladVydejka.objects.create(
            doklad='S202681000108',
            vystaveno='2026-01-07',
            symplio_subtype=20,
            duvod_vyskladneni='Vyskladnění z hlavního skladu - ruční',
            sklad_typ='hlavni',
            duvod_kategorie='rucni',
            spravce='Krumpolc Jan',
            vazba='32601256003',
            castka_s_dph=Decimal('-65.09'),
            castka_bez_dph=Decimal('-53.79'),
        )
        SkladVydejkaPolozka.objects.create(
            doklad_id='S202681000108',
            kod='P141931',
            nazev='Pouzdro',
            pocet_kusu=2,
            cena_ks_bez_dph=Decimal('8.26'),
            cena_celkem_bez_dph=Decimal('16.52'),
            vystaveno='2026-01-07',
        )
        SkladVydejka.objects.create(
            doklad='S999999999999',
            vystaveno='2026-01-08',
            symplio_subtype=99,
            duvod_vyskladneni='Jiný typ',
            sklad_typ='hlavni',
            duvod_kategorie='rucni',
            castka_s_dph=Decimal('-1'),
            castka_bez_dph=Decimal('-1'),
        )
        WebProdejeAll.objects.create(
            typ='2026-01-05',
            doklad='32601256003',
            kod='P141931',
            nazev='Pouzdro',
            pocet_kusu=2,
            cena_ks_vcl_dph=Decimal('65.09'),
            id_prodejce=5,
        )

    def test_queryset_filters_allowed_subtypes(self):
        qs = vydejky_queryset_for_month(2026, 1)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().doklad, 'S202681000108')

    def test_list_vydejky_with_polozky_and_vazba(self):
        qs = vydejky_queryset_for_month(2026, 1)
        rows = list_vydejky(qs)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['doklad'], 'S202681000108')
        self.assertEqual(row['duvod_kategorie'], 'rucni')
        self.assertTrue(row['vazba_nalezena'])
        self.assertEqual(row['vazba_doklad'], '32601256003')
        self.assertEqual(len(row['polozky']), 1)
        self.assertEqual(row['polozky'][0]['kod'], 'P141931')
        self.assertEqual(row['polozky'][0]['kusy'], 2)

    def test_list_vydejky_filter_duvod(self):
        SkladVydejka.objects.create(
            doklad='S202681000200',
            vystaveno='2026-01-10',
            symplio_subtype=204,
            duvod_vyskladneni='Vyskladnění z hlavního skladu - spotřeba',
            sklad_typ='hlavni',
            duvod_kategorie='spotreba',
            castka_s_dph=Decimal('-10'),
            castka_bez_dph=Decimal('-8'),
        )
        qs = vydejky_queryset_for_month(2026, 1)
        rows = list_vydejky(qs, duvod_kategorie='spotreba')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['doklad'], 'S202681000200')

    def test_vydejky_totals(self):
        qs = vydejky_queryset_for_month(2026, 1)
        totals = vydejky_totals(qs)
        self.assertEqual(totals['doklady'], 1)
        self.assertEqual(totals['polozky'], 1)
