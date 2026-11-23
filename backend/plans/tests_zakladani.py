"""Nedostatky týdenního zakládání karet."""
from django.test import TestCase
from rest_framework.test import APIClient

from plans.models import ZakladaniNedostatek
from plans.zakladani import zapis_nedostatek
from users.models import WebUser


class ZapisTests(TestCase):
    def test_stejny_otevreny_zaznam_se_aktualizuje(self):
        prvni, novy = zapis_nedostatek(
            kod='P1', typ='chybejici_kategorie', text='Chybí list A.',
        )
        druhy, novy2 = zapis_nedostatek(
            kod='P1', typ='chybejici_kategorie', text='Chybí list A a B.', nazev='Sklo',
        )
        self.assertTrue(novy)
        self.assertFalse(novy2)
        self.assertEqual(prvni.id, druhy.id)
        self.assertEqual(druhy.text, 'Chybí list A a B.')
        self.assertEqual(druhy.nazev, 'Sklo')
        self.assertEqual(ZakladaniNedostatek.objects.count(), 1)

    def test_vyreseny_se_neznovu_otevira_novym_radkem(self):
        row, _ = zapis_nedostatek(kod='P1', typ='nezname_ceny', text='Není řada.')
        row.stav = ZakladaniNedostatek.STAV_VYRESENO
        row.save(update_fields=['stav'])
        dalsi, novy = zapis_nedostatek(kod='P1', typ='nezname_ceny', text='Pořád není řada.')
        self.assertTrue(novy)
        self.assertNotEqual(row.id, dalsi.id)


class ApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = WebUser.objects.create(
            id=99111, uzivatelske_jmeno='zakl_admin', jmeno='Admin', prijmeni='Test',
            heslo='x', role='ADMIN',
        )
        self.prodejce = WebUser.objects.create(
            id=99112, uzivatelske_jmeno='zakl_prod', jmeno='Prod', prijmeni='Test',
            heslo='x', role='PRODEJCE',
        )

    def test_prodejce_nema_pristup(self):
        self.client.force_authenticate(user=self.prodejce)
        res = self.client.get('/api/kategorie-zbozi/zakladani/')
        self.assertEqual(res.status_code, 403)

    def test_admin_vyresi_zaznam(self):
        self.client.force_authenticate(user=self.admin)
        row, _ = zapis_nedostatek(
            kod='P153734', typ='chybejici_kategorie', text='Chybí Xiaomi Redmi 17C.',
        )
        res = self.client.post(f'/api/kategorie-zbozi/zakladani/{row.id}/vyresit/')
        self.assertEqual(res.status_code, 200)
        row.refresh_from_db()
        self.assertEqual(row.stav, ZakladaniNedostatek.STAV_VYRESENO)
        self.assertEqual(row.vyresil_id, self.admin.id)
        otevrene = self.client.get('/api/kategorie-zbozi/zakladani/')
        self.assertEqual(otevrene.json()['radky'], [])
