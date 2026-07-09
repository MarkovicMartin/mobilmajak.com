"""Audit log admin úprav dovolené a ručních hodin (vlna B – DV4)."""

from __future__ import annotations

from decimal import Decimal

from shifts.models import DovolenaKorekceLog, PrumerMzdyMesicOverrideLog


def _user_label(user) -> str | None:
    if not user:
        return None
    return f'{user.jmeno} {user.prijmeni}'.strip() or getattr(user, 'uzivatelske_jmeno', None)


def _decimal_str(value) -> str | None:
    if value is None:
        return None
    return str(value)


def serialize_dovolena_korekce_log(entry: DovolenaKorekceLog) -> dict:
    return {
        'typ': 'dovolena',
        'id': entry.id,
        'vytvoreno': entry.vytvoreno.isoformat() if entry.vytvoreno else None,
        'zmenil_jmeno': _user_label(entry.zmenil),
        'poznamka': entry.poznamka or '',
        'zmeny': [
            {
                'pole': 'fond_extra_h',
                'pred': _decimal_str(entry.fond_extra_h_pred),
                'po': _decimal_str(entry.fond_extra_h_po),
            },
            {
                'pole': 'korekce_cerpano_h',
                'pred': _decimal_str(entry.korekce_cerpano_h_pred),
                'po': _decimal_str(entry.korekce_cerpano_h_po),
            },
        ],
    }


def serialize_prumer_override_log(entry: PrumerMzdyMesicOverrideLog) -> dict:
    return {
        'typ': 'prumer',
        'id': entry.id,
        'vytvoreno': entry.vytvoreno.isoformat() if entry.vytvoreno else None,
        'zmenil_jmeno': _user_label(entry.zmenil),
        'poznamka': entry.poznamka or '',
        'akce': entry.akce,
        'rok': entry.rok,
        'mesic': entry.mesic,
        'zmeny': [
            {
                'pole': 'odpracovano_h',
                'pred': _decimal_str(entry.odpracovano_h_pred),
                'po': _decimal_str(entry.odpracovano_h_po),
            },
            {
                'pole': 'fixni_body',
                'pred': _decimal_str(entry.fixni_body_pred),
                'po': _decimal_str(entry.fixni_body_po),
            },
        ],
    }


def log_prumer_override_change(
    *,
    user,
    zmenil,
    akce: str,
    rok: int,
    mesic: int,
    override=None,
    odpracovano_h_pred=None,
    odpracovano_h_po=None,
    fixni_body_pred=None,
    fixni_body_po=None,
    poznamka: str = '',
) -> PrumerMzdyMesicOverrideLog:
    return PrumerMzdyMesicOverrideLog.objects.create(
        user=user,
        zmenil=zmenil,
        override=override,
        akce=akce,
        rok=rok,
        mesic=mesic,
        odpracovano_h_pred=odpracovano_h_pred,
        odpracovano_h_po=odpracovano_h_po,
        fixni_body_pred=fixni_body_pred,
        fixni_body_po=fixni_body_po,
        poznamka=(poznamka or '').strip(),
    )


def fetch_admin_adjustment_audit(user_id: int, limit: int = 30) -> list[dict]:
    dovolena = [
        serialize_dovolena_korekce_log(row)
        for row in DovolenaKorekceLog.objects.filter(user_id=user_id)
        .select_related('zmenil')
        .order_by('-vytvoreno')[:limit]
    ]
    prumer = [
        serialize_prumer_override_log(row)
        for row in PrumerMzdyMesicOverrideLog.objects.filter(user_id=user_id)
        .select_related('zmenil')
        .order_by('-vytvoreno')[:limit]
    ]
    merged = dovolena + prumer
    merged.sort(key=lambda item: item.get('vytvoreno') or '', reverse=True)
    return merged[:limit]
