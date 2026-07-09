"""Testy admin API – korekce dovolené a ruční hodiny."""
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from shifts.models import DovolenaKorekceLog, PrumerMzdyMesicOverride, PrumerMzdyMesicOverrideLog
from shifts.prumer_mzdy_override import clear_prumer_mzdy_override_cache, prumer_override_for_user
from stores.models import Prodejna
from users.models import WebUser


class AdminVacationAdjustmentsTest(TestCase):
    def setUp(self):
        self.prodejna = Prodejna.objects.create(
            id=9910,
            nazev='Test',
            nazev_kratkiy='Test',
            aktivni=True,
        )
        self.admin = WebUser.objects.create(
            id=9911,
            uzivatelske_jmeno='admin.vac.test',
            jmeno='Admin',
            prijmeni='Test',
            heslo='x',
            role='ADMIN',
            aktivni=True,
        )
        self.prodejce = WebUser.objects.create(
            id=9912,
            uzivatelske_jmeno='prodejce.vac.test',
            jmeno='Jan',
            prijmeni='Prodejce',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=self.prodejna.id,
        )
        self.client = APIClient()
        self.prumer_cache_patcher = patch(
            'shifts.payroll_service.build_prumer_mzdy_cache_for_prumer',
            return_value={},
        )
        self.prumer_cache_patcher.start()

    def tearDown(self):
        self.prumer_cache_patcher.stop()

    def test_vacation_corrections_admin_only(self):
        self.client.force_authenticate(user=self.prodejce)
        res = self.client.patch(
            f'/api/shifts/vacation-corrections/{self.prodejce.id}/',
            {'dovolena_fond_extra_h': 40},
            format='json',
        )
        self.assertEqual(res.status_code, 403)

    def test_vacation_corrections_update_and_log(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.patch(
            f'/api/shifts/vacation-corrections/{self.prodejce.id}/',
            {
                'dovolena_fond_extra_h': 40,
                'dovolena_korekce_cerpano_h': 8,
                'poznamka': 'Sync z Excelu',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn('overview', res.data)
        self.prodejce.refresh_from_db()
        self.assertEqual(self.prodejce.dovolena_fond_extra_h, Decimal('40'))
        self.assertEqual(self.prodejce.dovolena_korekce_cerpano_h, Decimal('8'))
        self.assertEqual(DovolenaKorekceLog.objects.filter(user=self.prodejce).count(), 1)

    def test_admin_adjustment_audit(self):
        self.client.force_authenticate(user=self.admin)
        self.client.patch(
            f'/api/shifts/vacation-corrections/{self.prodejce.id}/',
            {'dovolena_fond_extra_h': 10, 'poznamka': 'Test audit'},
            format='json',
        )
        res = self.client.get(
            f'/api/shifts/admin-adjustment-audit/?user_id={self.prodejce.id}',
        )
        self.assertEqual(res.status_code, 200)
        entries = res.data['entries']
        self.assertGreaterEqual(len(entries), 1)
        self.assertEqual(entries[0]['typ'], 'dovolena')

    def test_prumer_override_audit_log(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.post(
            '/api/shifts/prumer-overrides/',
            {
                'user_id': self.prodejce.id,
                'rok': 2026,
                'mesic': 5,
                'odpracovano_h': 100,
                'poznamka': 'Audit test',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201)
        self.assertIn('overview', res.data)
        self.assertEqual(
            PrumerMzdyMesicOverrideLog.objects.filter(user=self.prodejce, akce='create').count(),
            1,
        )
        row_id = res.data['override']['id']
        res_up = self.client.put(
            f'/api/shifts/prumer-overrides/{row_id}/',
            {'odpracovano_h': 110},
            format='json',
        )
        self.assertEqual(res_up.status_code, 200)
        self.assertEqual(
            PrumerMzdyMesicOverrideLog.objects.filter(user=self.prodejce, akce='update').count(),
            1,
        )
        res_del = self.client.delete(f'/api/shifts/prumer-overrides/{row_id}/')
        self.assertEqual(res_del.status_code, 200)
        self.assertEqual(
            PrumerMzdyMesicOverrideLog.objects.filter(user=self.prodejce, akce='delete').count(),
            1,
        )

    def test_prumer_override_db_preferred(self):
        PrumerMzdyMesicOverride.objects.create(
            user=self.prodejce,
            rok=2026,
            mesic=3,
            odpracovano_h=Decimal('120'),
            zmenil=self.admin,
        )
        clear_prumer_mzdy_override_cache()
        rows = prumer_override_for_user(self.prodejce)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['odpracovano_h'], 120.0)

    def test_prumer_override_api_crud(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.post(
            '/api/shifts/prumer-overrides/',
            {
                'user_id': self.prodejce.id,
                'rok': 2026,
                'mesic': 4,
                'odpracovano_h': 150,
                'poznamka': 'Ruční',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201)
        row_id = res.data['override']['id']
        res_del = self.client.delete(f'/api/shifts/prumer-overrides/{row_id}/')
        self.assertEqual(res_del.status_code, 200)
        self.assertFalse(PrumerMzdyMesicOverride.objects.filter(id=row_id).exists())
