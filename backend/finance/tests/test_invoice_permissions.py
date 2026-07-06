"""Přístup prodejců k fakturám – bez Fio pohybů."""
from datetime import date
from decimal import Decimal

from django.test import TestCase

from finance.models import NakladPolozka
from finance.permissions import naklady_qs_for_invoice_user, user_can_upload_doklad
from users.models import WebUser


class InvoicePermissionsTests(TestCase):
    def setUp(self):
        self.admin = WebUser.objects.create(
            id=9201,
            uzivatelske_jmeno='finadmin',
            jmeno='Admin',
            prijmeni='Fin',
            heslo='x',
            role='ADMIN',
            aktivni=True,
            moduly=[],
        )
        self.prodejce = WebUser.objects.create(
            id=9202,
            uzivatelske_jmeno='prodejce2',
            jmeno='Pro',
            prijmeni='Dejce',
            heslo='x',
            role='PRODEJCE',
            prodejna_id=6,
            aktivni=True,
            moduly=[],
        )
        base = dict(
            datum=date(2026, 6, 10),
            rok=2026,
            mesic=6,
            castka=Decimal('-500'),
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            dph_stav=NakladPolozka.DPH_STAV_CEKA,
            prodejna_id=6,
        )
        self.kasa = NakladPolozka.objects.create(
            **base,
            zdroj=NakladPolozka.ZDROJ_SYMPLIO_POKLADNA,
            popis='Manuální výdej',
            fio_id='symplio:6:1',
        )
        self.fio = NakladPolozka.objects.create(
            **base,
            zdroj=NakladPolozka.ZDROJ_FIO,
            popis='FACEBK reklama',
            fio_id='fio:123',
        )

    def test_prodejce_nevidi_fio_v_cekani_na_fakturu(self):
        qs = NakladPolozka.objects.filter(dph_stav=NakladPolozka.DPH_STAV_CEKA)
        visible = list(naklady_qs_for_invoice_user(qs, self.prodejce))
        self.assertIn(self.kasa, visible)
        self.assertNotIn(self.fio, visible)

    def test_admin_vidi_fio(self):
        qs = NakladPolozka.objects.filter(dph_stav=NakladPolozka.DPH_STAV_CEKA)
        visible = list(naklady_qs_for_invoice_user(qs, self.admin))
        self.assertIn(self.kasa, visible)
        self.assertIn(self.fio, visible)

    def test_prodejce_nemuze_nahrat_fakturu_k_fio(self):
        self.assertTrue(user_can_upload_doklad(self.prodejce, self.kasa))
        self.assertFalse(user_can_upload_doklad(self.prodejce, self.fio))

    def test_admin_muze_fio(self):
        self.assertTrue(user_can_upload_doklad(self.admin, self.fio))
