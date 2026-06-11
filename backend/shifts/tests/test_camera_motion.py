"""Testy pilotu pohybu kamer – období klidu v logu."""
from datetime import datetime, timedelta

from django.test import TestCase
from django.utils import timezone

from shifts.camera_motion import motion_detail_for_prodejna
from shifts.models import ProdejnaPohybUdalost
from stores.models import Prodejna


class CameraMotionDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.prodejna = Prodejna.objects.create(
            id=9301, nazev='Kamera test', nazev_kratkiy='KAM', aktivni=True,
        )

    def test_quiet_period_persists_after_motion_resumes(self):
        now = timezone.make_aware(datetime(2026, 6, 11, 12, 0))
        last_motion = now - timedelta(minutes=20)
        quiet_signal = now - timedelta(minutes=15)
        motion_resumed = now - timedelta(minutes=2)

        ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna, pohyb=True, cas=last_motion,
        )
        ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna, pohyb=False, cas=quiet_signal,
        )
        ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna, pohyb=True, cas=motion_resumed,
        )

        detail = motion_detail_for_prodejna(self.prodejna.id, now=now)

        self.assertIsNone(detail['current_quiet_minutes'])
        self.assertEqual(len(detail['quiet_periods']), 1)
        period = detail['quiet_periods'][0]
        self.assertFalse(period['ongoing'])
        self.assertGreaterEqual(period['minutes'], 18)
        self.assertIsNotNone(period['to'])

    def test_ongoing_quiet_while_still_idle(self):
        now = timezone.make_aware(datetime(2026, 6, 11, 12, 0))
        last_motion = now - timedelta(minutes=12)

        ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna, pohyb=True, cas=last_motion,
        )
        ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna, pohyb=False, cas=now - timedelta(minutes=7),
        )

        detail = motion_detail_for_prodejna(self.prodejna.id, now=now)

        self.assertEqual(detail['current_quiet_minutes'], 12)
        self.assertEqual(len(detail['quiet_periods']), 1)
        period = detail['quiet_periods'][0]
        self.assertTrue(period['ongoing'])
        self.assertIsNone(period['to'])
        self.assertEqual(period['minutes'], 12)
