"""Zpracování nahrané faktury – extrakce + porovnání s pokladnou."""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from .faktura_extract import extract_faktura_from_file
from .faktura_match import match_doklad_to_polozka
from .models import FinanceDoklad, NakladPolozka

logger = logging.getLogger(__name__)


def _media_path(rel: str) -> Path:
    return Path(settings.MEDIA_ROOT) / rel


def _apply_extracted(doklad: FinanceDoklad, extracted, *, overwrite_empty: bool = True) -> list[str]:
    """Aplikuje vyčtená pole; vrátí seznam změněných polí."""
    changed = []
    mapping = {
        'dodavatel_nazev': extracted.dodavatel_nazev,
        'dodavatel_ico': extracted.dodavatel_ico,
        'cislo_faktury': extracted.cislo_faktury,
        'vs': getattr(extracted, 'vs', '') or '',
    }
    for field, value in mapping.items():
        if not value:
            continue
        current = getattr(doklad, field) or ''
        if overwrite_empty and not current:
            setattr(doklad, field, value[: getattr(FinanceDoklad._meta.get_field(field), 'max_length', 200)])
            changed.append(field)
        elif not overwrite_empty and value:
            setattr(doklad, field, value[: getattr(FinanceDoklad._meta.get_field(field), 'max_length', 200)])
            changed.append(field)

    for field in ('castka_bez_dph', 'dph_castka', 'castka_celkem'):
        raw = getattr(extracted, field, None)
        if not raw or getattr(doklad, field) is not None:
            continue
        try:
            setattr(doklad, field, Decimal(str(raw)))
            changed.append(field)
        except (InvalidOperation, ValueError):
            pass

    if extracted.dph_sazba and doklad.dph_sazba is None:
        doklad.dph_sazba = extracted.dph_sazba
        changed.append('dph_sazba')

    if extracted.datum_vystaveni and not doklad.datum_vystaveni:
        from datetime import datetime
        for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d. %m. %Y'):
            try:
                doklad.datum_vystaveni = datetime.strptime(extracted.datum_vystaveni[:10], fmt).date()
                changed.append('datum_vystaveni')
                break
            except ValueError:
                continue
    return changed


def process_doklad_ocr(doklad_id: int, *, overwrite_empty: bool = True) -> FinanceDoklad:
    doklad = FinanceDoklad.objects.select_related('naklad_polozka').get(pk=doklad_id)
    if not doklad.soubor:
        doklad.stav = FinanceDoklad.STAV_KE_KONTROLE
        doklad.ocr_raw = {'error': 'Chybí soubor'}
        doklad.save(update_fields=['stav', 'ocr_raw', 'upraveno'])
        return doklad

    path = _media_path(doklad.soubor)
    if not path.is_file():
        doklad.stav = FinanceDoklad.STAV_KE_KONTROLE
        doklad.ocr_raw = {'error': f'Soubor nenalezen: {doklad.soubor}'}
        doklad.save(update_fields=['stav', 'ocr_raw', 'upraveno'])
        return doklad

    extracted, raw_text, meta = extract_faktura_from_file(path)
    ocr_payload = {
        'meta': meta,
        'extracted': extracted.to_dict(),
        'raw_text_preview': raw_text[:2000] if raw_text else '',
    }
    _apply_extracted(doklad, extracted, overwrite_empty=overwrite_empty)

    polozka = doklad.naklad_polozka
    match = match_doklad_to_polozka(doklad, polozka)
    doklad.match_stav = match['stav']
    doklad.match_detail = match
    doklad.ocr_raw = ocr_payload
    doklad.stav = FinanceDoklad.STAV_KE_KONTROLE
    doklad.upraveno = timezone.now()

    update_fields = [
        'dodavatel_nazev', 'dodavatel_ico', 'cislo_faktury', 'vs', 'datum_vystaveni',
        'castka_bez_dph', 'dph_castka', 'castka_celkem', 'dph_sazba',
        'match_stav', 'match_detail', 'ocr_raw', 'stav', 'upraveno',
    ]
    doklad.save(update_fields=update_fields)

    if polozka and doklad.castka_bez_dph is not None:
        polozka.castka_bez_dph = doklad.castka_bez_dph
        polozka.dph_castka = doklad.dph_castka
        polozka.dph_sazba = doklad.dph_sazba
        if doklad.castka_bez_dph is not None and doklad.dph_castka is not None:
            polozka.dph_stav = NakladPolozka.DPH_STAV_SPAROVANO
        polozka.save(update_fields=['castka_bez_dph', 'dph_castka', 'dph_sazba', 'dph_stav'])

    if not doklad.naklad_polozka_id:
        from .doklady import try_auto_link_doklad
        try_auto_link_doklad(doklad)
        doklad.refresh_from_db()

    return doklad


