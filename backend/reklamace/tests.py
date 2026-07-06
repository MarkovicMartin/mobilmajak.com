from datetime import datetime, timedelta
from pathlib import Path
import json
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from reklamace.management.commands.check_reklamace_reminders import Command as CheckRemindersCommand
from reklamace.management.commands.import_reklamace import parse_excel
from reklamace.models import (
    OVERDUE_HOURS,
    ReklamaceNotifikace,
    ReklamacePolozka,
    ReklamaceStatus,
    ZpusobVyrizeni,
)
from reklamace.reminders import send_10d_reminders, send_2d_tracking_reminders, send_30d_slack_reminders
from reklamace.znacka import generate_nase_znacka
from stores.models import Prodejna
from users.models import WebUser


def _make_user(pk=1, **kwargs):
    defaults = {
        'uzivatelske_jmeno': f'reklamace{pk}',
        'jmeno': 'Test',
        'prijmeni': 'User',
        'heslo': 'x',
        'role': 'PRODEJCE',
        'aktivni': True,
        'moduly': [],
        'email': f'reklamace{pk}@example.com',
    }
    defaults.update(kwargs)
    user, _ = WebUser.objects.update_or_create(id=pk, defaults=defaults)
    return user


class ReklamaceBootstrapTest(SimpleTestCase):
    def test_bootstrap_has_required_fields(self):
        path = Path(__file__).resolve().parent / 'bootstrap' / 'mastersheet.json'
        items = json.loads(path.read_text(encoding='utf-8'))
        self.assertGreater(len(items), 10)
        sample = items[0]
        for key in ('nase_znacka', 'nazev_zbozi', 'prodejna'):
            self.assertIn(key, sample)

    def test_parse_excel_if_available(self):
        excel = Path.home() / 'Downloads' / 'Mastersheet - prodejny.xlsx'
        if not excel.is_file():
            self.skipTest('Mastersheet Excel not on disk')
        items = parse_excel(excel)
        self.assertGreater(len(items), 10)
        self.assertTrue(items[0]['nase_znacka'].startswith('R'))


