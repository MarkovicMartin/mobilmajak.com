"""
Testy modulu plánů – 3m průměr, rozdělení prodejců podle hodin.
"""
from datetime import date, time
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase
from shifts.models import Smena

from plans.plneni import mesice_pred_planem, _prev_month
from plans.historie_3m import historie_3m_nahled, vypocitej_plan_z_3_mesicu
from plans.historie import ChybejiciDataError, vypocitej_plan_z_baseline
from plans.historie_auto import historie_auto_nahled, vypocitej_plan_automaticky, _sloucit_prodejny_hybrid
from plans.plan_service import ensure_plan_mesic, ensure_plans_bulk, mesice_bez_aktualniho_planu
from plans.prodejci_prepocet import mesice_pro_denni_prepocet
from plans.forecast import predikce_rok, vypocitej_plan_z_projekce, vyhled_forecast
from plans.prodejci_auto import (
    VYCHODIL_USER_ID,
    VIKEND_PRODEJ_SERVIS_VAHA,
    _efektivni_servis_hodin_mesic,
    _globus_segment_contributions,
    _legacy_podily_servis,
    _rozdel_kusy,
    _podily_z_hodin,
    _prirad_prodejce_prodejna,
    _servis_interval_contributions_globus,
    prirad_prodejce_automaticky,
)
from plans.models import PlanMonth, PlanStore, PlanCategory, PlanProdejce, PlanProdejceKategorie
from stores.models import Prodejna
from users.models import WebUser


class MesicePredPlanemTests(TestCase):
    def test_tri_mesice_pred_cervnem(self):
        months = mesice_pred_planem(2026, 6, 3)
        self.assertEqual(months, [(2026, 3), (2026, 4), (2026, 5)])

    def test_prev_month_leden(self):
        self.assertEqual(_prev_month(2026, 1), (2025, 12))


class RozdelKusyTests(TestCase):
    def test_soucet_sedi(self):
        podily = {1: 0.5, 2: 0.4, 3: 0.1}
        out = _rozdel_kusy(100, podily)
        self.assertEqual(sum(out.values()), 100)
        self.assertEqual(out[1], 50)
        self.assertEqual(out[2], 40)
        self.assertEqual(out[3], 10)


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


class ProdejciAutoHodinyTests(TestCase):
    def setUp(self):
        self.prodejna = Prodejna.objects.create(
            nazev='Test Globus Plans', nazev_kratkiy='TG', barva='#000000', aktivni=True,
        )
        pid = self.prodejna.id
        for uid, jmeno, role in [
            (201, 'Gabriel', 'PRODEJCE'),
            (202, 'Létal', 'PRODEJCE'),
            (203, 'Brig', 'BRIGADNIK'),
        ]:
            u = WebUser.objects.create(
                id=uid, uzivatelske_jmeno=f'u{uid}', jmeno=jmeno, prijmeni='T',
                role=role, prodejna_id=pid, aktivni=True,
            )
            u.set_heslo('x')
            u.save()
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

    def test_vychodil_vyloucen_z_prodejnich_podilu(self):
        hodiny = {201: 50.0, 202: 40.0, VYCHODIL_USER_ID: 10.0}
        p = _podily_z_hodin(hodiny, exclude_user_ids=[VYCHODIL_USER_ID])
        self.assertAlmostEqual(p[201], 50 / 90)
        self.assertAlmostEqual(p[202], 40 / 90)
        self.assertNotIn(VYCHODIL_USER_ID, p)

    @patch('plans.prodejci_auto._hodiny_na_prodejne')
    def test_proporcionalni_rozděleni_tri_lide(self, mock_hodiny):
        mock_hodiny.return_value = {201: 50.0, 202: 40.0, 203: 10.0}
        prirazeno, _ = _prirad_prodejce_prodejna(self.ps, 2026, 7)
        self.assertEqual(prirazeno, 3)
        g = PlanProdejce.objects.get(uzivatel_id=201)
        l = PlanProdejce.objects.get(uzivatel_id=202)
        b = PlanProdejce.objects.get(uzivatel_id=203)
        g_k = g.kategorie.get(kategorie_kod='NOVE_TELEFONY').pocet_kusu
        l_k = l.kategorie.get(kategorie_kod='NOVE_TELEFONY').pocet_kusu
        b_k = b.kategorie.get(kategorie_kod='NOVE_TELEFONY').pocet_kusu
        self.assertEqual(g_k + l_k + b_k, 20)
        self.assertEqual(g_k, 10)
        self.assertEqual(l_k, 8)
        self.assertEqual(b_k, 2)

    @patch('plans.prodejci_auto._hodiny_na_prodejne')
    def test_vychodil_bez_kusovych_kategorii(self, mock_hodiny):
        mock_hodiny.return_value = {VYCHODIL_USER_ID: 80.0, 201: 20.0}
        PlanCategory.objects.create(
            plan_prodejna=self.ps,
            kategorie_kod='SERVIS',
            podil_procenta=Decimal('0'),
            castka_kategorie=Decimal('1'),
            prumerna_cena_za_kus=Decimal('1'),
        )
        prirazeno, _ = _prirad_prodejce_prodejna(self.ps, 2026, 7)
        self.assertFalse(
            PlanProdejceKategorie.objects.filter(
                plan_prodejce__uzivatel_id=VYCHODIL_USER_ID,
                kategorie_kod='NOVE_TELEFONY',
            ).exists()
        )
        self.assertTrue(PlanProdejce.objects.filter(uzivatel_id=201).exists())


