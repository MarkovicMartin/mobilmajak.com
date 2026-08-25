"""Ukládání faktur a párování s položkou nákladu."""
from __future__ import annotations

import re
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from .models import FinanceDoklad, NakladPolozka
from .symplio_vydej_parse import faktura_hint_from_polozka

ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.webp'}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _safe_filename(name: str) -> str:
    base = Path(name).name
    base = re.sub(r'[^\w.\- ]+', '_', base, flags=re.UNICODE).strip('._ ')
    return base[:180] or 'faktura'


def save_doklad_file(uploaded_file) -> tuple[str, str]:
    ext = Path(uploaded_file.name or '').suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f'Povolené formáty: {", ".join(sorted(ALLOWED_EXTENSIONS))}')
    if uploaded_file.size > MAX_UPLOAD_BYTES:
        raise ValueError('Soubor je příliš velký (max 10 MB).')

    media_root = Path(settings.MEDIA_ROOT)
    subdir = media_root / 'finance' / 'doklady' / timezone.now().strftime('%Y/%m')
    subdir.mkdir(parents=True, exist_ok=True)
    stored_name = f'{uuid.uuid4().hex}_{_safe_filename(uploaded_file.name)}'
    dest = subdir / stored_name
    with dest.open('wb') as out:
        for chunk in uploaded_file.chunks():
            out.write(chunk)
    rel = str(dest.relative_to(media_root)).replace('\\', '/')
    return rel, uploaded_file.name


def _parse_decimal(value) -> Decimal | None:
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value).replace(',', '.').replace(' ', ''))
    except (InvalidOperation, ValueError):
        raise ValueError(f'Neplatná částka: {value!r}')


def link_doklad_to_polozka(
    polozka: NakladPolozka,
    uploaded_file,
    *,
    dodavatel_nazev: str = '',
    cislo_faktury: str = '',
    castka_bez_dph=None,
    dph_castka=None,
    dph_sazba=None,
    user_id: int | None = None,
) -> FinanceDoklad:
    if polozka.doklad_id:
        raise ValueError('K této položce je už faktura přiložena.')

    hint = faktura_hint_from_polozka(polozka)
    dodavatel_nazev = (dodavatel_nazev or (hint or {}).get('dodavatel_nazev') or '')[:200]
    cislo_faktury = (cislo_faktury or (hint or {}).get('cislo_faktury') or '')[:64]

    rel_path, _orig = save_doklad_file(uploaded_file)
    bez = _parse_decimal(castka_bez_dph)
    dph = _parse_decimal(dph_castka)
    sazba = None
    if dph_sazba not in (None, ''):
        try:
            sazba = int(dph_sazba)
        except (TypeError, ValueError):
            raise ValueError('Neplatná sazba DPH')

    celkem = None
    if bez is not None and dph is not None:
        celkem = bez + dph
    elif bez is not None:
        celkem = bez
    elif hint and hint.get('castka_celkem') and not castka_bez_dph:
        celkem = _parse_decimal(hint['castka_celkem'])

    has_amounts = bez is not None
    doklad = FinanceDoklad.objects.create(
        soubor=rel_path,
        dodavatel_nazev=dodavatel_nazev,
        cislo_faktury=cislo_faktury,
        castka_celkem=celkem,
        castka_bez_dph=bez,
        dph_castka=dph,
        dph_sazba=sazba,
        stav=FinanceDoklad.STAV_CEKA_NA_OCR,
        naklad_polozka=polozka,
    )

    polozka.doklad = doklad
    if has_amounts:
        polozka.castka_bez_dph = bez
        polozka.dph_castka = dph
        polozka.dph_sazba = sazba
        polozka.dph_stav = NakladPolozka.DPH_STAV_SPAROVANO
    polozka.upravil_user_id = user_id
    polozka.upraveno = timezone.now()
    polozka.save(update_fields=[
        'doklad', 'castka_bez_dph', 'dph_castka', 'dph_sazba', 'dph_stav',
        'upravil_user_id', 'upraveno',
    ])

    from .faktura_process import process_doklad_ocr
    process_doklad_ocr(doklad.id, overwrite_empty=not has_amounts)
    doklad.refresh_from_db()
    return doklad


