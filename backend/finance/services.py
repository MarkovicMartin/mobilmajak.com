"""Audit log, kategorizace Fio pohybů a DPH logika."""
from __future__ import annotations

import logging
import re
from decimal import Decimal

from django.utils import timezone

from .models import FinanceDoklad, FioKategorizacniPravidlo, NakladKategorie, NakladPolozka

from .kategorizace import apply_all_rules
from .symplio_vydej_parse import faktura_hint_from_polozka

logger = logging.getLogger(__name__)


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


def _text_field_matches(rule: FioKategorizacniPravidlo, zprava: str, popis: str) -> bool:
    needle = (rule.zprava_obsahuje or '').strip()
    if not needle:
        return True
    needle_l = needle.lower()
    z_l = (zprava or '').strip().lower()
    p_l = (popis or '').strip().lower()
    mode = rule.text_shoda or FioKategorizacniPravidlo.TEXT_SHODA_OBSAHUJE
    if mode == FioKategorizacniPravidlo.TEXT_SHODA_PRESNE:
        if z_l and p_l:
            return z_l == needle_l and p_l == needle_l
        if z_l:
            return z_l == needle_l
        if p_l:
            return p_l == needle_l
        return False
    text = f"{z_l} {p_l}".strip()
    return needle_l in text


def _matches_rule(rule: FioKategorizacniPravidlo, row: dict) -> bool:
    if rule.protiucet and rule.protiucet not in (row.get('protiucet') or ''):
        return False
    if rule.vs and rule.vs != (row.get('vs') or ''):
        return False
    if rule.zprava_obsahuje:
        if not _text_field_matches(rule, row.get('zprava') or '', row.get('popis') or ''):
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


_FA_TAIL_RE = re.compile(
    r'[\s\-–]*(?:fa|faktura|fakt\.?)?\s*[A-Z]?\d[\w./\-]{2,}\s*$',
    re.I,
)
_VYDEJ_PREFIX_RE = re.compile(r'^manu[aá]ln[ií]\s+v[yý]de[jj]\s+', re.I)


def _learn_snippet_from_symplio_popis(popis: str) -> str:
    """
    Stabilní text pro učení z kasy: dodavatel / typ výdeje bez čísla FA a jména admina.
    """
    from .symplio_vydej_parse import parse_symplio_vydej_faktura

    raw = (popis or '').strip()
    if not raw:
        return ''

    parsed = parse_symplio_vydej_faktura(raw)
    if parsed and parsed.get('dodavatel_nazev'):
        return _normalize_rule_snippet(parsed['dodavatel_nazev'], max_len=120)

    text = _VYDEJ_PREFIX_RE.sub('', raw).strip()
    text = _FA_TAIL_RE.sub('', text).strip(' -–')
    # Úhrada výkupky V2607… → „Úhrada výkupky“
    text = re.sub(r'\bV\d{6,}\b', '', text, flags=re.I).strip(' -–')
    text = ' '.join(text.split())
    return _normalize_rule_snippet(text, max_len=120)


def rule_key_from_polozka(polozka: NakladPolozka) -> dict | None:
    """
    Klíč z manuálního zařazení (bez ručního zadávání pravidel):
    - Fio: protiucet → vs → úryvek zprávy
    - Symplio pokladna: stabilní úryvek popisu (dodavatel), ne admin ani FA
    """
    if polozka.zdroj == NakladPolozka.ZDROJ_SYMPLIO_POKLADNA:
        snippet = _learn_snippet_from_symplio_popis(polozka.popis or '')
        if snippet:
            return {'protiucet': '', 'vs': '', 'zprava_obsahuje': snippet[:200]}
        return None

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


def pravidlo_ma_klic(rule: FioKategorizacniPravidlo) -> bool:
    """Pravidlo musí mít aspoň jeden matchovací klíč, jinak by trefilo vše."""
    return bool(
        (rule.protiucet or '').strip()
        or (rule.vs or '').strip()
        or (rule.zprava_obsahuje or '').strip()
        or rule.castka_min is not None
        or rule.castka_max is not None
    )


