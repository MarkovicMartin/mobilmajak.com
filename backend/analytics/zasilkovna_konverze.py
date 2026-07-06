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
    baliky_zpracovane_by_prodejce,
    baliky_zpracovane_by_prodejna,
    distinct_visit_counts,
    is_z_oznaceno,
    is_zasilkovna_prodej,
    link_sales_to_packeta,
    load_packeta_visits,
    prodeje_by_prodejce,
    prodeje_zasilkovna_by_prodejna,
    typ_skupina,
    typ_kategorie,
    typ_provize_label,
)
from users.prodejce_resolve import build_prodejce_key_to_user_id, resolve_web_user_id
from users.models import WebUser
from stores.models import Prodejna


def _pct(prodeje: int, navstevy: int) -> float | None:
    if not navstevy:
        return None
    return round(100 * prodeje / navstevy, 2)


def _prodejce_display_map(linked: list[LinkedSale]) -> dict[int, str]:
    """Mapuje raw id_prodejce ze Symplia → zobrazitelné jméno."""
    key_map = build_prodejce_key_to_user_id()
    raw_ids = {l.id_prodejce for l in linked if l.id_prodejce is not None}
    canonical = {resolve_web_user_id(rid, key_map) for rid in raw_ids}
    canonical.discard(None)
    names = {
        u.id: f'{u.jmeno} {u.prijmeni}'.strip()
        for u in WebUser.objects.filter(id__in=canonical)
    }
    out: dict[int, str] = {}
    for rid in raw_ids:
        cid = resolve_web_user_id(rid, key_map)
        if cid and names.get(cid):
            out[rid] = names[cid]
        else:
            out[rid] = f'Prodejce {rid}'
    return out


def _prodejce_label(prodejce_map: dict[int, str], id_prodejce: int | None) -> str | None:
    if id_prodejce is None:
        return None
    return prodejce_map.get(id_prodejce, f'Prodejce {id_prodejce}')


def _linked_with_typ(linked: list[LinkedSale]) -> list[LinkedSale]:
    return [l for l in linked if l.typ_provize]