def create_orphan_doklad(uploaded_file, *, user_id: int | None = None) -> FinanceDoklad:
    """Nahrání FA bez platby – OCR + případné auto-spárování podle VS."""
    rel_path, _orig = save_doklad_file(uploaded_file)
    doklad = FinanceDoklad.objects.create(
        soubor=rel_path,
        stav=FinanceDoklad.STAV_CEKA_NA_OCR,
    )
    from .faktura_process import process_doklad_ocr
    process_doklad_ocr(doklad.id, overwrite_empty=True)
    doklad.refresh_from_db()
    try_auto_link_doklad(doklad)
    doklad.refresh_from_db()
    return doklad


def _polozka_vs_candidates(polozka: NakladPolozka) -> set[str]:
    vals = set()
    vs = (polozka.vs or '').strip()
    if re.fullmatch(r'\d{4,}', vs):
        vals.add(vs)
    # Legacy Fio: VS bylo v protiucet
    proti = (polozka.protiucet or '').strip()
    if re.fullmatch(r'\d{4,}', proti):
        vals.add(proti)
    return vals


def try_auto_link_doklad(doklad: FinanceDoklad) -> bool:
    """
    Spojí osiřelý doklad s odchozí položkou podle VS.
    Zůstane ke_kontrole, nastaví prirazeno_automaticky.
    """
    if doklad.naklad_polozka_id:
        return False
    vs = (doklad.vs or '').strip()
    if not vs:
        # fallback: číslo FA jako VS
        digits = re.sub(r'\D', '', doklad.cislo_faktury or '')
        if len(digits) >= 4:
            vs = digits
    if not vs or not re.fullmatch(r'\d{4,}', vs):
        return False

    qs = NakladPolozka.objects.filter(
        typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
        doklad__isnull=True,
        ignorovat=False,
    ).filter(
        models_Q_vs(vs),
    ).order_by('-datum', '-id')[:5]

    matches = list(qs)
    if len(matches) != 1:
        return False

    return _attach_doklad_to_polozka(doklad, matches[0], automatic=True)


def try_auto_link_polozka(polozka: NakladPolozka) -> bool:
    """Po Fio importu: najdi osiřelou FA se stejným VS."""
    if polozka.doklad_id or polozka.typ_platby != NakladPolozka.TYP_PLATBY_ODCHOZI:
        return False
    if polozka.ignorovat:
        return False
    candidates = _polozka_vs_candidates(polozka)
    if not candidates:
        return False

    orphans = FinanceDoklad.objects.filter(
        naklad_polozka__isnull=True,
        stav__in=(
            FinanceDoklad.STAV_CEKA_NA_OCR,
            FinanceDoklad.STAV_KE_KONTROLE,
            FinanceDoklad.STAV_NOVA,
        ),
    ).exclude(vs='').order_by('-vytvoreno')[:50]

    hits = []
    for d in orphans:
        dvs = (d.vs or '').strip()
        if not dvs:
            dvs = re.sub(r'\D', '', d.cislo_faktury or '')
        if dvs in candidates:
            hits.append(d)
    if len(hits) != 1:
        return False
    return _attach_doklad_to_polozka(hits[0], polozka, automatic=True)


def models_Q_vs(vs: str):
    from django.db.models import Q
    return Q(vs=vs) | Q(vs='', protiucet=vs) | Q(protiucet=vs)