def _apply_matched_pravidlo(rule: FioKategorizacniPravidlo, p: NakladPolozka) -> None:
    if rule.ignorovat:
        p.stav = NakladPolozka.STAV_IGNOROVAT
        p.ignorovat = True
        p.kategorie_id = None
    else:
        p.stav = NakladPolozka.STAV_ZARAZENO
        p.kategorie_id = rule.kategorie_id
        p.ignorovat = False
        if rule.prodejna_id:
            p.prodejna_id = rule.prodejna_id
    p.zarazeno_automaticky = True
    p.auto_pravidlo = 'db_pravidlo'
    p.dph_stav = resolve_dph_stav(p.kategorie_id, p.typ_platby)
    p.save(update_fields=[
        'stav', 'kategorie_id', 'prodejna_id', 'ignorovat',
        'zarazeno_automaticky', 'auto_pravidlo', 'dph_stav',
    ])
    if not p.ignorovat:
        try:
            from .doklady import try_auto_link_polozka
            try_auto_link_polozka(p)
        except Exception:
            logger.exception('Auto-link doklad failed for polozka_id=%s', p.id)


def apply_pravidlo_to_nezarazene(rule: FioKategorizacniPravidlo, dry_run: bool = False) -> dict:
    """Aplikuje konkrétní DB pravidlo na už importované nezařazené odchozí platby."""
    from django.db.models import Q

    from .kategorizace import polozka_as_row

    empty = {'updated': 0, 'scanned': 0}
    if not pravidlo_ma_klic(rule):
        return empty
    if not rule.ignorovat and not rule.kategorie_id:
        return empty

    qs = NakladPolozka.objects.filter(
        stav=NakladPolozka.STAV_NEZARAZENO,
        typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
    )
    if rule.protiucet:
        qs = qs.filter(protiucet__contains=rule.protiucet)
    if rule.vs:
        qs = qs.filter(vs=rule.vs)
    if rule.zprava_obsahuje:
        snippet = rule.zprava_obsahuje
        if rule.text_shoda == FioKategorizacniPravidlo.TEXT_SHODA_PRESNE:
            qs = qs.filter(Q(zprava__iexact=snippet) | Q(popis__iexact=snippet))
        else:
            qs = qs.filter(Q(zprava__icontains=snippet) | Q(popis__icontains=snippet))
    qs = qs.order_by('datum', 'id')

    updated = 0
    scanned = 0
    for p in qs.iterator():
        scanned += 1
        if not _matches_rule(rule, polozka_as_row(p)):
            continue
        if dry_run:
            updated += 1
            continue
        _apply_matched_pravidlo(rule, p)
        updated += 1
    return {'updated': updated, 'scanned': scanned}


def _pravidlo_base_qs(scope: str):
    qs = NakladPolozka.objects.filter(typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI)
    if scope == 'nezarazene':
        qs = qs.filter(stav=NakladPolozka.STAV_NEZARAZENO)
    return qs.order_by('-datum', '-id')


def _pravidlo_prefilter_qs(qs, rule: FioKategorizacniPravidlo):
    from django.db.models import Q

    if rule.protiucet:
        qs = qs.filter(protiucet__contains=rule.protiucet)
    if rule.vs:
        qs = qs.filter(vs=rule.vs)
    if rule.zprava_obsahuje:
        snippet = rule.zprava_obsahuje
        if rule.text_shoda == FioKategorizacniPravidlo.TEXT_SHODA_PRESNE:
            qs = qs.filter(Q(zprava__iexact=snippet) | Q(popis__iexact=snippet))
        else:
            qs = qs.filter(Q(zprava__icontains=snippet) | Q(popis__icontains=snippet))
    return qs


def _serialize_pravidlo_preview_polozka(p: NakladPolozka) -> dict:
    return {
        'id': p.id,
        'datum': p.datum.isoformat(),
        'castka': str(p.castka),
        'popis': p.popis or '',
        'zprava': p.zprava or '',
        'protiucet': p.protiucet or '',
        'vs': p.vs or '',
        'stav': p.stav,
        'kategorie_nazev': p.kategorie.nazev if p.kategorie_id else None,
    }


