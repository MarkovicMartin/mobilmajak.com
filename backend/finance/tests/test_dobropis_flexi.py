"""Zápis přijatého dobropisu Partnertele do Flexi – bez reálného API."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from finance import views
from finance.flexi_client import FlexiError, parse_flexi_create_response
from finance.models import FinanceDoklad
from users.models import WebUser

_FLEXI_CFG = {
    'base_url': 'https://example.flexibee.eu:5434',
    'company': 'test',
    'username': 'u',
    'password': 'p',
    'mode': 'priloha',
    'typ_dokl': '',
    'dobropis_firma': '',
    'dobropis_typ_dokl': '',
    'dobropis_popis': '',
    'dobropis_clen_dph': '',
    'dobropis_typ_uc_op': '',
    'dobropis_stat': '',
}


@override_settings(MEDIA_ROOT='/tmp/mobilmajak-finance-dobropis-test-media')
class DobropisFlexiTests(TestCase):
    def setUp(self):
        self.admin = WebUser.objects.create(
            id=9401,
            uzivatelske_jmeno='dobadmin',
            jmeno='Admin',
            prijmeni='Dob',
            heslo='x',
            role='ADMIN',
            aktivni=True,
            moduly=[],
        )
        self.prodejce = WebUser.objects.create(
            id=9402,
            uzivatelske_jmeno='dobprodejce',
            jmeno='Pro',
            prijmeni='Dejce',
            heslo='x',
            role='PRODEJCE',
            prodejna_id=6,
            aktivni=True,
            moduly=[],
        )
        self.factory = APIRequestFactory()

    def _pdf(self, name='dobropis.pdf'):
        return SimpleUploadedFile(name, b'%PDF-1.4 dobropis', content_type='application/pdf')

    def _post(self, user, **fields):
        request = self.factory.post('/finance/dobropisy/', fields, format='multipart')
        force_authenticate(request, user=user)
        return views.dobropisy(request)

    def test_parse_create_response(self):
        parsed = parse_flexi_create_response({
            'winstrom': {
                'success': 'true',
                'results': [{
                    'id': '55',
                    'content': {'faktura-prijata': {'id': '55', 'kod': 'PF401150/26'}},
                }],
            },
        })
        self.assertEqual(parsed['flexi_id'], '55')
        self.assertEqual(parsed['flexi_kod'], 'PF401150/26')

    def test_parse_create_response_rejects_dry_run(self):
        with self.assertRaises(FlexiError):
            parse_flexi_create_response({
                'winstrom': {
                    'success': 'true',
                    'results': [{'id': '-1', 'content': {'faktura-prijata': {'id': '-1'}}}],
                },
            })

    def test_prodejce_nema_pristup(self):
        request = self.factory.get('/finance/dobropisy/')
        force_authenticate(request, user=self.prodejce)
        response = views.dobropisy(request)
        self.assertEqual(response.status_code, 403)

    @patch('finance.dobropis_flexi.is_flexi_sync_enabled', return_value=True)
    @patch('finance.dobropis_flexi.get_flexi_config', return_value=_FLEXI_CFG)
    @patch('finance.dobropis_flexi.FlexiClient')
    def test_admin_vytvori_zaporny_doklad(self, client_cls, _cfg, _enabled):
        client = MagicMock()
        client_cls.return_value = client
        client.find_faktura_prijata.return_value = []
        client.create_faktura_prijata.return_value = {
            'flexi_id': '55',
            'flexi_kod': 'PF401150/26',
        }
        client.upload_priloha.return_value = {'priloha_id': '9', 'status_code': 201}

        response = self._post(
            self.admin,
            file=self._pdf(),
            cislo_faktury='284/11/25/KFDWV',
            datum_vystaveni='2026-11-11',
            castka_celkem='70,30',
        )

        self.assertEqual(response.status_code, 201, getattr(response, 'data', response.status_code))
        self.assertEqual(response.data['flexi_id'], '55')
        self.assertEqual(response.data['druh'], 'dobropis')
        self.assertEqual(response.data['castka_celkem'], '-70.30')
        self.assertEqual(response.data['vs'], '2841125')

        fields = client.create_faktura_prijata.call_args.args[0]
        self.assertEqual(fields['cisDosle'], '284/11/25/KFDWV')
        self.assertEqual(fields['varSym'], '2841125')
        self.assertEqual(fields['firma'], 'code:PARTNER-PL')
        self.assertEqual(fields['typDokl'], 'code:FAKTURA')
        self.assertEqual(fields['popis'], 'ODD zboží EU')
        self.assertEqual(fields['sumZklZakl'], '-70.30')
        self.assertEqual(fields['sumDphZakl'], '-14.76')
        self.assertEqual(fields['sumCelkem'], '-70.30')
        self.assertEqual(fields['clenDph'], 'code:03-04, 43-44')
        client.upload_priloha.assert_called_once()
        find_kwargs = client.find_faktura_prijata.call_args.kwargs
        self.assertEqual(find_kwargs['firma_code'], 'PARTNER-PL')

        doklad = FinanceDoklad.objects.get(pk=response.data['id'])
        self.assertEqual(doklad.stav, FinanceDoklad.STAV_ODESLANO_FLEXI)
        self.assertEqual(doklad.dph_castka, Decimal('-14.76'))

    @patch('finance.dobropis_flexi.is_flexi_sync_enabled', return_value=True)
    @patch('finance.dobropis_flexi.get_flexi_config', return_value=_FLEXI_CFG)
    @patch('finance.dobropis_flexi.FlexiClient')
    def test_existujici_cislo_nevytvori_druhy_zapis(self, client_cls, _cfg, _enabled):
        client = MagicMock()
        client_cls.return_value = client
        client.find_faktura_prijata.return_value = [
            {'id': '245506', 'kod': 'PF400089/26'},
        ]

        response = self._post(
            self.admin,
            file=self._pdf(),
            cislo_faktury='284/11/25/KFDWV',
            datum_vystaveni='2026-11-11',
            castka_celkem='10',
        )

        self.assertEqual(response.status_code, 502)
        client.create_faktura_prijata.assert_not_called()
        self.assertIn('PF400089/26', response.data['error'])
        self.assertFalse(response.data['flexi_id'])


_SAMPLE = """
Invoice VAT WDT correction 100/07/26/KFWZDWV
Refers to: Faktura do WZ - dostawa wewnątrzwspólnotowa 2402/03/25/DWV from Mar 27, 2025
Doc. date: Jul 22, 2026
PARTNER TELE.COM SPÓŁKA
Difference -43,55 0% 0,00 -43,55
Summary -43,55
To pay: -43,55 CZK
"""


class PartnerteleDobropisExtractTests(TestCase):
    def test_vzor_cislo_a_castka(self):
        from finance.dobropis_extract import parse_partnertele_dobropis
        parsed = parse_partnertele_dobropis(_SAMPLE)
        self.assertEqual(parsed.cislo_faktury, '100/07/26/KFWZDWV')
        self.assertNotIn('2402', parsed.cislo_faktury)
        self.assertEqual(parsed.castka_celkem, '-43.55')
        self.assertEqual(parsed.castka_bez_dph, '-43.55')
        self.assertEqual(parsed.dph_castka, '0.00')
        self.assertEqual(parsed.dph_sazba, 0)
        self.assertEqual(parsed.datum_vystaveni, '2026-07-22')
        self.assertEqual(parsed.vs, '1000726')
        self.assertEqual(parsed.chyby, [])

    @override_settings(MEDIA_ROOT='/tmp/mobilmajak-finance-dobropis-test-media')
    @patch('finance.dobropis_flexi.extract_dobropis_file')
    def test_davka_ulozi_ke_kontrole_bez_flexi(self, extract):
        from finance.faktura_extract import FakturaExtracted
        from finance.views import dobropisy

        extract.return_value = (
            FakturaExtracted(
                cislo_faktury='100/07/26/KFWZDWV',
                vs='1000726',
                datum_vystaveni='2026-07-22',
                castka_celkem='-43.55',
                castka_bez_dph='-43.55',
                dph_castka='0.00',
                dph_sazba=0,
                dodavatel_nazev='PARTNER TELE.COM SP. Z O.O. S.K',
            ),
            'text',
            {'method': 'pdf_text'},
        )
        admin = WebUser.objects.create(
            id=9403,
            uzivatelske_jmeno='dobadmin2',
            jmeno='Admin',
            prijmeni='Dob',
            heslo='x',
            role='ADMIN',
            aktivni=True,
            moduly=[],
        )
        factory = APIRequestFactory()
        pdf = SimpleUploadedFile('dobropis.pdf', b'%PDF-1.4 dobropis', content_type='application/pdf')
        request = factory.post('/finance/dobropisy/', {'files': pdf}, format='multipart')
        force_authenticate(request, user=admin)
        response = dobropisy(request)
        self.assertEqual(response.status_code, 201, response.data)
        row = response.data['doklady'][0]
        self.assertEqual(row['cislo_faktury'], '100/07/26/KFWZDWV')
        self.assertEqual(row['castka_celkem'], '-43.55')
        self.assertEqual(row['dph_castka'], '0.00')
        self.assertEqual(row['datum_vystaveni'], '2026-07-22')
        self.assertEqual(row['stav'], FinanceDoklad.STAV_KE_KONTROLE)
        self.assertFalse(row['flexi_id'])

    @override_settings(MEDIA_ROOT='/tmp/mobilmajak-finance-dobropis-test-media')
    @patch('finance.dobropis_flexi.is_flexi_sync_enabled', return_value=True)
    @patch('finance.dobropis_flexi.get_flexi_config', return_value=_FLEXI_CFG)
    @patch('finance.dobropis_flexi.FlexiClient')
    def test_zapis_nula_dph(self, client_cls, _cfg, _enabled):
        from finance.views import dobropis_flexi_retry

        client = MagicMock()
        client_cls.return_value = client
        client.find_faktura_prijata.return_value = []
        client.create_faktura_prijata.return_value = {'flexi_id': '77', 'flexi_kod': 'PF9/26'}
        client.upload_priloha.return_value = {'priloha_id': '3'}

        media = Path('/tmp/mobilmajak-finance-dobropis-test-media')
        media.mkdir(parents=True, exist_ok=True)
        rel = 'finance/doklady/dobropis.pdf'
        dest = media / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b'%PDF-1.4')
        doklad = FinanceDoklad.objects.create(
            soubor=rel,
            cislo_faktury='100/07/26/KFWZDWV',
            vs='1000726',
            datum_vystaveni=date(2026, 7, 22),
            castka_celkem=Decimal('-43.55'),
            castka_bez_dph=Decimal('-43.55'),
            dph_castka=Decimal('0.00'),
            dph_sazba=0,
            druh=FinanceDoklad.DRUH_DOBROPIS,
            stav=FinanceDoklad.STAV_KE_KONTROLE,
            match_detail={'popis': 'ODD zboží EU', 'firma': 'PARTNER-PL'},
        )
        admin = WebUser.objects.create(
            id=9404,
            uzivatelske_jmeno='dobadmin3',
            jmeno='Admin',
            prijmeni='Dob',
            heslo='x',
            role='ADMIN',
            aktivni=True,
            moduly=[],
        )
        request = APIRequestFactory().post(f'/finance/dobropisy/{doklad.id}/flexi/')
        force_authenticate(request, user=admin)
        response = dobropis_flexi_retry(request, doklad.id)
        self.assertEqual(response.status_code, 200, response.data)
        fields = client.create_faktura_prijata.call_args.args[0]
        self.assertEqual(fields['cisDosle'], '100/07/26/KFWZDWV')
        self.assertEqual(fields['sumCelkem'], '-43.55')
        self.assertEqual(fields['sumZklZakl'], '-43.55')
        self.assertEqual(fields['sumDphZakl'], '0.00')

