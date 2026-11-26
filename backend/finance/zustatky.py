"""Zůstatky pokladen a účtů k začátku a konci období analytiky."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from .models import FinanceZustatek

_TYP_NAZEV = {
    FinanceZustatek.TYP_FIO: 'Fio',
    FinanceZustatek.TYP_RAIFFEISEN: 'Raiffeisen',
    FinanceZustatek.TYP_POKLADNA: 'Pokladna',
}


def _nazev(typ: str, label: str) -> str:
    prefix = _TYP_NAZEV.get(typ, typ)
    text = (label or '').strip()
    if typ == FinanceZustatek.TYP_POKLADNA:
        return text or prefix
    if text:
        return f'{prefix} {text}'
    return prefix


def _snapshot(row: FinanceZustatek | None) -> dict | None:
    if row is None:
        return None
    return {
        'castka': float(row.castka),
        'datum': row.datum.isoformat(),
        'mena': row.mena or 'CZK',
    }


def _latest(rows: list[FinanceZustatek]) -> FinanceZustatek | None:
    if not rows:
        return None
    return max(rows, key=lambda row: (row.datum, row.id))


def _suma(rows: list[dict], key: str) -> float | None:
    total = Decimal('0')
    found = False
    for row in rows:
        snap = row.get(key)
        if not snap:
            continue
        if (snap.get('mena') or 'CZK') != 'CZK':
            continue
        total += Decimal(str(snap['castka']))
        found = True
    if not found:
        return None
    return float(total)


def period_zustatky(start_date: date, end_date: date) -> dict:
    """Začátek = poslední snímek před start_date.

    Konec = poslední uložený snímek v období. U rozpracovaného měsíce je to
    poslední den, který už import zapsal, ne živý stav z banky.
    """
    grouped: dict[tuple, list[FinanceZustatek]] = {}
    qs = FinanceZustatek.objects.filter(datum__lte=end_date).only(
        'id', 'datum', 'typ', 'label', 'prodejna_id', 'castka', 'mena',
    )
    for row in qs:
        key = (row.typ, row.label or '', row.prodejna_id or 0)
        grouped.setdefault(key, []).append(row)

    pokladny = []
    ucty = []
    for (typ, label, prodejna_id), rows in grouped.items():
        opening = _latest([row for row in rows if row.datum < start_date])
        closing = _latest([
            row for row in rows
            if start_date <= row.datum <= end_date
        ])
        item = {
            'typ': typ,
            'label': label,
            'nazev': _nazev(typ, label),
            'prodejna_id': prodejna_id or None,
            'zacatek': _snapshot(opening),
            'konec': _snapshot(closing),
        }
        if typ == FinanceZustatek.TYP_POKLADNA:
            pokladny.append(item)
        else:
            ucty.append(item)

    pokladny.sort(key=lambda row: (row['nazev'], row['prodejna_id'] or 0))
    ucty.sort(key=lambda row: (row['typ'], row['nazev']))
    return {
        'pokladny': pokladny,
        'ucty': ucty,
        'pokladny_zacatek': _suma(pokladny, 'zacatek'),
        'pokladny_konec': _suma(pokladny, 'konec'),
        'ucty_zacatek': _suma(ucty, 'zacatek'),
        'ucty_konec': _suma(ucty, 'konec'),
    }
