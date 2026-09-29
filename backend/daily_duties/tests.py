from datetime import date

from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from daily_duties.models import DailyDutyCompletion, DailyDutyTemplate
from daily_duties.periods import period_bounds
from daily_duties.views import (
    CompleteDutyView,
    DailyDutyTemplateViewSet,
    DutyStatusView,
    MyDutiesView,
)
from stores.models import Prodejna
from users.models import WebUser


@override_settings(DAILY_DUTIES_MODULE_ENABLED=True)
class DailyDutyPeriodTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.store_a = Prodejna.objects.create(nazev='Prodejna A test', nazev_kratkiy='Atest')
        self.store_b = Prodejna.objects.create(nazev='Prodejna B test', nazev_kratkiy='Btest')
        self.admin = WebUser.objects.create(
            id=8830, uzivatelske_jmeno='dd_admin', jmeno='Admin', prijmeni='Dd',
            role='ADMIN', heslo='x', prodejna_id=None,
        )
        self.seller_a = WebUser.objects.create(
            id=8831, uzivatelske_jmeno='dd_a', jmeno='Anna', prijmeni='A',
            role='PRODEJCE', heslo='x', prodejna_id=self.store_a.id,
        )
        self.seller_a2 = WebUser.objects.create(
            id=8832, uzivatelske_jmeno='dd_a2', jmeno='Adam', prijmeni='A',
            role='PRODEJCE', heslo='x', prodejna_id=self.store_a.id,
        )
        self.seller_b = WebUser.objects.create(
            id=8833, uzivatelske_jmeno='dd_b', jmeno='Bara', prijmeni='B',
            role='PRODEJCE', heslo='x', prodejna_id=self.store_b.id,
        )
        self.store_daily = DailyDutyTemplate.objects.create(
            title='Otevrit', periodicity='daily', prodejna=self.store_a,
        )
        self.store_weekly = DailyDutyTemplate.objects.create(
            title='Inventura', periodicity='weekly', prodejna=self.store_a,
        )
        self.store_monthly = DailyDutyTemplate.objects.create(
            title='Report', periodicity='monthly', prodejna=self.store_a,
        )
        self.personal = DailyDutyTemplate.objects.create(
            title='Admin ukol', periodicity='daily', uzivatel=self.admin,
        )
        self.other_store = DailyDutyTemplate.objects.create(
            title='B otevirani', periodicity='daily', prodejna=self.store_b,
        )

    def _get(self, view, user, path, query=None):
        request = self.factory.get(path, query or {})
        force_authenticate(request, user=user)
        return view(request)

    def _complete(self, user, template, day, note=''):
        request = self.factory.post(
            f'/api/daily-duties/mine/{template.id}/complete/',
            {'date': day, 'note': note},
            format='json',
        )
        force_authenticate(request, user=user)
        return CompleteDutyView.as_view()(request, pk=template.id)

    def test_seller_cannot_create_template_admin_can(self):
        payload = {
            'title': 'Nova',
            'periodicity': 'weekly',
            'prodejna': self.store_a.id,
            'uzivatel': None,
        }
        seller_req = self.factory.post('/api/daily-duties/templates/', payload, format='json')
        force_authenticate(seller_req, user=self.seller_a)
        seller_res = DailyDutyTemplateViewSet.as_view({'post': 'create'})(seller_req)
        self.assertEqual(seller_res.status_code, 403)

        admin_req = self.factory.post('/api/daily-duties/templates/', payload, format='json')
        force_authenticate(admin_req, user=self.admin)
        admin_res = DailyDutyTemplateViewSet.as_view({'post': 'create'})(admin_req)
        self.assertEqual(admin_res.status_code, 201, admin_res.data)

        both = self.factory.post('/api/daily-duties/templates/', {
            'title': 'Oboji',
            'periodicity': 'daily',
            'prodejna': self.store_a.id,
            'uzivatel': self.admin.id,
        }, format='json')
        force_authenticate(both, user=self.admin)
        both_res = DailyDutyTemplateViewSet.as_view({'post': 'create'})(both)
        self.assertEqual(both_res.status_code, 400)

        neither = self.factory.post('/api/daily-duties/templates/', {
            'title': 'Nikdo',
            'periodicity': 'shift',
        }, format='json')
        force_authenticate(neither, user=self.admin)
        neither_res = DailyDutyTemplateViewSet.as_view({'post': 'create'})(neither)
        self.assertEqual(neither_res.status_code, 400)

    def test_visibility(self):
        mine = self._get(MyDutiesView.as_view(), self.seller_a, '/api/daily-duties/mine/', {'date': '2026-10-01'})
        titles = {item['title'] for item in mine.data['items']}
        self.assertEqual(titles, {'Otevrit', 'Inventura', 'Report'})
        self.assertEqual(len(mine.data['items']), 3)

        admin_mine = self._get(MyDutiesView.as_view(), self.admin, '/api/daily-duties/mine/', {'date': '2026-10-01'})
        self.assertEqual([item['title'] for item in admin_mine.data['items']], ['Admin ukol'])

        status = self._get(DutyStatusView.as_view(), self.admin, '/api/daily-duties/status/', {'date': '2026-10-01'})
        self.assertEqual(status.status_code, 200)
        self.assertGreaterEqual(len(status.data['items']), 5)

        denied = self._get(DutyStatusView.as_view(), self.seller_a, '/api/daily-duties/status/', {'date': '2026-10-01'})
        self.assertEqual(denied.status_code, 403)

    def test_daily_weekly_monthly_uniqueness(self):
        self.assertEqual(period_bounds('weekly', date(2026, 10, 1))[0], date(2026, 9, 28))
        self.assertEqual(period_bounds('monthly', date(2026, 10, 15))[0], date(2026, 10, 1))

        first = self._complete(self.seller_a, self.store_daily, '2026-10-01', 'hotovo')
        self.assertEqual(first.status_code, 201, first.data)
        self.assertTrue(first.data['completed'])
        self.assertFalse(first.data['can_complete'])

        again = self._complete(self.seller_a2, self.store_daily, '2026-10-01')
        self.assertEqual(again.status_code, 409)
        self.assertEqual(DailyDutyCompletion.objects.filter(template=self.store_daily).count(), 1)

        listed = self._get(MyDutiesView.as_view(), self.seller_a, '/api/daily-duties/mine/', {'date': '2026-10-01'})
        daily = next(item for item in listed.data['items'] if item['title'] == 'Otevrit')
        self.assertTrue(daily['completed'])
        self.assertEqual(daily['periodicity_display'], 'Denně')

        next_day = self._complete(self.seller_a, self.store_daily, '2026-10-02')
        self.assertEqual(next_day.status_code, 201)

        outsider = self._complete(self.seller_b, self.store_daily, '2026-10-03')
        self.assertEqual(outsider.status_code, 403)

        week = self._complete(self.seller_a, self.store_weekly, '2026-10-01')
        self.assertEqual(week.status_code, 201)
        same_week = self._complete(self.seller_a2, self.store_weekly, '2026-10-04')
        self.assertEqual(same_week.status_code, 409)
        next_week = self._complete(self.seller_a, self.store_weekly, '2026-10-05')
        self.assertEqual(next_week.status_code, 201)

        month = self._complete(self.seller_a, self.store_monthly, '2026-10-01')
        self.assertEqual(month.status_code, 201)
        same_month = self._complete(self.seller_a, self.store_monthly, '2026-10-31')
        self.assertEqual(same_month.status_code, 409)
        next_month = self._complete(self.seller_a, self.store_monthly, '2026-11-01')
        self.assertEqual(next_month.status_code, 201)

        personal = self._complete(self.seller_a, self.personal, '2026-10-01')
        self.assertEqual(personal.status_code, 403)
        own = self._complete(self.admin, self.personal, '2026-10-01')
        self.assertEqual(own.status_code, 201)

        status = self._get(DutyStatusView.as_view(), self.admin, '/api/daily-duties/status/', {'date': '2026-10-01'})
        by_title = {item['title']: item for item in status.data['items']}
        self.assertTrue(by_title['Otevrit']['completed'])
        self.assertEqual(by_title['Otevrit']['period_start'], '2026-10-01')
        self.assertTrue(by_title['Inventura']['completed'])
        self.assertEqual(by_title['Inventura']['period_start'], '2026-09-28')
        self.assertTrue(by_title['Report']['completed'])
        self.assertEqual(by_title['Report']['period_start'], '2026-10-01')
        self.assertEqual(by_title['Report']['period_label'], 'říjen 2026')


@override_settings(DAILY_DUTIES_MODULE_ENABLED=False)
class DailyDutyFlagOffTests(TestCase):
    def test_module_gate_blocks_when_disabled(self):
        user = WebUser.objects.create(
            id=8839, uzivatelske_jmeno='dd_off', jmeno='Off', prijmeni='Dd',
            role='ADMIN', heslo='x',
        )
        request = APIRequestFactory().get('/api/daily-duties/mine/')
        force_authenticate(request, user=user)
        response = MyDutiesView.as_view()(request)
        self.assertEqual(response.status_code, 403)
