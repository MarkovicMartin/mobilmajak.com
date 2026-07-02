"""
Testy přepočtu plánů po směně a rozšířeného muj-plan.
"""
from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from plans.models import PlanMonth, PlanStore, PlanCategory, PlanProdejce, PlanProdejceKategorie
from plans.muj_plan_service import build_muj_plan_payload
from plans.shift_hooks import naplanuj_prepocet_po_smene
from shifts.models import Smena
from stores.models import Prodejna
from users.models import WebUser


class ShiftHooksTests(TestCase):
    def setUp(self):
        self.prodejna = Prodejna.objects.create(
            id=9301, nazev='Hook Store', nazev_kratkiy='HS', aktivni=True,
        )
        self.user = WebUser.objects.create(
            id=9301,
            uzivatelske_jmeno='hook_user',
            jmeno='Hook',
            prijmeni='User',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=self.prodejna.id,
        )
        self.today = date.today()
        self.smena = Smena.objects.create(
            user=self.user,
            prodejna=self.prodejna,
            datum=self.today,
            cas_od=time(8, 0),
            cas_do=time(16, 0),
            typ_smeny='prace',
        )

    @patch('plans.shift_hooks.transaction.on_commit')
    def test_single_current_month_schedules_prepocet(self, mock_on_commit):
        naplanuj_prepocet_po_smene(self.smena, zdroj='single')
        mock_on_commit.assert_called_once()

    @patch('plans.shift_hooks.transaction.on_commit')
    def test_bulk_source_skips_prepocet(self, mock_on_commit):
        naplanuj_prepocet_po_smene(self.smena, zdroj='bulk')
        mock_on_commit.assert_not_called()

    @patch('plans.shift_hooks.transaction.on_commit')
    def test_future_month_skips_prepocet(self, mock_on_commit):
        future = self.today.replace(day=1) + timedelta(days=62)
        future = future.replace(day=15)
        smena = Smena(
            user=self.user,
            prodejna=self.prodejna,
            datum=future,
            cas_od=time(8, 0),
            cas_do=time(16, 0),
            typ_smeny='prace',
        )
        naplanuj_prepocet_po_smene(smena, zdroj='single')
        mock_on_commit.assert_not_called()

    @override_settings(PLAN_PREPOCET_ON_SHIFT=False)
    @patch('plans.shift_hooks.transaction.on_commit')
    def test_feature_flag_disables_prepocet(self, mock_on_commit):
        naplanuj_prepocet_po_smene(self.smena, zdroj='single')
        mock_on_commit.assert_not_called()


class MujPlanServiceTests(TestCase):
    def setUp(self):
        self.domaci = Prodejna.objects.create(
            id=9310, nazev='Domácí', nazev_kratkiy='DOM', aktivni=True,
        )
        self.cizi = Prodejna.objects.create(
            id=9311, nazev='Cizí', nazev_kratkiy='CIZ', aktivni=True,
        )
        self.user = WebUser.objects.create(
            id=9310,
            uzivatelske_jmeno='plan_user',
            jmeno='Plan',
            prijmeni='User',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=self.domaci.id,
        )
        self.today = date.today()
        rok, mesic = self.today.year, self.today.month
        self.plan = PlanMonth.objects.create(
            rok=rok, mesic=mesic, cislo_verze=1, castka_celkem=Decimal('100000'),
            je_aktualni=True,
        )
        for prodejna, kusy in [(self.domaci, 20), (self.cizi, 10)]:
            ps = PlanStore.objects.create(
                plan_mesic=self.plan,
                prodejna=prodejna,
                podil_procenta=Decimal('50'),
                castka_prodejna=Decimal('50000'),
                castka_prodej=Decimal('50000'),
                castka_servis=Decimal('0'),
            )
            PlanCategory.objects.create(
                plan_prodejna=ps,
                kategorie_kod='NOVE_TELEFONY',
                podil_procenta=Decimal('100'),
                castka_kategorie=Decimal('50000'),
                prumerna_cena_za_kus=Decimal('5000'),
            )
            pp = PlanProdejce.objects.create(plan_prodejna=ps, uzivatel=self.user)
            PlanProdejceKategorie.objects.create(
                plan_prodejce=pp,
                kategorie_kod='NOVE_TELEFONY',
                pocet_kusu=kusy,
                castka=Decimal('0'),
            )

        Smena.objects.create(
            user=self.user,
            prodejna=self.domaci,
            datum=self.today,
            cas_od=time(8, 0),
            cas_do=time(16, 0),
            typ_smeny='prace',
        )
        Smena.objects.create(
            user=self.user,
            prodejna=self.cizi,
            datum=self.today.replace(day=min(28, self.today.day)),
            cas_od=time(8, 0),
            cas_do=time(16, 0),
            typ_smeny='prace',
        )

    @patch('plans.muj_plan_service.plneni_prodejce', return_value={})
    @patch('plans.muj_plan_service.plneni_prodejce_den', return_value={})
    @patch('plans.muj_plan_service.plneni_prodejce_do_data', return_value={})
    def test_prodejny_breakdown(self, *_mocks):
        payload = build_muj_plan_payload(self.user, self.today.year, self.today.month)
        self.assertEqual(payload['celkem_polozek'], 30)
        self.assertEqual(len(payload['prodejny']), 2)
        nazvy = {p['prodejna_nazev'] for p in payload['prodejny']}
        self.assertIn('DOM', nazvy)
        self.assertIn('CIZ', nazvy)

    @patch('plans.muj_plan_service.plneni_prodejce', return_value={})
    @patch('plans.muj_plan_service.plneni_prodejce_den', return_value={})
    @patch('plans.muj_plan_service.plneni_prodejce_do_data', return_value={})
    def test_denni_plan_from_hours(self, *_mocks):
        payload = build_muj_plan_payload(self.user, self.today.year, self.today.month)
        self.assertIsNotNone(payload['denni'])
        self.assertGreater(payload['denni']['hodiny_mesic'], 0)
        self.assertGreater(payload['denni']['celkem_polozek'], 0)


class ShiftPlanIntegrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.prodejna = Prodejna.objects.create(
            id=9320, nazev='Int Store', nazev_kratkiy='INT', aktivni=True,
        )
        self.prodejce = WebUser.objects.create(
            id=9320,
            uzivatelske_jmeno='int_prod',
            jmeno='Int',
            prijmeni='Prod',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=self.prodejna.id,
        )
        self.admin = WebUser.objects.create(
            id=9321,
            uzivatelske_jmeno='int_admin',
            jmeno='Int',
            prijmeni='Admin',
            heslo='x',
            role='ADMIN',
            aktivni=True,
        )
        self.today = date.today()
        rok, mesic = self.today.year, self.today.month
        self.plan = PlanMonth.objects.create(
            rok=rok, mesic=mesic, cislo_verze=1, castka_celkem=Decimal('100000'),
            je_aktualni=True,
        )
        self.ps = PlanStore.objects.create(
            plan_mesic=self.plan,
            prodejna=self.prodejna,
            podil_procenta=Decimal('100'),
            castka_prodejna=Decimal('100000'),
            castka_prodej=Decimal('100000'),
            castka_servis=Decimal('0'),
        )
        PlanCategory.objects.create(
            plan_prodejna=self.ps,
            kategorie_kod='NOVE_TELEFONY',
            podil_procenta=Decimal('100'),
            castka_kategorie=Decimal('100000'),
            prumerna_cena_za_kus=Decimal('5000'),
        )
        self.client.force_authenticate(user=self.admin)

    @patch('plans.muj_plan_service.plneni_prodejce', return_value={})
    @patch('plans.muj_plan_service.plneni_prodejce_den', return_value={})
    @patch('plans.muj_plan_service.plneni_prodejce_do_data', return_value={})
    def test_single_shift_create_triggers_plan_assignment(self, *_mocks):
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.post('/api/shifts/', {
                'user_id': self.prodejce.id,
                'prodejna': 'INT',
                'datum': self.today.isoformat(),
                'cas_od': '10:00',
                'cas_do': '18:00',
                'typ_smeny': 'prace',
            }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(
            PlanProdejce.objects.filter(
                uzivatel=self.prodejce,
                plan_prodejna=self.ps,
            ).exists()
        )

    def test_bulk_create_does_not_require_immediate_plan(self):
        """Bulk endpoint nesmí spadnout; plán může chybět do cronu."""
        future_day = self.today.replace(day=min(26, 28))
        if future_day <= self.today:
            future_day = self.today.replace(day=min(28, 28))
        if future_day.month != self.today.month:
            future_day = self.today
        res = self.client.post('/api/shifts/bulk-create/', {
            'user_id': self.prodejce.id,
            'prodejna': 'INT',
            'datumy': [future_day.isoformat()],
            'cas_od': '06:00',
            'cas_do': '14:00',
            'typ_smeny': 'prace',
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['uspesne'], 1)
