"""Nový přijatý dobropis Partnertele ve Flexi (ne jen příloha k existující FA)."""
from __future__ import annotations

import logging
import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from .doklady import _parse_decimal, save_doklad_file
from .dobropis_extract import extract_dobropis_file
from .flexi_client import FlexiClient, FlexiError
from .flexi_sync import _content_type_for
from .models import FinanceDoklad
from .secrets import get_flexi_config, is_flexi_sync_enabled

logger = logging.getLogger(__name__)

# Stejný tvar jako ručně zaúčtované ODD od PARTNER TELE.COM (firma PARTNER-PL).
PARTNERTELE = {
    'firma': 'PARTNER-PL',
    'dodavatel_nazev': 'PARTNER TELE.COM SP. Z O.O. S.K',
    'dodavatel_dic': 'PL6792675514',
    'typ_dokl': 'FAKTURA',
    'popis': 'ODD zboží EU',
    'clen_dph': '03-04, 43-44',
    'typ_uc_op': '504001 EU ZBOŽÍ',
    'stat': 'PL',
    'dph_sazba': Decimal('21'),
}

_MONEY = Decimal('0.01')


def _cfg_or(cfg: dict | None, key: str, default: str) -> str:
    raw = (cfg or {}).get(key)
    text = str(raw).strip() if raw is not None else ''
    return text or default


def dobropis_nastaveni(cfg: dict | None = None) -> dict:
    cfg = cfg if cfg is not None else (get_flexi_config() or {})
    return {
        'firma': _cfg_or(cfg, 'dobropis_firma', PARTNERTELE['firma']),
        'typ_dokl': _cfg_or(cfg, 'dobropis_typ_dokl', PARTNERTELE['typ_dokl']),
        'popis': _cfg_or(cfg, 'dobropis_popis', PARTNERTELE['popis']),
        'clen_dph': _cfg_or(cfg, 'dobropis_clen_dph', PARTNERTELE['clen_dph']),
        'typ_uc_op': _cfg_or(cfg, 'dobropis_typ_uc_op', PARTNERTELE['typ_uc_op']),
        'stat': _cfg_or(cfg, 'dobropis_stat', PARTNERTELE['stat']),
    }


def _code(value: str) -> str:
    value = (value or '').strip()
    if value.lower().startswith('code:'):
        return value
    return f'code:{value}'


def var_sym_from_cislo(cislo: str) -> str:
    """284/11/25/KFDWV → 2841125 (jen číslice, jako u stávajících ODD)."""
    digits = re.sub(r'\D', '', cislo or '')
    if digits:
        return digits[:30]
    return re.sub(r'\s+', '', cislo or '')[:30]


def _money(value: Decimal) -> str:
    return f'{value.quantize(_MONEY, rounding=ROUND_HALF_UP):.2f}'


def _abs_money(value, *, label: str) -> Decimal:
    parsed = _parse_decimal(value)
    if parsed is None:
        raise ValueError(f'Chybí {label}')
    amount = abs(parsed).quantize(_MONEY, rounding=ROUND_HALF_UP)
    if amount <= 0:
        raise ValueError(f'{label} musí být větší než 0')
    return amount


def _parse_date(value) -> datetime.date:
    text = str(value or '').strip()[:10]
    if not text:
        raise ValueError('Chybí datum vystavení')
    try:
        return datetime.strptime(text, '%Y-%m-%d').date()
    except ValueError as exc:
        raise ValueError('Datum vystavení musí být RRRR-MM-DD') from exc


def flexi_dobropis_fields(
    *,
    cislo: str,
    datum,
    castka: Decimal,
    dph: Decimal,
    vs: str,
    popis: str,
    nastaveni: dict,
) -> dict:
    """
    Záporná přijatá FA.
    sumCelkem = základ (částka k zápočtu), DPH je zvlášť – stejně jako ODD zboží EU.
    """
    den = datum.isoformat()
    base = -castka
    vat = -dph
    fields = {
        'typDokl': _code(nastaveni['typ_dokl']),
        'firma': _code(nastaveni['firma']),
        'cisDosle': cislo,
        'varSym': vs,
        'datVyst': den,
        'duzpPuv': den,
        'duzpUcto': den,
        'datSplat': den,
        'popis': popis[:255],
        'bezPolozek': True,
        'sumZklZakl': _money(base),
        'sumDphZakl': _money(vat),
        'sumCelkem': _money(base),
    }
    if nastaveni.get('clen_dph'):
        fields['clenDph'] = _code(nastaveni['clen_dph'])
    if nastaveni.get('typ_uc_op'):
        fields['typUcOp'] = _code(nastaveni['typ_uc_op'])
    if nastaveni.get('stat'):
        fields['stat'] = _code(nastaveni['stat'])
    return fields


