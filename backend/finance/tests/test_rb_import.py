"""Raiffeisen pohyby – stejné náklady jako Fio, převody mezi vlastními účty ignorovat."""
from datetime import date
from decimal import Decimal

from django.test import TestCase

from finance.bank_accounts import mark_internal_transfers, own_account
from finance.models import NakladKategorie, NakladPolozka
from finance.rb_client import map_rb_transaction, parse_rb_date
from finance.services import upsert_fio_row


def _rb_tx(**overrides):
    tx = {
        'entryReference': 'ref1',
        'amount': {'value': 1500, 'currency': 'CZK'},
        'creditDebitIndication': 'DBIT',
        'bookingDate': '2026-10-21T10:00:00+02:00',
        'entryDetails': {
            'transactionDetails': {
                'relatedParties': {
                    'counterParty': {
                        'name': 'Dodavatel s.r.o.',
                        'organisationIdentification': {'bankCode': '0100'},
                        'account': {'accountNumber': '1234567890'},
                    },
                },
                'remittanceInformation': {
                    'creditorReferenceInformation': {'variable': '100042023'},
                    'originatorMessage': 'platba faktury',
                },
            },
        },
    }
    tx.update(overrides)
    return tx


class MapRbTransactionTests(TestCase):
    def test_outgoing_is_negative_and_keeps_vs(self):
        row = map_rb_transaction(_rb_tx(), '1110155', '0155')
        self.assertEqual(row['castka'], Decimal('-1500'))
        self.assertEqual(row['vs'], '100042023')
        self.assertEqual(row['protiucet'], '1234567890/0100')
        self.assertEqual(row['protiucet_banka'], '0100')
        self.assertEqual(row['fio_id'], 'rb:1110155:ref1')
        self.assertEqual(row['account_label'], '0155')
        self.assertEqual(row['datum'], date(2026, 10, 21))

    def test_incoming_is_positive(self):
        row = map_rb_transaction(_rb_tx(creditDebitIndication='CRDT'), '1110155', '0155')
        self.assertEqual(row['castka'], Decimal('1500'))

    def test_non_czk_skipped(self):
        tx = _rb_tx()
        tx['amount'] = {'value': 10, 'currency': 'EUR'}
        self.assertIsNone(map_rb_transaction(tx, '1110155', '0155'))

    def test_utc_evening_is_next_prague_day(self):
        self.assertEqual(parse_rb_date('2026-10-21T22:30:00Z'), date(2026, 10, 22))


class InternalTransferTests(TestCase):
    def setUp(self):
        self.own = [
            own_account('2601110155', '2010'),
            own_account('1112220155', '5500'),
            own_account('3334440630', '5500'),
        ]

    def test_fio_to_raiffeisen_is_internal(self):
        row = {
            'protiucet': '1112220155',
            'protiucet_cislo': '1112220155',
            'protiucet_banka': '5500',
        }
        self.assertEqual(mark_internal_transfers([row], self.own), 1)
        self.assertTrue(row['interni'])

    def test_raiffeisen_to_fio_is_internal(self):
        row = {
            'protiucet_cislo': '2601110155',
            'protiucet_banka': '2010',
        }
        self.assertEqual(mark_internal_transfers([row], self.own), 1)

    def test_between_raiffeisen_accounts_is_internal(self):
        row = {
            'protiucet_cislo': '0003334440630',
            'protiucet_banka': '5500',
        }
        self.assertEqual(mark_internal_transfers([row], self.own), 1)

    def test_supplier_is_not_internal(self):
        row = {
            'protiucet_cislo': '1234567890',
            'protiucet_banka': '0100',
        }
        self.assertEqual(mark_internal_transfers([row], self.own), 0)
        self.assertNotIn('interni', row)


class UpsertBankRowTests(TestCase):
    def test_rb_outgoing_is_naklad_like_fio(self):
        NakladKategorie.objects.create(nazev='Energie rb')
        result = upsert_fio_row({
            'fio_id': 'rb:1:out',
            'datum': date(2026, 10, 1),
            'castka': Decimal('-800'),
            'popis': 'Dodavatel',
            'protiucet': '1234567890/0100',
            'vs': '55',
            'zprava': 'faktura',
            'account_label': '0155',
        }, zdroj=NakladPolozka.ZDROJ_RAIFFEISEN)
        self.assertEqual(result, 'created')
        p = NakladPolozka.objects.get(fio_id='rb:1:out')
        self.assertEqual(p.zdroj, NakladPolozka.ZDROJ_RAIFFEISEN)
        self.assertEqual(p.typ_platby, NakladPolozka.TYP_PLATBY_ODCHOZI)
        self.assertEqual(p.stav, NakladPolozka.STAV_NEZARAZENO)
        self.assertEqual(p.dph_stav, NakladPolozka.DPH_STAV_CEKA)
        self.assertEqual(p.pokladna_label, '0155')

    def test_internal_transfer_is_not_a_cost(self):
        result = upsert_fio_row({
            'fio_id': 'rb:1:move',
            'datum': date(2026, 10, 2),
            'castka': Decimal('-5000'),
            'popis': 'Codaruina',
            'protiucet': '1112220155/2010',
            'vs': '',
            'zprava': 'prevod',
            'interni': True,
            'account_label': '0649',
        }, zdroj=NakladPolozka.ZDROJ_RAIFFEISEN)
        self.assertEqual(result, 'internal')
        p = NakladPolozka.objects.get(fio_id='rb:1:move')
        self.assertEqual(p.stav, NakladPolozka.STAV_IGNOROVAT)
        self.assertEqual(p.typ_platby, NakladPolozka.TYP_PLATBY_INTERNI)
        self.assertTrue(p.ignorovat)
        self.assertEqual(p.auto_pravidlo, 'bank:interni_prevod')
        self.assertEqual(
            NakladPolozka.objects.filter(stav=NakladPolozka.STAV_NEZARAZENO).count(),
            0,
        )

    def test_fio_internal_flag_same_as_rb(self):
        upsert_fio_row({
            'fio_id': 'fio-move',
            'datum': date(2026, 10, 3),
            'castka': Decimal('-5000'),
            'popis': '',
            'protiucet': '1112220155',
            'vs': '',
            'zprava': '',
            'interni': True,
        })
        p = NakladPolozka.objects.get(fio_id='fio-move')
        self.assertEqual(p.zdroj, NakladPolozka.ZDROJ_FIO)
        self.assertEqual(p.typ_platby, NakladPolozka.TYP_PLATBY_INTERNI)
        self.assertEqual(p.stav, NakladPolozka.STAV_IGNOROVAT)
