"""Návrh přijaté faktury a zápis do Flexi až po potvrzení."""
from __future__ import annotations

import logging
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from .flexi_client import FlexiClient, FlexiError
from .flexi_sync import _content_type_for
from .models import FinanceDoklad, NakladPolozka
from .secrets import get_flexi_config, get_ucetni_config, is_flexi_sync_enabled
from .ucetni_pravidla import bez_diakritiky, klasifikuj_prijatou

logger = logging.getLogger(__name__)


def _firma_z_nastaveni(doklad: FinanceDoklad, nastaveni: dict) -> dict | None:
    ico = re_ico(doklad.dodavatel_ico)
    nazev = bez_diakritiky(doklad.dodavatel_nazev)
    for raw in nastaveni.get('znami_dodavatele') or []:
        if not isinstance(raw, dict):
            continue
        cfg_ico = re_ico(raw.get('ico'))
        cfg_nazev = bez_diakritiky(str(raw.get('nazev') or ''))
        if ico and cfg_ico and ico == cfg_ico:
            return raw
        if nazev and cfg_nazev and cfg_nazev in nazev:
            return raw
    return None


def re_ico(value) -> str:
    return ''.join(ch for ch in str(value or '') if ch.isdigit())


def _historie(doklad: FinanceDoklad) -> FinanceDoklad | None:
    ico = re_ico(doklad.dodavatel_ico)
    nazev = (doklad.dodavatel_nazev or '').strip()
    qs = FinanceDoklad.objects.filter(stav=FinanceDoklad.STAV_ODESLANO_FLEXI)
    if doklad.pk:
        qs = qs.exclude(pk=doklad.pk)
    if ico:
        qs = qs.filter(dodavatel_ico=doklad.dodavatel_ico)
    elif nazev:
        qs = qs.filter(dodavatel_nazev__iexact=nazev)
    else:
        return None
    return qs.order_by('-id').first()


def _firma_z_historie(historie: FinanceDoklad | None) -> str:
    if not historie:
        return ''
    detail = historie.match_detail or {}
    zapis = detail.get('ucetni_zapis') or {}
    if isinstance(zapis, dict) and zapis.get('firma_kod'):
        return str(zapis['firma_kod']).strip()
    flexi = detail.get('flexi') or {}
    if isinstance(flexi, dict) and flexi.get('firma_kod'):
        return str(flexi['firma_kod']).strip()
    return ''


def sestav_navrh(doklad: FinanceDoklad, *, firma_kod: str = '', popis: str = '') -> dict:
    nastaveni = get_ucetni_config()
    nalezeny = _firma_z_nastaveni(doklad, nastaveni)
    historie = _historie(doklad)
    znamy = bool(nalezeny or historie)
    kod = ''
    if isinstance(nalezeny, dict):
        kod = str(nalezeny.get('firma_kod') or '').strip()
    if not kod:
        kod = _firma_z_historie(historie)
    if (firma_kod or '').strip() and znamy:
        kod = firma_kod.strip()
    ocr = ((doklad.ocr_raw or {}).get('extracted') or {}) if doklad.ocr_raw else {}
    dic = str(ocr.get('dic') or ocr.get('dodavatel_dic') or '')
    text_popisu = str(ocr.get('popis') or '')
    return klasifikuj_prijatou(
        dodavatel=doklad.dodavatel_nazev,
        ico=doklad.dodavatel_ico,
        dic=dic,
        popis=text_popisu,
        cislo=doklad.cislo_faktury,
        vs=doklad.vs,
        datum=doklad.datum_vystaveni.isoformat() if doklad.datum_vystaveni else '',
        splatnost=doklad.datum_splatnosti.isoformat() if doklad.datum_splatnosti else '',
        castka_bez_dph=doklad.castka_bez_dph,
        dph_castka=doklad.dph_castka,
        castka_celkem=doklad.castka_celkem,
        znamy=znamy,
        firma_kod=kod,
        typ_dokl=nastaveni.get('typ_dokl') or 'FAKTURA',
        prim_ucet=nastaveni.get('prim_ucet') or '321001',
        popis_override=popis,
    )


def dopln_ucetni_navrh(doklad: FinanceDoklad) -> dict:
    navrh = sestav_navrh(doklad)
    detail = dict(doklad.match_detail or {})
    detail['ucetni_navrh'] = navrh
    doklad.match_detail = detail
    return navrh


def stav_upominky(vs: str) -> dict:
    """Upomínka: systém jen řekne, jestli VS už je v pohybech. Platbu schvaluje p. Bajtek."""
    symbol = (vs or '').strip()
    if not symbol:
        return {
            'vs': '',
            'zaplaceno': False,
            'k_bajtkovi': True,
            'pohybu': 0,
            'duvod': 'Chybí variabilní symbol.',
        }
    pocet = NakladPolozka.objects.filter(vs=symbol, ignorovat=False).count()
    if pocet:
        return {
            'vs': symbol,
            'zaplaceno': True,
            'k_bajtkovi': False,
            'pohybu': pocet,
            'duvod': 'VS už je na účtu nebo v pokladně.',
        }
    return {
        'vs': symbol,
        'zaplaceno': False,
        'k_bajtkovi': True,
        'pohybu': 0,
        'duvod': 'VS není zaplacené. Probrat s p. Bajtkem. Systém platbu neschvaluje.',
    }