def rule_from_preview_payload(data: dict, existing: FioKategorizacniPravidlo | None = None) -> FioKategorizacniPravidlo:
    """Dočasné pravidlo pro náhled – bez uložení do DB."""
    rule = existing or FioKategorizacniPravidlo()
    for field in ('protiucet', 'zprava_obsahuje', 'vs', 'text_shoda', 'ignorovat', 'aktivni'):
        if field in data:
            setattr(rule, field, data[field])
    if 'kategorie_id' in data:
        rule.kategorie_id = data['kategorie_id'] or None
    if 'prodejna_id' in data:
        rule.prodejna_id = data['prodejna_id'] or None
    if not rule.text_shoda:
        rule.text_shoda = FioKategorizacniPravidlo.TEXT_SHODA_OBSAHUJE
    return rule


def preview_pravidlo(
    rule: FioKategorizacniPravidlo,
    *,
    scope: str = 'nezarazene',
    limit: int = 50,
) -> dict:
    """Náhled plateb odpovídajících pravidlu (bez zápisu)."""
    from .kategorizace import polozka_as_row

    empty = {
        'total': 0,
        'total_nezarazene': 0,
        'total_vse_odchozi': 0,
        'polozky': [],
        'limit': limit,
        'scope': scope,
    }
    if not pravidlo_ma_klic(rule):
        return empty
    if not rule.ignorovat and not rule.kategorie_id:
        return empty

    qs = _pravidlo_prefilter_qs(_pravidlo_base_qs('vse_odchozi'), rule)
    total_vse = 0
    total_nezarazene = 0
    polozky = []
    for p in qs.iterator():
        if not _matches_rule(rule, polozka_as_row(p)):
            continue
        total_vse += 1
        if p.stav == NakladPolozka.STAV_NEZARAZENO:
            total_nezarazene += 1
        if scope == 'nezarazene' and p.stav != NakladPolozka.STAV_NEZARAZENO:
            continue
        if len(polozky) < limit:
            polozky.append(_serialize_pravidlo_preview_polozka(p))

    total = total_nezarazene if scope == 'nezarazene' else total_vse
    return {
        'total': total,
        'total_nezarazene': total_nezarazene,
        'total_vse_odchozi': total_vse,
        'polozky': polozky,
        'limit': limit,
        'scope': scope,
    }


def apply_all_pravidla_to_nezarazene(dry_run: bool = False, limit: int = 0) -> dict:
    """Vestavěná + DB pravidla na nezařazené odchozí položky (jako apply_finance_pravidla)."""
    from .kategorizace import apply_rules_to_polozka

    qs = NakladPolozka.objects.filter(
        stav=NakladPolozka.STAV_NEZARAZENO,
        typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
    ).order_by('datum', 'id')
    if limit:
        qs = qs[:limit]

    updated = 0
    scanned = 0
    for p in qs:
        scanned += 1
        if apply_rules_to_polozka(p, dry_run=dry_run):
            updated += 1
    return {'updated': updated, 'scanned': scanned}


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
        'pokladna_key': p.pokladna_key or None,
        'pokladna_label': p.pokladna_label or None,
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
        'text_shoda': rule.text_shoda,
        'text_shoda_label': rule.get_text_shoda_display(),
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
    polozka = NakladPolozka.objects.create(**payload)
    try:
        from .doklady import try_auto_link_polozka
        try_auto_link_polozka(polozka)
    except Exception:
        logger.exception('Auto-link doklad failed for fio_id=%s', fio_id)
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
    pokladna_key: str = '',
    pokladna_label: str = '',
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
            'dph_stav': (
                NakladPolozka.DPH_STAV_BEZ if cat['ignorovat']
                else resolve_dph_stav(cat['kategorie_id'], NakladPolozka.TYP_PLATBY_ODCHOZI)
            ),
        }
        if pokladna_key:
            payload['pokladna_key'] = pokladna_key[:32]
        if pokladna_label:
            payload['pokladna_label'] = pokladna_label[:80]

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