class HybridHistorieAutoTests(TestCase):
    def test_sloucit_6m_obrat_3m_kategorie(self):
        p6 = {
            1: {'obrat': Decimal('600'), 'kusy': 0, 'kategorie': {'A': {'obrat': Decimal('1')}}},
        }
        p3 = {
            1: {'obrat': Decimal('100'), 'kusy': 0, 'kategorie': {'B': {'obrat': Decimal('50')}}},
        }
        merged = _sloucit_prodejny_hybrid(p6, p3)
        self.assertEqual(merged[1]['obrat'], Decimal('600'))
        self.assertIn('B', merged[1]['kategorie'])

    @patch('plans.historie_auto.plneni_celkem_firma')
    @patch('plans.historie_auto.plneni_prodejny_za_obdobi')
    @patch('plans.historie_auto.plneni_firma_za_obdobi')
    @patch('plans.historie_auto.vypocitej_plan_z_baseline')
    def test_vypocet_yoy_a_okna(
        self, mock_baseline, mock_firma, mock_prodejny, mock_celkem
    ):
        mock_celkem.return_value = {'obrat': Decimal('2000000'), 'kusy': 0}
        mock_prodejny.side_effect = [
            {10: {'obrat': Decimal('800000'), 'kusy': 0, 'kategorie': {}}},
            {10: {'obrat': Decimal('100000'), 'kusy': 0, 'kategorie': {'NOVE_TELEFONY': {'obrat': Decimal('50')}}}},
        ]
        mock_firma.return_value = {'NOVE_TELEFONY': {'obrat': Decimal('500000'), 'kusy': 0}}
        mock_baseline.return_value = (Decimal('2200000'), [])

        vypocitej_plan_automaticky(2026, 6, 10)
        mock_celkem.assert_called_with(2025, 6)
        self.assertEqual(mock_prodejny.call_count, 2)
        args_baseline = mock_baseline.call_args[0]
        self.assertEqual(args_baseline[0], Decimal('2000000'))
        prodejny_arg = args_baseline[1]
        self.assertEqual(prodejny_arg[10]['obrat'], Decimal('800000'))
        self.assertIn('NOVE_TELEFONY', prodejny_arg[10]['kategorie'])

    @patch('plans.historie_auto.plneni_celkem_firma')
    @patch('plans.historie_auto.plneni_prodejny_za_obdobi')
    @patch('plans.historie_auto.plneni_firma_za_obdobi')
    @patch('plans.historie_auto.Prodejna.get_aktivni_prodejny')
    def test_nahled_hybrid(self, mock_aktivni, mock_fk, mock_pd, mock_celkem):
        mock_celkem.return_value = {'obrat': Decimal('1000000'), 'kusy': 0}
        mock_pd.side_effect = [
            {1: {'obrat': Decimal('1000000'), 'kusy': 0, 'kategorie': {}}},
            {1: {'obrat': Decimal('1000000'), 'kusy': 0, 'kategorie': {}}},
        ]
        mock_fk.return_value = {}
        p = MagicMock(id=1, nazev='A')
        mock_aktivni.return_value = [p]
        nahled = historie_auto_nahled(2026, 6, 10)
        self.assertEqual(nahled['zdroj'], 'hybrid_yoy_6m_3m')
        self.assertEqual(nahled['navrh_obrat'], 1100000.0)


