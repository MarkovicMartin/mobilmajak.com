from datetime import date, time

from django.test import TestCase

from shifts.models import Smena
from shifts.shift_helpers import is_backoffice_user
from shifts.views import _normalize_pozice_smeny
from stores.models import Prodejna
from users.models import WebUser


class BackofficePositionTest(TestCase):
    def setUp(self):
        self.prodejna = Prodejna.objects.create(
            id=9901,
            nazev='Test Prodejna',
            nazev_kratkiy='Test',
            aktivni=True,
            povolena_pozice_servis=True,
        )

    def test_michaela_smckova_is_backoffice(self):
        user = WebUser(
            id=9901,
            jmeno='Michaela',
            prijmeni='Smrčková',
            role='PRODEJCE',
            prodejna_id=self.prodejna.id,
        )
        self.assertTrue(is_backoffice_user(user))

    def test_michaela_smrckova_is_backoffice(self):
        user = WebUser(
            id=9905,
            jmeno='Michaela',
            prijmeni='Smčková',
            role='PRODEJCE',
            prodejna_id=self.prodejna.id,
        )
        self.assertTrue(is_backoffice_user(user))

    def test_prodejce_bez_prodejny_is_backoffice(self):
        user = WebUser(
            id=9902,
            jmeno='Centr',
            prijmeni='Staff',
            role='PRODEJCE',
            prodejna_id=None,
        )
        self.assertTrue(is_backoffice_user(user))

    def test_normalize_pozice_backoffice(self):
        user = WebUser(
            id=9903,
            jmeno='Michaela',
            prijmeni='Smčková',
            role='PRODEJCE',
            prodejna_id=self.prodejna.id,
        )
        pozice = _normalize_pozice_smeny(self.prodejna, 'prace', 'prodej', user=user)
        self.assertEqual(pozice, 'backoffice')

    def test_migration_sets_existing_shifts(self):
        user = WebUser.objects.create(
            id=9904,
            uzivatelske_jmeno='michaela.smckova',
            jmeno='Michaela',
            prijmeni='Smčková',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=self.prodejna.id,
        )
        Smena.objects.create(
            user=user,
            prodejna=self.prodejna,
            datum=date(2026, 7, 2),
            cas_od=time(8, 0),
            cas_do=time(16, 0),
            typ_smeny='prace',
            pozice_smeny='prodej',
        )
        user.prodejna_id = None
        user.save(update_fields=['prodejna_id'])
        Smena.objects.filter(user=user, typ_smeny='prace').update(pozice_smeny='backoffice')
        smena = Smena.objects.get(user=user)
        self.assertEqual(smena.pozice_smeny, 'backoffice')
        self.assertIsNone(user.prodejna_id)