def _clean_cislo(cislo: str) -> str:
    text = re.sub(r'\s+', ' ', (cislo or '').strip())
    if not text:
        raise ValueError('Chybí číslo dobropisu')
    if len(text) > 40:
        raise ValueError('Číslo dobropisu může mít nejvýš 40 znaků')
    return text


def vytvor_dobropis_partnertele(
    *,
    uploaded_file,
    cislo: str,
    datum,
    castka,
    dph=None,
    vs: str = '',
    popis: str = '',
    user_id: int | None = None,
) -> FinanceDoklad:
    cislo = _clean_cislo(cislo)
    den = _parse_date(datum)
    base = _abs_money(castka, label='Částka dobropisu')
    explicit_dph = dph not in (None, '')
    vat = _abs_money(dph, label='DPH') if explicit_dph else (
        (base * PARTNERTELE['dph_sazba'] / Decimal('100')).quantize(_MONEY, rounding=ROUND_HALF_UP)
    )
    symbol = (vs or '').strip() or var_sym_from_cislo(cislo)
    nastaveni = dobropis_nastaveni()
    text = (popis or '').strip() or nastaveni['popis']

    if FinanceDoklad.objects.filter(
        druh=FinanceDoklad.DRUH_DOBROPIS,
        cislo_faktury=cislo,
    ).exclude(stav=FinanceDoklad.STAV_ZAMITNUTO).exists():
        raise ValueError(f'Dobropis {cislo} už je uložený. Opakujte odeslání u existujícího řádku.')

    rel_path, _orig = save_doklad_file(uploaded_file)
    now = timezone.now()
    doklad = FinanceDoklad.objects.create(
        soubor=rel_path,
        dodavatel_nazev=PARTNERTELE['dodavatel_nazev'][:200],
        cislo_faktury=cislo,
        vs=symbol[:32],
        datum_vystaveni=den,
        datum_splatnosti=den,
        castka_celkem=-base,
        castka_bez_dph=-base,
        dph_castka=-vat,
        dph_sazba=int(PARTNERTELE['dph_sazba']),
        stav=FinanceDoklad.STAV_SCHVALENO,
        druh=FinanceDoklad.DRUH_DOBROPIS,
        schvalil_user_id=user_id,
        schvaleno=now,
        match_detail={
            'druh': FinanceDoklad.DRUH_DOBROPIS,
            'popis': text[:255],
            'dodavatel_dic': PARTNERTELE['dodavatel_dic'],
            'dph_vypocteno': not explicit_dph,
            'firma': nastaveni['firma'],
        },
    )
    return odeslat_dobropis_do_flexi(doklad, reuse_existing=False)


def ulozit_dobropis_ze_souboru(uploaded_file, *, user_id: int | None = None) -> FinanceDoklad:
    """Uloží soubor a vyčte číslo, datum a částku. Do Flexi se ještě nezapisuje."""
    rel_path, _orig = save_doklad_file(uploaded_file)
    path = Path(settings.MEDIA_ROOT) / rel_path
    try:
        extracted, raw_text, meta = extract_dobropis_file(path)
        cislo = (extracted.cislo_faktury or '').strip()[:40]
        if cislo and FinanceDoklad.objects.filter(
            druh=FinanceDoklad.DRUH_DOBROPIS,
            cislo_faktury=cislo,
        ).exclude(stav=FinanceDoklad.STAV_ZAMITNUTO).exists():
            raise ValueError(f'Dobropis {cislo} už je uložený.')

        nastaveni = dobropis_nastaveni()
        den = _parse_date(extracted.datum_vystaveni) if extracted.datum_vystaveni else None
        base = _parse_decimal(extracted.castka_celkem) if extracted.castka_celkem else None
        vat = _parse_decimal(extracted.dph_castka) if extracted.dph_castka not in (None, '') else None
        bez = _parse_decimal(extracted.castka_bez_dph) if extracted.castka_bez_dph else base
        symbol = (extracted.vs or '').strip() or (var_sym_from_cislo(cislo) if cislo else '')
        return FinanceDoklad.objects.create(
            soubor=rel_path,
            dodavatel_nazev=(extracted.dodavatel_nazev or PARTNERTELE['dodavatel_nazev'])[:200],
            cislo_faktury=cislo[:64],
            vs=symbol[:32],
            datum_vystaveni=den,
            datum_splatnosti=den,
            castka_celkem=base,
            castka_bez_dph=bez,
            dph_castka=vat,
            dph_sazba=extracted.dph_sazba,
            stav=FinanceDoklad.STAV_KE_KONTROLE,
            druh=FinanceDoklad.DRUH_DOBROPIS,
            ocr_raw={
                'meta': meta,
                'extracted': extracted.to_dict(),
                'raw_text_preview': (raw_text or '')[:2000],
            },
            match_detail={
                'druh': FinanceDoklad.DRUH_DOBROPIS,
                'popis': nastaveni['popis'],
                'dodavatel_dic': extracted.dodavatel_dic or PARTNERTELE['dodavatel_dic'],
                'dph_vypocteno': False,
                'firma': nastaveni['firma'],
            },
        )
    except Exception:
        if path.is_file() and not FinanceDoklad.objects.filter(soubor=rel_path.replace('\\', '/')).exists():
            path.unlink(missing_ok=True)
        raise


