"""Testy docházky – zápis příchodu/odchodu a log hodin."""
from datetime import date, datetime, time, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from shifts.attendance_service import (
    attendance_state_from_history,
    build_absent_stores_report,
    build_today_work_board,
    format_local_hm,
    work_hours_from_history,
)
from shifts.models import Smena, SmenaDochazka
from stores.models import Prodejna
from users.models import WebUser


class AttendanceServiceTests(TestCase):
    def test_format_local_hm_from_utc(self):
        # make_aware() bez tz používá Europe/Prague — UTC musíme zadat explicitně
        dt = timezone.make_aware(datetime(2026, 6, 11, 8, 25), timezone.utc)
        self.assertEqual(format_local_hm(dt), '10:25')

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

    def test_attendance_log_with_backoffice_shift_without_store(self):
        """Backoffice směna bez prodejny nesmí shodit attendance log (500)."""
        Smena.objects.create(
            user=self.admin,
            prodejna=None,
            datum=self.today,
            cas_od=time(7, 30),
            cas_do=time(15, 30),
            typ_smeny='prace',
            pozice_smeny='backoffice',
            aktivni=True,
            poznamka='admin práce',
        )
        client = APIClient()
        client.force_authenticate(user=self.admin)
        mesic = f'{self.today.year}-{self.today.month:02d}'
        res = client.get(f'/api/shifts/attendance/log/?mesic={mesic}')
        self.assertEqual(res.status_code, 200)
        bo = next(
            (e for e in res.data['entries'] if e['user_id'] == self.admin.id),
            None,
        )
        self.assertIsNotNone(bo)
        self.assertEqual(bo['prodejna'], 'Backoffice')

    def test_smeny_list_admin_returns_both_users_shifts(self):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        mesic = f'{self.today.year}-{self.today.month:02d}'
        res = client.get(f'/api/shifts/?mesic={mesic}')
        self.assertEqual(res.status_code, 200)
        user_ids = {row['user_id'] for row in res.data}
        self.assertEqual(user_ids, {self.prodejce_a.id, self.prodejce_b.id})

    def test_smeny_list_datum_filter_returns_only_that_day(self):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        other = self.today + timedelta(days=1)
        Smena.objects.create(
            user=self.prodejce_a,
            prodejna=self.prodejna,
            datum=other,
            cas_od=time(9, 0),
            cas_do=time(17, 0),
            typ_smeny='prace',
            aktivni=True,
        )
        res = client.get(f'/api/shifts/?datum={self.today.isoformat()}')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(res.data) >= 1)
        self.assertTrue(all(str(row['datum']).startswith(self.today.isoformat()) for row in res.data))

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

    def test_today_board_with_backoffice_shift_without_store(self):
        """Backoffice směna bez prodejny nesmí shodit today-board (500)."""
        Smena.objects.create(
            user=self.admin,
            prodejna=None,
            datum=self.today,
            cas_od=time(7, 30),
            cas_do=time(15, 30),
            typ_smeny='prace',
            pozice_smeny='backoffice',
            aktivni=True,
            poznamka='admin práce',
        )
        board = build_today_work_board()
        backoffice = next(
            (s for s in board['stores'] if s['prodejna_id'] == 'backoffice'),
            None,
        )
        self.assertIsNotNone(backoffice)
        self.assertEqual(backoffice['prodejna_nazev'], 'Backoffice')
        self.assertTrue(any(p['user_id'] == self.admin.id for p in backoffice['people']))

        client = APIClient()
        client.force_authenticate(user=self.admin)
        res = client.get('/api/shifts/attendance/today-board/')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(
            any(s['prodejna_id'] == 'backoffice' for s in res.data['stores'])
        )

    def test_absent_report_with_home_office_shift_without_store(self):
        now = timezone.make_aware(datetime.combine(self.today, time(10, 0)))
        Smena.objects.create(
            user=self.admin,
            prodejna=None,
            datum=self.today,
            cas_od=time(8, 0),
            cas_do=time(16, 0),
            typ_smeny='prace',
            pozice_smeny='home_office',
            aktivni=True,
        )
        report = build_absent_stores_report(now=now)
        rows = report['absent_stores'] + report['ok_stores']
        home = next((s for s in rows if s['prodejna_id'] == 'home_office'), None)
        self.assertIsNotNone(home)
        self.assertEqual(home['prodejna_nazev'], 'Home office')
