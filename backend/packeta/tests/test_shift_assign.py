"""Testy přiřazení prodejce k výdeji balíku."""
from datetime import date, datetime, time, timedelta

from django.test import TestCase
from django.utils import timezone

from packeta.shift_assign import resolve_prodejce_for_packeta
from shifts.models import Smena
from stores.models import Prodejna
from users.models import WebUser


class ShiftAssignTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.prodejna = Prodejna.objects.create(
            id=9101, nazev='Test', nazev_kratkiy='TST', aktivni=True,
        )
        cls.user_a = WebUser.objects.create(
            id=9101,
            uzivatelske_jmeno='prodejce_a',
            jmeno='Anna',
            prijmeni='A',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=cls.prodejna.id,
        )
        cls.user_b = WebUser.objects.create(
            id=9102,
            uzivatelske_jmeno='prodejce_b',
            jmeno='Boris',
            prijmeni='B',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=cls.prodejna.id,
        )
        cls.day = date(2026, 6, 10)
        Smena.objects.create(
            prodejna=cls.prodejna,
            user=cls.user_a,
            datum=cls.day,
            cas_od=time(8, 0),
            cas_do=time(16, 0),
            typ_smeny='prace',
            pozice_smeny='prodej',
            aktivni=True,
        )
        Smena.objects.create(
            prodejna=cls.prodejna,
            user=cls.user_b,
            datum=cls.day,
            cas_od=time(16, 0),
            cas_do=time(20, 0),
            typ_smeny='prace',
            pozice_smeny='prodej',
            aktivni=True,
        )

    def _aware(self, hour, minute=0):
        loc = timezone.get_current_timezone()
        return timezone.make_aware(datetime.combine(self.day, time(hour, minute)), loc)

    def test_inside_shift(self):
        pid = resolve_prodejce_for_packeta(self.prodejna.id, self._aware(10))
        self.assertEqual(pid, self.user_a.id)

    def test_slightly_after_shift_end(self):
        pid = resolve_prodejce_for_packeta(self.prodejna.id, self._aware(16, 20))
        self.assertEqual(pid, self.user_b.id)

    def test_before_first_shift(self):
        pid = resolve_prodejce_for_packeta(self.prodejna.id, self._aware(7, 30))
        self.assertEqual(pid, self.user_a.id)

    def test_no_sales_shift_ignored(self):
        Smena.objects.filter(pozice_smeny='prodej').update(pozice_smeny='servis')
        pid = resolve_prodejce_for_packeta(self.prodejna.id, self._aware(10))
        self.assertIsNone(pid)

    def test_no_shift_on_store(self):
        pid = resolve_prodejce_for_packeta(9999, self._aware(10))
        self.assertIsNone(pid)

    def test_previous_day_shift(self):
        prev = self.day - timedelta(days=1)
        Smena.objects.create(
            prodejna=self.prodejna,
            user=self.user_b,
            datum=prev,
            cas_od=time(16, 0),
            cas_do=time(20, 0),
            typ_smeny='prace',
            pozice_smeny='prodej',
            aktivni=True,
        )
        loc = timezone.get_current_timezone()
        cas = timezone.make_aware(datetime.combine(self.day, time(0, 30)), loc)
        pid = resolve_prodejce_for_packeta(self.prodejna.id, cas)
        self.assertEqual(pid, self.user_b.id)

    def test_overlap_prefers_seller_with_nearby_sales(self):
        from analytics.models import WebProdejeAll
        from decimal import Decimal

        overlap_day = date(2026, 6, 11)
        Smena.objects.create(
            prodejna=self.prodejna,
            user=self.user_a,
            datum=overlap_day,
            cas_od=time(8, 0),
            cas_do=time(20, 0),
            typ_smeny='prace',
            pozice_smeny='prodej',
            aktivni=True,
        )
        Smena.objects.create(
            prodejna=self.prodejna,
            user=self.user_b,
            datum=overlap_day,
            cas_od=time(8, 0),
            cas_do=time(17, 0),
            typ_smeny='prace',
            pozice_smeny='prodej',
            aktivni=True,
        )
        WebProdejeAll.objects.create(
            typ=overlap_day,
            doklad='UCT-OVERLAP-1',
            kod='P100',
            nazev='Test',
            pocet_kusu=1,
            cena_ks_vcl_dph=Decimal('100'),
            id_prodejce=self.user_a.id,
            id_prodejny=self.prodejna.id,
            stredisko='Test',
            cas_prodeje=time(10, 0),
        )
        loc = timezone.get_current_timezone()
        cas = timezone.make_aware(datetime.combine(overlap_day, time(10, 30)), loc)
        pid = resolve_prodejce_for_packeta(self.prodejna.id, cas)
        self.assertEqual(pid, self.user_a.id)