def aktualizuj_dobropis(doklad: FinanceDoklad, data) -> FinanceDoklad:
    """Úprava vyčtených polí před zápisem do Flexi. Zachová popis a firmu."""
    if 'cislo_faktury' in data:
        doklad.cislo_faktury = str(data.get('cislo_faktury') or '').strip()[:64]
    if 'vs' in data:
        doklad.vs = str(data.get('vs') or '').strip()[:32]
    if 'dodavatel_nazev' in data:
        doklad.dodavatel_nazev = str(data.get('dodavatel_nazev') or '')[:200]
    for field in ('castka_bez_dph', 'dph_castka', 'castka_celkem'):
        if field not in data:
            continue
        raw = data[field]
        if raw in (None, ''):
            setattr(doklad, field, None)
        else:
            setattr(doklad, field, _parse_decimal(raw))
    if 'dph_sazba' in data and data['dph_sazba'] not in (None, ''):
        try:
            doklad.dph_sazba = int(data['dph_sazba'])
        except (TypeError, ValueError) as exc:
            raise ValueError('Neplatná sazba DPH') from exc
    if 'datum_vystaveni' in data:
        raw = str(data.get('datum_vystaveni') or '').strip()
        den = _parse_date(raw) if raw else None
        doklad.datum_vystaveni = den
        doklad.datum_splatnosti = den
    if not (doklad.vs or '').strip() and doklad.cislo_faktury:
        doklad.vs = var_sym_from_cislo(doklad.cislo_faktury)[:32]
    detail = dict(doklad.match_detail or {})
    nastaveni = dobropis_nastaveni()
    detail['druh'] = FinanceDoklad.DRUH_DOBROPIS
    detail.setdefault('popis', nastaveni['popis'])
    detail.setdefault('firma', nastaveni['firma'])
    doklad.match_detail = detail
    if doklad.stav != FinanceDoklad.STAV_ODESLANO_FLEXI:
        doklad.stav = FinanceDoklad.STAV_KE_KONTROLE
    doklad.upraveno = timezone.now()
    doklad.save()
    return doklad


def odeslat_dobropis_do_flexi(doklad: FinanceDoklad, *, reuse_existing: bool = False) -> FinanceDoklad:
    try:
        result = _zapsat(doklad, reuse_existing=reuse_existing)
    except Exception as exc:
        logger.exception('Flexi dobropis selhal doklad=%s', doklad.id)
        result = {'ok': False, 'error': str(exc)[:500]}

    detail = dict(doklad.match_detail or {})
    detail['flexi'] = result
    doklad.match_detail = detail
    doklad.upraveno = timezone.now()
    update_fields = ['match_detail', 'upraveno']
    flexi_id = str(result.get('flexi_id') or '')[:32]
    if flexi_id:
        doklad.flexi_id = flexi_id
        update_fields.append('flexi_id')
    if result.get('ok') and flexi_id and not result.get('skipped'):
        doklad.stav = FinanceDoklad.STAV_ODESLANO_FLEXI
        update_fields.append('stav')
    elif result.get('ok') and result.get('skipped') and flexi_id:
        doklad.stav = FinanceDoklad.STAV_ODESLANO_FLEXI
        update_fields.append('stav')
    doklad.save(update_fields=update_fields)
    return doklad


