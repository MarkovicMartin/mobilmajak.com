from django.test import TestCase

from shifts.shift_helpers import is_home_office_pozice
from shifts.views import _normalize_pozice_smeny, _resolve_work_shift_prodejna
from stores.models import Prodejna
from users.models import WebUser


class HomeOfficePositionTest(TestCase):
    def setUp(self):
        self.prodejna = Prodejna.objects.create(
            id=9910,
            nazev='Test Prodejna',
            nazev_kratkiy='Test',
            aktivni=True,
        )

    def test_admin_home_office_pozice(self):
        admin = WebUser(id=9910, jmeno='Admin', prijmeni='Test', role='ADMIN')
        pozice = _normalize_pozice_smeny(self.prodejna, 'prace', 'home_office', user=admin)
        self.assertEqual(pozice, 'home_office')

    def test_home_office_bez_prodejny(self):
        admin = WebUser.objects.create(
            id=9911,
            uzivatelske_jmeno='admin.ho',
            jmeno='Admin',
            prijmeni='Home',
            heslo='x',
            role='ADMIN',
            aktivni=True,
        )
        prodejna = _resolve_work_shift_prodejna(
            {'pozice_smeny': 'home_office'},
            'prace',
            admin,
            'home_office',
        )
        self.assertIsNone(prodejna)
        self.assertTrue(is_home_office_pozice('home_office'))
