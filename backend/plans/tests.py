"""
Testy modulu plánů – 3m průměr, auto přiřazení prodejců, Vychodil.
"""
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase

from plans.plneni import mesice_pred_planem, _prev_month
from plans.historie_3m import historie_3m_nahled, vypocitej_plan_z_3_mesicu
from plans.historie import ChybejiciDataError, vypocitej_plan_z_baseline
from plans.prodejci_auto import (
    VYCHODIL_USER_ID,
    _hlavni_prodejce_id,
    _prirad_prodejce_prodejna,
    prirad_prodejce_automaticky,
)
from plans.models import PlanMonth, PlanStore, PlanCategory, PlanProdejce
from stores.models import Prodejna
from users.models import WebUser


class MesicePredPlanemTests(TestCase):
    def test_tri_mesice_pred_cervnem(self):
        months = mesice_pred_planem(2026, 6, 3)
        self.assertEqual(months, [(2026, 3), (2026, 4), (2026, 5)])

    def test_prev_month_leden(self):
        self.assertEqual(_prev_month(2026, 1), (2025, 12))


class Historie3mTests(TestCase):
    @patch('plans.historie_3m.plneni_celkem_firma_za_obdobi')
    @patch('plans.historie_3m.plneni_prodejny_za_obdobi')
    @patch('plans.historie_3m.plneni_firma_za_obdobi')
    @patch('plans.historie_3m.Prodejna.get_aktivni_prodejny')
    def test_nahled_aplikuje_rust(
        self, mock_aktivni, mock_firma_kat, mock_prodejny, mock_celkem
    ):
        mock_celkem.return_value = {
            'obrat': Decimal('1000000'),
            'kusy': 100,
            'pocet_mesicu': 3,
        }
        mock_prodejny.return_value = {1: {'obrat': Decimal('1000000'), 'kusy': 100, 'kategorie': {}}}
        mock_firma_kat.return_value = {'NOVE_TELEFONY': {'obrat': Decimal('500000'), 'kusy': 50}}
        p = MagicMock(id=1, nazev='Test')
        mock_aktivni.return_value = [p]

        nahled = historie_3m_nahled(2026, 6, 10)
        self.assertEqual(nahled['obrat_prumer_3m'], 1000000.0)
        self.assertEqual(nahled['navrh_obrat'], 1100000.0)
        self.assertEqual(len(nahled['mesice']), 3)

    @patch('plans.historie_3m.vypocitej_plan_z_baseline')
    @patch('plans.historie_3m.plneni_celkem_firma_za_obdobi')
    @patch('plans.historie_3m.plneni_prodejny_za_obdobi')
    @patch('plans.historie_3m.plneni_firma_za_obdobi')
    def test_vypocet_volá_baseline(self, mock_fk, mock_pd, mock_celkem, mock_baseline):
        mock_celkem.return_value = {'obrat': Decimal('900000'), 'pocet_mesicu': 3}
        mock_pd.return_value = {}
        mock_fk.return_value = {}
        mock_baseline.return_value = (Decimal('990000'), [])

        result = vypocitej_plan_z_3_mesicu(2026, 6, 10)
        self.assertEqual(result[0], Decimal('990000'))
        mock_baseline.assert_called_once()


class ProdejciAutoTests(TestCase):
    def setUp(self):
        self.prodejna = Prodejna.objects.create(
            nazev='Test Globus Plans', nazev_kratkiy='TG', barva='#000000', aktivni=True,
        )
        pid = self.prodejna.id
        self.hlavni = WebUser.objects.create(
            id=201, uzivatelske_jmeno='hlavni_plans', jmeno='Hlavní', prijmeni='Prodejce',
            role='PRODEJCE', prodejna_id=pid, aktivni=True,
        )
        self.hlavni.set_heslo('x')
        self.hlavni.save()
        self.brigadnik = WebUser.objects.create(
            id=202, uzivatelske_jmeno='brig_plans', jmeno='Brig', prijmeni='Adnik',
            role='BRIGADNIK', prodejna_id=pid, aktivni=True,
        )
        self.brigadnik.set_heslo('x')
        self.brigadnik.save()
        self.plan = PlanMonth.objects.create(
            rok=2026, mesic=7, cislo_verze=1, castka_celkem=Decimal('100000'),
        )
        self.ps = PlanStore.objects.create(
            plan_mesic=self.plan,
            prodejna=self.prodejna,
            podil_procenta=Decimal('100'),
            castka_prodejna=Decimal('100000'),
            castka_prodej=Decimal('70000'),
            castka_servis=Decimal('30000'),
        )
        PlanCategory.objects.create(
            plan_prodejna=self.ps,
            kategorie_kod='NOVE_TELEFONY',
            podil_procenta=Decimal('100'),
            castka_kategorie=Decimal('100000'),
            prumerna_cena_za_kus=Decimal('5000'),
        )

    @patch('plans.prodejci_auto.Smena')
    def test_hlavni_prodejce_nejvic_smen(self, mock_smena):
        mock_smena.objects.filter.return_value.values_list.return_value.distinct.return_value = [201, 202]
        mock_smena.objects.filter.return_value.count.side_effect = [20, 5]

        hlavni = _hlavni_prodejce_id(2026, 7, self.prodejna.id)
        self.assertEqual(hlavni, 201)

    @patch('plans.prodejci_auto._servis_kusy_vychodil', return_value=3)
    @patch('plans.prodejci_auto._hlavni_prodejce_id', return_value=201)
    @patch('plans.prodejci_auto._lide_se_smenou_na_prodejne', return_value={121, 201})
    def test_vychodil_jen_servis_pri_dvojobsazeni(self, *_mocks):
        prirazeno, warnings = _prirad_prodejce_prodejna(self.ps, 2026, 7)
        self.assertEqual(prirazeno, 2)
        vych = PlanProdejce.objects.filter(uzivatel_id=VYCHODIL_USER_ID).first()
        self.assertIsNotNone(vych)
        self.assertEqual(list(vych.kategorie.values_list('kategorie_kod', flat=True)), ['SERVIS'])
        hlavni = PlanProdejce.objects.get(uzivatel_id=201)
        kody = set(hlavni.kategorie.values_list('kategorie_kod', flat=True))
        self.assertIn('NOVE_TELEFONY', kody)
        self.assertNotIn('SERVIS', kody)

    @patch('plans.prodejci_auto._prirad_prodejce_prodejna', return_value=(1, []))
    def test_prirad_celý_plan(self, mock_one):
        res = prirad_prodejce_automaticky(self.plan)
        self.assertEqual(res['prirazeno_prodejen'], 1)


class BaselineErrorTests(TestCase):
    def test_zero_obrat_raises(self):
        with self.assertRaises(ChybejiciDataError):
            vypocitej_plan_z_baseline(Decimal('0'), {}, {}, 10)
