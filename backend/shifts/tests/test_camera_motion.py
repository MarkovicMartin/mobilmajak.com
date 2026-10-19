"""Testy pilotu pohybu kamer – období klidu v logu."""
from datetime import datetime, timedelta

from django.test import TestCase
from django.utils import timezone

from shifts.camera_motion import (
    EVENT_RETENTION_DAYS,
    LOG_MARGIN_MINUTES,
    motion_detail_for_prodejna,
    record_motion_event,
)
from shifts.models import ProdejnaPohybUdalost
from stores.models import Prodejna
from stores.oteviraci_doba_utils import default_oteviraci_doba


def _samples(prodejna, start, minutes, pohyb):
    for i in range(minutes + 1):
        ProdejnaPohybUdalost.objects.create(
            prodejna=prodejna,
            pohyb=pohyb,
            cas=start + timedelta(minutes=i),
        )


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
        ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna, pohyb=True, cas=now - timedelta(minutes=20),
        )
        _samples(self.prodejna, now - timedelta(minutes=19), 16, False)
        ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna, pohyb=True, cas=now - timedelta(minutes=2),
        )

        detail = motion_detail_for_prodejna(self.prodejna.id, now=now)

        self.assertIsNone(detail['current_quiet_minutes'])
        self.assertEqual(len(detail['quiet_periods']), 1)
        period = detail['quiet_periods'][0]
        self.assertFalse(period['ongoing'])
        self.assertGreaterEqual(period['minutes'], 16)
        self.assertIsNotNone(period['to'])

    def test_ongoing_quiet_while_still_idle(self):
        now = timezone.make_aware(datetime(2026, 6, 11, 12, 0))
        ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna, pohyb=True, cas=now - timedelta(minutes=12),
        )
        _samples(self.prodejna, now - timedelta(minutes=11), 11, False)

        detail = motion_detail_for_prodejna(self.prodejna.id, now=now)

        self.assertGreaterEqual(detail['current_quiet_minutes'], 11)
        self.assertEqual(len(detail['quiet_periods']), 1)
        period = detail['quiet_periods'][0]
        self.assertTrue(period['ongoing'])
        self.assertIsNone(period['to'])
        self.assertGreaterEqual(period['minutes'], 11)

    def test_gaps_under_ten_minutes_are_omitted(self):
        now = timezone.make_aware(datetime(2026, 6, 11, 12, 0))
        _samples(self.prodejna, now - timedelta(minutes=8), 8, False)

        detail = motion_detail_for_prodejna(self.prodejna.id, now=now)

        self.assertIsNone(detail['current_quiet_minutes'])
        self.assertEqual(detail['quiet_periods'], [])
        self.assertEqual(detail['quiet_log_min_minutes'], 10)

    def test_ten_minute_gap_is_logged(self):
        now = timezone.make_aware(datetime(2026, 6, 11, 12, 0))
        ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna, pohyb=True, cas=now - timedelta(minutes=12),
        )
        _samples(self.prodejna, now - timedelta(minutes=11), 9, False)
        ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna, pohyb=True, cas=now - timedelta(minutes=1),
        )

        detail = motion_detail_for_prodejna(self.prodejna.id, now=now)

        self.assertEqual(len(detail['quiet_periods']), 1)
        self.assertGreaterEqual(detail['quiet_periods'][0]['minutes'], 10)
        self.assertFalse(detail['quiet_periods'][0]['ongoing'])

    def test_hole_without_samples_is_not_a_closure(self):
        now = timezone.make_aware(datetime(2026, 6, 11, 12, 0))
        ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna, pohyb=True, cas=now - timedelta(minutes=40),
        )
        ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna, pohyb=True, cas=now - timedelta(minutes=1),
        )

        detail = motion_detail_for_prodejna(self.prodejna.id, now=now)

        self.assertEqual(detail['quiet_periods'], [])

    def test_overnight_gap_clipped_to_opening_hours(self):
        """Klid na konci dne a ráno jsou dvě okna, ne jedna noc."""
        evening = timezone.make_aware(datetime(2026, 6, 10, 19, 45))
        morning = timezone.make_aware(datetime(2026, 6, 11, 8, 0))
        _samples(self.prodejna, evening, 15, False)
        _samples(self.prodejna, morning, 15, False)
        now = timezone.make_aware(datetime(2026, 6, 11, 12, 0))

        detail = motion_detail_for_prodejna(
            self.prodejna.id, now=now, lookback_hours=36,
        )

        self.assertEqual(len(detail['quiet_periods']), 2)
        minutes = sorted(p['minutes'] for p in detail['quiet_periods'])
        self.assertTrue(all(10 <= m <= 20 for m in minutes), minutes)

    def test_outside_hours_quiet_not_logged(self):
        """Klid jen po zavíračce → do logu nepatří."""
        now = timezone.make_aware(datetime(2026, 6, 11, 22, 0))
        _samples(self.prodejna, timezone.make_aware(datetime(2026, 6, 11, 20, 30)), 20, False)

        detail = motion_detail_for_prodejna(self.prodejna.id, now=now)

        self.assertIsNone(detail['current_quiet_minutes'])
        self.assertEqual(detail['quiet_periods'], [])

    def test_closed_day_omitted(self):
        oteviraci = default_oteviraci_doba()
        oteviraci['stejne_pro_vsechny'] = False
        oteviraci['dny']['ne'] = {'zavreno': True}
        self.prodejna.oteviraci_doba = oteviraci
        self.prodejna.save(update_fields=['oteviraci_doba'])

        now = timezone.make_aware(datetime(2026, 6, 14, 15, 0))
        _samples(self.prodejna, timezone.make_aware(datetime(2026, 6, 14, 10, 0)), 30, False)

        detail = motion_detail_for_prodejna(self.prodejna.id, now=now)

        self.assertIsNone(detail['current_quiet_minutes'])
        self.assertEqual(detail['quiet_periods'], [])


class CameraMotionLogWindowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.prodejna = Prodejna.objects.create(
            id=9302,
            nazev='Okno test',
            nazev_kratkiy='OKN',
            aktivni=True,
            oteviraci_doba=default_oteviraci_doba(),
        )

    def test_retention_is_two_months(self):
        self.assertEqual(EVENT_RETENTION_DAYS, 60)
        self.assertEqual(LOG_MARGIN_MINUTES, 30)

    def test_stores_inside_margin_and_drops_outside(self):
        day = datetime(2026, 6, 11)
        kept = []
        for hh, mm in ((7, 29), (7, 30), (12, 0), (20, 29), (20, 30), (21, 0)):
            event = record_motion_event(
                prodejna_id=self.prodejna.id,
                pohyb=False,
                cas=timezone.make_aware(day.replace(hour=hh, minute=mm)),
                zdroj='test',
            )
            kept.append(event is not None)
        self.assertEqual(kept, [False, True, True, True, False, False])

    def test_closed_day_is_not_stored(self):
        oteviraci = default_oteviraci_doba()
        oteviraci['stejne_pro_vsechny'] = False
        oteviraci['dny']['ne'] = {'zavreno': True}
        self.prodejna.oteviraci_doba = oteviraci
        self.prodejna.save(update_fields=['oteviraci_doba'])

        event = record_motion_event(
            prodejna_id=self.prodejna.id,
            pohyb=True,
            cas=timezone.make_aware(datetime(2026, 6, 14, 12, 0)),
            zdroj='test',
        )
        self.assertIsNone(event)

    def test_prune_drops_samples_older_than_retention(self):
        now = timezone.now()
        old = ProdejnaPohybUdalost.objects.create(
            prodejna=self.prodejna,
            pohyb=False,
            cas=now - timedelta(days=EVENT_RETENTION_DAYS + 1),
        )
        fresh = record_motion_event(
            prodejna_id=self.prodejna.id,
            pohyb=True,
            cas=timezone.now().replace(hour=12, minute=0, second=0, microsecond=0),
            zdroj='test',
        )
        self.assertIsNotNone(fresh)
        self.assertFalse(ProdejnaPohybUdalost.objects.filter(pk=old.pk).exists())