class EnsurePlanMesicTests(TestCase):
    def setUp(self):
        self.admin = WebUser.objects.create(
            uzivatelske_jmeno='admin_plans',
            jmeno='Admin',
            prijmeni='Plans',
            role='ADMIN',
            aktivni=True,
        )
        self.admin.set_heslo('x')
        self.admin.save()

    def test_past_month_not_allowed(self):
        res = ensure_plan_mesic(2020, 1, self.admin, rust_procent=10)
        self.assertFalse(res['created'])
        self.assertEqual(res['reason'], 'past_month')

    @patch('plans.plan_service.vypocitej_plan_automaticky')
    @patch('plans.plan_service._vytvor_plan_z_prodejny_data')
    def test_idempotent_second_call(self, mock_vytvor, mock_vypocet):
        mock_vypocet.return_value = (Decimal('1000000'), [])
        mock_vytvor.return_value = (
            PlanMonth.objects.create(rok=2028, mesic=6, cislo_verze=1, castka_celkem=Decimal('1000000')),
            {'id': 1, 'castka_celkem': '1000000'},
        )
        r1 = ensure_plan_mesic(2028, 6, self.admin)
        self.assertTrue(r1['created'])
        r2 = ensure_plan_mesic(2028, 6, self.admin)
        self.assertFalse(r2['created'])
        self.assertEqual(r2['reason'], 'already_exists')
        mock_vypocet.assert_called_once()