def build_konverze_report(
    date_from: date,
    date_to: date,
    prodejna_id: int | None = None,
) -> dict:
    visits = load_packeta_visits(date_from, date_to, prodejna_id)
    visit_stats = distinct_visit_counts(visits)
    linked, invalid_z = link_sales_to_packeta(date_from, date_to, prodejna_id)

    linked_typed = _linked_with_typ(linked)
    prodeje_z_note = {l.doklad for l in linked if is_z_oznaceno(l)}
    prodeje_z_cislem = {l.doklad for l in linked if is_zasilkovna_prodej(l)}
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
            'typ_baliku': typ_provize_label(typ),
            'typ_kategorie': typ_kategorie(typ),
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
    for item in linked:
        if item.id_prodejny and is_zasilkovna_prodej(item):
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
    prodejci_stats = prodeje_by_prodejce(linked)
    baliky_map = baliky_zpracovane_by_prodejce(date_from, date_to, prodejna_id)
    user_ids = sorted(set(prodejci_stats) | set(baliky_map))
    users = {u.id: u for u in WebUser.objects.filter(id__in=user_ids)} if user_ids else {}

    prodejci = []
    for uid in user_ids:
        stats = prodejci_stats.get(uid, {})
        baliku = baliky_map.get(uid, 0)
        prodeje = stats.get('zasilkovna_prodeje', 0)
        user = users.get(uid)
        jmeno = f'{user.jmeno} {user.prijmeni}'.strip() if user else f'Prodejce {uid}'
        prodejci.append({
            'id_prodejce': uid,
            'prodejce': jmeno,
            'zasilkovna_baliku': baliku,
            'zasilkovna_prodeje': prodeje,
            'zasilkovna_oznaceno': stats.get('zasilkovna_oznaceno', 0),
            'zasilkovna_z_bez_cisla': stats.get('zasilkovna_z_bez_cisla', 0),
            'zasilkovna_sleva_bez_baliku': stats.get('zasilkovna_sleva_bez_baliku', 0),
            'zasilkovna_konverze_pct': _pct(prodeje, baliku),
            'zasilkovna_konverze_z_pct': stats.get('zasilkovna_konverze_z_pct'),
        })
    prodejci.sort(
        key=lambda row: (
            (row['zasilkovna_baliku'] or 0) > 0 or (row['zasilkovna_prodeje'] or 0) > 0,
            row['zasilkovna_konverze_pct'] if row['zasilkovna_konverze_pct'] is not None else -1,
            row['zasilkovna_baliku'] or 0,
        ),
        reverse=True,
    )

    # Běžní zákazníci (účtenky bez Zásilkovna dopravy)
    bezni_qs = WebProdejeAll.objects.filter(typ__gte=date_from, typ__lte=date_to)
    if prodejna_id:
        bezni_qs = bezni_qs.filter(id_prodejny=prodejna_id)
    navstevy_bezni = (
        bezni_qs.filter(leaderboard_doklad_q())
        .aggregate(v=Count(Coalesce('doklad', 'objednavka'), distinct=True))['v'] or 0
    )

    prodejce_map = _prodejce_display_map(linked)

    detail = [
        {
            'doklad': l.doklad,
            'zasilka': l.zasilka,
            'typ_provize': l.typ_provize,
            'typ_baliku': typ_provize_label(l.typ_provize),
            'typ_kategorie': typ_kategorie(l.typ_provize),
            'typ_skupina': l.typ_skupina,
            'typ_inferovano': l.typ_inferovano,
            'datum_prodeje': l.datum_prodeje.isoformat() if l.datum_prodeje else None,
            'id_prodejce': l.id_prodejce,
            'prodejce': _prodejce_label(prodejce_map, l.id_prodejce),
            'id_prodejny': l.id_prodejny,
            'match_source': l.match_source,
            'packeta_nalezeno': l.packeta_nalezeno,
            'z_marker': l.z_marker,
        }
        for l in sorted(
            [x for x in linked if is_zasilkovna_prodej(x)],
            key=lambda x: (x.datum_prodeje or date.min, x.doklad),
            reverse=True,
        )[:300]
    ]

    # Jen „Z“ bez čísla – ne počítá se jako prodej
    chybi_propojeni = [
        {
            'doklad': l.doklad,
            'datum_prodeje': l.datum_prodeje.isoformat() if l.datum_prodeje else None,
            'id_prodejce': l.id_prodejce,
            'prodejce': _prodejce_label(prodejce_map, l.id_prodejce),
            'id_prodejny': l.id_prodejny,
            'match_source': l.match_source,
            'z_marker': l.z_marker,
            'zasilka': l.zasilka or None,
        }
        for l in linked
        if l.z_marker and not l.packeta_nalezeno
    ][:100]

    sleva_bez_baliku = [
        {
            'doklad': l.doklad,
            'datum_prodeje': l.datum_prodeje.isoformat() if l.datum_prodeje else None,
            'id_prodejce': l.id_prodejce,
            'prodejce': _prodejce_label(prodejce_map, l.id_prodejce),
            'id_prodejny': l.id_prodejny,
        }
        for l in linked
        if l.match_source == 'sleva_fallback'
    ][:100]

    return {
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
        'summary': {
            'navstevy_bezni': navstevy_bezni,
            'navstevy_baliku': navstevy,
            'navstevy_vydane': visit_stats['navstevy_vydane'],
            'navstevy_podani': visit_stats['navstevy_podani'],
            'navstevy_c2c': visit_stats['navstevy_c2c'],
            'navstevy_prijate': visit_stats['navstevy_prijate'],
            'prodeje_propojene': len(prodeje_propojene),
            'prodeje_z_cislem': len(prodeje_z_cislem),
            'prodeje_oznacene_z': len(prodeje_z_note),
            'prodeje_sleva_fallback': len(prodeje_fallback),
            'prodeje_z_bez_cisla': sum(
                s.get('zasilkovna_z_bez_cisla', 0) for s in prodejci_stats.values()
            ),
            'prodeje_celkem': len(prodeje_celkem),
            'konverze_pct': _pct(len(prodeje_z_cislem), navstevy),
            'konverze_packeta_pct': _pct(len(prodeje_propojene), navstevy),
            'neplatne_z': len(invalid_z),
            'chybi_propojeni_z': len(chybi_propojeni),
        },
        'po_typu': po_typu,
        'po_prodejne': po_prodejne,
        'prodejci': prodejci,
        'detail': detail,
        'neplatne_z': invalid_z[:100],
        'chybi_propojeni': chybi_propojeni,
        'sleva_bez_baliku': sleva_bez_baliku,
    }


def zasilkovna_leaderboard_map(date_from: date, date_to: date) -> dict[int, dict]:
    """Mapa id_prodejce → metriky pro žebříček."""
    linked, _ = link_sales_to_packeta(date_from, date_to)
    sales = prodeje_by_prodejce(linked)
    baliky = baliky_zpracovane_by_prodejce(date_from, date_to)
    result: dict[int, dict] = {}
    for pid in set(sales) | set(baliky):
        stats = sales.get(pid, {})
        baliku = baliky.get(pid, 0)
        prodeje = stats.get('zasilkovna_prodeje', 0)
        result[pid] = {
            'zasilkovna_baliku': baliku,
            'zasilkovna_prodeje': prodeje,
            'zasilkovna_oznaceno': stats.get('zasilkovna_oznaceno', 0),
            'zasilkovna_z_bez_cisla': stats.get('zasilkovna_z_bez_cisla', 0),
            'zasilkovna_sleva_bez_baliku': stats.get('zasilkovna_sleva_bez_baliku', 0),
            'zasilkovna_konverze_pct': _pct(prodeje, baliku),
        }
    return result


def zasilkovna_store_leaderboard_map(date_from: date, date_to: date) -> dict[int, dict]:
    """Mapa id_prodejny → metriky pro žebříček prodejen."""
    linked, _ = link_sales_to_packeta(date_from, date_to)
    prodeje = prodeje_zasilkovna_by_prodejna(linked)
    baliky = baliky_zpracovane_by_prodejna(date_from, date_to)
    result: dict[int, dict] = {}
    for sid in set(prodeje) | set(baliky):
        baliku = baliky.get(sid, 0)
        prod = prodeje.get(sid, 0)
        result[sid] = {
            'zasilkovna_baliku': baliku,
            'zasilkovna_prodeje': prod,
            'zasilkovna_konverze_pct': _pct(prod, baliku),
        }
    return result
