"""Odeslání schváleného dokladu do Flexi (režim příloha)."""
from __future__ import annotations

import logging
import mimetypes
import re
from pathlib import Path

from django.conf import settings

from .flexi_client import FlexiClient, FlexiError
from .models import FinanceDoklad, NakladPolozka
from .secrets import get_flexi_config, is_flexi_sync_enabled

logger = logging.getLogger(__name__)

_VYDEJ_PREFIX = re.compile(r'^manu[aá]ln[ií]\s+v[yý]de[jj]\s+', re.I)


def _symplio_poznamka_for_flexi(popis: str) -> str:
    """Poznámka z pokladny → text, který účetní dává do Flexi popis."""
    text = (popis or '').strip()
    text = _VYDEJ_PREFIX.sub('', text).strip()
    return text[:300]


def resolve_flexi_match_keys(doklad: FinanceDoklad, polozka: NakladPolozka | None) -> list[dict]:
    """
    Klíče pro hledání přijaté FA ve Flexi.
    Fio → varSym (VS). Symplio ruční výdej → popis (poznámka), ne číslo dokladu.
    """
    keys: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    def add(field: str, value: str, source: str, *, op: str = 'eq'):
        value = (value or '').strip()
        if not value:
            return
        pair = (field, value, op)
        if pair in seen:
            return
        seen.add(pair)
        keys.append({'field': field, 'value': value, 'source': source, 'op': op})

    if polozka and polozka.zdroj == NakladPolozka.ZDROJ_FIO:
        vs = (polozka.vs or '').strip()
        # Legacy bug: dřív se do vs ukládal column10 (název), VS bylo v protiucet (column5).
        if not re.fullmatch(r'\d{4,}', vs):
            legacy = (polozka.protiucet or '').strip()
            if re.fullmatch(r'\d{4,}', legacy):
                vs = legacy
        add('varSym', vs, 'fio_vs')
        if doklad.cislo_faktury:
            add('varSym', doklad.cislo_faktury, 'doklad_cislo_as_vs')
            add('cisDosle', doklad.cislo_faktury, 'doklad_cislo')
        if doklad.vs:
            add('varSym', doklad.vs, 'doklad_vs')
        return keys

    # Osiřelá FA / OCR VS → Flexi varSym i bez platby
    if doklad.vs and re.fullmatch(r'\d{4,}', (doklad.vs or '').strip()):
        add('varSym', doklad.vs.strip(), 'doklad_vs')

    if polozka and polozka.zdroj == NakladPolozka.ZDROJ_SYMPLIO_POKLADNA:
        poznamka = _symplio_poznamka_for_flexi(polozka.popis or '')
        if poznamka:
            add('popis', poznamka, 'symplio_poznamka', op='eq')
            add('popis', poznamka, 'symplio_poznamka_like', op='like')
            add('popis', poznamka, 'symplio_poznamka_like_similar', op='like_similar')
        return keys

    # Ostatní zdroje – fallback na číslo FA / popis položky
    add('cisDosle', doklad.cislo_faktury or '', 'doklad_cislo')
    if polozka and polozka.popis:
        add('popis', polozka.popis.strip()[:300], 'polozka_popis', op='like')
    return keys


def _content_type_for(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    if guessed:
        return guessed
    ext = path.suffix.lower()
    return {
        '.pdf': 'application/pdf',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp',
    }.get(ext, 'application/octet-stream')


def sync_doklad_to_flexi(doklad: FinanceDoklad) -> dict:
    """
    Najde jednu přijatou FA a přiloží soubor.
    Vrací dict pro match_detail['flexi'] – nikdy nehází ven (volající loguje).
    """
    if doklad.flexi_id:
        return {
            'ok': True,
            'skipped': True,
            'reason': 'already_synced',
            'flexi_id': doklad.flexi_id,
        }

    if not is_flexi_sync_enabled():
        return {'ok': False, 'skipped': True, 'reason': 'flexi_disabled'}

    cfg = get_flexi_config()
    if not cfg:
        return {'ok': False, 'skipped': True, 'reason': 'flexi_not_configured'}

    if cfg.get('mode') != 'priloha':
        return {
            'ok': False,
            'skipped': True,
            'reason': f"mode_{cfg.get('mode')}_not_supported",
        }

    if not doklad.soubor:
        return {'ok': False, 'error': 'Chybí soubor dokladu'}

    path = Path(settings.MEDIA_ROOT) / doklad.soubor
    if not path.is_file():
        return {'ok': False, 'error': f'Soubor nenalezen: {doklad.soubor}'}

    keys = resolve_flexi_match_keys(doklad, doklad.naklad_polozka)
    if not keys:
        return {
            'ok': False,
            'error': 'Chybí klíč pro párování (Fio: VS, výdej: poznámka → Flexi popis)',
            'tried': [],
        }

    try:
        client = FlexiClient(cfg)
    except FlexiError as exc:
        return {'ok': False, 'error': exc.message}

    tried = []
    matches: list[dict] = []
    match_meta = None

    for key in keys:
        try:
            found = client.find_faktura_prijata(
                field=key['field'],
                value=key['value'],
                op=key.get('op') or 'eq',
            )
        except FlexiError as exc:
            return {
                'ok': False,
                'error': exc.message,
                'tried': tried + [{**key, 'error': exc.message}],
            }
        tried.append({**key, 'count': len(found)})
        if len(found) == 1:
            matches = found
            match_meta = key
            break
        if len(found) > 1:
            return {
                'ok': False,
                'error': f"Vícenásobná shoda ve Flexi ({key['field']}={key['value']})",
                'tried': tried,
                'candidates': [
                    {
                        'id': x.get('id'),
                        'kod': x.get('kod'),
                        'varSym': x.get('varSym'),
                        'popis': x.get('popis'),
                    }
                    for x in found[:5]
                ],
            }

    if not matches:
        return {
            'ok': False,
            'error': 'Ve Flexi nenalezena přijatá faktura',
            'tried': tried,
        }

    fa = matches[0]
    flexi_id = str(fa.get('id') or '')
    if not flexi_id:
        return {'ok': False, 'error': 'Flexi vrátilo FA bez id', 'tried': tried}

    content = path.read_bytes()
    filename = path.name
    content_type = _content_type_for(path)

    try:
        upload = client.upload_priloha(
            flexi_id,
            filename=filename,
            content=content,
            content_type=content_type,
        )
    except FlexiError as exc:
        logger.warning('Flexi upload failed doklad=%s: %s', doklad.id, exc.message)
        return {
            'ok': False,
            'error': exc.message,
            'flexi_id': flexi_id,
            'matched_by': match_meta,
            'flexi_kod': fa.get('kod'),
            'tried': tried,
        }

    return {
        'ok': True,
        'flexi_id': flexi_id,
        'flexi_kod': fa.get('kod'),
        'flexi_varSym': fa.get('varSym'),
        'flexi_cisDosle': fa.get('cisDosle'),
        'flexi_popis': fa.get('popis'),
        'priloha_id': upload.get('priloha_id'),
        'matched_by': match_meta,
        'tried': tried,
        'filename': filename,
    }
