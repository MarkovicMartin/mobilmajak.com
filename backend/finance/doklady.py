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


def serialize_doklad(d: FinanceDoklad, *, include_polozka: bool = False) -> dict:
    from .symplio_vydej_parse import faktura_hint_from_polozka

    polozka = d.naklad_polozka
    payload = {
        'id': d.id,
        'stav': d.stav,
        'match_stav': d.match_stav or None,
        'match_detail': d.match_detail,
        'dodavatel_nazev': d.dodavatel_nazev,
        'dodavatel_ico': d.dodavatel_ico or None,
        'cislo_faktury': d.cislo_faktury,
        'datum_vystaveni': d.datum_vystaveni.isoformat() if d.datum_vystaveni else None,
        'castka_celkem': str(d.castka_celkem) if d.castka_celkem is not None else None,
        'castka_bez_dph': str(d.castka_bez_dph) if d.castka_bez_dph is not None else None,
        'dph_castka': str(d.dph_castka) if d.dph_castka is not None else None,
        'dph_sazba': d.dph_sazba,
        'soubor_url': f'{settings.MEDIA_URL.rstrip("/")}/{d.soubor}' if d.soubor else None,
        'schvaleno': d.schvaleno.isoformat() if d.schvaleno else None,
        'vytvoreno': d.vytvoreno.isoformat() if d.vytvoreno else None,
        'ocr_zdroj': (d.ocr_raw or {}).get('extracted', {}).get('zdroj') if d.ocr_raw else None,
        'flexi_id': d.flexi_id or None,
        'flexi': (d.match_detail or {}).get('flexi'),
    }
    if include_polozka and polozka:
        payload['naklad_polozka'] = {
            'id': polozka.id,
            'datum': polozka.datum.isoformat(),
            'castka': str(polozka.castka),
            'popis': polozka.popis,
            'prodejna_id': polozka.prodejna_id,
            'zdroj': polozka.zdroj,
            'faktura_hint': faktura_hint_from_polozka(polozka),
        }
    return payload
