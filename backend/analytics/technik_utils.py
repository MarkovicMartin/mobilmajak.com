"""
Mapování hodnot sloupce WEB_PRODEJE_ALL.Technik na zobrazované jméno technika.

Actor/EDA někdy ukládá „ID: 148“ místo jména; historicky „Benny Babušík“ → „Artur Babušík“.
"""
import re
from collections import defaultdict

from django.db.models import Q

from users.models import WebUser

# technik_id -> další raw hodnoty v Technik (kromě jména z WEB_USERS a „ID: {id}“)
HISTORICAL_TECHNIK_RAW = {
    148: ['Benny Babušík'],
    343: [],
}

_ID_PREFIX_RE = re.compile(r'^ID:\s*(\d+)\s*$', re.IGNORECASE)

_NUMERIC_BREAKDOWN_KEYS = frozenset({
    'obrat_bez_dph', 'marze', 'polozky', 'doklady',
    'sluzby_obrat', 'sluzby_zisk', 'sluzby_polozky', 'sluzby_doklady',
    'prumerna_cena_na_doklad', 'service_score', 'seller_score',
})


def _load_technik_maps():
    """technik_id -> kanonické jméno; kanonické jméno -> množina raw variant pro SQL filtr."""
    id_to_name = {}
    name_to_variants = defaultdict(set)

    users = WebUser.objects.exclude(technik_id__isnull=True).exclude(technik_id=0)
    for u in users:
        name = f'{u.jmeno} {u.prijmeni}'.strip()
        if not name:
            continue
        id_to_name[u.technik_id] = name
        name_to_variants[name].add(name)
        name_to_variants[name].add(f'ID: {u.technik_id}')

    for technik_id, extras in HISTORICAL_TECHNIK_RAW.items():
        canonical = id_to_name.get(technik_id)
        if not canonical:
            continue
        for raw in extras:
            name_to_variants[canonical].add(raw)

    return id_to_name, dict(name_to_variants)


def resolve_technik_display(raw_technik, id_to_name=None):
    """„ID: 148“ / „Benny Babušík“ -> „Artur Babušík“."""
    if not raw_technik:
        return raw_technik
    raw = str(raw_technik).strip()
    if id_to_name is None:
        id_to_name, _ = _load_technik_maps()

    m = _ID_PREFIX_RE.match(raw)
    if m:
        tid = int(m.group(1))
        if tid in id_to_name:
            return id_to_name[tid]

    for technik_id, extras in HISTORICAL_TECHNIK_RAW.items():
        if raw in extras:
            canonical = id_to_name.get(technik_id)
            if canonical:
                return canonical

    return raw


def technik_filter_q(display_name):
    """Q filtr pro všechny raw varianty jednoho technika (detail / položky)."""
    _, name_to_variants = _load_technik_maps()
    variants = name_to_variants.get(display_name, {display_name})
    return Q(technik__in=list(variants))


def merge_technici_rows(rows):
    """Sloučí řádky rozpadu techniků podle kanonického jména."""
    if not rows:
        return rows

    id_to_name, _ = _load_technik_maps()
    merged = {}

    for row in rows:
        raw_name = row.get('technik')
        canonical = resolve_technik_display(raw_name, id_to_name)
        item = dict(row)
        item['technik'] = canonical

        if canonical not in merged:
            merged[canonical] = item
            continue

        target = merged[canonical]
        for key, val in item.items():
            if key == 'technik':
                continue
            if key in _NUMERIC_BREAKDOWN_KEYS and isinstance(val, (int, float)):
                target[key] = (target.get(key) or 0) + val

        if target.get('doklady'):
            target['prumerna_cena_na_doklad'] = round(
                (target.get('obrat_bez_dph') or 0) / target['doklady'], 2
            )

    result = list(merged.values())
    result.sort(key=lambda x: -(x.get('obrat_bez_dph') or 0))
    return result


def aggregate_by_canonical_technik(rows, value_key='obrat_bez_dph'):
    """{raw Technik: číslo} -> {kanonické jméno: součet}."""
    id_to_name, _ = _load_technik_maps()
    out = defaultdict(float)
    for row in rows:
        raw = row.get('technik')
        canonical = resolve_technik_display(raw, id_to_name)
        out[canonical] += float(row.get(value_key) or 0)
    return dict(out)