def _uloz_vysledek(doklad: FinanceDoklad, result: dict, *, schvalit: bool, user_id: int | None) -> None:
    detail = dict(doklad.match_detail or {})
    detail['flexi'] = result
    if result.get('firma_kod'):
        detail['ucetni_zapis'] = {
            'firma_kod': result['firma_kod'],
            'typ': (detail.get('ucetni_navrh') or {}).get('typ') or '',
        }
    doklad.match_detail = detail
    doklad.upraveno = timezone.now()
    fields = ['match_detail', 'upraveno']
    if result.get('flexi_id'):
        doklad.flexi_id = str(result['flexi_id'])[:32]
        fields.append('flexi_id')
    if schvalit and result.get('ok'):
        doklad.stav = FinanceDoklad.STAV_ODESLANO_FLEXI
        doklad.schvalil_user_id = user_id
        doklad.schvaleno = timezone.now()
        fields.extend(['stav', 'schvalil_user_id', 'schvaleno'])
    doklad.save(update_fields=fields)


def _priloha(client: FlexiClient, doklad: FinanceDoklad, flexi_id: str) -> dict:
    if not doklad.soubor:
        return {'ok': False, 'error': 'Chybí soubor dokladu', 'flexi_id': flexi_id}
    path = Path(settings.MEDIA_ROOT) / doklad.soubor
    if not path.is_file():
        return {'ok': False, 'error': f'Soubor nenalezen: {doklad.soubor}', 'flexi_id': flexi_id}
    upload = client.upload_priloha(
        flexi_id,
        filename=path.name,
        content=path.read_bytes(),
        content_type=_content_type_for(path),
    )
    return {
        'ok': True,
        'flexi_id': flexi_id,
        'priloha_id': upload.get('priloha_id'),
        'filename': path.name,
    }


def zalozit_prijatou_ve_flexi(
    doklad: FinanceDoklad,
    *,
    firma_kod: str = '',
    popis: str = '',
    user_id: int | None = None,
) -> dict:
    """
    Založí přijatou FA a přiloží PDF.
    Neznámý dodavatel a nejasný předpis zůstanou ve frontě, bez změny stavu.
    """
    if doklad.druh == FinanceDoklad.DRUH_DOBROPIS:
        return {'ok': False, 'fronta': True, 'error': 'Dobropis se zakládá jinou cestou.'}

    navrh = sestav_navrh(doklad, firma_kod=firma_kod, popis=popis)
    detail = dict(doklad.match_detail or {})
    detail['ucetni_navrh'] = navrh
    doklad.match_detail = detail

    if doklad.flexi_id:
        if not is_flexi_sync_enabled():
            doklad.save(update_fields=['match_detail', 'upraveno'])
            return {'ok': False, 'skipped': True, 'fronta': True, 'reason': 'flexi_disabled', 'ucetni_navrh': navrh}
        try:
            client = FlexiClient(get_flexi_config())
            uploaded = _priloha(client, doklad, doklad.flexi_id)
        except FlexiError as exc:
            uploaded = {'ok': False, 'error': exc.message, 'flexi_id': doklad.flexi_id}
        uploaded['firma_kod'] = navrh.get('firma_kod') or ''
        uploaded['ucetni_navrh'] = navrh
        _uloz_vysledek(doklad, uploaded, schvalit=uploaded.get('ok'), user_id=user_id)
        return uploaded

    if not navrh.get('lze_zapsat'):
        doklad.upraveno = timezone.now()
        doklad.save(update_fields=['match_detail', 'upraveno'])
        return {
            'ok': False,
            'fronta': True,
            'error': navrh.get('duvod') or 'Návrh nelze zapsat.',
            'ucetni_navrh': navrh,
        }

    if not is_flexi_sync_enabled():
        doklad.save(update_fields=['match_detail', 'upraveno'])
        return {
            'ok': False,
            'skipped': True,
            'fronta': True,
            'reason': 'flexi_disabled',
            'error': 'Flexi sync je vypnutý. Doklad zůstává ve frontě.',
            'ucetni_navrh': navrh,
        }

    fields = dict(navrh.get('flexi_fields') or {})
    if not fields:
        return {'ok': False, 'fronta': True, 'error': 'Chybí pole pro Flexi.', 'ucetni_navrh': navrh}

    try:
        client = FlexiClient(get_flexi_config())
        created = client.create_faktura_prijata(fields)
    except FlexiError as exc:
        logger.warning('Flexi přijatá FA doklad=%s: %s', doklad.id, exc.message)
        failed = {
            'ok': False,
            'error': exc.message,
            'firma_kod': navrh.get('firma_kod') or '',
            'ucetni_navrh': navrh,
        }
        _uloz_vysledek(doklad, failed, schvalit=False, user_id=user_id)
        return failed

    flexi_id = created['flexi_id']
    try:
        uploaded = _priloha(client, doklad, flexi_id)
    except FlexiError as exc:
        uploaded = {'ok': False, 'error': exc.message, 'flexi_id': flexi_id}
    uploaded.update({
        'flexi_id': flexi_id,
        'flexi_kod': created.get('flexi_kod') or '',
        'firma_kod': navrh.get('firma_kod') or '',
        'vytvoreno': True,
        'ucetni_navrh': navrh,
    })
    _uloz_vysledek(doklad, uploaded, schvalit=uploaded.get('ok'), user_id=user_id)
    return uploaded
