"""Rozhodnutí o bodu za kategorii a seskupení nálezů."""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from plans.kategorie_zbozi import (
    BODY_ZA_KATEGORII,
    aplikuj_vysledek,
    body_podle_uzivatele,
    kategorie_splnuje_plan,
    moje_body,
    oznac_audit,
    rozhodni_kategorii,
    seskup_podle_kodu,
    zapis_odmenu,
    zrus_claim,
)
from plans.models import KategorieZboziClaim
from shifts.models import MzdovaOdmenaMesic
from users.models import WebUser


class RozhodniTests(SimpleTestCase):
    def test_pracovni_presun_neda_body(self):
        stav, _ = rozhodni_kategorii('Nově naskladněno', '', 'Zakládání', '')
        self.assertEqual(stav, 'nepotvrzeno')

    def test_beze_zmeny(self):
        stav, _ = rozhodni_kategorii('Nově naskladněno', 'Bajtek', 'Nově naskladněno', 'Bajtek')
        self.assertEqual(stav, 'nepotvrzeno')

    def test_skla_jsou_plan(self):
        stav, _ = rozhodni_kategorii('Nově naskladněno', '', 'PŘÍSLUŠENSTVÍ', 'Skla a fólie')
        self.assertEqual(stav, 'potvrzeno')
        self.assertTrue(kategorie_splnuje_plan('PŘÍSLUŠENSTVÍ', 'Skla a fólie'))

    def test_prislusenstvi_zbytek_je_plan(self):
        self.assertTrue(kategorie_splnuje_plan('PŘÍSLUŠENSTVÍ', 'Zboží s recyklačním poplatkem'))

    def test_nahodna_kategorie_neni_plan(self):
        stav, _ = rozhodni_kategorii('Nově naskladněno', '', 'Něco jiného', '')
        self.assertEqual(stav, 'nepotvrzeno')
        self.assertFalse(kategorie_splnuje_plan('Něco jiného', ''))

    def test_konflikt_zustava_ve_fronte(self):
        stav, poznamka = rozhodni_kategorii('Nově naskladněno', '', '', '', konflikt=True)
        self.assertEqual(stav, 'ceka')
        self.assertIn('dvě', poznamka)

    def test_seskupeni_na_jeden_radek(self):
        radky = seskup_podle_kodu([
            {
                'kod': 'P1', 'nazev': 'HAD', 'kategorie': 'A', 'kategorie_1': '',
                'nalezy': 2, 'kusy': 2, 'posledni_den': None,
            },
            {
                'kod': 'P1', 'nazev': 'HAD dlouhý', 'kategorie': 'B', 'kategorie_1': 'X',
                'nalezy': 18, 'kusy': 18, 'posledni_den': date(2026, 9, 2),
            },
        ])
        self.assertEqual(len(radky), 1)
        self.assertEqual(radky[0]['nalezy'], 20)
        self.assertEqual(radky[0]['kategorie'], 'B')
        self.assertTrue(radky[0]['vice_kategorii'])


