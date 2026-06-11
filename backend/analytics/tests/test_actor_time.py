"""Testy serializace času importu Actoru."""
from datetime import datetime
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase
from django.utils import timezone

from analytics.actor_time import actor_import_iso


class ActorImportIsoTests(SimpleTestCase):
    def test_naive_prague_wall_clock(self):
        dt = datetime(2026, 6, 11, 17, 24, 24)
        self.assertEqual(actor_import_iso(dt), '2026-06-11T17:24:24+02:00')

    def test_aware_utc_same_digits_reinterpreted_as_prague(self):
        dt = timezone.make_aware(datetime(2026, 6, 11, 17, 24, 24), ZoneInfo('UTC'))
        self.assertEqual(actor_import_iso(dt), '2026-06-11T17:24:24+02:00')

    def test_none(self):
        self.assertIsNone(actor_import_iso(None))
