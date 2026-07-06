from django.test import SimpleTestCase, TestCase, override_settings
from pathlib import Path
from rest_framework.test import APIClient

from users.models import WebUser
from wreck_parts.management.commands.import_wreck_parts import parse_excel
from wreck_parts.models import WreckPart


def _make_user(pk=1):
    user, _ = WebUser.objects.update_or_create(
        id=pk,
        defaults={
            'uzivatelske_jmeno': f'wreck{pk}',
            'jmeno': 'Test',
            'prijmeni': 'User',
            'heslo': 'x',
            'role': 'PRODEJCE',
            'aktivni': True,
            'moduly': [],
        },
    )
    return user


class WreckPartsImportTest(SimpleTestCase):
    def test_bootstrap_json_exists(self):
        path = Path(__file__).resolve().parent / 'bootstrap' / 'mastersheet.json'
        self.assertTrue(path.is_file(), 'bootstrap JSON missing')

    def test_parse_excel_if_available(self):
        excel = Path.home() / 'Downloads' / 'Mastersheet - prodejny.xlsx'
        if not excel.is_file():
            self.skipTest('Mastersheet Excel not on disk')
        items = parse_excel(excel)
        self.assertGreater(len(items), 40)
        self.assertEqual(items[0]['part_type'], 'LCD')


@override_settings(ROOT_URLCONF='webapp.urls')
class WreckPartsAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user()
        self.client.force_authenticate(user=self.user)

    def test_prodejce_can_list_parts(self):
        WreckPart.objects.create(store='Servis', model_name='iPhone 8', part_type='LCD')
        res = self.client.get('/api/wreck-parts/parts/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)

    def test_prodejce_can_access_store_summary(self):
        res = self.client.get('/api/wreck-parts/store-summary/')
        self.assertEqual(res.status_code, 200)

    def test_unauthenticated_denied(self):
        self.client.force_authenticate(user=None)
        res = self.client.get('/api/wreck-parts/parts/')
        self.assertIn(res.status_code, (401, 403))
