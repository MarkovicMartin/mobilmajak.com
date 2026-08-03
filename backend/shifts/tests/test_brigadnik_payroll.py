"""Testy výplaty brigádníka – režim výpomoc vs. jako prodejce."""
from datetime import date, time
from decimal import Decimal

from django.test import TestCase

from shifts.models import Smena
from shifts.payroll_service import aggregate_hours_by_user, build_payroll_row
from stores.models import Prodejna
from users.models import WebUser


class BrigadnikPayrollTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.prodejna = Prodejna.objects.create(
            id=9101, nazev='Test', nazev_kratkiy='TST', aktivni=True,
        )
        cls.brigadnik = WebUser.objects.create(
            id=9101,
            uzivatelske_jmeno='brig_test',
            jmeno='Brig',
            prijmeni='Test',
            heslo='x',
            role='BRIGADNIK',
            aktivni=True,
            prodejna_id=cls.prodejna.id,
            mzda_zaklad=Decimal('100'),
            mzda_doplnky=[],
        )

    def _shift(self, datum, rezim='prodejce', hours=8):
        cas_do = time(8 + hours, 0) if hours < 16 else time(16, 0)
        return Smena.objects.create(
            user=self.brigadnik,
            prodejna=self.prodejna,
            datum=datum,
            cas_od=time(8, 0),
            cas_do=cas_do,
            typ_smeny='prace',
            brigadnik_rezim=rezim,
        )

    def test_vypomoc_hours_at_150_no_provize(self):
        self._shift(date(2026, 3, 3), rezim='vypomoc')
        hours_map = aggregate_hours_by_user(2026, 3)
        uid = self.brigadnik.id
        self.assertEqual(hours_map[uid]['vypomoc_h'], 8)
        self.assertEqual(hours_map[uid]['prodejce_h'], 0)

        row = build_payroll_row(
            self.brigadnik, 2026, 3, hours_map, date(2026, 3, 1), {}, 160,
            {uid: {'polozky_nad_100': 10}}, {uid: (50, None)}, {},
        )
        self.assertEqual(row['zaklad_body'], 1200.0)  # 8 × 150
        self.assertEqual(row['provize_body'], 0)

    def test_prodejce_hours_at_profile_rate_with_provize(self):
        self._shift(date(2026, 3, 4), rezim='prodejce')
        hours_map = aggregate_hours_by_user(2026, 3)
        uid = self.brigadnik.id
        self.assertEqual(hours_map[uid]['prodejce_h'], 8)
        self.assertEqual(hours_map[uid]['vypomoc_h'], 0)

        row = build_payroll_row(
            self.brigadnik, 2026, 3, hours_map, date(2026, 3, 1), {}, 160,
            {uid: {'polozky_nad_100': 2}}, {uid: (0, None)}, {},
        )
        self.assertEqual(row['zaklad_body'], 800.0)  # 8 × 100
        self.assertGreater(row['provize_body'], 0)

    def test_mixed_modes_split_hours(self):
        self._shift(date(2026, 3, 5), rezim='vypomoc', hours=4)
        self._shift(date(2026, 3, 6), rezim='prodejce', hours=4)
        hours_map = aggregate_hours_by_user(2026, 3)
        uid = self.brigadnik.id
        self.assertEqual(hours_map[uid]['vypomoc_h'], 4)
        self.assertEqual(hours_map[uid]['prodejce_h'], 4)

        row = build_payroll_row(
            self.brigadnik, 2026, 3, hours_map, date(2026, 3, 1), {}, 160,
            {uid: {'polozky_nad_100': 1}}, {uid: (0, None)}, {},
        )
        # 4×150 + 4×100 = 1000
        self.assertEqual(row['zaklad_body'], 1000.0)
        self.assertGreater(row['provize_body'], 0)

    def test_brigadnik_no_pol_dok_bonus_nor_penalizace(self):
        self._shift(date(2026, 3, 7), rezim='prodejce')
        hours_map = aggregate_hours_by_user(2026, 3)
        uid = self.brigadnik.id
        pol_dok_map = {uid: {'pol_dok': 3.5, 'unikatni_doklady': 12}}

        row = build_payroll_row(
            self.brigadnik, 2026, 3, hours_map, date(2026, 3, 1), {}, 160,
            {uid: {'polozky_nad_100': 2}}, {uid: (0, None)}, {},
            pol_dok_map=pol_dok_map,
        )
        self.assertGreater(row['pol_dok'], 2)
        self.assertEqual(row['pol_dok_odmena_body'], 0.0)

        pol_dok_map[uid] = {'pol_dok': 1.2, 'unikatni_doklady': 8}
        row_pen = build_payroll_row(
            self.brigadnik, 2026, 3, hours_map, date(2026, 3, 1), {}, 160,
            {uid: {'polozky_nad_100': 2}}, {uid: (0, None)}, {},
            pol_dok_map=pol_dok_map,
        )
        self.assertLess(row_pen['pol_dok'], 2)
        self.assertEqual(row_pen['pol_dok_odmena_body'], 0.0)

    def test_holiday_shift_hours_counted_double(self):
        # 1. 5. 2026 = Svátek práce
        self._shift(date(2026, 5, 1), rezim='prodejce', hours=8)
        hours_map = aggregate_hours_by_user(2026, 5)
        uid = self.brigadnik.id
        self.assertEqual(hours_map[uid]['odpracovano_h'], 16)
        self.assertEqual(hours_map[uid]['prodejce_h'], 16)
        self.assertEqual(hours_map[uid]['svatek_h'], 8)

        row = build_payroll_row(
            self.brigadnik, 2026, 5, hours_map, date(2026, 5, 1), {}, 160,
            {uid: {'polozky_nad_100': 0}}, {uid: (0, None)}, {},
        )
        self.assertEqual(row['zaklad_body'], 1600.0)  # 16 × 100
        self.assertEqual(row['svatek_h'], 8)
