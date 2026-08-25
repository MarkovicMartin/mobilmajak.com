"""Testy Fio import logiky – odchozí vs příchozí, dph_stav."""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from finance.models import FioKategorizacniPravidlo, NakladKategorie, NakladPolozka
from finance.services import (
    apply_categorization_rules,
    resolve_dph_stav,
    typ_platby_from_castka,
    upsert_fio_row,
)


class TypPlatbyTests(TestCase):
    def test_negative_is_odchozi(self):
        self.assertEqual(typ_platby_from_castka('-500'), NakladPolozka.TYP_PLATBY_ODCHOZI)

    def test_positive_is_prichozi(self):
        self.assertEqual(typ_platby_from_castka('500'), NakladPolozka.TYP_PLATBY_PRICHOZI)


class ResolveDphStavTests(TestCase):
    def setUp(self):
        self.bez = NakladKategorie.objects.create(
            nazev='Mzdy test', typ_dph=NakladKategorie.TYP_DPH_BEZ,
        )
        self.z_faktury = NakladKategorie.objects.create(
            nazev='IT test', typ_dph=NakladKategorie.TYP_DPH_Z_FAKTURY,
        )

    def test_outgoing_z_faktury_ceka(self):
        self.assertEqual(
            resolve_dph_stav(self.z_faktury.id, NakladPolozka.TYP_PLATBY_ODCHOZI),
            NakladPolozka.DPH_STAV_CEKA,
        )

    def test_mzdy_bez_dph(self):
        self.assertEqual(
            resolve_dph_stav(self.bez.id, NakladPolozka.TYP_PLATBY_ODCHOZI),
            NakladPolozka.DPH_STAV_BEZ,
        )

    def test_prichozi_vzdy_bez(self):
        self.assertEqual(
            resolve_dph_stav(self.z_faktury.id, NakladPolozka.TYP_PLATBY_PRICHOZI),
            NakladPolozka.DPH_STAV_BEZ,
        )


class UpsertFioRowTests(TestCase):
    def setUp(self):
        self.kat = NakladKategorie.objects.create(nazev='Energie test')

    def _row(self, castka, fio_id='fio-1'):
        return {
            'fio_id': fio_id,
            'datum': date(2026, 3, 1),
            'castka': Decimal(castka),
            'popis': 'test',
            'protiucet': '123/0100',
            'vs': '42',
            'zprava': 'elektřina',
        }

    def test_outgoing_creates_naklad_ceka_na_fakturu(self):
        result = upsert_fio_row(self._row('-1500'))
        self.assertEqual(result, 'created')
        p = NakladPolozka.objects.get(fio_id='fio-1')
        self.assertEqual(p.typ_platby, NakladPolozka.TYP_PLATBY_ODCHOZI)
        self.assertEqual(p.dph_stav, NakladPolozka.DPH_STAV_CEKA)
        self.assertEqual(p.stav, NakladPolozka.STAV_NEZARAZENO)

    def test_incoming_stored_as_cashflow_not_queue(self):
        result = upsert_fio_row(self._row('2000', fio_id='fio-in'))
        self.assertEqual(result, 'incoming')
        p = NakladPolozka.objects.get(fio_id='fio-in')
        self.assertEqual(p.typ_platby, NakladPolozka.TYP_PLATBY_PRICHOZI)
        self.assertEqual(p.stav, NakladPolozka.STAV_IGNOROVAT)
        self.assertEqual(p.dph_stav, NakladPolozka.DPH_STAV_BEZ)

    def test_skip_duplicate(self):
        upsert_fio_row(self._row('-100'))
        self.assertEqual(upsert_fio_row(self._row('-100')), 'skipped')

    def test_auto_categorize_sets_dph_from_category(self):
        bez = NakladKategorie.objects.create(
            nazev='Odvody test', typ_dph=NakladKategorie.TYP_DPH_BEZ,
        )
        FioKategorizacniPravidlo.objects.create(
            zprava_obsahuje='cssz',
            kategorie=bez,
            aktivni=True,
        )
        upsert_fio_row({
            **self._row('-5000', fio_id='fio-odvody'),
            'zprava': 'Platba CSSZ odvody',
        })
        p = NakladPolozka.objects.get(fio_id='fio-odvody')
        self.assertEqual(p.stav, NakladPolozka.STAV_ZARAZENO)
        self.assertEqual(p.dph_stav, NakladPolozka.DPH_STAV_BEZ)


class ApplyRulesTests(TestCase):
    def test_rule_match_vs(self):
        kat = NakladKategorie.objects.create(nazev='Nájem test')
        FioKategorizacniPravidlo.objects.create(vs='999', kategorie=kat, aktivni=True)
        row = {'protiucet': '', 'vs': '999', 'zprava': '', 'castka': '-10000'}
        cat = apply_categorization_rules(row)
        self.assertEqual(cat['kategorie_id'], kat.id)
        self.assertTrue(cat['zarazeno_automaticky'])

    @patch('finance.fio_client.requests.get')
    def test_fetch_transactions_maps_vs_column5(self, mock_get):
        from finance.fio_client import fetch_transactions

        mock_get.return_value.json.return_value = {
            'accountStatement': {
                'transactionList': {
                    'transaction': [{
                        'column0': {'value': '2026-03-01+01:00'},
                        'column1': {'value': '-1500.00'},
                        'column2': {'value': '1234567890'},
                        'column5': {'value': '100042023'},
                        'column7': {'value': 'Dodavatel FA'},
                        'column10': {'value': 'Dodavatel s.r.o.'},
                        'column16': {'value': 'platba faktury'},
                        'column22': {'value': '999001'},
                    }],
                },
            },
        }
        mock_get.return_value.raise_for_status = lambda: None
        with patch('finance.fio_client.ensure_fio_available'):
            rows = fetch_transactions('token', date(2026, 3, 1), date(2026, 3, 1))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['vs'], '100042023')
        self.assertEqual(rows[0]['protiucet'], '1234567890')
        self.assertNotEqual(rows[0]['vs'], 'Dodavatel s.r.o.')

    @patch('finance.fio_client.requests.get')
    def test_fetch_account_balance_parses_closing(self, mock_get):
        from finance.fio_client import fetch_account_balance

        mock_get.return_value.json.return_value = {
            'accountStatement': {
                'closingBalance': '12345.67',
                'dateEnd': '2026-03-01+01:00',
                'currency': 'CZK',
                'transactionList': {'transaction': []},
            },
        }
        mock_get.return_value.raise_for_status = lambda: None

        with patch('finance.fio_client.ensure_fio_available'):
            bal = fetch_account_balance('fake-token')
        self.assertEqual(bal['castka'], Decimal('12345.67'))
        self.assertEqual(bal['mena'], 'CZK')
