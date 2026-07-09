from datetime import date, time

from django.test import TestCase

from shifts.models import Smena
from shifts.shift_helpers import apply_backoffice_calendar_filter
from stores.models import Prodejna
from users.models import WebUser


class BackofficeCalendarFilterTest(TestCase):
    def setUp(self):
        self.prodejna = Prodejna.objects.create(
            nazev='Globus',
            nazev_kratkiy='GLO',
            aktivni=True,
        )
        self.backoffice_user = WebUser.objects.create(
            id=99101,
            jmeno='Michaela',
            prijmeni='Smčková',
            uzivatelske_jmeno='michaela.backoffice.cal',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=None,
        )
        self.store_user = WebUser.objects.create(
            id=99102,
            jmeno='Jan',
            prijmeni='Prodejce',
            uzivatelske_jmeno='jan.prodejce.cal',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=self.prodejna.id,
        )

    def test_backoffice_filter_returns_only_backoffice_shifts(self):
        Smena.objects.create(
            user=self.backoffice_user,
            prodejna=None,
            datum=date(2026, 7, 10),
            cas_od=time(8, 0),
            cas_do=time(16, 0),
            typ_smeny='prace',
            pozice_smeny='backoffice',
            poznamka='Fakturace',
        )
        Smena.objects.create(
            user=self.store_user,
            prodejna=self.prodejna,
            datum=date(2026, 7, 10),
            cas_od=time(8, 0),
            cas_do=time(16, 0),
            typ_smeny='prace',
            pozice_smeny='prodej',
        )
        qs = apply_backoffice_calendar_filter(Smena.objects.filter(aktivni=True))
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pozice_smeny, 'backoffice')