class ForecastTests(TestCase):
    def test_stav_mesice(self):
        from plans.forecast import stav_mesice
        ref = date(2026, 6, 4)
        self.assertEqual(stav_mesice(2026, 5, ref), 'ukonceny')
        self.assertEqual(stav_mesice(2026, 6, ref), 'probiha')
        self.assertEqual(stav_mesice(2026, 7, ref), 'budouci')

    def test_souhrn_ytd_prorated_probiha(self):
        from plans.forecast import _souhrn_ytd
        ref = date(2026, 6, 4)
        mesice = [
            {
                'rok': 2026, 'mesic': 1, 'stav': 'ukonceny', 'obrat_pred': 100, 'obrat_ly': 90,
                'plneni': {'obrat': 100, 'plan_obrat': 95},
            },
            {
                'rok': 2026, 'mesic': 6, 'stav': 'probiha', 'obrat_pred': 3000, 'obrat_ly': 3000,
                'plneni': {
                    'obrat': 300, 'plan_obrat': 2900,
                    'den_v_mesici': 4, 'dni_v_mesici': 30,
                },
            },
        ]
        ytd = _souhrn_ytd(mesice, reference=ref)
        self.assertTrue(ytd['prorated'])
        self.assertIn('do 4. 6.', ytd['popis_obdobi'])
        # pred: 100 + 3000*(4/30) = 100 + 400 = 500; sk: 100+300=400 → 80 %
        self.assertEqual(ytd['pct_vs_predikce'], 80)
        # ly: 90 + 3000*(4/30) = 490; sk 400 → ~82 %
        self.assertEqual(ytd['pct_vs_ly'], 82)

    @patch('plans.forecast.plneni_celkem_firma')
    @patch('plans.forecast.PlanMonth')
    def test_dopln_plneni_ukonceny(self, mock_plan, mock_plneni):
        from plans.forecast import dopln_plneni_k_mesici
        mock_plneni.return_value = {'obrat': Decimal('1100000'), 'kusy': 50}
        mock_plan.objects.filter.return_value.first.return_value = None
        pm = {'rok': 2026, 'mesic': 1, 'obrat_pred': 1000000.0}
        dopln_plneni_k_mesici(pm, reference=date(2026, 6, 4))
        self.assertEqual(pm['stav'], 'ukonceny')
        self.assertEqual(pm['plneni']['obrat'], 1100000.0)
        self.assertEqual(pm['plneni']['pct_predikce'], 110.0)

    @patch('plans.forecast.plneni_celkem_firma_mesicne')
    def test_predikce_rok_12_mesicu(self, mock_map):
        mock_map.return_value = {
            (y, m): {'obrat': Decimal('100000'), 'kusy': 10}
            for y in range(2023, 2028)
            for m in range(1, 13)
        }
        out = predikce_rok(2027, rust_procent=10, reference=date(2026, 6, 4))
        self.assertEqual(len(out['mesice']), 12)
        self.assertEqual(mock_map.call_count, 1)
        self.assertIn('obrat_pred', out['mesice'][0])
        self.assertNotIn('prodejny_data', out['mesice'][0])
        self.assertIn('souhrn_roku', out)

    @patch('plans.forecast.plneni_celkem_firma_mesicne')
    def test_vyhled_forecast_porovnani(self, mock_map):
        mock_map.return_value = {
            (y, m): {'obrat': Decimal('100000'), 'kusy': 10}
            for y in range(2023, 2028)
            for m in range(1, 13)
        }
        out = vyhled_forecast(2026, compare_roky=[2025, 2024], reference=date(2026, 6, 4))
        self.assertEqual(out['hlavni_rok'], 2026)
        self.assertEqual(len(out['predikce']['mesice']), 12)
        self.assertGreaterEqual(len(out['porovnani_roky']), 2)

    @patch('plans.forecast.vypocitej_plan_z_baseline')
    @patch('plans.forecast.predikce_mesic')
    def test_projekce_plan(self, mock_pred, mock_base):
        mock_pred.return_value = {
            'obrat_baseline': Decimal('500000'),
            'prodejny_data': {},
            'firma_kategorie': {},
            'rust_pouzity_pct': 10.0,
        }
        mock_base.return_value = (Decimal('550000'), [])
        result = vypocitej_plan_z_projekce(2027, 3, rust_procent=10)
        self.assertEqual(result[0], Decimal('550000'))

    def test_mesice_pro_denni_prepocet(self):
        self.assertEqual(
            mesice_pro_denni_prepocet(date(2026, 6, 4)),
            [(2026, 7)],
        )
        self.assertEqual(
            mesice_pro_denni_prepocet(date(2026, 6, 15)),
            [(2026, 6), (2026, 7)],
        )

    @patch('plans.prodejci_prepocet.prepocet_prodejci_mesice')
    @patch('plans.plan_service.ensure_plan_mesic')
    def test_bulk_prepocet_prodejci(self, mock_ensure, mock_prepocet):
        mock_ensure.return_value = {'created': True, 'plan_id': 1, 'warnings': []}
        mock_prepocet.return_value = {
            'vysledky': [],
            'pocet_prepocet': 2,
            'warnings': [],
        }
        admin = MagicMock()
        souhrn = ensure_plans_bulk([(2026, 1), (2026, 2)], admin, prepocet_prodejci=True)
        mock_prepocet.assert_called_once()
        self.assertEqual(souhrn['pocet_prepocet_prodejci'], 2)

    def test_bulk_skip_existing(self):
        PlanMonth.objects.create(
            rok=2027, mesic=1, cislo_verze=1, je_aktualni=True, castka_celkem=Decimal('1'),
        )
        admin = MagicMock()
        with patch('plans.plan_service.ensure_plan_mesic') as mock_ensure:
            souhrn = ensure_plans_bulk([(2027, 1), (2027, 2)], admin, skip_existing=True)
            self.assertEqual(souhrn['pocet_preskoceno'], 1)
            mock_ensure.assert_called_once()

    def test_mesice_bez_aktualniho_planu(self):
        PlanMonth.objects.create(
            rok=2029, mesic=1, cislo_verze=1, je_aktualni=True, castka_celkem=Decimal('1'),
        )
        PlanMonth.objects.create(
            rok=2029, mesic=6, cislo_verze=1, je_aktualni=True, castka_celkem=Decimal('2'),
        )
        PlanMonth.objects.create(
            rok=2029, mesic=3, cislo_verze=1, je_aktualni=False, castka_celkem=Decimal('3'),
        )
        self.assertEqual(
            mesice_bez_aktualniho_planu(2029),
            [2, 3, 4, 5, 7, 8, 9, 10, 11, 12],
        )

    @patch('plans.prodejci_prepocet.prepocet_prodejci_mesice')
    @patch('plans.plan_service.ensure_plan_mesic')
    def test_bulk_prepocet_only_created(self, mock_ensure, mock_prepocet):
        mock_ensure.return_value = {'created': True, 'plan_id': 1, 'warnings': []}
        mock_prepocet.return_value = {'vysledky': [], 'pocet_prepocet': 1, 'warnings': []}
        admin = MagicMock()
        PlanMonth.objects.create(
            rok=2030, mesic=1, cislo_verze=1, je_aktualni=True, castka_celkem=Decimal('1'),
        )
        souhrn = ensure_plans_bulk([(2030, 2), (2030, 3)], admin, prepocet_prodejci=True)
        mock_prepocet.assert_called_once_with([(2030, 2), (2030, 3)])
        self.assertEqual(souhrn['pocet_vytvoreno'], 2)


