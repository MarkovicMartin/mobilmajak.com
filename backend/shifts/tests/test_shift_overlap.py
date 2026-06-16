"""Dvě směny jeden den na stejné prodejně – povoleno bez časového překryvu."""
from datetime import date, time

from django.test import TestCase

from shifts.models import Smena
from shifts.shift_helpers import find_overlapping_shift, shifts_time_overlap
from stores.models import Prodejna
from users.models import WebUser


class ShiftOverlapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.prodejna = Prodejna.objects.create(
            nazev='Test Šternberk', nazev_kratkiy='ŠTR', aktivni=True,
        )
        cls.brigadnik = WebUser.objects.create(
            uzivatelske_jmeno='brig_overlap',
            jmeno='Brig',
            prijmeni='Overlap',
            heslo='x',
            role='BRIGADNIK',
            aktivni=True,
            prodejna_id=cls.prodejna.id,
        )

    def test_non_overlapping_same_day_same_store_allowed(self):
        d = date(2026, 6, 15)
        Smena.objects.create(
            user=self.brigadnik,
            prodejna=self.prodejna,
            datum=d,
            cas_od=time(8, 0),
            cas_do=time(14, 0),
            typ_smeny='prace',
            brigadnik_rezim='vypomoc',
        )
        conflict = find_overlapping_shift(
            self.brigadnik, d, self.prodejna, 'prace', time(14, 0), time(20, 0),
        )
        self.assertIsNone(conflict)

    def test_two_non_overlapping_shifts_persist(self):
        """DB nesmí blokovat druhou směnu (výpomoc + prodej) bez překryvu."""
        d = date(2026, 6, 17)
        Smena.objects.create(
            user=self.brigadnik,
            prodejna=self.prodejna,
            datum=d,
            cas_od=time(8, 0),
            cas_do=time(12, 0),
            typ_smeny='prace',
            brigadnik_rezim='vypomoc',
        )
        second = Smena.objects.create(
            user=self.brigadnik,
            prodejna=self.prodejna,
            datum=d,
            cas_od=time(12, 0),
            cas_do=time(16, 0),
            typ_smeny='prace',
            brigadnik_rezim='prodejce',
        )
        self.assertEqual(
            Smena.objects.filter(user=self.brigadnik, datum=d, prodejna=self.prodejna).count(),
            2,
        )
        self.assertEqual(second.brigadnik_rezim, 'prodejce')

    def test_overlapping_same_day_same_store_blocked(self):
        d = date(2026, 6, 16)
        Smena.objects.create(
            user=self.brigadnik,
            prodejna=self.prodejna,
            datum=d,
            cas_od=time(8, 0),
            cas_do=time(16, 0),
            typ_smeny='prace',
            brigadnik_rezim='vypomoc',
        )
        conflict = find_overlapping_shift(
            self.brigadnik, d, self.prodejna, 'prace', time(12, 0), time(20, 0),
        )
        self.assertIsNotNone(conflict)

    def test_shifts_time_overlap_helper(self):
        d = date(2026, 1, 1)
        self.assertFalse(shifts_time_overlap(d, time(8, 0), time(14, 0), time(14, 0), time(20, 0)))
        self.assertTrue(shifts_time_overlap(d, time(8, 0), time(15, 0), time(14, 0), time(20, 0)))
