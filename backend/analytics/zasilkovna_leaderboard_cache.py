"""
Cache metrik Zásilkovna pro žebříček.

Výpočet link_sales_to_packeta je drahý (~2–3 s za měsíc). Packeta actor běží
párkrát denně → po importu přepočítáme den + aktuální měsíc a žebříček jen čte DB.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from django.db.utils import OperationalError, ProgrammingError
from django.utils import timezone

logger = logging.getLogger(__name__)


def period_key_day(day: date) -> str:
    return f'day:{day.isoformat()}'


def period_key_month(ym: str) -> str:
    return f'month:{ym}'


def period_key_for(date_from: date, date_to: date) -> str:
    if date_from == date_to:
        return period_key_day(date_from)
    if (
        date_from.year == date_to.year
        and date_from.month == date_to.month
        and date_from.day == 1
    ):
        return period_key_month(date_from.strftime('%Y-%m'))
    return f'range:{date_from.isoformat()}_{date_to.isoformat()}'


def _cache_table_available() -> bool:
    from analytics.models import ZasilkovnaLeaderboardCache
    from django.db import connection

    try:
        return ZasilkovnaLeaderboardCache._meta.db_table in connection.introspection.table_names()
    except Exception:
        return False


def _json_keys_to_int(raw: dict | None) -> dict[int, dict]:
    if not raw:
        return {}
    out: dict[int, dict] = {}
    for key, value in raw.items():
        try:
            out[int(key)] = value if isinstance(value, dict) else {}
        except (TypeError, ValueError):
            continue
    return out


def _json_keys_to_str(raw: dict[int, dict]) -> dict[str, dict]:
    return {str(k): v for k, v in raw.items()}


def compute_and_store(
    date_from: date,
    date_to: date,
    *,
    source: str = 'manual',
) -> dict[str, Any]:
    """Spočítá mapy prodejců + prodejen a uloží do cache."""
    from analytics.models import ZasilkovnaLeaderboardCache
    from analytics.zasilkovna_konverze import (
        zasilkovna_leaderboard_map,
        zasilkovna_store_leaderboard_map,
    )

    by_prodejce = zasilkovna_leaderboard_map(date_from, date_to)
    by_prodejna = zasilkovna_store_leaderboard_map(date_from, date_to)
    key = period_key_for(date_from, date_to)

    if _cache_table_available():
        try:
            ZasilkovnaLeaderboardCache.objects.update_or_create(
                period_key=key,
                defaults={
                    'date_from': date_from,
                    'date_to': date_to,
                    'by_prodejce': _json_keys_to_str(by_prodejce),
                    'by_prodejna': _json_keys_to_str(by_prodejna),
                    'source': (source or '')[:32],
                },
            )
        except (ProgrammingError, OperationalError):
            logger.exception('Uložení Zásilkovna leaderboard cache selhalo (%s)', key)

    return {
        'period_key': key,
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
        'prodejcu': len(by_prodejce),
        'prodejen': len(by_prodejna),
        'source': source,
    }


def get_zasilkovna_leaderboard_map(date_from: date, date_to: date) -> dict[int, dict]:
    """Mapa prodejců – z cache, při miss dopočítá a uloží."""
    by_prodejce, _ = get_zasilkovna_leaderboard_maps(date_from, date_to)
    return by_prodejce


def get_zasilkovna_store_leaderboard_map(date_from: date, date_to: date) -> dict[int, dict]:
    """Mapa prodejen – z cache, při miss dopočítá a uloží."""
    _, by_prodejna = get_zasilkovna_leaderboard_maps(date_from, date_to)
    return by_prodejna


def get_zasilkovna_leaderboard_maps(
    date_from: date,
    date_to: date,
) -> tuple[dict[int, dict], dict[int, dict]]:
    from analytics.models import ZasilkovnaLeaderboardCache
    from analytics.zasilkovna_konverze import (
        zasilkovna_leaderboard_map,
        zasilkovna_store_leaderboard_map,
    )

    key = period_key_for(date_from, date_to)
    if _cache_table_available():
        try:
            row = ZasilkovnaLeaderboardCache.objects.filter(period_key=key).first()
        except (ProgrammingError, OperationalError):
            row = None
        if row is not None:
            return (
                _json_keys_to_int(row.by_prodejce),
                _json_keys_to_int(row.by_prodejna),
            )

    by_prodejce = zasilkovna_leaderboard_map(date_from, date_to)
    by_prodejna = zasilkovna_store_leaderboard_map(date_from, date_to)
    if _cache_table_available():
        try:
            ZasilkovnaLeaderboardCache.objects.update_or_create(
                period_key=key,
                defaults={
                    'date_from': date_from,
                    'date_to': date_to,
                    'by_prodejce': _json_keys_to_str(by_prodejce),
                    'by_prodejna': _json_keys_to_str(by_prodejna),
                    'source': 'lazy',
                },
            )
        except (ProgrammingError, OperationalError):
            logger.exception('Lazy uložení Zásilkovna cache selhalo (%s)', key)
    return by_prodejce, by_prodejna


def refresh_after_packeta_import(*, source: str = 'packeta_import') -> dict[str, Any]:
    """
    Po Packeta actoru / importu: přepočítá dnešní den + aktuální měsíc (MTD).
    Nesmí shodit import – volající má zachytit výjimky, tady logujeme.
    """
    today = timezone.localdate()
    month_start = today.replace(day=1)
    results = []
    try:
        results.append(compute_and_store(today, today, source=source))
        results.append(compute_and_store(month_start, today, source=source))
    except Exception:
        logger.exception('Obnova Zásilkovna leaderboard cache po Packeta importu selhala')
        return {'ok': False, 'periods': results}
    return {
        'ok': True,
        'refreshed_at': timezone.now().isoformat(),
        'periods': results,
    }
