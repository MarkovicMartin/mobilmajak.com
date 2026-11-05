"""Úkol na nedokončenou kartu výkupu a měsíční hlášení Bulandrovi."""
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from analytics.models import VykupKartyHlaseni, VykupKartaStav
from analytics.vykup_karty import (
    format_hlaseni,
    karta_je_hotova,
    parse_skladem,
    po_druhem_dni,
    zpracuj,
)
from shifts.models import Smena
from stores.models import Prodejna
from tasks.models import Ukol
from users.models import WebUser


def karta(**kwargs):
    data = {
        'nalezeno': True,
        'photos': 0,
        'params': 0,
        'popis_text_len': 0,
        'popis_ma_obrazek': False,
        'volne': 1,
        'cat': '190',
        'zbozi_id': '154000',
        'nazev': 'Telefon',
    }
    data.update(kwargs)
    return data


class VykupKartyPravidlaTests(TestCase):
    def test_sklad_a_rezervace(self):
        self.assertEqual(parse_skladem('1 ks'), (1, 1))
        self.assertEqual(parse_skladem('0 ks'), (0, 0))
        self.assertEqual(parse_skladem('1 ks (1ks rezervace / 0ks volné)'), (1, 0))

    def test_obrazek_v_popisu_staci(self):
        self.assertTrue(karta_je_hotova(karta(photos=8, params=25, popis_text_len=0, popis_ma_obrazek=True)))
        self.assertFalse(karta_je_hotova(karta(photos=8, params=25, popis_text_len=10, popis_ma_obrazek=False)))
        self.assertFalse(karta_je_hotova(karta(photos=8, params=0, popis_text_len=2000)))

    def test_druhy_den(self):
        pondeli = date(2026, 11, 2)
        self.assertFalse(po_druhem_dni(pondeli, date(2026, 11, 3)))
        self.assertTrue(po_druhem_dni(pondeli, date(2026, 11, 4)))


class VykupKartyUkolyTests(TestCase):
    def setUp(self):
        self.store = Prodejna.objects.create(id=880, nazev='Testovna', nazev_kratkiy='T', aktivni=True)
        self.creator = WebUser.objects.create(
            id=999,
            uzivatelske_jmeno='markovic',
            jmeno='Martin',
            prijmeni='Markovič',
            heslo='x',
            role='ADMIN',
            aktivni=True,
            moduly=[],
        )
        self.seller = WebUser.objects.create(
            id=8801,
            uzivatelske_jmeno='prodejce',
            jmeno='Šimon',
            prijmeni='Gabriel',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            moduly=[],
            prodejna_id=self.store.id,
        )
        self.dnes = date(2026, 11, 5)
        self.ted = timezone.make_aware(datetime(2026, 11, 5, 8, 0))
        Smena.objects.create(
            user=self.seller,
            prodejna=self.store,
            datum=self.dnes,
            cas_od=datetime.strptime('09:00', '%H:%M').time(),
            cas_do=datetime.strptime('18:00', '%H:%M').time(),
            typ_smeny='prace',
            aktivni=True,
        )

    def vykup(self, kod='V26100016', den=None):
        return SimpleNamespace(
            kod=kod,
            vystaveno=den or date(2026, 11, 3),
            nazev='Motorola',
            id_prodejce=self.seller.id,
            id_prodejny=self.store.id,
        )

    def zpracuj(self, vykupy, karty, hlasit=None):
        with patch('tasks.task_create_service.notify_task_lifecycle_change'), \
                patch('analytics.vykup_karty.send_slack_dm', return_value=True) as dm, \
                patch('analytics.vykup_karty.slack_user_id_for_web_user', return_value='USLACK'), \
                patch('analytics.vykup_karty.bulandra_slack_id', return_value='UBUL'):
            result = zpracuj(
                dnes=self.dnes,
                ted=self.ted,
                vykupy=vykupy,
                karty=karty,
                creator=self.creator,
                hlasit_mesic=hlasit,
            )
            result['_dm'] = dm
            return result

    def test_zalozi_ukol_a_podruhe_nic(self):
        result = self.zpracuj([self.vykup()], {'V26100016': karta(volne=1)})
        self.assertEqual(result['due'], ['V26100016'])
        self.assertEqual(len(result['vytvorene']), 1)
        task = Ukol.objects.get(id=result['vytvorene'][0]['ukol_id'])
        self.assertEqual(task.deadline, self.dnes)
        self.assertEqual(task.deadline_cas.strftime('%H:%M'), '15:00')
        self.assertIn('V26100016', task.dod_polozky[0]['text'])
        self.assertIn('kategorie-190/zbozi-154000', task.dod_polozky[0]['text'])
        znovu = self.zpracuj([self.vykup()], {'V26100016': karta(volne=1)})
        self.assertEqual(znovu['due'], [])
        self.assertEqual(Ukol.objects.filter(ukol='Chybějící karty').count(), 1)

    def test_neni_skladem_ani_brzy(self):
        mimo = self.zpracuj([self.vykup()], {'V26100016': karta(stock_text='0 ks', volne=None)})
        self.assertEqual(mimo['due'], [])
        rezervace = self.zpracuj(
            [self.vykup('V26100160')],
            {'V26100160': karta(stock_text='1 ks (1ks rezervace / 0ks volné)', volne=None)},
        )
        self.assertEqual(rezervace['due'], [])
        brzy = self.zpracuj([self.vykup(den=date(2026, 11, 4))], {'V26100016': karta()})
        self.assertEqual(brzy['due'], [])
        self.assertEqual(Ukol.objects.count(), 0)

    def test_hlaseni_jednou(self):
        hotova = karta(photos=8, params=25, popis_text_len=0, popis_ma_obrazek=True, volne=1)
        nedokoncena = karta(volne=1, nazev='iPhone')
        result = self.zpracuj(
            [self.vykup('V26100001', date(2026, 10, 10)), self.vykup('V26100002', date(2026, 10, 11))],
            {'V26100001': hotova, 'V26100002': nedokoncena},
            hlasit='2026-10',
        )
        self.assertEqual(result['hlaseni']['stav'], 'odeslano')
        self.assertEqual(result['hlaseni']['pocet'], 1)
        text = result['_dm'].call_args[0][1]
        self.assertIn('říjen 2026', text)
        self.assertIn('Šimon Gabriel: 1', text)
        self.assertIn('V26100002', text)
        self.assertNotIn('V26100001', text)
        znovu = self.zpracuj(
            [self.vykup('V26100002', date(2026, 10, 11))],
            {'V26100002': nedokoncena},
            hlasit='2026-10',
        )
        self.assertEqual(znovu['hlaseni']['stav'], 'uz_odeslano')
        self.assertEqual(VykupKartyHlaseni.objects.get(mesic='2026-10').pocet, 1)

    def test_format_prazdneho_mesice(self):
        text = format_hlaseni('2026-11', [])
        self.assertIn('Celkem: 0', text)
        self.assertIn('listopad 2026', text)