def _attach_doklad_to_polozka(
    doklad: FinanceDoklad,
    polozka: NakladPolozka,
    *,
    automatic: bool,
) -> bool:
    if polozka.doklad_id and polozka.doklad_id != doklad.id:
        return False
    if doklad.naklad_polozka_id and doklad.naklad_polozka_id != polozka.id:
        return False

    from .faktura_match import match_doklad_to_polozka

    doklad.naklad_polozka = polozka
    doklad.prirazeno_automaticky = automatic
    doklad.upraveno = timezone.now()
    match = match_doklad_to_polozka(doklad, polozka)
    doklad.match_stav = match['stav']
    doklad.match_detail = match
    if doklad.stav == FinanceDoklad.STAV_CEKA_NA_OCR:
        doklad.stav = FinanceDoklad.STAV_KE_KONTROLE
    doklad.save(update_fields=[
        'naklad_polozka', 'prirazeno_automaticky', 'match_stav', 'match_detail',
        'stav', 'upraveno',
    ])

    polozka.doklad = doklad
    update = ['doklad', 'upraveno']
    polozka.upraveno = timezone.now()
    if doklad.castka_bez_dph is not None:
        polozka.castka_bez_dph = doklad.castka_bez_dph
        polozka.dph_castka = doklad.dph_castka
        polozka.dph_sazba = doklad.dph_sazba
        polozka.dph_stav = NakladPolozka.DPH_STAV_SPAROVANO
        update.extend(['castka_bez_dph', 'dph_castka', 'dph_sazba', 'dph_stav'])
    polozka.save(update_fields=update)
    return True


def serialize_doklad(d: FinanceDoklad, *, include_polozka: bool = False) -> dict:
    from .symplio_vydej_parse import faktura_hint_from_polozka

    polozka = d.naklad_polozka
    soubor_nazev = ''
    if d.soubor:
        base = Path(d.soubor).name
        # uloženo jako uuid_originalName
        if '_' in base and len(base.split('_', 1)[0]) == 32:
            soubor_nazev = base.split('_', 1)[1]
        else:
            soubor_nazev = base
    payload = {
        'id': d.id,
        'stav': d.stav,
        'match_stav': d.match_stav or None,
        'match_detail': d.match_detail,
        'dodavatel_nazev': d.dodavatel_nazev,
        'dodavatel_ico': d.dodavatel_ico or None,
        'cislo_faktury': d.cislo_faktury,
        'vs': d.vs or None,
        'datum_vystaveni': d.datum_vystaveni.isoformat() if d.datum_vystaveni else None,
        'castka_celkem': str(d.castka_celkem) if d.castka_celkem is not None else None,
        'castka_bez_dph': str(d.castka_bez_dph) if d.castka_bez_dph is not None else None,
        'dph_castka': str(d.dph_castka) if d.dph_castka is not None else None,
        'dph_sazba': d.dph_sazba,
        'soubor': d.soubor or None,
        'soubor_nazev': soubor_nazev or None,
        'soubor_url': f'{settings.MEDIA_URL.rstrip("/")}/{d.soubor}' if d.soubor else None,
        'schvaleno': d.schvaleno.isoformat() if d.schvaleno else None,
        'vytvoreno': d.vytvoreno.isoformat() if d.vytvoreno else None,
        'ocr_zdroj': (d.ocr_raw or {}).get('extracted', {}).get('zdroj') if d.ocr_raw else None,
        'ocr_method': (d.ocr_raw or {}).get('meta', {}).get('method') if d.ocr_raw else None,
        'ocr_chyby': (
            (d.ocr_raw or {}).get('extracted', {}).get('chyby')
            or ([d.ocr_raw['error']] if d.ocr_raw and d.ocr_raw.get('error') else [])
        ),
        'flexi_id': d.flexi_id or None,
        'flexi': (d.match_detail or {}).get('flexi'),
        'prirazeno_automaticky': bool(d.prirazeno_automaticky),
        'ceka_na_platbu': d.naklad_polozka_id is None,
    }
    if include_polozka and polozka:
        payload['naklad_polozka'] = {
            'id': polozka.id,
            'datum': polozka.datum.isoformat(),
            'castka': str(polozka.castka),
            'popis': polozka.popis,
            'prodejna_id': polozka.prodejna_id,
            'zdroj': polozka.zdroj,
            'vs': polozka.vs or None,
            'faktura_hint': faktura_hint_from_polozka(polozka),
        }
    elif include_polozka:
        payload['naklad_polozka'] = None
    return payload
