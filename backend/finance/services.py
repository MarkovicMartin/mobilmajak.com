"""Audit log, kategorizace Fio pohybů a DPH logika."""
from __future__ import annotations

from decimal import Decimal

from django.utils import timezone

from .models import FioKategorizacniPravidlo, NakladKategorie, NakladPolozka


def log_finance_audit(request, akce: str, detail: str = ''):
    from .models import FinanceAuditLog
    from .permissions import _client_ip

    FinanceAuditLog.objects.create(
        user_id=getattr(request.user, 'id', None),
        akce=akce,
        detail=(detail or '')[:2000],
        ip=_client_ip(request),
    )


def log_finance_system(akce: str, detail: str = ''):
    from .models import FinanceAuditLog

    FinanceAuditLog.objects.create(
        user_id=None,
        akce=akce,
        detail=(detail or '')[:2000],
        ip='',
    )


def resolve_dph_stav(kategorie_id: int | None, typ_platby: str) -> str:
    """DPH stav podle kategorie a typu platby – DPH jen z faktury (OCR)."""
    if typ_platby == NakladPolozka.TYP_PLATBY_PRICHOZI:
        return NakladPolozka.DPH_STAV_BEZ
    if not kategorie_id:
        return NakladPolozka.DPH_STAV_CEKA
    try:
        kat = NakladKategorie.objects.only('typ_dph').get(pk=kategorie_id)
    except NakladKategorie.DoesNotExist:
        return NakladPolozka.DPH_STAV_CEKA
    if kat.typ_dph == NakladKategorie.TYP_DPH_BEZ:
        return NakladPolozka.DPH_STAV_BEZ
    return NakladPolozka.DPH_STAV_CEKA


def typ_platby_from_castka(castka) -> str:
    amount = Decimal(str(castka))
    if amount < 0:
        return NakladPolozka.TYP_PLATBY_ODCHOZI
    if amount > 0:
        return NakladPolozka.TYP_PLATBY_PRICHOZI
    return NakladPolozka.TYP_PLATBY_INTERNI


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
        'castka_bez_dph': str(p.castka_bez_dph) if p.castka_bez_dph is not None else None,
        'dph_castka': str(p.dph_castka) if p.dph_castka is not None else None,
        'dph_sazba': p.dph_sazba,
        'dph_stav': p.dph_stav,
        'typ_platby': p.typ_platby,
        'symplio_doklad': p.symplio_doklad or None,
        'doklad_id': p.doklad_id,
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


def serialize_pravidlo(rule: FioKategorizacniPravidlo) -> dict:
    return {
        'id': rule.id,
        'protiucet': rule.protiucet,
        'zprava_obsahuje': rule.zprava_obsahuje,
        'vs': rule.vs,
        'castka_min': str(rule.castka_min) if rule.castka_min is not None else None,
        'castka_max': str(rule.castka_max) if rule.castka_max is not None else None,
        'kategorie_id': rule.kategorie_id,
        'kategorie_nazev': rule.kategorie.nazev if rule.kategorie_id else None,
        'prodejna_id': rule.prodejna_id,
        'ignorovat': rule.ignorovat,
        'aktivni': rule.aktivni,
        'vytvoreno': rule.vytvoreno.isoformat() if rule.vytvoreno else None,
    }


def upsert_fio_row(row: dict, dry_run: bool = False) -> str:
    """Vrátí 'created' | 'skipped' | 'incoming'."""
    fio_id = row['fio_id']
    if NakladPolozka.objects.filter(fio_id=fio_id).exists():
        return 'skipped'

    castka = Decimal(str(row['castka']))
    typ_platby = typ_platby_from_castka(castka)

    if typ_platby == NakladPolozka.TYP_PLATBY_PRICHOZI:
        payload = {
            'datum': row['datum'],
            'rok': row['datum'].year,
            'mesic': row['datum'].month,
            'castka': castka,
            'kategorie_id': None,
            'prodejna_id': None,
            'stav': NakladPolozka.STAV_IGNOROVAT,
            'zdroj': NakladPolozka.ZDROJ_FIO,
            'fio_id': fio_id,
            'popis': row.get('popis', ''),
            'protiucet': row.get('protiucet', ''),
            'vs': row.get('vs', ''),
            'zprava': row.get('zprava', ''),
            'ignorovat': True,
            'zarazeno_automaticky': False,
            'typ_platby': typ_platby,
            'dph_stav': NakladPolozka.DPH_STAV_BEZ,
        }
        if dry_run:
            return 'incoming'
        NakladPolozka.objects.create(**payload)
        return 'incoming'

    cat = apply_categorization_rules(row)
    dph_stav = resolve_dph_stav(cat['kategorie_id'], typ_platby)
    payload = {
        'datum': row['datum'],
        'rok': row['datum'].year,
        'mesic': row['datum'].month,
        'castka': castka,
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
        'typ_platby': typ_platby,
        'dph_stav': dph_stav,
    }
    if dry_run:
        return 'created'
    NakladPolozka.objects.create(**payload)
    return 'created'