def schvalit_doklad(doklad: FinanceDoklad, user_id: int) -> FinanceDoklad:
    doklad.stav = FinanceDoklad.STAV_SCHVALENO
    doklad.schvalil_user_id = user_id
    doklad.schvaleno = timezone.now()
    doklad.upraveno = timezone.now()
    doklad.save(update_fields=['stav', 'schvalil_user_id', 'schvaleno', 'upraveno'])
    polozka = doklad.naklad_polozka
    if polozka:
        if doklad.castka_bez_dph is not None:
            polozka.castka_bez_dph = doklad.castka_bez_dph
            polozka.dph_castka = doklad.dph_castka
            polozka.dph_sazba = doklad.dph_sazba
            polozka.dph_stav = NakladPolozka.DPH_STAV_SPAROVANO
            polozka.save(update_fields=['castka_bez_dph', 'dph_castka', 'dph_sazba', 'dph_stav'])

    from .flexi_sync import sync_doklad_to_flexi

    try:
        flexi_result = sync_doklad_to_flexi(doklad)
    except Exception as exc:
        logger.exception('Flexi sync failed doklad=%s', doklad.id)
        flexi_result = {'ok': False, 'error': str(exc)[:500]}

    detail = dict(doklad.match_detail or {})
    detail['flexi'] = flexi_result
    doklad.match_detail = detail
    update_fields = ['match_detail', 'upraveno']
    doklad.upraveno = timezone.now()
    if flexi_result.get('ok') and flexi_result.get('flexi_id') and not flexi_result.get('skipped'):
        doklad.flexi_id = str(flexi_result['flexi_id'])[:32]
        doklad.stav = FinanceDoklad.STAV_ODESLANO_FLEXI
        update_fields.extend(['flexi_id', 'stav'])
    doklad.save(update_fields=update_fields)
    return doklad


def odeslat_doklad_do_flexi(doklad: FinanceDoklad) -> FinanceDoklad:
    """Opakovaný pokus o odeslání přílohy (po schválení / chybě)."""
    from .flexi_sync import sync_doklad_to_flexi

    try:
        flexi_result = sync_doklad_to_flexi(doklad)
    except Exception as exc:
        logger.exception('Flexi sync retry failed doklad=%s', doklad.id)
        flexi_result = {'ok': False, 'error': str(exc)[:500]}

    detail = dict(doklad.match_detail or {})
    detail['flexi'] = flexi_result
    doklad.match_detail = detail
    doklad.upraveno = timezone.now()
    update_fields = ['match_detail', 'upraveno']
    if flexi_result.get('ok') and flexi_result.get('flexi_id'):
        doklad.flexi_id = str(flexi_result['flexi_id'])[:32]
        doklad.stav = FinanceDoklad.STAV_ODESLANO_FLEXI
        update_fields.extend(['flexi_id', 'stav'])
    doklad.save(update_fields=update_fields)
    return doklad


def zamitnout_doklad(doklad: FinanceDoklad, user_id: int, duvod: str = '') -> FinanceDoklad:
    doklad.stav = FinanceDoklad.STAV_ZAMITNUTO
    doklad.schvalil_user_id = user_id
    doklad.schvaleno = timezone.now()
    doklad.upraveno = timezone.now()
    detail = doklad.match_detail or {}
    detail['zamitnuto_duvod'] = (duvod or '')[:500]
    doklad.match_detail = detail
    doklad.save(update_fields=['stav', 'schvalil_user_id', 'schvaleno', 'upraveno', 'match_detail'])
    return doklad
