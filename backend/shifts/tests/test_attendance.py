"""Testy docházky – zápis příchodu/odchodu a log hodin."""
from datetime import date, datetime, time, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from shifts.attendance_service import attendance_state_from_history, work_hours_from_history
from shifts.models import Smena, SmenaDochazka
from stores.models import Prodejna
from users.models import WebUser


class AttendanceServiceTests(TestCase):
    def test_compute_hours_closed_shift(self):
        base = timezone.make_aware(datetime(2026, 6, 9, 8, 0))
        history = [
            type('R', (), {'typ_akce': 'prichod', 'cas': base})(),
            type('R', (), {'typ_akce': 'odchod', 'cas': base + timedelta(hours=8)})(),
        ]
        self.assertEqual(work_hours_from_history(history), 8.0)

    def test_compute_hours_open_shift_includes_now(self):
        base = timezone.make_aware(datetime(2026, 6, 9, 8, 0))
        now = base + timedelta(hours=3, minutes=30)
        history = [
            type('R', (), {'typ_akce': 'prichod', 'cas': base})(),
        ]
        hours = work_hours_from_history(history, now=now)
        self.assertEqual(hours, 3.5)


class AttendanceApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.prodejna = Prodejna.objects.create(
            id=9201, nazev='Test', nazev_kratkiy='TST', aktivni=True,
        )
        cls.prodejce_a = WebUser.objects.create(
            id=9201,
            uzivatelske_jmeno='prod_a',
            jmeno='Anna',
            prijmeni='Babusic',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=cls.prodejna.id,
        )
        cls.prodejce_b = WebUser.objects.create(
            id=9202,
            uzivatelske_jmeno='prod_b',
            jmeno='Bára',
            prijmeni='Nová',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=cls.prodejna.id,
        )
        cls.admin = WebUser.objects.create(
            id=9203,
            uzivatelske_jmeno='admin_test',
            jmeno='Admin',
            prijmeni='Test',
            heslo='x',
            role='ADMIN',
            aktivni=True,
        )
        cls.today = date.today()
        cls.smena_a = Smena.objects.create(
            user=cls.prodejce_a,
            prodejna=cls.prodejna,
            datum=cls.today,
            cas_od=time(8, 0),
            cas_do=time(16, 0),
            typ_smeny='prace',
        )
        cls.smena_b = Smena.objects.create(
            user=cls.prodejce_b,
            prodejna=cls.prodejna,
            datum=cls.today,
            cas_od=time(9, 0),
            cas_do=time(17, 0),
            typ_smeny='prace',
        )

    def test_prodejce_records_own_shift(self):
        client = APIClient()
        client.force_authenticate(user=self.prodejce_b)
        res = client.post(
            '/api/shifts/attendance/',
            {'smena_id': self.smena_b.id, 'typ_akce': 'prichod'},
            format='json',
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(
            SmenaDochazka.objects.filter(smena=self.smena_b, typ_akce='prichod').count(),
            1,
        )
        self.assertEqual(
            SmenaDochazka.objects.filter(smena=self.smena_a).count(),
            0,
        )

    def test_prodejce_cannot_record_other_shift(self):
        client = APIClient()
        client.force_authenticate(user=self.prodejce_b)
        res = client.post(
            '/api/shifts/attendance/',
            {'smena_id': self.smena_a.id, 'typ_akce': 'prichod'},
            format='json',
        )
        self.assertEqual(res.status_code, 403)

    def test_attendance_log_lists_all_users(self):
        SmenaDochazka.objects.create(
            smena=self.smena_a,
            typ_akce='prichod',
            cas=timezone.now(),
        )
        SmenaDochazka.objects.create(
            smena=self.smena_b,
            typ_akce='prichod',
            cas=timezone.now(),
        )
        client = APIClient()
        client.force_authenticate(user=self.admin)
        mesic = f'{self.today.year}-{self.today.month:02d}'
        res = client.get(f'/api/shifts/attendance/log/?mesic={mesic}')
        self.assertEqual(res.status_code, 200)
        jmena = {e['jmeno'] for e in res.data['entries']}
        self.assertIn('Anna Babusic', jmena)
        self.assertIn('Bára Nová', jmena)

    def test_smeny_list_admin_returns_both_users_shifts(self):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        mesic = f'{self.today.year}-{self.today.month:02d}'
        res = client.get(f'/api/shifts/?mesic={mesic}')
        self.assertEqual(res.status_code, 200)
        user_ids = {row['user_id'] for row in res.data}
        self.assertEqual(user_ids, {self.prodejce_a.id, self.prodejce_b.id})

    def test_calendar_with_absence_today_returns_200(self):
        Smena.objects.create(
            user=self.prodejce_a,
            prodejna=None,
            datum=self.today,
            cas_od=time(8, 0),
            cas_do=time(16, 0),
            typ_smeny='dovolena',
            aktivni=True,
        )
        client = APIClient()
        client.force_authenticate(user=self.admin)
        mesic = f'{self.today.year}-{self.today.month:02d}'
        res = client.get(f'/api/shifts/calendar/?mesic={mesic}&prodejna=vse')
        self.assertEqual(res.status_code, 200)
        self.assertIn('dnes_smeny', res.data)
        self.assertTrue(any('Dovolená' in row for row in res.data['dnes_smeny']))
