"""Testy Flexi párování a sync (bez reálného API)."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from finance.faktura_process import schvalit_doklad
from finance.flexi_sync import resolve_flexi_match_keys, sync_doklad_to_flexi
from finance.models import FinanceDoklad, NakladPolozka


@override_settings(MEDIA_ROOT='/tmp/mobilmajak-finance-flexi-test-media')
class FlexiSyncTests(TestCase):
    def setUp(self):
        self.media = Path('/tmp/mobilmajak-finance-flexi-test-media')
        self.media.mkdir(parents=True, exist_ok=True)
        rel = 'finance/doklady/2026/08/test-fa.pdf'
        dest = self.media / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b'%PDF-1.4 mobilmajak-test')

        self.fio_polozka = NakladPolozka.objects.create(
            datum=date(2026, 1, 23),
            rok=2026,
            mesic=1,
            castka=Decimal('-17750'),
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            dph_stav=NakladPolozka.DPH_STAV_CEKA,
            zdroj=NakladPolozka.ZDROJ_FIO,
            vs='100042023',
            popis='ucetnictvi',
            fio_id='fio:test:1',
        )
        self.fio_doklad = FinanceDoklad.objects.create(
            soubor=rel,
            cislo_faktury='VF1-0004/2023',
            stav=FinanceDoklad.STAV_KE_KONTROLE,
            naklad_polozka=self.fio_polozka,
        )

        self.sym_polozka = NakladPolozka.objects.create(
            datum=date(2026, 6, 10),
            rok=2026,
            mesic=6,
            castka=Decimal('-500'),
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            dph_stav=NakladPolozka.DPH_STAV_CEKA,
            zdroj=NakladPolozka.ZDROJ_SYMPLIO_POKLADNA,
            prodejna_id=6,
            popis='ASWO Czech - zbozi FA2026/001',
            fio_id='symplio:test:flexi1',
        )
        self.sym_doklad = FinanceDoklad.objects.create(
            soubor=rel,
            cislo_faktury='FA2026/001',
            stav=FinanceDoklad.STAV_KE_KONTROLE,
            naklad_polozka=self.sym_polozka,
        )

    def test_resolve_keys_fio_prefers_vs(self):
        keys = resolve_flexi_match_keys(self.fio_doklad, self.fio_polozka)
        self.assertEqual(keys[0]['field'], 'varSym')
        self.assertEqual(keys[0]['value'], '100042023')
        self.assertTrue(any(k['field'] == 'cisDosle' for k in keys))

    def test_resolve_keys_symplio_uses_popis_not_cislo(self):
        keys = resolve_flexi_match_keys(self.sym_doklad, self.sym_polozka)
        self.assertTrue(keys)
        self.assertTrue(all(k['field'] == 'popis' for k in keys))
        self.assertFalse(any(k['field'] == 'cisDosle' for k in keys))
        self.assertEqual(keys[0]['value'], 'ASWO Czech - zbozi FA2026/001')
        self.assertEqual(keys[0]['op'], 'eq')
        self.assertTrue(any(k['op'] == 'like' for k in keys))

    def test_resolve_keys_strips_manualni_vydej_prefix(self):
        self.sym_polozka.popis = 'Manuální výdej PANFICO - servis 202601234'
        self.sym_polozka.save(update_fields=['popis'])
        keys = resolve_flexi_match_keys(self.sym_doklad, self.sym_polozka)
        self.assertEqual(keys[0]['value'], 'PANFICO - servis 202601234')

    @patch('finance.flexi_sync.is_flexi_sync_enabled', return_value=True)
    @patch('finance.flexi_sync.get_flexi_config')
    @patch('finance.flexi_sync.FlexiClient')
    def test_sync_success_via_vs(self, client_cls, get_cfg, _enabled):
        get_cfg.return_value = {
            'base_url': 'https://example.flexibee.eu:5434',
            'company': 'test',
            'username': 'u',
            'password': 'p',
            'mode': 'priloha',
            'typ_dokl': '',
        }
        client = MagicMock()
        client_cls.return_value = client
        client.find_faktura_prijata.return_value = [
            {'id': '166512', 'kod': 'PF400126/24', 'varSym': '100042023', 'cisDosle': 'VF1-0004/2023'},
        ]
        client.upload_priloha.return_value = {'priloha_id': '21', 'status_code': 201}

        result = sync_doklad_to_flexi(self.fio_doklad)
        self.assertTrue(result['ok'])
        self.assertEqual(result['flexi_id'], '166512')
        client.upload_priloha.assert_called_once()
        args, kwargs = client.upload_priloha.call_args
        self.assertEqual(args[0], '166512')
        self.assertEqual(kwargs['content_type'], 'application/pdf')

    @patch('finance.flexi_sync.is_flexi_sync_enabled', return_value=True)
    @patch('finance.flexi_sync.get_flexi_config')
    @patch('finance.flexi_sync.FlexiClient')
    def test_schvalit_sets_odeslano_flexi(self, client_cls, get_cfg, _enabled):
        get_cfg.return_value = {
            'base_url': 'https://example.flexibee.eu:5434',
            'company': 'test',
            'username': 'u',
            'password': 'p',
            'mode': 'priloha',
            'typ_dokl': '',
        }
        client = MagicMock()
        client_cls.return_value = client
        client.find_faktura_prijata.return_value = [{'id': '99', 'kod': 'X'}]
        client.upload_priloha.return_value = {'priloha_id': '1', 'status_code': 201}

        doklad = schvalit_doklad(self.fio_doklad, user_id=1)
        self.assertEqual(doklad.stav, FinanceDoklad.STAV_ODESLANO_FLEXI)
        self.assertEqual(doklad.flexi_id, '99')
        self.assertTrue((doklad.match_detail or {}).get('flexi', {}).get('ok'))

    @patch('finance.flexi_sync.is_flexi_sync_enabled', return_value=True)
    @patch('finance.flexi_sync.get_flexi_config')
    @patch('finance.flexi_sync.FlexiClient')
    def test_schvalit_keeps_schvaleno_on_flexi_miss(self, client_cls, get_cfg, _enabled):
        get_cfg.return_value = {
            'base_url': 'https://example.flexibee.eu:5434',
            'company': 'test',
            'username': 'u',
            'password': 'p',
            'mode': 'priloha',
            'typ_dokl': '',
        }
        client = MagicMock()
        client_cls.return_value = client
        client.find_faktura_prijata.return_value = []

        doklad = schvalit_doklad(self.fio_doklad, user_id=1)
        self.assertEqual(doklad.stav, FinanceDoklad.STAV_SCHVALENO)
        self.assertFalse(doklad.flexi_id)
        self.assertFalse((doklad.match_detail or {}).get('flexi', {}).get('ok'))