def get_finance_counts() -> dict:
    return {
        'nezarazene': NakladPolozka.objects.filter(stav=NakladPolozka.STAV_NEZARAZENO).count(),
        'ceka_na_fakturu': NakladPolozka.objects.filter(
            dph_stav=NakladPolozka.DPH_STAV_CEKA,
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
        ).count(),
    }


def import_symplio_pokladna_file(path, prodejna_id: int, dry_run: bool = False) -> dict:
    """Import jednoho XLSX exportu historie pokladny. Vrací statistiky."""
    from pathlib import Path

    from .symplio_pokladna import (
        find_existing_symplio_polozka,
        is_symplio_vydej,
        parse_symplio_pokladna_xlsx,
        symplio_pokladna_external_id,
    )

    rows = parse_symplio_pokladna_xlsx(Path(path))
    stats = {'created': 0, 'updated': 0, 'skipped': 0, 'non_vydej': 0}

    for row in rows:
        if not is_symplio_vydej(row):
            stats['non_vydej'] += 1
            continue

        external_id = symplio_pokladna_external_id(prodejna_id, row)
        castka = Decimal(str(row['castka']))
        payload = {
            'datum': row['datum'],
            'rok': row['datum'].year,
            'mesic': row['datum'].month,
            'castka': castka,
            'kategorie_id': None,
            'prodejna_id': prodejna_id,
            'stav': NakladPolozka.STAV_NEZARAZENO,
            'zdroj': NakladPolozka.ZDROJ_SYMPLIO_POKLADNA,
            'fio_id': external_id,
            'symplio_doklad': row.get('symplio_doklad') or '',
            'popis': row.get('popis') or '',
            'vs': row.get('objednavka') or '',
            'zprava': row.get('admin') or '',
            'ignorovat': False,
            'zarazeno_automaticky': False,
            'typ_platby': NakladPolozka.TYP_PLATBY_ODCHOZI,
            'dph_stav': NakladPolozka.DPH_STAV_CEKA,
        }

        existing = find_existing_symplio_polozka(prodejna_id, row)
        if existing:
            if dry_run:
                stats['skipped'] += 1
                continue
            changed = False
            for field, value in payload.items():
                if field == 'fio_id' and existing.fio_id:
                    continue
                if getattr(existing, field) != value:
                    setattr(existing, field, value)
                    changed = True
            if changed:
                existing.save()
                stats['updated'] += 1
            else:
                stats['skipped'] += 1
            continue

        if dry_run:
            stats['created'] += 1
            continue
        NakladPolozka.objects.create(**payload)
        stats['created'] += 1

    return stats


def get_last_fio_import_info() -> dict | None:
    from .models import FinanceAuditLog

    row = (
        FinanceAuditLog.objects.filter(akce='fio_import')
        .order_by('-vytvoreno')
        .values('detail', 'vytvoreno')
        .first()
    )
    if not row:
        latest = (
            NakladPolozka.objects.filter(zdroj=NakladPolozka.ZDROJ_FIO)
            .order_by('-vytvoreno')
            .values('vytvoreno')
            .first()
        )
        if not latest:
            return None
        return {'vytvoreno': latest['vytvoreno'].isoformat(), 'detail': ''}
    return {
        'vytvoreno': row['vytvoreno'].isoformat(),
        'detail': row['detail'],
    }
