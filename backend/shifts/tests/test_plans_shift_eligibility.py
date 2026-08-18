"""Kdo se započítá do plánů podle směny (brigádník, výpomoc)."""
from datetime import date, time

from django.test import TestCase

from shifts.models import Smena
from shifts.shift_helpers import is_plans_eligible_user, smena_pocita_do_planovych_hodin
from stores.models import Prodejna
from users.models import WebUser


class PlansShiftEligibilityTests(TestCase):
    def setUp(self):
        self.prodejna = Prodejna.objects.create(
            id=9950, nazev='Plan Elig', nazev_kratkiy='PE', aktivni=True,
        )
        self.brig = WebUser.objects.create(
            id=9950,
            uzivatelske_jmeno='brig_plan',
            jmeno='Brig',
            prijmeni='Test',
            heslo='x',
            role='BRIGADNIK',
            aktivni=True,
            prodejna_id=self.prodejna.id,
        )
        self.prodejce = WebUser.objects.create(
            id=9951,
            uzivatelske_jmeno='prod_plan',
            jmeno='Prod',
            prijmeni='Test',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=self.prodejna.id,
        )

    def _smena(self, user, rezim='prodejce', pozice='prodej'):
        return Smena(
            user=user,
            prodejna=self.prodejna,
            datum=date(2026, 7, 10),
            cas_od=time(8, 0),
            cas_do=time(16, 0),
            typ_smeny='prace',
            brigadnik_rezim=rezim,
            pozice_smeny=pozice,
        )

    def test_brigadnik_je_plan_eligible(self):
        self.assertTrue(is_plans_eligible_user(self.brig))

    def test_brigadnik_prodejce_směna_pocita(self):
        self.assertTrue(smena_pocita_do_planovych_hodin(self._smena(self.brig, 'prodejce')))

    def test_brigadnik_vypomoc_směna_ne(self):
        self.assertFalse(smena_pocita_do_planovych_hodin(self._smena(self.brig, 'vypomoc')))

    def test_prodejce_směna_pocita(self):
        self.assertTrue(smena_pocita_do_planovych_hodin(self._smena(self.prodejce)))

    def test_prodejce_vypomoc_pozice_ne(self):
        self.assertFalse(smena_pocita_do_planovych_hodin(
            self._smena(self.prodejce, pozice='vypomoc'),
        ))
