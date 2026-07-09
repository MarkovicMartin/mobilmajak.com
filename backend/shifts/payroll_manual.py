"""Manuální úpravy výplaty – lehký endpoint pro merge do cache provizí."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from .models import MzdovaOdmenaMesic, MzdovaPenalizaceMesic
from .payroll_service import _body_float, _body_whole, provize_po_penalizaci


def _penalizace_namespace(row):
    return SimpleNamespace(
        typ=row.typ or MzdovaPenalizaceMesic.TYP_PROCENTA,
        hodnota=row.hodnota,
        duvod=row.duvod or '',
    )


def serialize_penalizace(p, srazka_body=None):
    return {
        'id': p.id,
        'duvod': p.duvod or '',
        'typ': p.typ or MzdovaPenalizaceMesic.TYP_PROCENTA,
        'hodnota': float(p.hodnota or 0),
        'srazka_body': float(srazka_body or 0),
        'vytvoreno': p.vytvoreno.isoformat() if p.vytvoreno else None,
        'vytvoril_jmeno': (
            f'{p.vytvoril.jmeno} {p.vytvoril.prijmeni}'.strip()
            if getattr(p, 'vytvoril_id', None) else None
        ),
    }


def serialize_odmena(o):
    return {
        'id': o.id,
        'castka': float(o.castka or 0),
        'poznamka': o.poznamka or '',
        'vytvoreno': o.vytvoreno.isoformat() if o.vytvoreno else None,
        'vytvoril_jmeno': (
            f'{o.vytvoril.jmeno} {o.vytvoril.prijmeni}'.strip()
            if getattr(o, 'vytvoril_id', None) else None
        ),
    }


def _sum_odmeny(odmeny_rows):
    rows = list(odmeny_rows or [])
    total = sum(Decimal(str(r.castka or 0)) for r in rows)
    return total, rows


def manual_payroll_revision(mesic_date, odmeny_map=None, penalizace_map=None):
    """ISO timestamp poslední změny manuálních úprav v měsíci."""
    times = []
    if odmeny_map is None:
        odmeny_map = {}
        for o in MzdovaOdmenaMesic.objects.filter(mesic=mesic_date):
            odmeny_map.setdefault(o.user_id, []).append(o)
    if penalizace_map is None:
        penalizace_map = {}
        for p in MzdovaPenalizaceMesic.objects.filter(mesic=mesic_date):
            penalizace_map.setdefault(p.user_id, []).append(p)
    for rows in odmeny_map.values():
        for o in rows:
            if o.upraveno:
                times.append(o.upraveno)
            if o.vytvoreno:
                times.append(o.vytvoreno)
    for rows in penalizace_map.values():
        for p in rows:
            if p.vytvoreno:
                times.append(p.vytvoreno)
    if not times:
        return None
    return max(times).isoformat()


def _celkem_from_parts(row, provize_body, odmena_mesic):
    return _body_whole(
        Decimal(str(row.get('mzda_fixni_body') or 0))
        + provize_body
        + odmena_mesic
        + Decimal(str(row.get('dovolena_body') or 0))
        + Decimal(str(row.get('prescas_body') or 0))
        + Decimal(str(row.get('cestovne_body') or 0))
        + Decimal(str(row.get('dyska_body') or 0))
        + Decimal(str(row.get('pol_dok_odmena_body') or 0))
    )


def apply_manual_adjustments_to_row(row, odmeny_rows=None, penalizace_rows=None):
    """
    Aplikuje měsíční odměny a penalizace na řádek výplaty.
    row musí obsahovat provize_body_brutto (nebo provize_body jako brutto před srážkami).
    """
    row = dict(row)
    provize_brutto = _body_whole(row.get('provize_body_brutto') or row.get('provize_body') or 0)

    odmena_mesic, odmeny_rows = _sum_odmeny(odmeny_rows)

    penalizace_rows = list(penalizace_rows or [])
    provize_body, penalizace_srazka, penalizace_procent, penalizace_detail = provize_po_penalizaci(
        provize_brutto, [_penalizace_namespace(p) for p in penalizace_rows],
    )
    penalizace_fixni = sum(
        float(d.get('srazka_body') or 0)
        for d in penalizace_detail
        if d.get('typ') == 'fixni'
    )

    row['odmena_mesic_body'] = _body_float(odmena_mesic)
    row['odmena_mesic_poznamka'] = '; '.join(
        (o.poznamka or '').strip() for o in odmeny_rows if (o.poznamka or '').strip()
    )
    row['odmeny'] = [serialize_odmena(o) for o in odmeny_rows]
    row['provize_body_brutto'] = _body_float(provize_brutto)
    row['provize_body'] = _body_float(provize_body)
    row['penalizace_pocet'] = len(penalizace_rows)
    row['penalizace_procent'] = float(penalizace_procent)
    row['penalizace_fixni_body'] = penalizace_fixni
    row['penalizace_srazka_body'] = _body_float(penalizace_srazka)
    row['penalizace_popis'] = '; '.join(
        (p.duvod or '').strip() for p in penalizace_rows if (p.duvod or '').strip()
    )
    row['penalizace'] = [
        serialize_penalizace(p, d.get('srazka_body'))
        for p, d in zip(penalizace_rows, penalizace_detail)
    ]
    row['celkem_body'] = _body_float(_celkem_from_parts(row, provize_body, odmena_mesic))
    return row


def strip_manual_adjustments_from_row(row):
    """Řádek bez manuálních úprav – vhodné pro cache těžkého výpočtu provizí."""
    row = dict(row)
    provize_brutto = _body_whole(row.get('provize_body_brutto') or row.get('provize_body') or 0)
    row['provize_body_brutto'] = _body_float(provize_brutto)
    row['odmena_mesic_body'] = 0.0
    row['odmena_mesic_poznamka'] = ''
    row['odmeny'] = []
    row['penalizace_pocet'] = 0
    row['penalizace_procent'] = 0.0
    row['penalizace_fixni_body'] = 0.0
    row['penalizace_srazka_body'] = 0.0
    row['penalizace_popis'] = ''
    row['penalizace'] = []
    row['provize_body'] = _body_float(provize_brutto)
    row['celkem_body'] = _body_float(
        _celkem_from_parts(row, provize_brutto, Decimal('0')),
    )
    return row


def load_manual_maps(mesic_date, user_ids=None):
    odmeny_qs = MzdovaOdmenaMesic.objects.filter(mesic=mesic_date).select_related('vytvoril').order_by('vytvoreno')
    penalizace_qs = MzdovaPenalizaceMesic.objects.filter(
        mesic=mesic_date,
    ).select_related('vytvoril').order_by('vytvoreno')
    if user_ids is not None:
        user_ids = list(user_ids)
        odmeny_qs = odmeny_qs.filter(user_id__in=user_ids)
        penalizace_qs = penalizace_qs.filter(user_id__in=user_ids)
    odmeny_map = {}
    for o in odmeny_qs:
        odmeny_map.setdefault(o.user_id, []).append(o)
    penalizace_map = {}
    for p in penalizace_qs:
        penalizace_map.setdefault(p.user_id, []).append(p)
    return odmeny_map, penalizace_map


def merge_manual_into_rows(rows, mesic_str):
    """Aplikuje aktuální manuální úpravy na řádky (např. z cache bez manual)."""
    if not rows:
        return rows, None
    rok, mesic_cislo = map(int, mesic_str.split('-'))
    mesic_date = date(rok, mesic_cislo, 1)
    user_ids = [r['user_id'] for r in rows]
    odmeny_map, penalizace_map = load_manual_maps(mesic_date, user_ids)
    revision = manual_payroll_revision(mesic_date, odmeny_map, penalizace_map)
    merged = []
    for row in rows:
        uid = row['user_id']
        merged.append(apply_manual_adjustments_to_row(
            row,
            odmeny_map.get(uid),
            penalizace_map.get(uid),
        ))
    return merged, revision
