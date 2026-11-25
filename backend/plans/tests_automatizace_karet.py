"""Problémy sobotního zpracování karet z !Import / PARTNER PL."""
from django.test import TestCase
from rest_framework.test import APIClient

from plans.automatizace_karet import doplnit_dodavatele, je_skladem, problemy_mereni, zapis_problem
from plans.models import AutomatizaceKaretProblem
from users.models import WebUser


class DodavatelTests(TestCase):
    def test_prazdny_dodavatel_ve_slozce_partner(self):
        self.assertEqual(doplnit_dodavatele(None), {'id': 2, 'nazev': 'PARTNER PL'})
        self.assertEqual(doplnit_dodavatele(''), {'id': 2, 'nazev': 'PARTNER PL'})

    def test_vyplneny_dodavatel_a_jina_slozka_zustavaji(self):
        self.assertIsNone(doplnit_dodavatele(39))
        self.assertIsNone(doplnit_dodavatele(None, kategorie_id=15562))


class MereniTests(TestCase):
    def test_mimo_sklad_se_nezapisuje(self):
        self.assertFalse(je_skladem('0 ks'))
        self.assertFalse(je_skladem('Není skladem'))
        self.assertFalse(je_skladem(''))
        self.assertEqual(problemy_mereni({'kod': 'P1', 'sklad': '0 ks', 'fotek': 0}), [])

    def test_skladem_bez_fotky_a_ceny(self):
        nalez = problemy_mereni({
            'kod': 'P1', 'sklad': '2 ks', 'fotek': 0, 'ceny_prazdne': True,
        })
        typy = [row['typ'] for row in nalez]
        self.assertEqual(typy, ['chybejici_fotka', 'nezname_ceny'])


class ZapisTests(TestCase):
    def test_stejny_otevreny_problem_se_aktualizuje(self):
        prvni, novy = zapis_problem(kod='P1', typ='chybejici_fotka', text='Není fotka.')
        druhy, novy2 = zapis_problem(
            kod='P1', typ='chybejici_fotka', text='Pořád není fotka.', nazev='Kryt',
        )
        self.assertTrue(novy)
        self.assertFalse(novy2)
        self.assertEqual(prvni.id, druhy.id)
        self.assertEqual(druhy.text, 'Pořád není fotka.')
        self.assertEqual(AutomatizaceKaretProblem.objects.count(), 1)


class ApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = WebUser.objects.create(
            id=99121, uzivatelske_jmeno='auto_admin', jmeno='Admin', prijmeni='Test',
            heslo='x', role='ADMIN',
        )
        self.prodejce = WebUser.objects.create(
            id=99122, uzivatelske_jmeno='auto_prod', jmeno='Prod', prijmeni='Test',
            heslo='x', role='PRODEJCE',
        )

    def test_prodejce_nema_pristup(self):
        self.client.force_authenticate(user=self.prodejce)
        res = self.client.get('/api/kategorie-zbozi/automatizace/')
        self.assertEqual(res.status_code, 403)

    def test_admin_vyresi_problem(self):
        self.client.force_authenticate(user=self.admin)
        row, _ = zapis_problem(kod='P9', typ='jine', text='Chybí popis.')
        res = self.client.post(f'/api/kategorie-zbozi/automatizace/{row.id}/vyresit/')
        self.assertEqual(res.status_code, 200)
        row.refresh_from_db()
        self.assertEqual(row.stav, AutomatizaceKaretProblem.STAV_VYRESENO)
        otevrene = self.client.get('/api/kategorie-zbozi/automatizace/')
        self.assertEqual(otevrene.json()['radky'], [])
