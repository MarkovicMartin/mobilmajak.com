"""Testy pilotu pohybu kamer – období klidu v logu."""
from datetime import datetime, timedelta

from django.test import TestCase
from django.utils import timezone

from shifts.camera_motion import motion_detail_for_prodejna
from shifts.models import ProdejnaPohybUdalost
from stores.models import Prodejna
from stores.oteviraci_doba_utils import default_oteviraci_doba


class CameraMotionDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.prodejna = Prodejna.objects.create(
            id=9301,
            nazev='Kamera test',
            nazev_kratkiy='KAM',
            aktivni=True,
            oteviraci_doba=default_oteviraci_doba(),
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

    def test_gaps_under_ten_minutes_are_omitted(self):
        now = timezone.make_aware(datetime(2026, 6, 11, 12, 0))
        ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna, pohyb=True, cas=now - timedelta(minutes=9),
        )
        ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna, pohyb=True, cas=now - timedelta(minutes=6),
        )
        ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna, pohyb=True, cas=now - timedelta(minutes=1),
        )

        detail = motion_detail_for_prodejna(self.prodejna.id, now=now)

        self.assertIsNone(detail['current_quiet_minutes'])
        self.assertEqual(detail['quiet_periods'], [])
        self.assertEqual(detail['quiet_log_min_minutes'], 10)

    def test_ten_minute_gap_is_logged(self):
        now = timezone.make_aware(datetime(2026, 6, 11, 12, 0))
        ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna, pohyb=True, cas=now - timedelta(minutes=12),
        )
        ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna, pohyb=True, cas=now - timedelta(minutes=2),
        )

        detail = motion_detail_for_prodejna(self.prodejna.id, now=now)

        self.assertEqual(len(detail['quiet_periods']), 1)
        self.assertEqual(detail['quiet_periods'][0]['minutes'], 10)
        self.assertFalse(detail['quiet_periods'][0]['ongoing'])

    def test_overnight_gap_clipped_to_opening_hours(self):
        """Mezera přes noc → jen úseky v otevírací době (ne celá noc)."""
        now = timezone.make_aware(datetime(2026, 6, 11, 12, 0))
        ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna, pohyb=True, cas=now - timedelta(hours=20),
        )
        ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna, pohyb=True, cas=now - timedelta(minutes=1),
        )

        detail = motion_detail_for_prodejna(
            self.prodejna.id, now=now, lookback_hours=16,
        )

        self.assertEqual(len(detail['quiet_periods']), 2)
        minutes = sorted(p['minutes'] for p in detail['quiet_periods'])
        # 10.6. 16:00–20:00 = 240; 11.6. 08:00–11:59 = 239
        self.assertEqual(minutes, [239, 240])
        self.assertTrue(all(p['minutes'] < 12 * 60 for p in detail['quiet_periods']))

    def test_outside_hours_quiet_not_logged(self):
        """Klid jen po zavíračce → do logu nepatří."""
        now = timezone.make_aware(datetime(2026, 6, 11, 22, 0))
        ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna, pohyb=True,
            cas=timezone.make_aware(datetime(2026, 6, 11, 20, 30)),
        )

        detail = motion_detail_for_prodejna(self.prodejna.id, now=now)

        self.assertIsNone(detail['current_quiet_minutes'])
        self.assertEqual(detail['quiet_periods'], [])

    def test_closed_day_omitted(self):
        oteviraci = default_oteviraci_doba()
        oteviraci['stejne_pro_vsechny'] = False
        oteviraci['dny']['ne'] = {'zavreno': True}
        self.prodejna.oteviraci_doba = oteviraci
        self.prodejna.save(update_fields=['oteviraci_doba'])

        # Neděle 14. 6. 2026
        now = timezone.make_aware(datetime(2026, 6, 14, 15, 0))
        ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna, pohyb=True,
            cas=timezone.make_aware(datetime(2026, 6, 14, 10, 0)),
        )

        detail = motion_detail_for_prodejna(self.prodejna.id, now=now)

        self.assertIsNone(detail['current_quiet_minutes'])
        self.assertEqual(detail['quiet_periods'], [])
