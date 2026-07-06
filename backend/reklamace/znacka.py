"""Generování naší značky reklamace ve formátu R + YY + MM + NNN."""
from __future__ import annotations

import re

from django.db import transaction
from django.utils import timezone

from .models import ReklamacePolozka

NEW_ZNACKA_RE = re.compile(r'^R(\d{2})(\d{2})(\d{3})$', re.IGNORECASE)
ZNACKA_LEN = 8  # R + YY + MM + NNN


def _max_seq_for_month(prefix: str, yy: str, mm: str) -> int:
    max_seq = 0
    for znacka in (
        ReklamacePolozka.objects
        .select_for_update()
        .filter(nase_znacka__istartswith=prefix)
        .values_list('nase_znacka', flat=True)
    ):
        if len(znacka) != ZNACKA_LEN:
            continue
        match = NEW_ZNACKA_RE.match(znacka)
        if match and match.group(1) == yy and match.group(2) == mm:
            max_seq = max(max_seq, int(match.group(3)))
    return max_seq


def generate_nase_znacka(when=None) -> str:
    """Další značka pro daný měsíc (R + YY + MM + 3-digit seq)."""
    when = when or timezone.now()
    yy = when.strftime('%y')
    mm = when.strftime('%m')
    prefix = f'R{yy}{mm}'

    with transaction.atomic():
        next_seq = _max_seq_for_month(prefix, yy, mm) + 1
        if next_seq > 999:
            raise ValueError(f'Vyčerpána číselná řada pro prefix {prefix}')
        return f'{prefix}{next_seq:03d}'
