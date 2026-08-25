"""Audit log, kategorizace Fio pohybů a DPH logika."""
from __future__ import annotations

from decimal import Decimal

from django.utils import timezone

from .models import FinanceDoklad, FioKategorizacniPravidlo, NakladKategorie, NakladPolozka

from .kategorizace import apply_all_rules
from .symplio_vydej_parse import faktura_hint_from_polozka


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
    # Zpráva + popis – Symplio/manuál často má text jen v popisu
    text = f"{row.get('zprava') or ''} {row.get('popis') or ''}".lower()
    if rule.zprava_obsahuje and rule.zprava_obsahuje.lower() not in text:
        return False
    castka = abs(Decimal(str(row.get('castka') or 0)))
    if rule.castka_min is not None and castka < rule.castka_min:
        return False
    if rule.castka_max is not None and castka > rule.castka_max:
        return False
    return True


def _normalize_rule_snippet(text: str, max_len: int = 80) -> str:
    """Normalizovaný úryvek pro zprava_obsahuje (min. 4 znaky)."""
    cleaned = ' '.join((text or '').split())
    if len(cleaned) < 4:
        return ''
    return cleaned[:max_len]


def rule_key_from_polozka(polozka: NakladPolozka) -> dict | None:
    """
    Preferovaný klíč pravidla: protiucet → vs → úryvek zpravy/popisu.
    Vrací dict polí pro FioKategorizacniPravidlo, nebo None.
    """
    protiucet = (polozka.protiucet or '').strip()
    if protiucet:
        return {'protiucet': protiucet[:64], 'vs': '', 'zprava_obsahuje': ''}
    vs = (polozka.vs or '').strip()
    if vs:
        return {'protiucet': '', 'vs': vs[:32], 'zprava_obsahuje': ''}
    snippet = _normalize_rule_snippet(polozka.zprava or '') or _normalize_rule_snippet(polozka.popis or '')
    if snippet:
        return {'protiucet': '', 'vs': '', 'zprava_obsahuje': snippet[:200]}
    return None


def upsert_pravidlo_from_polozka(polozka: NakladPolozka, user_id: int | None = None) -> dict:
    """
    Po ručním zařazení/změně kategorie: upsert aktivního Fio pravidla.
    Vrací {pravidlo_created, pravidlo_updated, pravidlo_id}.
    """
    empty = {'pravidlo_created': False, 'pravidlo_updated': False, 'pravidlo_id': None}
    if not polozka.kategorie_id:
        return empty
    key = rule_key_from_polozka(polozka)
    if not key:
        return empty

    existing = (
        FioKategorizacniPravidlo.objects.filter(
            aktivni=True,
            protiucet=key['protiucet'],
            vs=key['vs'],
            zprava_obsahuje=key['zprava_obsahuje'],
        )
        .order_by('id')
        .first()
    )
    if existing:
        changed = False
        if existing.kategorie_id != polozka.kategorie_id:
            existing.kategorie_id = polozka.kategorie_id
            changed = True
        if polozka.prodejna_id and existing.prodejna_id != polozka.prodejna_id:
            existing.prodejna_id = polozka.prodejna_id
            changed = True
        if existing.ignorovat:
            existing.ignorovat = False
            changed = True
        if changed:
            existing.save()
        return {
            'pravidlo_created': False,
            'pravidlo_updated': changed,
            'pravidlo_id': existing.id,
        }

    rule = FioKategorizacniPravidlo.objects.create(
        protiucet=key['protiucet'],
        vs=key['vs'],
        zprava_obsahuje=key['zprava_obsahuje'],
        kategorie_id=polozka.kategorie_id,
        prodejna_id=polozka.prodejna_id,
        ignorovat=False,
        aktivni=True,
        vytvoril_user_id=user_id,
    )
    return {
        'pravidlo_created': True,
        'pravidlo_updated': False,
        'pravidlo_id': rule.id,
    }


def compute_stav_rozdilu(prijmy, naklady) -> str:
    """minus | vyrovnano | plus – KPI barva rozdílu."""
    p = Decimal(str(prijmy or 0))
    n = Decimal(str(naklady or 0))
    rozdil = p - n
    if rozdil < 0:
        return 'minus'
    if p > 0 and (abs(rozdil) / p) < Decimal('0.05'):
        return 'vyrovnano'
    if rozdil > 0:
        return 'plus'
    return 'vyrovnano'


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


def serialize_doklad_brief(d) -> dict:
    from .doklady import serialize_doklad
    return serialize_doklad(d)


