"""Skladové výdejky – seznam a souhrny pro payroll panel."""
from __future__ import annotations

from datetime import date

from django.db.models import Count, Sum

from analytics.sklad_vydejky_parse import (
    DUVOD_KATEGORIE_LABELS,
    SKLAD_TYP_LABELS,
    VYDEJKA_ALLOWED_SUBTYPES,
)


def _month_bounds(rok: int, mesic: int) -> tuple[date, date]:
    import calendar
    last = calendar.monthrange(rok, mesic)[1]
    return date(rok, mesic, 1), date(rok, mesic, last)


def vydejky_queryset_for_month(rok: int, mesic: int):
    from analytics.models import SkladVydejka

    start, end = _month_bounds(rok, mesic)
    return (
        SkladVydejka.objects.filter(
            vystaveno__gte=start,
            vystaveno__lte=end,
            symplio_subtype__in=VYDEJKA_ALLOWED_SUBTYPES,
        )
        .prefetch_related('polozky')
    )


def _resolve_spravce_ids(spravce_names: set[str]) -> dict[str, int]:
    if not spravce_names:
        return {}
    from users.models import WebUser

    out = {}
    for user in WebUser.objects.all().only('id', 'jmeno', 'prijmeni'):
        label = f'{user.jmeno} {user.prijmeni}'.strip()
        if label in spravce_names:
            out[label] = user.id
    return out


def _vazba_prodej_info(vazba: str | None) -> dict:
    if not vazba:
        return {'vazba_nalezena': False, 'vazba_doklad': None, 'vazba_datum': None}
    from analytics.models import WebProdejeAll

    vazba = vazba.strip()
    row = (
        WebProdejeAll.objects.filter(doklad=vazba)
        .order_by('-typ')
        .values('doklad', 'typ')
        .first()
    )
    if not row:
        return {'vazba_nalezena': False, 'vazba_doklad': vazba, 'vazba_datum': None}
    return {
        'vazba_nalezena': True,
        'vazba_doklad': row['doklad'],
        'vazba_datum': row['typ'].isoformat() if row.get('typ') else None,
    }


def vydejky_totals(qs) -> dict:
    agg = qs.aggregate(
        doklady=Count('doklad'),
        polozky=Count('polozky'),
        castka=Sum('castka_s_dph'),
    )
    return {
        'doklady': int(agg['doklady'] or 0),
        'polozky': int(agg['polozky'] or 0),
        'castka': float(agg['castka'] or 0),
    }


def vydejky_summary_by_spravce(qs) -> list[dict]:
    rows = (
        qs.exclude(spravce__isnull=True)
        .exclude(spravce='')
        .values('spravce')
        .annotate(
            doklady=Count('doklad'),
            polozky=Count('polozky'),
            castka=Sum('castka_s_dph'),
        )
        .order_by('-doklady', 'spravce')
    )
    return [
        {
            'spravce': row['spravce'],
            'doklady': int(row['doklady'] or 0),
            'polozky': int(row['polozky'] or 0),
            'castka': float(row['castka'] or 0),
        }
        for row in rows
    ]


def duvod_totals_from_rows(rows: list[dict]) -> dict[str, int]:
    out = {'rucni': 0, 'spotreba': 0, 'reklamace': 0}
    for row in rows:
        key = row.get('duvod_kategorie')
        if key in out:
            out[key] += 1
    return out


def list_vydejky(qs, *, duvod_kategorie: str | None = None, sklad_typ: str | None = None) -> list[dict]:
    if duvod_kategorie:
        qs = qs.filter(duvod_kategorie=duvod_kategorie)
    if sklad_typ:
        qs = qs.filter(sklad_typ=sklad_typ)

    spravce_names = {v.spravce for v in qs if v.spravce}
    spravce_ids = _resolve_spravce_ids(spravce_names)

    rows = []
    for doc in qs.order_by('-vystaveno', 'doklad'):
        polozky = []
        for p in doc.polozky.all():
            polozky.append({
                'kod': p.kod,
                'nazev': (p.nazev or '')[:100],
                'kusy': int(p.pocet_kusu or 0),
                'cena_ks_bez_dph': float(p.cena_ks_bez_dph) if p.cena_ks_bez_dph is not None else None,
                'castka': float(p.cena_celkem_bez_dph) if p.cena_celkem_bez_dph is not None else None,
                'stredisko': p.stredisko,
            })
        vazba_info = _vazba_prodej_info(doc.vazba)
        rows.append({
            'datum': doc.vystaveno.isoformat(),
            'doklad': doc.doklad,
            'duvod_vyskladneni': doc.duvod_vyskladneni,
            'duvod_kategorie': doc.duvod_kategorie,
            'duvod_kategorie_label': DUVOD_KATEGORIE_LABELS.get(doc.duvod_kategorie, doc.duvod_kategorie),
            'sklad_typ': doc.sklad_typ,
            'sklad_typ_label': SKLAD_TYP_LABELS.get(doc.sklad_typ, doc.sklad_typ),
            'symplio_subtype': doc.symplio_subtype,
            'spravce': doc.spravce,
            'id_spravce': spravce_ids.get(doc.spravce),
            'vazba': doc.vazba,
            'castka_s_dph': float(doc.castka_s_dph or 0),
            'castka_bez_dph': float(doc.castka_bez_dph or 0),
            'polozky': polozky,
            **vazba_info,
        })
    return rows
