"""Testy parseru a importu Symplio pokladny."""
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.test import TestCase

from finance.models import NakladPolozka
from finance.services import import_symplio_pokladna_file
from finance.symplio_pokladna import (
    is_symplio_vydej,
    parse_symplio_castka,
    parse_symplio_datum,
    parse_symplio_pokladna_xlsx,
    symplio_pokladna_external_id,
)

FIXTURE = Path(__file__).resolve().parent / 'fixtures' / 'symplio_pokladna_sternberk.xlsx'
STERNBERK_PRODEJNA_ID = 6


class SymplioParserTests(TestCase):
    def test_parse_datum(self):
        self.assertEqual(parse_symplio_datum('06. 07. 2026 08:52'), date(2026, 7, 6))

    def test_parse_castka_negative(self):
        self.assertEqual(parse_symplio_castka(-5000), Decimal('-5000'))

    def test_fixture_headers_and_row_count(self):
        rows = parse_symplio_pokladna_xlsx(FIXTURE)
        self.assertEqual(len(rows), 28)
        self.assertEqual(rows[0]['popis'], 'Příjem za prodej zboží')
        self.assertEqual(rows[0]['symplio_doklad'], '32607061003')

    def test_vydeje_are_negative_only(self):
        rows = parse_symplio_pokladna_xlsx(FIXTURE)
        vydeje = [r for r in rows if is_symplio_vydej(r)]
        self.assertEqual(len(vydeje), 4)
        for row in vydeje:
            self.assertLess(row['castka'], 0)

    def test_external_id_with_doklad(self):
        row = {
            'datum': date(2026, 7, 6),
            'castka': Decimal('-349'),
            'popis': 'Storno',
            'objednavka': '',
            'symplio_doklad': '32607061002',
        }
        self.assertEqual(
            symplio_pokladna_external_id(STERNBERK_PRODEJNA_ID, row),
            'symplio:6:32607061002',
        )


class SymplioImportTests(TestCase):
    def test_import_creates_only_vydeje(self):
        result = import_symplio_pokladna_file(FIXTURE, prodejna_id=STERNBERK_PRODEJNA_ID)
        self.assertEqual(result['created'], 4)
        self.assertEqual(result['non_vydej'], 24)
        polozky = NakladPolozka.objects.filter(zdroj=NakladPolozka.ZDROJ_SYMPLIO_POKLADNA)
        self.assertEqual(polozky.count(), 4)
        p = polozky.get(symplio_doklad='32607061002')
        self.assertEqual(p.prodejna_id, STERNBERK_PRODEJNA_ID)
        self.assertTrue(p.ignorovat)
        self.assertEqual(p.dph_stav, NakladPolozka.DPH_STAV_BEZ)
        self.assertEqual(p.typ_platby, NakladPolozka.TYP_PLATBY_ODCHOZI)
        self.assertEqual(p.castka, Decimal('-349'))
        self.assertEqual(p.pokladna_key, '')
        self.assertEqual(p.pokladna_label, '')

    def test_import_stores_pokladna_znacka(self):
        result = import_symplio_pokladna_file(
            FIXTURE,
            prodejna_id=STERNBERK_PRODEJNA_ID,
            pokladna_key='sternberk',
            pokladna_label='Šternberk',
        )
        self.assertEqual(result['created'], 4)
        p = NakladPolozka.objects.get(symplio_doklad='32607061002')
        self.assertEqual(p.pokladna_key, 'sternberk')
        self.assertEqual(p.pokladna_label, 'Šternberk')

    def test_vykupka_without_doklad(self):
        import_symplio_pokladna_file(FIXTURE, prodejna_id=STERNBERK_PRODEJNA_ID)
        p = NakladPolozka.objects.get(popis='Úhrada výkupky V26070012')
        self.assertEqual(p.symplio_doklad, '')
        self.assertEqual(p.castka, Decimal('-5000'))
        self.assertTrue(p.fio_id.startswith('symplio:'))
        self.assertTrue(p.ignorovat)
        self.assertEqual(p.stav, NakladPolozka.STAV_IGNOROVAT)
        self.assertEqual(p.dph_stav, NakladPolozka.DPH_STAV_BEZ)
        self.assertEqual(p.auto_pravidlo, 'symplio:vykup')

    def test_skip_duplicate_on_reimport(self):
        import_symplio_pokladna_file(FIXTURE, prodejna_id=STERNBERK_PRODEJNA_ID)
        result = import_symplio_pokladna_file(FIXTURE, prodejna_id=STERNBERK_PRODEJNA_ID)
        self.assertEqual(result['created'], 0)
        self.assertEqual(result['skipped'], 4)
        self.assertEqual(
            NakladPolozka.objects.filter(zdroj=NakladPolozka.ZDROJ_SYMPLIO_POKLADNA).count(),
            4,
        )

    def test_dry_run_no_db_writes(self):
        result = import_symplio_pokladna_file(
            FIXTURE, prodejna_id=STERNBERK_PRODEJNA_ID, dry_run=True,
        )
        self.assertEqual(result['created'], 4)
        self.assertEqual(NakladPolozka.objects.count(), 0)