def serialize_naklad_polozka(p: NakladPolozka, prodejna_map: dict | None = None) -> dict:
    prodejna_nazev = None
    if p.prodejna_id and prodejna_map is not None:
        prodejna_nazev = prodejna_map.get(p.prodejna_id)
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
        'doklad': serialize_doklad_brief(p.doklad) if p.doklad_id else None,
        'kategorie_id': p.kategorie_id,
        'kategorie_nazev': p.kategorie.nazev if p.kategorie_id else None,
        'prodejna_id': p.prodejna_id,
        'prodejna_nazev': prodejna_nazev,
        'stav': p.stav,
        'zdroj': p.zdroj,
        'fio_id': p.fio_id,
        'popis': p.popis,
        'protiucet': p.protiucet,
        'vs': p.vs,
        'zprava': p.zprava,
        'ignorovat': p.ignorovat,
        'zarazeno_automaticky': p.zarazeno_automaticky,
        'auto_pravidlo': p.auto_pravidlo or None,
        'faktura_hint': faktura_hint_from_polozka(p),
        'poznamka_admin': p.poznamka_admin,
        'upravil_user_id': p.upravil_user_id,
        'upraveno': p.upraveno.isoformat() if p.upraveno else None,
        'vytvoreno': p.vytvoreno.isoformat() if p.vytvoreno else None,
    }


def serialize_naklad_polozky(qs) -> list:
    polozky = list(qs)
    ids = {p.prodejna_id for p in polozky if p.prodejna_id}
    prodejna_map = {}
    if ids:
        from stores.models import Prodejna
        prodejna_map = {
            row.id: row.nazev
            for row in Prodejna.objects.filter(id__in=ids).only('id', 'nazev')
        }
    return [serialize_naklad_polozka(p, prodejna_map) for p in polozky]


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

    cat = apply_all_rules(row, zdroj=NakladPolozka.ZDROJ_FIO)
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
        'auto_pravidlo': cat.get('auto_pravidlo', ''),
        'typ_platby': typ_platby,
        'dph_stav': dph_stav,
    }
    if dry_run:
        return 'created'
    NakladPolozka.objects.create(**payload)
    return 'created'


def get_finance_counts() -> dict:
    odchozi = NakladPolozka.objects.filter(typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI)
    return {
        'nezarazene': odchozi.filter(stav=NakladPolozka.STAV_NEZARAZENO).count(),
        'ceka_na_fakturu': odchozi.filter(
            dph_stav=NakladPolozka.DPH_STAV_CEKA,
        ).count(),
        'auto_zarazeno': odchozi.filter(
            stav=NakladPolozka.STAV_ZARAZENO,
            zarazeno_automaticky=True,
        ).count(),
        'rucne_zarazeno': odchozi.filter(stav=NakladPolozka.STAV_RUCNE).count(),
        'ignorovano': odchozi.filter(stav=NakladPolozka.STAV_IGNOROVAT).count(),
        'bez_faktury': odchozi.filter(
            dph_stav=NakladPolozka.DPH_STAV_CEKA,
            doklad__isnull=True,
        ).exclude(stav=NakladPolozka.STAV_IGNOROVAT).count(),
        'doklady_ke_kontrole': FinanceDoklad.objects.filter(
            stav__in=(
                FinanceDoklad.STAV_CEKA_NA_OCR,
                FinanceDoklad.STAV_KE_KONTROLE,
                FinanceDoklad.STAV_NOVA,
            ),
        ).count(),
    }


def import_symplio_pokladna_file(
    path,
    prodejna_id: int,
    dry_run: bool = False,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    """Import jednoho XLSX exportu historie pokladny. Vrací statistiky."""
    from pathlib import Path

    from .symplio_pokladna import (
        find_existing_symplio_polozka,
        is_symplio_vydej,
        parse_symplio_pokladna_xlsx,
        symplio_pokladna_external_id,
    )

    rows = parse_symplio_pokladna_xlsx(Path(path))
    stats = {'created': 0, 'updated': 0, 'skipped': 0, 'non_vydej': 0, 'out_of_range': 0}

    for row in rows:
        if date_from and row['datum'] < date_from:
            stats['out_of_range'] += 1
            continue
        if date_to and row['datum'] > date_to:
            stats['out_of_range'] += 1
            continue
        if not is_symplio_vydej(row):
            stats['non_vydej'] += 1
            continue

        external_id = symplio_pokladna_external_id(prodejna_id, row)
        castka = Decimal(str(row['castka']))
        rule_row = {
            'popis': row.get('popis') or '',
            'zprava': row.get('admin') or '',
            'castka': castka,
        }
        cat = apply_all_rules(rule_row, zdroj=NakladPolozka.ZDROJ_SYMPLIO_POKLADNA, prodejna_id=prodejna_id)
        payload = {
            'datum': row['datum'],
            'rok': row['datum'].year,
            'mesic': row['datum'].month,
            'castka': castka,
            'kategorie_id': cat['kategorie_id'],
            'prodejna_id': cat['prodejna_id'] or prodejna_id,
            'stav': cat['stav'],
            'zdroj': NakladPolozka.ZDROJ_SYMPLIO_POKLADNA,
            'fio_id': external_id,
            'symplio_doklad': row.get('symplio_doklad') or '',
            'popis': row.get('popis') or '',
            'vs': row.get('objednavka') or '',
            'zprava': row.get('admin') or '',
            'ignorovat': cat['ignorovat'],
            'zarazeno_automaticky': cat['zarazeno_automaticky'],
            'auto_pravidlo': cat.get('auto_pravidlo', ''),
            'typ_platby': NakladPolozka.TYP_PLATBY_ODCHOZI,
            'dph_stav': resolve_dph_stav(cat['kategorie_id'], NakladPolozka.TYP_PLATBY_ODCHOZI),
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
