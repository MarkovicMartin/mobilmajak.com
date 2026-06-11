"""Čas importu z Actoru – datum_vlozeni je wall-clock Europe/Prague, ne UTC."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from django.utils import timezone

PRAGUE = ZoneInfo('Europe/Prague')


def actor_import_iso(dt: datetime | None) -> str | None:
    """
    Actor/MySQL ukládá datum_vlozeni jako lokální čas (Praha).
    Django ho často načte jako aware UTC se stejnými číslicemi → API posílá +00:00.
  """
    if dt is None:
        return None
    wall = dt.replace(tzinfo=None) if timezone.is_aware(dt) else dt
    return wall.replace(tzinfo=PRAGUE).isoformat()
