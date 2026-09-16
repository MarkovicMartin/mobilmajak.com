"""Rozpad čisté výplaty na HPP a DPP."""
from datetime import date, time
from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from shifts.hpp_dpp import (
    DPP_GROSS_MAX,
    HPP_GROSS_MIN,
    REZIM_MAX_DPP,
    REZIM_MIN_HPP,
    REZIM_POD_MINIMEM,
    attach_hpp_dpp_to_row,
    dpp_odvody,
    hpp_minimum_hruba,
    hpp_odvody,
    recommend_hpp_dpp,
    svatek_priplatek_hruba,
    vikend_priplatek_hruba,
)
from shifts.models import Smena
from shifts.payroll_service import aggregate_hours_by_user, build_payroll_row
from stores.models import Prodejna
from users.models import WebUser


class HppDppCalcTests(SimpleTestCase):
    def test_min_hpp_cista_without_surcharge(self):
        self.assertEqual(hpp_odvody(HPP_GROSS_MIN)['cista'], Decimal('19012'))
        self.assertEqual(dpp_odvody(DPP_GROSS_MAX)['cista'], Decimal('10199'))

    def test_zero_target(self):
        split = recommend_hpp_dpp(0)
        self.assertEqual(split['hpp_hruba'], 0)
        self.assertEqual(split['dpp_hruba'], 0)
        self.assertEqual(split['rezim'], REZIM_POD_MINIMEM)

    def test_below_min_hpp_all_on_hpp(self):
        split = recommend_hpp_dpp(15000, odpracovano_h=168)
        self.assertEqual(split['dpp_hruba'], 0)
        self.assertEqual(split['soucet_cista'], 15000)
        self.assertEqual(split['rezim'], REZIM_POD_MINIMEM)
        self.assertTrue(split['warning'])

    def test_mid_range_keeps_min_hpp(self):
        split = recommend_hpp_dpp(25000, odpracovano_h=168)
        self.assertEqual(split['rezim'], REZIM_MIN_HPP)
        self.assertEqual(split['hpp_hruba'], 22400)
        self.assertEqual(split['soucet_cista'], 25000)
        self.assertLess(split['dpp_hruba'], 11999)

    def test_gabriel_max_dpp_with_weekend(self):
        split = recommend_hpp_dpp(33102, odpracovano_h=168, vikend_h=84)
        self.assertEqual(split['rezim'], REZIM_MAX_DPP)
        self.assertEqual(split['dpp_hruba'], 11999)
        self.assertEqual(split['dpp_cista'], 10199)
        self.assertEqual(split['hpp_hruba'], 27702)
        self.assertEqual(split['hpp_cista'], 22903)
        self.assertEqual(split['soucet_cista'], 33102)
        self.assertEqual(split['vikend_priplatek_hruba'], 1120)

    def test_holiday_surcharge_raises_min_hpp(self):
        vikend, svatek = (
            vikend_priplatek_hruba(HPP_GROSS_MIN, 176, 0, 8),
            svatek_priplatek_hruba(HPP_GROSS_MIN, 176, 8),
        )
        self.assertEqual(vikend, Decimal('0'))
        self.assertEqual(svatek, Decimal('1067'))
        hpp_min, _, svatek_p = hpp_minimum_hruba(176, 0, 8)
        self.assertEqual(svatek_p, Decimal('1067'))
        self.assertEqual(hpp_min, Decimal('23467'))

        split = recommend_hpp_dpp(30000, odpracovano_h=176, svatek_h=8)
        self.assertGreaterEqual(split['hpp_hruba'], 23467)
        self.assertEqual(split['svatek_h'], 8.0)
        self.assertEqual(split['soucet_cista'], 30000)

    def test_weekend_holiday_adds_110_percent(self):
        hpp_min, vikend_p, svatek_p = hpp_minimum_hruba(176, 8, 8)
        self.assertEqual(vikend_p, Decimal('107'))
        self.assertEqual(svatek_p, Decimal('1067'))
        self.assertEqual(hpp_min, Decimal('23574'))

    def test_attach_skips_brigadnik(self):
        row = attach_hpp_dpp_to_row({
            'is_brigadnik': True,
            'celkem_body': 12000,
            'odpracovano_h': 80,
        })
        self.assertIsNone(row['hpp_dpp'])

    def test_attach_employee_split(self):
        row = attach_hpp_dpp_to_row({
            'is_brigadnik': False,
            'celkem_body': 25000,
            'odpracovano_h': 168,
            'vikend_h': 0,
            'svatek_h': 0,
        })
        self.assertEqual(row['hpp_dpp']['soucet_cista'], 25000)
        self.assertEqual(row['hpp_dpp']['hpp_hruba'], 22400)


class HppDppHoursTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.prodejna = Prodejna.objects.create(
            id=9201, nazev='HPP Test', nazev_kratkiy='HPP', aktivni=True,
        )
        cls.prodejce = WebUser.objects.create(
            id=9201,
            uzivatelske_jmeno='hpp_prodejce',
            jmeno='Hpp',
            prijmeni='Test',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=cls.prodejna.id,
            mzda_zaklad=Decimal('14000'),
            mzda_doplnky=[],
        )
        cls.brigadnik = WebUser.objects.create(
            id=9202,
            uzivatelske_jmeno='hpp_brig',
            jmeno='Brig',
            prijmeni='Hpp',
            heslo='x',
            role='BRIGADNIK',
            aktivni=True,
            prodejna_id=cls.prodejna.id,
            mzda_zaklad=Decimal('100'),
            mzda_doplnky=[],
        )

    def _shift(self, user, datum, hours=8):
        return Smena.objects.create(
            user=user,
            prodejna=self.prodejna,
            datum=datum,
            cas_od=time(8, 0),
            cas_do=time(8 + hours, 0),
            typ_smeny='prace',
            brigadnik_rezim='prodejce',
        )

    def test_weekend_hours_saturday(self):
        self._shift(self.prodejce, date(2026, 8, 1))  # sobota
        hours = aggregate_hours_by_user(2026, 8)[self.prodejce.id]
        self.assertEqual(hours['vikend_h'], 8)
        self.assertEqual(hours['svatek_h'], 0)
        self.assertEqual(hours['odpracovano_h'], 8)

    def test_holiday_hours_not_counted_as_weekend_when_weekday(self):
        self._shift(self.prodejce, date(2026, 5, 1))  # pátek, svátek práce
        hours = aggregate_hours_by_user(2026, 5)[self.prodejce.id]
        self.assertEqual(hours['svatek_h'], 8)
        self.assertEqual(hours['vikend_h'], 0)
        self.assertEqual(hours['odpracovano_h'], 16)

    def test_payroll_row_has_split_for_employee(self):
        self._shift(self.prodejce, date(2026, 8, 3))
        uid = self.prodejce.id
        hours_map = aggregate_hours_by_user(2026, 8)
        row = build_payroll_row(
            self.prodejce, 2026, 8, hours_map, date(2026, 8, 1), {}, 168,
            {uid: {}}, {uid: (0, None)}, {},
            prumer_cache={},
        )
        self.assertFalse(row['is_brigadnik'])
        self.assertIsNotNone(row['hpp_dpp'])
        self.assertEqual(row['hpp_dpp']['soucet_cista'], int(row['celkem_body']))

    def test_payroll_row_skips_split_for_brigadnik(self):
        self._shift(self.brigadnik, date(2026, 8, 3))
        uid = self.brigadnik.id
        hours_map = aggregate_hours_by_user(2026, 8)
        row = build_payroll_row(
            self.brigadnik, 2026, 8, hours_map, date(2026, 8, 1), {}, 168,
            {uid: {}}, {uid: (0, None)}, {},
        )
        self.assertTrue(row['is_brigadnik'])
        self.assertIsNone(row['hpp_dpp'])