@override_settings(ROOT_URLCONF='webapp.urls')
class ReklamaceWorkflowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user()
        self.client.force_authenticate(user=self.user)

    def _create(self, **kwargs):
        defaults = {
            'nase_znacka': 'R99999',
            'nazev_zbozi': 'Test díl',
            'prodejna': 'Servis',
            'status': ReklamaceStatus.NEZPRACOVANE,
        }
        defaults.update(kwargs)
        return ReklamacePolozka.objects.create(**defaults)

    def test_is_overdue_only_for_nezpracovane_after_24h(self):
        item = self._create(nase_znacka='R90001')
        self.assertFalse(item.is_overdue)
        ReklamacePolozka.objects.filter(pk=item.pk).update(
            created_at=timezone.now() - timedelta(hours=OVERDUE_HOURS + 1),
        )
        item.refresh_from_db()
        self.assertTrue(item.is_overdue)

        item.status = ReklamaceStatus.ODESLANE
        item.save(update_fields=['status'])
        self.assertFalse(item.is_overdue)

    def test_list_excludes_vyrizene_by_default(self):
        self._create(nase_znacka='R90002', status=ReklamaceStatus.VRIZENE)
        self._create(nase_znacka='R90003', status=ReklamaceStatus.ODESLANE)
        res = self.client.get('/api/reklamace/polozky/')
        self.assertEqual(res.status_code, 200)
        znacky = {row['nase_znacka'] for row in res.data}
        self.assertNotIn('R90002', znacky)
        self.assertIn('R90003', znacky)

    def test_list_include_resolved(self):
        self._create(nase_znacka='R90004', status=ReklamaceStatus.VRIZENE)
        res = self.client.get('/api/reklamace/polozky/?include_resolved=1')
        znacky = {row['nase_znacka'] for row in res.data}
        self.assertIn('R90004', znacky)

    def test_odeslat_dodavateli_transition(self):
        item = self._create(nase_znacka='R90005')
        res = self.client.post(f'/api/reklamace/polozky/{item.id}/odeslat_dodavateli/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['status'], ReklamaceStatus.ODESLANE)
        self.assertIsNotNone(res.data['datum_odeslani'])
        self.assertIsNotNone(res.data['odeslano_dodavateli_at'])

    def test_odeslat_dodavateli_rejects_non_nezpracovane(self):
        item = self._create(nase_znacka='R90006', status=ReklamaceStatus.ODESLANE)
        res = self.client.post(f'/api/reklamace/polozky/{item.id}/odeslat_dodavateli/')
        self.assertEqual(res.status_code, 400)

    def test_potvrdit_zpracovani_transition(self):
        item = self._create(nase_znacka='R90007', status=ReklamaceStatus.ODESLANE)
        res = self.client.post(
            f'/api/reklamace/polozky/{item.id}/potvrdit_zpracovani/',
            {'zpusob_vyrizeni': ZpusobVyrizeni.VYMENA},
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['status'], ReklamaceStatus.VRIZENE)
        self.assertEqual(res.data['zpusob_vyrizeni'], ZpusobVyrizeni.VYMENA)
        self.assertIsNotNone(res.data['datum_vyrizeni'])

    def test_potvrdit_zpracovani_rejects_nezpracovane(self):
        item = self._create(nase_znacka='R90008')
        res = self.client.post(
            f'/api/reklamace/polozky/{item.id}/potvrdit_zpracovani/',
            {'zpusob_vyrizeni': ZpusobVyrizeni.DOBROPIS},
            format='json',
        )
        self.assertEqual(res.status_code, 400)

    def test_serializer_includes_is_overdue(self):
        item = self._create(nase_znacka='R90009')
        ReklamacePolozka.objects.filter(pk=item.pk).update(
            created_at=timezone.now() - timedelta(hours=OVERDUE_HOURS + 2),
        )
        res = self.client.get(f'/api/reklamace/polozky/{item.id}/')
        self.assertTrue(res.data['is_overdue'])


class ReklamaceZnackaGenerationTests(TestCase):
    JULY_2026 = datetime(2026, 7, 6, 12, 0, tzinfo=ZoneInfo('Europe/Prague'))

    def test_first_of_month(self):
        with patch('reklamace.znacka.timezone.now', return_value=self.JULY_2026):
            self.assertEqual(generate_nase_znacka(), 'R2607001')

    def test_second_in_same_month(self):
        ReklamacePolozka.objects.create(
            nase_znacka='R2607001',
            nazev_zbozi='Díl',
            prodejna='Servis',
        )
        with patch('reklamace.znacka.timezone.now', return_value=self.JULY_2026):
            self.assertEqual(generate_nase_znacka(), 'R2607002')

    def test_month_rollover(self):
        ReklamacePolozka.objects.create(
            nase_znacka='R2607005',
            nazev_zbozi='Díl',
            prodejna='Servis',
        )
        august = datetime(2026, 8, 1, 9, 0, tzinfo=ZoneInfo('Europe/Prague'))
        with patch('reklamace.znacka.timezone.now', return_value=august):
            self.assertEqual(generate_nase_znacka(), 'R2608001')

    def test_ignores_legacy_znacka_format(self):
        ReklamacePolozka.objects.create(
            nase_znacka='R25022',
            nazev_zbozi='Starý import',
            prodejna='Servis',
        )
        with patch('reklamace.znacka.timezone.now', return_value=self.JULY_2026):
            self.assertEqual(generate_nase_znacka(), 'R2607001')


@override_settings(ROOT_URLCONF='webapp.urls')
class ReklamaceApiCreateZnackaTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user()
        self.client.force_authenticate(user=self.user)
        self.july_2026 = datetime(2026, 7, 6, 12, 0, tzinfo=ZoneInfo('Europe/Prague'))

    def test_api_create_auto_generates_znacka(self):
        with patch('reklamace.znacka.timezone.now', return_value=self.july_2026):
            res = self.client.post(
                '/api/reklamace/polozky/',
                {
                    'nase_znacka': 'R99999',
                    'nazev_zbozi': 'Nový díl',
                    'prodejna': 'Servis',
                },
                format='json',
            )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['nase_znacka'], 'R2607001')
        self.assertEqual(res.data['created_by_id'], self.user.id)


class ReklamaceTrackingReminderTests(TestCase):
    def setUp(self):
        self.user = _make_user()
        self.now = timezone.make_aware(datetime(2026, 7, 8, 10, 0))

    def _create_open(self, **kwargs):
        defaults = {
            'nase_znacka': 'R2607001',
            'nazev_zbozi': 'Test díl',
            'prodejna': 'Servis',
            'cislo_zasilky': '',
            'created_by': self.user,
        }
        defaults.update(kwargs)
        return ReklamacePolozka.objects.create(**defaults)

    def test_sends_once_for_missing_tracking_after_2_days(self):
        item = self._create_open()
        ReklamacePolozka.objects.filter(pk=item.pk).update(
            created_at=self.now - timedelta(days=3),
        )
        count = send_2d_tracking_reminders(now=self.now)
        self.assertEqual(count, 1)
        notif = ReklamaceNotifikace.objects.get(reklamace=item)
        self.assertEqual(notif.typ, 'reminder_tracking_2d')
        self.assertIn('R2607001', notif.message)
        item.refresh_from_db()
        self.assertIsNotNone(item.reminder_tracking_2d_sent_at)

        count_again = send_2d_tracking_reminders(now=self.now)
        self.assertEqual(count_again, 0)
        self.assertEqual(ReklamaceNotifikace.objects.filter(reklamace=item).count(), 1)

    def test_skips_when_tracking_present(self):
        item = self._create_open(cislo_zasilky='DR123')
        ReklamacePolozka.objects.filter(pk=item.pk).update(
            created_at=self.now - timedelta(days=3),
        )
        self.assertEqual(send_2d_tracking_reminders(now=self.now), 0)

    def test_skips_vyrizene(self):
        item = self._create_open(status=ReklamaceStatus.VRIZENE)
        ReklamacePolozka.objects.filter(pk=item.pk).update(
            created_at=self.now - timedelta(days=3),
        )
        self.assertEqual(send_2d_tracking_reminders(now=self.now), 0)

    def test_skips_before_2_days(self):
        item = self._create_open()
        ReklamacePolozka.objects.filter(pk=item.pk).update(
            created_at=self.now - timedelta(days=1),
        )
        self.assertEqual(send_2d_tracking_reminders(now=self.now), 0)