def _zapsat(doklad: FinanceDoklad, *, reuse_existing: bool) -> dict:
    if not is_flexi_sync_enabled():
        return {'ok': False, 'skipped': True, 'reason': 'flexi_disabled', 'error': 'Flexi není zapnuté'}
    cfg = get_flexi_config()
    if not cfg:
        return {'ok': False, 'skipped': True, 'reason': 'flexi_not_configured', 'error': 'Flexi není nakonfigurované'}

    detail = doklad.match_detail or {}
    previous = detail.get('flexi') or {}
    if doklad.flexi_id and previous.get('priloha_id'):
        return {
            'ok': True,
            'skipped': True,
            'reason': 'already_synced',
            'flexi_id': doklad.flexi_id,
            'flexi_kod': previous.get('flexi_kod'),
            'priloha_id': previous.get('priloha_id'),
        }

    if not doklad.soubor:
        return {'ok': False, 'error': 'Chybí soubor dobropisu'}
    path = Path(settings.MEDIA_ROOT) / doklad.soubor
    if not path.is_file():
        return {'ok': False, 'error': f'Soubor nenalezen: {doklad.soubor}'}

    nastaveni = dobropis_nastaveni(cfg)
    if not doklad.cislo_faktury:
        return {'ok': False, 'error': 'Chybí číslo dobropisu'}
    if not doklad.datum_vystaveni:
        return {'ok': False, 'error': 'Chybí datum vystavení'}
    if doklad.castka_celkem is None:
        return {'ok': False, 'error': 'Chybí částka dobropisu'}
    base = abs(Decimal(doklad.castka_celkem)).quantize(_MONEY, rounding=ROUND_HALF_UP)
    vat = abs(Decimal(doklad.dph_castka if doklad.dph_castka is not None else 0)).quantize(
        _MONEY, rounding=ROUND_HALF_UP,
    )
    popis = (detail.get('popis') or nastaveni['popis']).strip()
    fields = flexi_dobropis_fields(
        cislo=doklad.cislo_faktury,
        datum=doklad.datum_vystaveni,
        castka=base,
        dph=vat,
        vs=(doklad.vs or var_sym_from_cislo(doklad.cislo_faktury)),
        popis=popis,
        nastaveni=nastaveni,
    )

    try:
        client = FlexiClient(cfg)
    except FlexiError as exc:
        return {'ok': False, 'error': exc.message}

    flexi_id = (doklad.flexi_id or '').strip()
    flexi_kod = previous.get('flexi_kod') or ''
    created = False

    if not flexi_id:
        try:
            found = client.find_faktura_prijata(
                field='cisDosle',
                value=doklad.cislo_faktury,
                firma_code=nastaveni['firma'],
                limit=2,
            )
        except FlexiError as exc:
            return {'ok': False, 'error': exc.message}
        if found and not reuse_existing:
            kod = found[0].get('kod') or found[0].get('id')
            return {
                'ok': False,
                'error': f'Ve Flexi už je doklad {kod} se stejným číslem. Nový zápis nevznikl.',
                'existing_id': str(found[0].get('id') or ''),
                'flexi_kod': kod,
            }
        if len(found) > 1:
            return {'ok': False, 'error': 'Ve Flexi je víc dokladů se stejným číslem dobropisu'}
        if found:
            flexi_id = str(found[0].get('id') or '')
            flexi_kod = found[0].get('kod') or ''
        else:
            try:
                created_row = client.create_faktura_prijata(fields)
            except FlexiError as exc:
                return {'ok': False, 'error': exc.message, 'payload_cislo': doklad.cislo_faktury}
            flexi_id = created_row.get('flexi_id') or ''
            flexi_kod = created_row.get('flexi_kod') or ''
            created = True

    if not flexi_id:
        return {'ok': False, 'error': 'Flexi nevrátilo id dokladu'}

    try:
        upload = client.upload_priloha(
            flexi_id,
            filename=path.name,
            content=path.read_bytes(),
            content_type=_content_type_for(path),
        )
    except FlexiError as exc:
        logger.warning('Flexi příloha dobropisu selhala doklad=%s: %s', doklad.id, exc.message)
        return {
            'ok': False,
            'created': created,
            'flexi_id': flexi_id,
            'flexi_kod': flexi_kod,
            'error': f'Doklad ve Flexi vznikl ({flexi_kod or flexi_id}), příloha se nepodařila: {exc.message}',
        }

    return {
        'ok': True,
        'created': created,
        'flexi_id': flexi_id,
        'flexi_kod': flexi_kod,
        'priloha_id': upload.get('priloha_id'),
        'filename': path.name,
        'firma': nastaveni['firma'],
        'popis': popis,
    }