class PoziceServisAutoTests(TestCase):
    """Testy pozice směny servis + servis_uroven + Globus intervaly."""

    def setUp(self):
        self.globus = Prodejna.objects.create(
            nazev='Globus',
            nazev_kratkiy='GL',
            barva='#0000aa',
            aktivni=True,
            povolena_pozice_servis=True,
        )
        self.jina = Prodejna.objects.create(
            nazev='Jina Plans Test',
            nazev_kratkiy='JP',
            barva='#aaaa00',
            aktivni=True,
            povolena_pozice_servis=False,
        )
        pid_g = self.globus.id
        for uid, jmeno, role, uroven, technik in [
            (301, 'Technik', 'PRODEJCE', 'plny', 501),
            (302, 'Prodejce', 'PRODEJCE', 'plny', 0),
            (303, 'Zadny', 'PRODEJCE', 'zadna', 0),
            (304, 'Zauceny', 'PRODEJCE', 'zauceni', 0),
        ]:
            u = WebUser.objects.create(
                id=uid,
                uzivatelske_jmeno=f'ps{uid}',
                jmeno=jmeno,
                prijmeni='T',
                role=role,
                prodejna_id=pid_g,
                aktivni=True,
                servis_uroven=uroven,
                technik_id=technik if technik else None,
            )
            u.set_heslo('x')
            u.save()

        self.plan = PlanMonth.objects.create(
            rok=2026, mesic=8, cislo_verze=1, castka_celkem=Decimal('100000'),
        )
        self.ps_globus = PlanStore.objects.create(
            plan_mesic=self.plan,
            prodejna=self.globus,
            podil_procenta=Decimal('100'),
            castka_prodejna=Decimal('100000'),
            castka_prodej=Decimal('70000'),
            castka_servis=Decimal('30000'),
        )
        for kod, castka in [('NOVE_TELEFONY', '70000'), ('SERVIS', '30000')]:
            PlanCategory.objects.create(
                plan_prodejna=self.ps_globus,
                kategorie_kod=kod,
                podil_procenta=Decimal('50'),
                castka_kategorie=Decimal(castka),
                prumerna_cena_za_kus=Decimal('5000') if kod != 'SERVIS' else Decimal('1000'),
            )

    def _smena(self, user_id, datum, cas_od, cas_do, pozice='prodej', prodejna=None):
        return Smena.objects.create(
            user_id=user_id,
            prodejna=prodejna or self.globus,
            datum=datum,
            cas_od=cas_od,
            cas_do=cas_do,
            typ_smeny='prace',
            pozice_smeny=pozice,
        )

    def test_legacy_bez_servis_smen(self):
        self._smena(301, date(2026, 8, 4), time(8, 0), time(16, 0), pozice='prodej')
        self._smena(302, date(2026, 8, 4), time(8, 0), time(16, 0), pozice='prodej')
        hodiny = {301: 8.0, 302: 8.0}
        legacy = _legacy_podily_servis(hodiny)
        self.assertEqual(legacy, {301: 1.0})
        efektivni, _ = _efektivni_servis_hodin_mesic(2026, 8, self.globus)
        self.assertIsNone(efektivni)

    def test_globus_servis_jen_technikovi(self):
        self._smena(301, date(2026, 8, 4), time(8, 0), time(16, 0), pozice='servis')
        self._smena(302, date(2026, 8, 4), time(8, 0), time(16, 0), pozice='prodej')
        prirazeno, _ = _prirad_prodejce_prodejna(self.ps_globus, 2026, 8)
        self.assertGreaterEqual(prirazeno, 2)
        servis_t = PlanProdejceKategorie.objects.filter(
            plan_prodejce__uzivatel_id=301, kategorie_kod='SERVIS',
        ).first()
        servis_p = PlanProdejceKategorie.objects.filter(
            plan_prodejce__uzivatel_id=302, kategorie_kod='SERVIS',
        ).first()
        self.assertIsNotNone(servis_t)
        self.assertTrue(servis_t.pocet_kusu > 0)
        self.assertTrue(servis_p is None or servis_p.pocet_kusu == 0)

    def test_vikend_prodejce_schopny_ma_vahu(self):
        # sobota 2026-08-01 – víkendový pool jen prodej + schopný
        self._smena(301, date(2026, 8, 1), time(8, 0), time(12, 0), pozice='servis')
        self._smena(302, date(2026, 8, 1), time(8, 0), time(12, 0), pozice='prodej')
        self._smena(303, date(2026, 8, 1), time(8, 0), time(12, 0), pozice='prodej')
        efektivni, _ = _efektivni_servis_hodin_mesic(2026, 8, self.globus)
        self.assertIn(302, efektivni)
        self.assertNotIn(303, efektivni)
        self.assertNotIn(301, efektivni)
        self.assertAlmostEqual(efektivni[302], 4.0)

    def test_zauceni_prekryv_s_plnym(self):
        datum = date(2026, 8, 5)  # středa
        sm_t = self._smena(301, datum, time(8, 0), time(12, 0), pozice='servis')
        sm_z = self._smena(304, datum, time(8, 0), time(12, 0), pozice='servis')
        contrib, unc = _globus_segment_contributions(datum, [sm_t, sm_z])
        self.assertFalse(unc)
        self.assertAlmostEqual(contrib[301], 1.0 / 1.2, places=3)
        self.assertAlmostEqual(contrib[304], 0.2 / 1.2, places=3)

    def test_solo_edge_prodejce_globus(self):
        datum = date(2026, 8, 6)
        sm = self._smena(302, datum, time(8, 0), time(12, 0), pozice='prodej')
        contrib, unc = _globus_segment_contributions(datum, [sm])
        self.assertFalse(unc)
        self.assertEqual(contrib[302], 1.0)
        day_h, _ = _servis_interval_contributions_globus(datum, [sm])
        self.assertAlmostEqual(day_h[302], 4.0)

    def test_vychodil_mimo_prodejni_pool_s_pozici(self):
        u = WebUser.objects.create(
            id=VYCHODIL_USER_ID,
            uzivatelske_jmeno='vych',
            jmeno='František',
            prijmeni='Vychodil',
            role='PRODEJCE',
            prodejna_id=self.globus.id,
            aktivni=True,
            servis_uroven='zadna',
        )
        u.set_heslo('x')
        u.save()
        self._smena(VYCHODIL_USER_ID, date(2026, 8, 7), time(8, 0), time(16, 0), pozice='prodej')
        self._smena(301, date(2026, 8, 7), time(8, 0), time(16, 0), pozice='servis')
        self._smena(302, date(2026, 8, 7), time(8, 0), time(16, 0), pozice='prodej')
        prirazeno, _ = _prirad_prodejce_prodejna(self.ps_globus, 2026, 8)
        self.assertGreater(prirazeno, 0)
        self.assertFalse(
            PlanProdejceKategorie.objects.filter(
                plan_prodejce__uzivatel_id=VYCHODIL_USER_ID,
                kategorie_kod='NOVE_TELEFONY',
            ).exists()
        )