@override_settings(ROOT_URLCONF='webapp.urls')
class ReklamaceAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user(pk=10, role='PRODEJCE')
        self.client.force_authenticate(user=self.user)

    def test_prodejce_can_list_and_create(self):
        res = self.client.get('/api/reklamace/polozky/')
        self.assertEqual(res.status_code, 200)
        res = self.client.post(
            '/api/reklamace/polozky/',
            {'nase_znacka': 'R80001', 'nazev_zbozi': 'Díl', 'prodejna': 'Servis'},
            format='json',
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['created_by_id'], self.user.id)

    def test_unauthenticated_denied(self):
        self.client.force_authenticate(user=None)
        res = self.client.get('/api/reklamace/polozky/')
        self.assertIn(res.status_code, (401, 403))


@override_settings(ROOT_URLCONF='webapp.urls')
class ReklamaceReminderTests(TestCase):
    def setUp(self):
        self.creator = _make_user(pk=20, email='creator@example.com')
        self.vedouci = _make_user(pk=21, email='vedouci@example.com')
        self.store = Prodejna.objects.create(
            id=9001,
            nazev='Servis',
            nazev_kratkiy='SRV',
            vedouci_user_id=self.vedouci.id,
        )

    def _create(self, **kwargs):
        defaults = {
            'nase_znacka': 'R70001',
            'nazev_zbozi': 'Test díl',
            'prodejna': self.store.nazev,
            'status': ReklamaceStatus.NEZPRACOVANE,
            'created_by': self.creator,
        }
        defaults.update(kwargs)
        item = ReklamacePolozka.objects.create(**defaults)
        ReklamacePolozka.objects.filter(pk=item.pk).update(
            created_at=timezone.now() - timedelta(days=11),
        )
        item.refresh_from_db()
        return item

    def test_10d_creates_in_app_notifications_for_creator_and_vedouci(self):
        item = self._create(nase_znacka='R70010')
        sent = send_10d_reminders()
        self.assertEqual(sent, 2)
        self.assertEqual(ReklamaceNotifikace.objects.filter(reklamace=item).count(), 2)
        item.refresh_from_db()
        self.assertIsNotNone(item.reminder_10d_sent_at)

    def test_10d_skips_vyrizene(self):
        item = self._create(nase_znacka='R70011', status=ReklamaceStatus.VRIZENE)
        sent = send_10d_reminders()
        self.assertEqual(sent, 0)
        self.assertEqual(ReklamaceNotifikace.objects.filter(reklamace=item).count(), 0)

    def test_10d_no_duplicate_on_second_run(self):
        self._create(nase_znacka='R70012')
        self.assertEqual(send_10d_reminders(), 2)
        self.assertEqual(send_10d_reminders(), 0)
        self.assertEqual(ReklamaceNotifikace.objects.count(), 2)

    @patch('reklamace.reminders.send_slack_dm', return_value=True)
    @patch('reklamace.reminders.slack_user_id_for_web_user', return_value='U999')
    def test_30d_slack_to_creator_and_vedouci(self, _lookup, mock_dm):
        item = self._create(nase_znacka='R70030')
        ReklamacePolozka.objects.filter(pk=item.pk).update(
            created_at=timezone.now() - timedelta(days=31),
        )
        sent = send_30d_slack_reminders()
        self.assertEqual(sent, 2)
        self.assertEqual(mock_dm.call_count, 2)
        item.refresh_from_db()
        self.assertIsNotNone(item.reminder_30d_slack_sent_at)

    @patch('reklamace.reminders.send_slack_dm', return_value=True)
    @patch('reklamace.reminders.slack_user_id_for_web_user', return_value='U999')
    def test_30d_no_duplicate_on_second_run(self, _lookup, mock_dm):
        self._create(nase_znacka='R70031')
        ReklamacePolozka.objects.filter(nase_znacka='R70031').update(
            created_at=timezone.now() - timedelta(days=31),
        )
        self.assertEqual(send_30d_slack_reminders(), 2)
        mock_dm.reset_mock()
        self.assertEqual(send_30d_slack_reminders(), 0)
        self.assertEqual(mock_dm.call_count, 0)

    def test_management_command_runs(self):
        self._create(nase_znacka='R70040')
        cmd = CheckRemindersCommand()
        cmd.handle(dry_run=True)

    def test_notifications_api(self):
        item = self._create(nase_znacka='R70050')
        send_10d_reminders()
        client = APIClient()
        client.force_authenticate(user=self.creator)
        res = client.get('/api/reklamace/notifikace/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertIn(item.nase_znacka, res.data[0]['message'])
        res = client.post('/api/reklamace/notifikace/mark-read/', {'ids': [res.data[0]['id']]}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            ReklamaceNotifikace.objects.filter(user=self.creator, read_at__isnull=True).count(),
            0,
        )
