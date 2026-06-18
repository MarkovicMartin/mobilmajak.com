"""
Marže / zisk přiřazený prodejcům pro modul Položky.

- Běžný prodej: marže podle id_prodejce (kdo prodal).
- Servisní práce: marže podle sloupce Technik (kdo provedl), ne podle prodejce.
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from functools import lru_cache
from typing import Iterable, Optional

from django.db.models import F, Q, Sum

from analytics.polozky_aggregate import PolozkyParams
from analytics.technik_utils import _load_technik_maps, resolve_technik_display
from stores.models import Prodejna
from users.models import WebUser


def _base_servis_q() -> Q:
    return Q(objednavku_zalozil__icontains='servis eda') & Q(k_servisu='ANO')


def _servisni_prace_segment_q() -> Q:
    return Q(kategorie__icontains='!Servis') & ~Q(kategorie_1__icontains='Služby')


def _servis_prace_attributed_to_technik_q() -> Q:
    return _base_servis_q() & _servisni_prace_segment_q()


def resolve_payroll_month(params: PolozkyParams) -> Optional[str]:
    """YYYY-MM pokud jde o celý kalendářní měsíc (pro výplatu ve výpočtu výnosu)."""
    if params.period == 'monthly_select' and params.selected_month:
        return params.selected_month
    sd = params.period_start
    ed = params.period_end
    if not sd or not ed or sd.year != ed.year or sd.month != ed.month:
        return None
    if sd.day != 1:
        return None
    last_day = calendar.monthrange(sd.year, sd.month)[1]
    if ed.day != last_day:
        return None
    return f'{sd.year:04d}-{sd.month:02d}'


def _technik_name_to_user_id() -> dict[str, int]:
    return dict(_technik_name_to_user_id_cached())


@lru_cache(maxsize=1)
def _technik_name_to_user_id_cached() -> tuple[tuple[str, int], ...]:
    out = []
    for user in WebUser.objects.only('id', 'jmeno', 'prijmeni', 'technik_id').exclude(
        technik_id__isnull=True,
    ).exclude(technik_id=0):
        name = f'{user.jmeno} {user.prijmeni}'.strip()
        if name:
            out.append((name, user.id))
    return tuple(out)


def batch_sales_margin_by_prodejce(queryset, prodejci_ids: Iterable[int]) -> dict[int, float]:
    """Marže z prodeje přiřazená prodejci; servisní práce (Technik) se nepočítají dvakrát."""
    ids = list(prodejci_ids)
    if not ids:
        return {}

    rows = (
        queryset.filter(id_prodejce__in=ids)
        .exclude(_servis_prace_attributed_to_technik_q())
        .values('id_prodejce')
        .annotate(marze=Sum(F('pocet_kusu') * F('zisk'), default=0))
    )
    return {int(r['id_prodejce']): float(r['marze'] or 0) for r in rows}


def batch_servis_margin_by_technik(queryset) -> dict[int, float]:
    """Marže servisních prací přiřazená technikovi, který je provedl."""
    id_to_name, _ = _load_technik_maps()
    name_to_user_id = _technik_name_to_user_id()

    prace_qs = queryset.filter(_servis_prace_attributed_to_technik_q())
    by_technik = prace_qs.values('technik').annotate(
        marze=Sum(F('pocet_kusu') * F('zisk'), default=0),
    )

    result: dict[int, float] = defaultdict(float)
    for row in by_technik:
        raw_technik = row.get('technik')
        if not raw_technik:
            continue
        canonical = resolve_technik_display(raw_technik, id_to_name)
        user_id = name_to_user_id.get(canonical)
        if not user_id:
            continue
        result[user_id] += float(row['marze'] or 0)
    return dict(result)


def batch_payroll_body_for_month(mesic_str: str) -> dict[int, float]:
    """Celková měsíční výplata (body) – stejný zdroj jako modul Výplata."""
    return dict(_batch_payroll_body_for_month_cached(mesic_str))


@lru_cache(maxsize=8)
def _batch_payroll_body_for_month_cached(mesic_str: str) -> tuple[tuple[int, float], ...]:
    from shifts.payroll_service import build_payroll_preview

    preview = build_payroll_preview(mesic_str)
    return tuple(
        (int(r['user_id']), float(r.get('celkem_body') or 0))
        for r in preview.get('rows') or []
    )


def attach_profit_fields(
    rows: list[dict],
    queryset,
    params: PolozkyParams,
) -> list[dict]:
    """Doplní marže a výnos pro firmu do řádků agregace prodejců."""
    if not getattr(params, 'include_profit', True):
        return rows

    servis_margin = batch_servis_margin_by_technik(queryset)

    existing_ids = {int(r['id_prodejce']) for r in rows if r.get('id_prodejce') is not None}
    servis_only_ids = [uid for uid in servis_margin if uid not in existing_ids and servis_margin[uid] > 0]
    if servis_only_ids:
        users = {
            u.id: u
            for u in WebUser.objects.filter(id__in=servis_only_ids).only(
                'id', 'jmeno', 'prijmeni', 'prodejna_id',
            )
        }
        prodejny_map = {p.id: p.nazev for p in Prodejna.objects.filter(id__in={
            u.prodejna_id for u in users.values() if u.prodejna_id
        })}
        for uid in servis_only_ids:
            user = users.get(uid)
            if not user:
                continue
            pname = prodejny_map.get(user.prodejna_id, 'Neznámá') if user.prodejna_id else 'Neznámá'
            rows.append({
                'id_prodejce': uid,
                'prodejce': f'{user.jmeno} {user.prijmeni}'.strip() or f'Prodejce {uid}',
                'prodejna': str(pname),
                'polozky_nad_100': 0,
                'sluzby_celkem': 0,
            })

    if not rows:
        return rows

    prodejci_ids = [int(r['id_prodejce']) for r in rows if r.get('id_prodejce') is not None]
    sales_margin = batch_sales_margin_by_prodejce(queryset, prodejci_ids)

    payroll_month = resolve_payroll_month(params)
    payroll_map = batch_payroll_body_for_month(payroll_month) if payroll_month else {}

    for row in rows:
        uid = int(row['id_prodejce'])
        marze_prodej = round(sales_margin.get(uid, 0.0), 2)
        marze_servis = round(servis_margin.get(uid, 0.0), 2)
        marze_celkem = round(marze_prodej + marze_servis, 2)
        row['marze_prodej'] = marze_prodej
        row['marze_servis'] = marze_servis
        row['marze_vytvorena'] = marze_celkem

        if payroll_month:
            vyplata = round(payroll_map.get(uid, 0.0), 2)
            row['vyplata_body'] = vyplata
            row['vynos_firmy'] = round(marze_celkem - vyplata, 2)
            row['profit_payroll_month'] = payroll_month
        else:
            row['vyplata_body'] = None
            row['vynos_firmy'] = None
            row['profit_payroll_month'] = None

    return rows
