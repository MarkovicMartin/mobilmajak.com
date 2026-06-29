"""Audit log a kategorizace Fio pohybů."""
from __future__ import annotations

from decimal import Decimal

from django.utils import timezone

from .models import FioKategorizacniPravidlo, NakladPolozka


def log_finance_audit(request, akce: str, detail: str = ''):
    from .models import FinanceAuditLog
    from .permissions import _client_ip

    FinanceAuditLog.objects.create(
        user_id=getattr(request.user, 'id', None),
        akce=akce,
        detail=(detail or '')[:2000],
        ip=_client_ip(request),
    )


def _matches_rule(rule: FioKategorizacniPravidlo, row: dict) -> bool:
    if rule.protiucet and rule.protiucet not in (row.get('protiucet') or ''):
        return False
    if rule.vs and rule.vs != (row.get('vs') or ''):
        return False
    zprava = (row.get('zprava') or '').lower()
    if rule.zprava_obsahuje and rule.zprava_obsahuje.lower() not in zprava:
        return False
    castka = abs(Decimal(str(row.get('castka') or 0)))
    if rule.castka_min is not None and castka < rule.castka_min:
        return False
    if rule.castka_max is not None and castka > rule.castka_max:
        return False
    return True


def apply_categorization_rules(row: dict) -> dict:
    """Vrátí dict s stav, kategorie_id, prodejna_id, ignorovat, zarazeno_automaticky."""
    rules = FioKategorizacniPravidlo.objects.filter(aktivni=True).order_by('id')
    for rule in rules:
        if not _matches_rule(rule, row):
            continue
        if rule.ignorovat:
            return {
                'stav': NakladPolozka.STAV_IGNOROVAT,
                'kategorie_id': None,
                'prodejna_id': rule.prodejna_id,
                'ignorovat': True,
                'zarazeno_automaticky': True,
            }
        if rule.kategorie_id:
            return {
                'stav': NakladPolozka.STAV_ZARAZENO,
                'kategorie_id': rule.kategorie_id,
                'prodejna_id': rule.prodejna_id,
                'ignorovat': False,
                'zarazeno_automaticky': True,
            }
    return {
        'stav': NakladPolozka.STAV_NEZARAZENO,
        'kategorie_id': None,
        'prodejna_id': None,
        'ignorovat': False,
        'zarazeno_automaticky': False,
    }


def serialize_naklad_polozka(p: NakladPolozka) -> dict:
    return {
        'id': p.id,
        'datum': p.datum.isoformat(),
        'rok': p.rok,
        'mesic': p.mesic,
        'castka': str(p.castka),
        'kategorie_id': p.kategorie_id,
        'kategorie_nazev': p.kategorie.nazev if p.kategorie_id else None,
        'prodejna_id': p.prodejna_id,
        'stav': p.stav,
        'zdroj': p.zdroj,
        'fio_id': p.fio_id,
        'popis': p.popis,
        'protiucet': p.protiucet,
        'vs': p.vs,
        'zprava': p.zprava,
        'ignorovat': p.ignorovat,
        'zarazeno_automaticky': p.zarazeno_automaticky,
        'poznamka_admin': p.poznamka_admin,
        'upravil_user_id': p.upravil_user_id,
        'upraveno': p.upraveno.isoformat() if p.upraveno else None,
        'vytvoreno': p.vytvoreno.isoformat() if p.vytvoreno else None,
    }


def upsert_fio_row(row: dict, dry_run: bool = False) -> str:
    """Vrátí 'created' | 'skipped' | 'updated'."""
    fio_id = row['fio_id']
    if NakladPolozka.objects.filter(fio_id=fio_id).exists():
        return 'skipped'
    cat = apply_categorization_rules(row)
    datum = row['datum']
    payload = {
        'datum': datum,
        'rok': datum.year,
        'mesic': datum.month,
        'castka': row['castka'],
        'kategorie_id': cat['kategorie_id'],
        'prodejna_id': cat['prodejna_id'],
        'stav': cat['stav'],
        'zdroj': NakladPolozka.ZDROJ_FIO,
        'fio_id': fio_id,
        'popis': row.get('popis', ''),
        'protiucet': row.get('protiucet', ''),
        'vs': row.get('vs', ''),
        'zprava': row.get('zprava', ''),
        'ignorovat': cat['ignorovat'],
        'zarazeno_automaticky': cat['zarazeno_automaticky'],
    }
    if dry_run:
        return 'created'
    NakladPolozka.objects.create(**payload)
    return 'created'