class OdmenaTests(TestCase):
    def setUp(self):
        self.user = WebUser.objects.create(
            id=99021,
            uzivatelske_jmeno='kat_zbozi_test',
            jmeno='Kat',
            prijmeni='Test',
            heslo='x',
            role='PRODEJCE',
        )

    def _claim(self):
        return KategorieZboziClaim.objects.create(
            kod='P99021',
            nazev='HAD',
            rok=2026,
            mesic=9,
            user=self.user,
            kategorie_pred='Nově naskladněno',
            kategorie_1_pred='',
        )

    @patch('plans.kategorie_zbozi.aktualizuj_kategorii_kodu', return_value=3)
    def test_potvrzeni_zapise_odmenu(self, _update):
        claim = self._claim()
        stav = aplikuj_vysledek(claim, 'PŘÍSLUŠENSTVÍ', 'Skla a fólie', '')
        claim.refresh_from_db()
        self.assertEqual(stav, 'potvrzeno')
        self.assertEqual(claim.body, Decimal(BODY_ZA_KATEGORII))
        self.assertEqual(MzdovaOdmenaMesic.objects.filter(user=self.user).count(), 1)
        odmena = MzdovaOdmenaMesic.objects.get(user=self.user)
        self.assertEqual(odmena.castka, Decimal('1'))
        self.assertIn('P99021', odmena.poznamka)
        self.assertEqual(odmena.mesic, timezone.localdate().replace(day=1))
        self.assertFalse(claim.prepsano)
        _update.assert_not_called()

    @patch('plans.kategorie_zbozi.aktualizuj_nazev_kodu', return_value=2)
    def test_zmena_nazvu_prepise_oznaceni(self, update):
        claim = self._claim()
        claim.nazev = 'Starý HAD'
        claim.save(update_fields=['nazev'])
        stav = aplikuj_vysledek(claim, 'Nově naskladněno', '', '', nazev='Nový HAD')
        claim.refresh_from_db()
        self.assertEqual(stav, 'nepotvrzeno')
        self.assertEqual(claim.nazev, 'Nový HAD')
        self.assertFalse(claim.prepsano)
        update.assert_called_once_with('P99021', 'Nový HAD')

    def test_beze_zmeny_neprepisuje_databazi(self):
        claim = self._claim()
        stav = aplikuj_vysledek(claim, 'Nově naskladněno', '', '')
        claim.refresh_from_db()
        self.assertEqual(stav, 'nepotvrzeno')
        self.assertFalse(claim.prepsano)

    def test_odskrtnuti_pripise_bod_audit_ho_sebere(self):
        claim = self._claim()
        zapis_odmenu(claim)
        claim.save(update_fields=['odmena', 'body'])
        dnes = timezone.localdate()
        self.assertEqual(moje_body(self.user, dnes.year, dnes.month), 1)
        self.assertEqual(body_podle_uzivatele(dnes, dnes)[self.user.id], 1)

        stav = aplikuj_vysledek(claim, 'Nově naskladněno', '', '')
        claim.refresh_from_db()
        self.assertEqual(stav, 'nepotvrzeno')
        self.assertEqual(claim.body, 0)
        self.assertIsNone(claim.odmena_id)
        self.assertEqual(MzdovaOdmenaMesic.objects.filter(user=self.user).count(), 0)
        self.assertEqual(moje_body(self.user, dnes.year, dnes.month), 0)

    @patch('plans.kategorie_zbozi.aktualizuj_kategorii_kodu', return_value=1)
    def test_potvrzeni_nezdvoji_odmenu(self, _update):
        claim = self._claim()
        zapis_odmenu(claim)
        claim.save(update_fields=['odmena', 'body'])
        stav = aplikuj_vysledek(claim, 'PŘÍSLUŠENSTVÍ', 'Skla a fólie', '')
        claim.refresh_from_db()
        self.assertEqual(stav, 'potvrzeno')
        self.assertEqual(MzdovaOdmenaMesic.objects.filter(user=self.user).count(), 1)
        self.assertEqual(claim.body, Decimal(BODY_ZA_KATEGORII))

    @patch('plans.kategorie_zbozi.aktualizuj_kategorii_kodu', return_value=4)
    def test_prepis_az_po_auditu(self, update):
        claim = self._claim()
        aplikuj_vysledek(claim, 'PŘÍSLUŠENSTVÍ', 'Skla a fólie', 'Fólie')
        claim.refresh_from_db()
        self.assertFalse(claim.prepsano)
        update.assert_not_called()

        oznac_audit([claim.id], True)
        claim.refresh_from_db()
        self.assertTrue(claim.prepsano)
        self.assertTrue(claim.zkontrolovano)
        update.assert_called_once_with('P99021', 'PŘÍSLUŠENSTVÍ', 'Skla a fólie', 'Fólie')

    @patch('plans.kategorie_zbozi.aktualizuj_kategorii_kodu', return_value=2)
    def test_audit_pred_nocni_kontrolou_prepise_po_ni(self, update):
        claim = self._claim()
        claim.zkontrolovano = True
        claim.save(update_fields=['zkontrolovano'])
        aplikuj_vysledek(claim, 'PŘÍSLUŠENSTVÍ', 'Pouzdra a kryty', '')
        claim.refresh_from_db()
        self.assertTrue(claim.prepsano)
        update.assert_called_once_with('P99021', 'PŘÍSLUŠENSTVÍ', 'Pouzdra a kryty', '')

    def test_zruseni_odskrtnuti_odebere_bod(self):
        claim = self._claim()
        zapis_odmenu(claim)
        claim.save(update_fields=['odmena', 'body'])
        self.assertTrue(zrus_claim(self.user, claim.id))
        self.assertFalse(KategorieZboziClaim.objects.filter(id=claim.id).exists())
        self.assertEqual(MzdovaOdmenaMesic.objects.filter(user=self.user).count(), 0)
