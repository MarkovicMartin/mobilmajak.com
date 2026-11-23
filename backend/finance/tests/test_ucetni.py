"""Účetní předpisy, návrh přijaté FA, výkupy a kontrola před DPH."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from finance import views
from finance.dph_kontrola import kontrola_pred_dph, termin_dph
from finance.models import FinanceDoklad, NakladPolozka
from finance.ucetni_pravidla import klasifikuj_prijatou, klasifikuj_zpravu
from finance.vykupy import priprav_vykupy, zapsat_vykupy
from users.models import WebUser

_MEDIA = '/tmp/mobilmajak-finance-ucetni-test-media'
_NASTAVENI = {
    'typ_dokl': 'FAKTURA',
    'prim_ucet': '321001',
    'znami_dodavatele': [
        {'ico': '12345678', 'nazev': 'Znama firma s.r.o.', 'firma_kod': 'ZNAMA'},
    ],
    'spreadsheet_id': 'sheet',
    'sheet_name': 'MM výkupy',
    'credentials_file': 'secrets/missing.json',
}
_FLEXI = {
    'base_url': 'https://example.flexibee.eu:5434',
    'company': 'test',
    'username': 'u',
    'password': 'p',
    'mode': 'priloha',
}


def _radek(**kwargs):
    base = {
        'datum': '2026-10-04',
        'doklad': 'U1',
        'nazev': 'iPhone 12 bazar',
        'kategorie': 'Bazar',
        'pocet': 1,
        'cena_bez_dph': '1000',
        'cena_s_dph': '1000',
        'nakupni': '700',
        'zisk': '300',
        'stredisko': 'Zlín',
    }
    base.update(kwargs)
    return base


class PravidlaTests(TestCase):
    def test_vyjimky_z_manualu(self):
        valouch = klasifikuj_prijatou(dodavatel='R. Valouchová', ico='12345678', cislo='1')
        self.assertEqual(valouch['akce'], 'pokladna')
        self.assertFalse(valouch['lze_zapsat'])
        bakr = klasifikuj_prijatou(dodavatel='Bakr s.r.o.', cislo='2')
        self.assertEqual(bakr['akce'], 'archiv')
        comgate = klasifikuj_prijatou(dodavatel='Comgate', cislo='3')
        self.assertEqual(comgate['akce'], 'archiv')
        senimo = klasifikuj_prijatou(dodavatel='Senimo', popis='nájem', cislo='4')
        self.assertEqual(senimo['akce'], 'fyzicky')

    def test_ceske_zbozi_znamych(self):
        navrh = klasifikuj_prijatou(
            dodavatel='Znama firma s.r.o.',
            ico='12345678',
            cislo='2026001',
            vs='2026001',
            datum='2026-10-01',
            castka_bez_dph='1000',
            dph_castka='210',
            castka_celkem='1210',
            znamy=True,
            firma_kod='ZNAMA',
        )
        self.assertEqual(navrh['typ'], 'ceske_zbozi')
        self.assertEqual(navrh['ucet_md'], '504001')
        self.assertEqual(navrh['clen_dph'], '40-41')
        self.assertEqual(navrh['clen_kon_vyk'], 'B.2-3. AUTO')
        self.assertTrue(navrh['lze_zapsat'])
        self.assertEqual(navrh['flexi_fields']['protiUcet'], 'code:504001')
        self.assertEqual(navrh['flexi_fields']['datVyst'], '2026-10-01')

    def test_neznamy_dodavatel_se_nezapisuje(self):
        navrh = klasifikuj_prijatou(
            dodavatel='Nova firma',
            ico='87654321',
            cislo='9',
            datum='2026-10-01',
            castka_bez_dph='100',
            dph_castka='21',
            castka_celkem='121',
            znamy=False,
            firma_kod='NOVA',
        )
        self.assertFalse(navrh['lze_zapsat'])
        self.assertEqual(navrh['akce'], 'navrh')
        self.assertIn('Neznámý dodavatel', navrh['duvod'])

    def test_zahranicni_a_prenesena(self):
        foreign = klasifikuj_prijatou(
            dodavatel='Partner',
            dic='PL6792675514',
            cislo='8',
            datum='2026-10-02',
            castka_bez_dph='10',
            dph_castka='2',
            castka_celkem='12',
            znamy=True,
            firma_kod='PARTNER',
        )
        self.assertEqual(foreign['clen_dph'], '05-06, 43-44')
        self.assertEqual(foreign['clen_kon_vyk'], 'A.2.')
        self.assertTrue(foreign['lze_zapsat'])
        prenesena = klasifikuj_prijatou(
            dodavatel='Stavebni',
            ico='11111111',
            popis='přenesená daň',
            cislo='7',
            datum='2026-10-02',
            castka_bez_dph='10',
            dph_castka='0',
            castka_celkem='10',
            znamy=True,
            firma_kod='STAV',
        )
        self.assertEqual(prenesena['clen_dph'], '10-11')
        self.assertEqual(prenesena['clen_kon_vyk'], 'B.1.')
        self.assertFalse(prenesena['lze_zapsat'])

    def test_sluzba_nema_ucet_md(self):
        navrh = klasifikuj_prijatou(
            dodavatel='Pronajem s.r.o.',
            ico='22222222',
            popis='nájem kanceláře',
            cislo='5',
            datum='2026-10-01',
            castka_bez_dph='1000',
            dph_castka='210',
            castka_celkem='1210',
            znamy=True,
            firma_kod='NAJEM',
        )
        self.assertEqual(navrh['typ'], 'ceska_sluzba')
        self.assertEqual(navrh['clen_dph'], '40-41')
        self.assertFalse(navrh['lze_zapsat'])

    def test_posta(self):
        self.assertEqual(klasifikuj_zpravu('Žádost o dovolenou')['komu'], 'R. Bulandr')
        self.assertEqual(klasifikuj_zpravu('Upozornění z datové schránky')['akce'], 'datovka')
        self.assertEqual(klasifikuj_zpravu('Upomínka FA 12')['akce'], 'upominka')
        self.assertEqual(klasifikuj_zpravu('Comgate výpis')['akce'], 'archiv')


class VykupyBazarTests(TestCase):
    def test_jen_telefon_a_mix_a_doprava(self):
        data = priprav_vykupy([
            _radek(),
            _radek(doklad='U2', nazev='Pouzdro', kategorie='Příslušenství', cena_bez_dph='100', cena_s_dph='121', nakupni='40', zisk='60'),
            _radek(doklad='U2', nazev='iPhone 11', cena_bez_dph='800', cena_s_dph='800', nakupni='500', zisk='300'),
            _radek(doklad='U3', nazev='Doprava Zásilkovna', cena_bez_dph='90', cena_s_dph='90', nakupni='0', zisk='90'),
            _radek(doklad='U3', nazev='Samsung bazar', cena_bez_dph='400', cena_s_dph='400', nakupni='200', zisk='200'),
        ])
        self.assertEqual(data['pocet_nula'], 4)
        podle = {row['doklad']: row for row in data['bazary']}
        self.assertEqual(podle['U1']['predpis'], '604200')
        self.assertEqual(podle['U2']['prislusenstvi']['ucet'], '604001')
        self.assertEqual(podle['U2']['prislusenstvi']['kontrolni_hlaseni'], 'A4-5.AUTO')
        self.assertEqual(podle['U3']['doprava_dph'], '0')
        self.assertEqual(data['souhrn']['nakupni_cena'], '1400.00')
        self.assertEqual(data['souhrn']['zisk'], '800.00')

    def test_nejista_polozka_zustava_ve_fronte(self):
        data = priprav_vykupy([
            _radek(doklad='U4', nazev='', cena_bez_dph=None, cena_s_dph=None, nakupni=None, zisk=None),
            _radek(doklad='U4'),
        ])
        navrh = data['bazary'][0]
        self.assertTrue(navrh['nejisty'])
        self.assertEqual(data['nejistych'], 1)

    def test_zapis_tabulky_jen_pres_writer(self):
        calls = {}

        def writer(values, config):
            calls['values'] = values
            calls['sheet'] = config['sheet_name']
            return {'ok': True, 'pocet': len(values)}

        with patch('finance.vykupy.get_ucetni_config', return_value=_NASTAVENI):
            result = zapsat_vykupy([_radek()], writer=writer)
        self.assertEqual(calls['sheet'], 'MM výkupy')
        self.assertEqual(calls['values'][0][1], 'U1')
        self.assertTrue(result['zapis']['ok'])


class DphKontrolaTests(TestCase):
    def test_termin_vikend_na_pondeli(self):
        self.assertEqual(date(2026, 7, 25).weekday(), 5)
        self.assertEqual(termin_dph(2026, 6), date(2026, 7, 27))

    def test_interni_doklady_a_obrat(self):
        report = kontrola_pred_dph(
            rok=2026,
            mesic=10,
            radky=[_radek()],
            prijate_otevrene=0,
            pokladna_pohybu=4,
            vydane_flexi=12,
            prodejnich_dokladu=1,
            priznani='1000',
            vynosy='1000.40',
            cisty_zisk='200',
            allegro='VF-99',
        )
        self.assertEqual(report['interni_doklady'][0]['castka'], '700.00')
        self.assertEqual(report['interni_doklady'][1]['nazev'], 'Provize – zisk z bazarovek')
        self.assertTrue(report['interni_doklady'][2]['castka'].startswith('-'))
        self.assertEqual(report['interni_doklady'][0]['vystaveno'], '2026-10-31')
        self.assertTrue(report['obrat']['sedi'])
        self.assertEqual(report['obrat']['cisty_zisk'], '200.00')
        self.assertEqual(report['allegro']['nova_fa'], 'VF-99')
        self.assertTrue(report['pripraveno'])
        self.assertIn('člověk', report['podani'])

    def test_nesedi_obrat_a_chybi_podklady(self):
        report = kontrola_pred_dph(
            rok=2026,
            mesic=10,
            radky=[],
            prijate_otevrene=2,
            pokladna_pohybu=0,
            vydane_flexi=None,
            prodejnich_dokladu=0,
            priznani='500',
            vynosy='520',
        )
        self.assertFalse(report['pripraveno'])
        self.assertFalse(report['obrat']['sedi'])
        self.assertIn('pohybech', report['obrat']['dalsi_krok'])
        stavy = {row['kod']: row['stav'] for row in report['polozky']}
        self.assertEqual(stavy['prijate'], 'chybi')
        self.assertEqual(stavy['vydane'], 'nezjisteno')


@override_settings(MEDIA_ROOT=_MEDIA)
class ZalozitFlexiTests(TestCase):
    def setUp(self):
        self.admin = WebUser.objects.create(
            id=9501,
            uzivatelske_jmeno='ucetadmin',
            jmeno='Ucet',
            prijmeni='Admin',
            heslo='x',
            role='ADMIN',
            aktivni=True,
            moduly=[],
        )
        self.factory = APIRequestFactory()
        Path(_MEDIA, 'finance').mkdir(parents=True, exist_ok=True)
        self.soubor = Path(_MEDIA, 'finance', 'fa.pdf')
        self.soubor.write_bytes(b'%PDF-1.4')

    def _doklad(self, **kwargs):
        data = dict(
            dodavatel_nazev='Znama firma s.r.o.',
            dodavatel_ico='12345678',
            cislo_faktury='FA-1',
            vs='1010',
            datum_vystaveni=date(2026, 10, 3),
            castka_bez_dph=Decimal('1000.00'),
            dph_castka=Decimal('210.00'),
            castka_celkem=Decimal('1210.00'),
            stav=FinanceDoklad.STAV_KE_KONTROLE,
            soubor='finance/fa.pdf',
        )
        data.update(kwargs)
        return FinanceDoklad.objects.create(**data)

    def _post(self, doklad, body=None):
        request = self.factory.post(
            f'/finance/doklady/{doklad.id}/zalozit-flexi/',
            body or {},
            format='json',
        )
        force_authenticate(request, user=self.admin)
        return views.doklad_zalozit_flexi(request, doklad_id=doklad.id)

    @patch('finance.prijata_navrh.get_ucetni_config', return_value=_NASTAVENI)
    def test_neznamy_zustane_ve_fronte(self, _cfg):
        doklad = self._doklad(dodavatel_nazev='Nova', dodavatel_ico='87654321')
        response = self._post(doklad, {'firma_kod': 'NOVA'})
        self.assertEqual(response.status_code, 400)
        doklad.refresh_from_db()
        self.assertEqual(doklad.stav, FinanceDoklad.STAV_KE_KONTROLE)
        self.assertFalse(doklad.flexi_id)

    @patch('finance.prijata_navrh.FlexiClient')
    @patch('finance.prijata_navrh.is_flexi_sync_enabled', return_value=True)
    @patch('finance.prijata_navrh.get_flexi_config', return_value=_FLEXI)
    @patch('finance.prijata_navrh.get_ucetni_config', return_value=_NASTAVENI)
    def test_znama_firma_zalozí_fa_a_prilohu(self, _cfg, _flexi_cfg, _enabled, client_cls):
        client = MagicMock()
        client.create_faktura_prijata.return_value = {'flexi_id': '77', 'flexi_kod': 'PF1'}
        client.upload_priloha.return_value = {'priloha_id': '9'}
        client_cls.return_value = client
        doklad = self._doklad()
        response = self._post(doklad)
        self.assertEqual(response.status_code, 200, response.data)
        fields = client.create_faktura_prijata.call_args.args[0]
        self.assertEqual(fields['firma'], 'code:ZNAMA')
        self.assertEqual(fields['clenDph'], 'code:40-41')
        self.assertEqual(fields['clenKonVykDph'], 'code:B.2-3. AUTO')
        doklad.refresh_from_db()
        self.assertEqual(doklad.flexi_id, '77')
        self.assertEqual(doklad.stav, FinanceDoklad.STAV_ODESLANO_FLEXI)
        self.assertEqual(doklad.match_detail['ucetni_zapis']['firma_kod'], 'ZNAMA')

    @patch('finance.prijata_navrh.get_ucetni_config', return_value=_NASTAVENI)
    def test_upominka_pro_bajtka(self, _cfg):
        request = self.factory.get('/finance/ucetni/upominka/', {'vs': '555'})
        force_authenticate(request, user=self.admin)
        prazdna = views.ucetni_upominka(request)
        self.assertTrue(prazdna.data['k_bajtkovi'])
        NakladPolozka.objects.create(
            datum=date(2026, 10, 1),
            rok=2026,
            mesic=10,
            castka=Decimal('-100'),
            vs='555',
            zdroj=NakladPolozka.ZDROJ_FIO,
        )
        zaplacena = views.ucetni_upominka(request)
        self.assertTrue(zaplacena.data['zaplaceno'])
        self.assertFalse(zaplacena.data['k_bajtkovi'])

    @patch('finance.views._vydane_flexi', return_value=3)
    @patch('finance.views.nacti_radky_prodeje', create=True)
    def test_dph_endpoint_nevola_flexi_sam(self, _nacti, _flexi):
        with patch('finance.vykupy.nacti_radky_prodeje', return_value=[_radek()]):
            NakladPolozka.objects.create(
                datum=date(2026, 10, 2),
                rok=2026,
                mesic=10,
                castka=Decimal('-50'),
                zdroj=NakladPolozka.ZDROJ_SYMPLIO_POKLADNA,
                fio_id='symplio:ucetni:1',
            )
            request = self.factory.get('/finance/ucetni/dph/', {
                'rok': 2026,
                'mesic': 10,
                'priznani': '10',
                'vynosy': '10',
            })
            force_authenticate(request, user=self.admin)
            response = views.ucetni_dph(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['interni_doklady'][0]['castka'], '700.00')
        self.assertEqual(response.data['termin'], '2026-11-25')
        _flexi.assert_called_once()
