"""Agregace metrik konverze Zásilkovna pro analytiku."""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from django.db.models import Count
from django.db.models.functions import Coalesce

from analytics.models import WebProdejeAll
from analytics.receipt_metrics import leaderboard_doklad_q
from analytics.zasilkovna_link import (
    LinkedSale,
    distinct_visit_counts,
    link_sales_to_packeta,
    load_packeta_visits,
    prodeje_by_prodejce,
    typ_skupina,
)
from stores.models import Prodejna


def _pct(prodeje: int, navstevy: int) -> float | None:
    if not navstevy:
        return None
    return round(100 * prodeje / navstevy, 2)


def _linked_with_typ(linked: list[LinkedSale]) -> list[LinkedSale]:
    return [l for l in linked if l.packeta_nalezeno and l.typ_provize]


def build_konverze_report(
    date_from: date,
    date_to: date,
    prodejna_id: int | None = None,
) -> dict:
    visits = load_packeta_visits(date_from, date_to, prodejna_id)
    visit_stats = distinct_visit_counts(visits)
    linked, invalid_z = link_sales_to_packeta(date_from, date_to, prodejna_id)

    linked_typed = _linked_with_typ(linked)
    prodeje_z_note = {l.doklad for l in linked if l.match_source == 'poznamka' and l.zasilka}
    prodeje_fallback = {l.doklad for l in linked if l.match_source == 'sleva_fallback'}
    prodeje_propojene = {l.doklad for l in linked if l.packeta_nalezeno}
    prodeje_celkem = {l.doklad for l in linked}

    navstevy = visit_stats['navstevy_celkem']

    # Prodeje podle typu balíku
    prodeje_po_typu: dict[str, set[str]] = defaultdict(set)
    for item in linked_typed:
        prodeje_po_typu[item.typ_provize].add(item.doklad)

    po_typu = []
    for typ, nav in sorted(visit_stats['po_typu'].items(), key=lambda x: -x[1]):
        prod = len(prodeje_po_typu.get(typ, set()))
        po_typu.append({
            'typ_provize': typ,
            'typ_skupina': typ_skupina(typ),
            'navstevy': nav,
            'prodeje': prod,
            'konverze_pct': _pct(prod, nav),
        })

    # Po prodejně
    prodejny_map = {p.id: p.nazev for p in Prodejna.objects.all()}
    visits_by_store: dict[int, set] = defaultdict(set)
    for v in visits:
        visits_by_store[v.prodejna_id].add(v.zasilka)
    prodeje_by_store: dict[int, set[str]] = defaultdict(set)
    for item in linked_typed:
        if item.id_prodejny:
            prodeje_by_store[item.id_prodejny].add(item.doklad)

    po_prodejne = []
    store_ids = sorted(set(visits_by_store) | set(prodeje_by_store))
    for sid in store_ids:
        if prodejna_id and sid != prodejna_id:
            continue
        n = len(visits_by_store.get(sid, set()))
        p = len(prodeje_by_store.get(sid, set()))
        po_prodejne.append({
            'id_prodejny': sid,
            'prodejna': prodejny_map.get(sid, f'Prodejna {sid}'),
            'navstevy': n,
            'prodeje': p,
            'konverze_pct': _pct(p, n),
        })
    po_prodejne.sort(key=lambda x: -x['navstevy'])

    # Prodejci
    from users.models import WebUser

    prodejci_stats = prodeje_by_prodejce(linked)
    user_ids = list(prodejci_stats.keys())
    users = {u.id: u for u in WebUser.objects.filter(id__in=user_ids)} if user_ids else {}

    prodejci = []
    for uid, stats in sorted(prodejci_stats.items(), key=lambda x: -x[1]['zasilkovna_prodeje']):
        user = users.get(uid)
        jmeno = f'{user.jmeno} {user.prijmeni}'.strip() if user else f'Prodejce {uid}'
        prodejci.append({
            'id_prodejce': uid,
            'prodejce': jmeno,
            **stats,
        })

    # Běžní zákazníci (účtenky bez Zásilkovna dopravy)
    bezni_qs = WebProdejeAll.objects.filter(typ__gte=date_from, typ__lte=date_to)
    if prodejna_id:
        bezni_qs = bezni_qs.filter(id_prodejny=prodejna_id)
    navstevy_bezni = (
        bezni_qs.filter(leaderboard_doklad_q())
        .aggregate(v=Count(Coalesce('doklad', 'objednavka'), distinct=True))['v'] or 0
    )

    detail = [
        {
            'doklad': l.doklad,
            'zasilka': l.zasilka,
            'typ_provize': l.typ_provize,
            'typ_skupina': l.typ_skupina,
            'datum_prodeje': l.datum_prodeje.isoformat() if l.datum_prodeje else None,
            'id_prodejce': l.id_prodejce,
            'id_prodejny': l.id_prodejny,
            'match_source': l.match_source,
            'packeta_nalezeno': l.packeta_nalezeno,
        }
        for l in sorted(linked_typed, key=lambda x: (x.datum_prodeje or date.min, x.doklad), reverse=True)[:300]
    ]

    return {
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
        'summary': {
            'navstevy_bezni': navstevy_bezni,
            'navstevy_baliku': navstevy,
            'navstevy_vydane': visit_stats['navstevy_vydane'],
            'navstevy_prijate': visit_stats['navstevy_prijate'],
            'prodeje_propojene': len(prodeje_propojene),
            'prodeje_oznacene_z': len(prodeje_z_note),
            'prodeje_sleva_fallback': len(prodeje_fallback),
            'prodeje_celkem': len(prodeje_celkem),
            'konverze_pct': _pct(len(prodeje_propojene), navstevy),
            'neplatne_z': len(invalid_z),
        },
        'po_typu': po_typu,
        'po_prodejne': po_prodejne,
        'prodejci': prodejci,
        'detail': detail,
        'neplatne_z': invalid_z[:100],
    }


def zasilkovna_leaderboard_map(date_from: date, date_to: date) -> dict[int, dict]:
    """Mapa id_prodejce → metriky pro žebříček."""
    linked, _ = link_sales_to_packeta(date_from, date_to)
    return prodeje_by_prodejce(linked)
