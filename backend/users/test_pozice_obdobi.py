from datetime import date
from decimal import Decimal

from django.test import TestCase

from users.models import WebUser
from users.mzda_utils import (
    BRIGADNIK_DEFAULT_BODY_ZA_HODINU,
    PRODEJCE_ZAKLAD_BODY,
    coerce_mzda_zaklad_for_role,
    is_brigadnik,
    mzda_user_as_of,
    snapshot_pozice,
)
from users.serializers import WebUserUpdateSerializer


class CoerceMzdaZakladTests(TestCase):
    def test_brigadnik_replaces_prodejce_default(self):
        self.assertEqual(
            coerce_mzda_zaklad_for_role('BRIGADNIK', Decimal('14000')),
            BRIGADNIK_DEFAULT_BODY_ZA_HODINU,
        )

    def test_prodejce_replaces_brigadnik_default(self):
        self.assertEqual(
            coerce_mzda_zaklad_for_role('PRODEJCE', Decimal('100')),
            PRODEJCE_ZAKLAD_BODY,
        )

    def test_keeps_custom_brigadnik_rate(self):
        self.assertEqual(
            coerce_mzda_zaklad_for_role('BRIGADNIK', Decimal('120')),
            Decimal('120'),
        )


class PoziceObdobiTests(TestCase):
    def setUp(self):
        self.user = WebUser.objects.create(
            id=9201,
            uzivatelske_jmeno='pozice_test',
            jmeno='Jan',
            prijmeni='Test',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            technik_id=9201,
            mzda_zaklad=Decimal('14000'),
            mzda_doplnky=[],
            pozice_od=date(2026, 9, 1),
            pozice_predchozi={
                'role': 'BRIGADNIK',
                'mzda_zaklad': 100,
                'mzda_doplnky': [],
                'mzda_cestovne': None,
            },
        )

    def test_before_pozice_od_is_brigadnik(self):
        self.assertTrue(is_brigadnik(self.user, on_date=date(2026, 8, 1)))
        viewed = mzda_user_as_of(self.user, date(2026, 8, 1))
        self.assertEqual(viewed.role, 'BRIGADNIK')
        self.assertEqual(viewed.mzda_zaklad, Decimal('100'))

    def test_from_pozice_od_is_prodejce(self):
        self.assertFalse(is_brigadnik(self.user, on_date=date(2026, 9, 1)))
        viewed = mzda_user_as_of(self.user, date(2026, 9, 1))
        self.assertEqual(viewed.role, 'PRODEJCE')
        self.assertEqual(viewed.mzda_zaklad, Decimal('14000'))

    def test_without_date_uses_current_role(self):
        self.assertFalse(is_brigadnik(self.user))

    def test_update_snapshots_previous_role(self):
        brig = WebUser.objects.create(
            id=9202,
            uzivatelske_jmeno='pozice_brig',
            jmeno='Petr',
            prijmeni='Brig',
            heslo='x',
            role='BRIGADNIK',
            aktivni=True,
            technik_id=9202,
            mzda_zaklad=Decimal('100'),
            mzda_doplnky=[],
        )
        ser = WebUserUpdateSerializer(brig, data={
            'role': 'PRODEJCE',
            'mzda_zaklad': '14000',
            'zmena_pozice_od': '2026-09-01',
        }, partial=True)
        self.assertTrue(ser.is_valid(), ser.errors)
        updated = ser.save()
        self.assertEqual(updated.role, 'PRODEJCE')
        self.assertEqual(updated.mzda_zaklad, Decimal('14000'))
        self.assertEqual(updated.pozice_od, date(2026, 9, 1))
        self.assertEqual(updated.pozice_predchozi['role'], 'BRIGADNIK')
        self.assertEqual(updated.pozice_predchozi['mzda_zaklad'], 100.0)

    def test_snapshot_helper(self):
        snap = snapshot_pozice(self.user)
        self.assertEqual(snap['role'], 'PRODEJCE')
        self.assertEqual(snap['mzda_zaklad'], 14000.0)
