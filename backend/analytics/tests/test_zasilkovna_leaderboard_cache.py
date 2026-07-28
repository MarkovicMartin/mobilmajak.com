from datetime import date
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from analytics.models import ZasilkovnaLeaderboardCache
from analytics.zasilkovna_leaderboard_cache import (
    get_zasilkovna_leaderboard_map,
    period_key_for,
    refresh_after_packeta_import,
)


class ZasilkovnaLeaderboardCacheTests(TestCase):
    def test_period_key_day_and_month(self):
        self.assertEqual(period_key_for(date(2026, 7, 28), date(2026, 7, 28)), 'day:2026-07-28')
        self.assertEqual(period_key_for(date(2026, 7, 1), date(2026, 7, 28)), 'month:2026-07')
        self.assertEqual(
            period_key_for(date(2026, 6, 15), date(2026, 7, 1)),
            'range:2026-06-15_2026-07-01',
        )

    @override_settings(USE_TZ=True)
    def test_get_uses_cache_without_recompute(self):
        today = timezone.localdate()
        ZasilkovnaLeaderboardCache.objects.create(
            period_key=f'day:{today.isoformat()}',
            date_from=today,
            date_to=today,
            by_prodejce={'4': {'zasilkovna_baliku': 10, 'zasilkovna_prodeje': 1}},
            by_prodejna={},
            source='test',
        )
        with patch(
            'analytics.zasilkovna_konverze.zasilkovna_leaderboard_map',
        ) as compute_sellers, patch(
            'analytics.zasilkovna_konverze.zasilkovna_store_leaderboard_map',
        ) as compute_stores:
            result = get_zasilkovna_leaderboard_map(today, today)
            self.assertEqual(result[4]['zasilkovna_baliku'], 10)
            compute_sellers.assert_not_called()
            compute_stores.assert_not_called()

    def test_refresh_after_packeta_stores_day_and_month(self):
        today = timezone.localdate()
        month_start = today.replace(day=1)
        fake_sellers = {4: {'zasilkovna_baliku': 3, 'zasilkovna_prodeje': 1}}
        fake_stores = {2: {'zasilkovna_baliku': 5, 'zasilkovna_prodeje': 2}}

        with patch(
            'analytics.zasilkovna_konverze.zasilkovna_leaderboard_map',
            return_value=fake_sellers,
        ), patch(
            'analytics.zasilkovna_konverze.zasilkovna_store_leaderboard_map',
            return_value=fake_stores,
        ):
            result = refresh_after_packeta_import(source='test')

        self.assertTrue(result['ok'])
        self.assertEqual(len(result['periods']), 2)
        day_row = ZasilkovnaLeaderboardCache.objects.get(period_key=f'day:{today.isoformat()}')
        month_row = ZasilkovnaLeaderboardCache.objects.get(
            period_key=f'month:{month_start.strftime("%Y-%m")}',
        )
        self.assertEqual(day_row.by_prodejce['4']['zasilkovna_baliku'], 3)
        self.assertEqual(month_row.by_prodejna['2']['zasilkovna_baliku'], 5)
        self.assertEqual(day_row.source, 'test')
