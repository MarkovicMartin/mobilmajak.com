"""Předpisy přijaté faktury z účetního manuálu. Bez zápisu do Flexi."""
from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, ROUND_HALF_UP

_MONEY = Decimal('0.01')
_ICO = re.compile(r'^\d{8}$')
_DIC = re.compile(r'^([A-Za-z]{2})')

# Účtování, které účetní opisuje z předpisu.
CESKE_DPH = '40-41'
CESKE_KH = 'B.2-3. AUTO'
ZBOZI_MD = '504001'
ZAHRANICNI_DPH = '05-06, 43-44'
ZAHRANICNI_KH = 'A.2.'
PRENESENA_DPH = '10-11'
PRENESENA_KH = 'B.1.'

_SLUZBY = (
    'najem', 'sluzb', 'energi', 'elektr', 'plyn', 'vodne', 'vodneho',
    'telefon', 'internet', 'pojist', 'mzda', 'software', 'hosting',
)
_PRENESENA = ('prenesena', 'reverse charge', 'dan odvede zakaznik')


def bez_diakritiky(value: str) -> str:
    text = unicodedata.normalize('NFKD', value or '')
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r'\s+', ' ', text).strip().casefold()


def _money(value: Decimal) -> str:
    return f'{value.quantize(_MONEY, rounding=ROUND_HALF_UP):.2f}'


def _var_sym(vs: str, cislo: str) -> str:
    raw = (vs or '').strip()
    if raw:
        return raw[:30]
    digits = re.sub(r'\D', '', cislo or '')
    return (digits or re.sub(r'\s+', '', cislo or ''))[:30]


def klasifikuj_zpravu(text: str) -> dict:
    """Třídění pošty z manuálu. Nerozhoduje obsah datové schránky ani platbu."""
    folded = bez_diakritiky(text)
    if 'dovolen' in folded:
        return {
            'akce': 'preposlat',
            'komu': 'R. Bulandr',
            'duvod': 'Žádost o dovolenou se přeposílá R. Bulandrovi.',
        }
    if 'datov' in folded:
        return {
            'akce': 'datovka',
            'duvod': 'Přečíst datovou schránku. Pokutu předat R. Valouchové.',
        }
    if 'bakr' in folded:
        return {
            'akce': 'archiv',
            'duvod': 'Bakr se platí hotově. Nezadávat do přijatých faktur, jen archivovat.',
        }
    if 'comgate' in folded:
        return {'akce': 'archiv', 'duvod': 'Comgate jen archivovat.'}
    if 'upom' in folded:
        return {
            'akce': 'upominka',
            'duvod': 'Zkontrolovat, jestli už VS není zaplacené. Nezaplacené probrat s p. Bajtkem.',
        }
    if 'vypis' in folded:
        return {
            'akce': 'archiv',
            'duvod': 'Výpis archivovat. Pohyby jdou z Fio a Raiffeisen.',
        }
    if 'faktur' in folded or 'invoice' in folded:
        return {'akce': 'fronta', 'duvod': 'Fakturu zadat do fronty a archivovat.'}
    return {'akce': 'clovek', 'duvod': 'Zpráva nemá pravidlo z manuálu.'}


def _vyjimka(folded: str) -> dict | None:
    if 'valouch' in folded:
        return {
            'akce': 'pokladna',
            'typ': 'vyjimka',
            'duvod': 'Faktury od R. Valouchové jdou do korunové pokladny, ne do přijatých faktur.',
        }
    if 'bakr' in folded:
        return {
            'akce': 'archiv',
            'typ': 'vyjimka',
            'duvod': 'Bakr se platí hotově. Nezadávat do přijatých faktur, jen archivovat.',
        }
    if 'comgate' in folded:
        return {
            'akce': 'archiv',
            'typ': 'vyjimka',
            'duvod': 'Comgate jen archivovat.',
        }
    if 'senimo' in folded:
        return {
            'akce': 'fyzicky',
            'typ': 'vyjimka',
            'duvod': 'Senimo nájem a energie nechodí mailem. Doklad přinese sekretářka na prodejnu.',
        }
    return None


def _zeme(ico: str, dic: str) -> str:
    ico_text = re.sub(r'\s+', '', ico or '')
    dic_text = re.sub(r'\s+', '', dic or '').upper()
    if _ICO.fullmatch(ico_text):
        return 'cz'
    match = _DIC.match(dic_text)
    if not match:
        return ''
    return 'cz' if match.group(1) == 'CZ' else 'zahranicni'


def _je_sluzba(folded: str) -> bool:
    return any(word in folded for word in _SLUZBY)


def _je_prenesena(folded: str) -> bool:
    return any(word in folded for word in _PRENESENA)


def _castky(bez, dph, celkem) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    def parse(value):
        if value is None or value == '':
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    base = parse(bez)
    vat = parse(dph)
    total = parse(celkem)
    if base is None and total is not None and vat is not None:
        base = total - vat
    if vat is None and base is not None and total is not None:
        vat = total - base
    if total is None and base is not None and vat is not None:
        total = base + vat
    return base, vat, total


def klasifikuj_prijatou(
    *,
    dodavatel: str = '',
    ico: str = '',
    dic: str = '',
    popis: str = '',
    cislo: str = '',
    vs: str = '',
    datum: str = '',
    splatnost: str = '',
    castka_bez_dph=None,
    dph_castka=None,
    castka_celkem=None,
    znamy: bool = False,
    firma_kod: str = '',
    typ_dokl: str = 'FAKTURA',
    prim_ucet: str = '321001',
    popis_override: str = '',
) -> dict:
    """
    Suchý návrh přijaté faktury.
    Zápis smí proběhnout jen u známého dodavatele a jasného předpisu.
    """
    folded = bez_diakritiky(f'{dodavatel} {popis}')
    vyjimka = _vyjimka(folded)
    base, vat, total = _castky(castka_bez_dph, dph_castka, castka_celkem)
    kod = (firma_kod or '').strip()
    if not znamy:
        kod = ''

    if vyjimka:
        return _vysledek(
            akce=vyjimka['akce'],
            typ=vyjimka['typ'],
            duvod=vyjimka['duvod'],
            znamy=znamy,
            firma_kod='',
            lze=False,
            blokuje=[vyjimka['duvod']],
            doplnit=[],
            base=base,
            vat=vat,
            total=total,
            fields=None,
            ucet_md='',
            clen_dph='',
            clen_kh='',
            popis_dokladu='',
        )

    zeme = _zeme(ico, dic)
    if _je_prenesena(folded):
        typ = 'prenesena'
        ucet_md = ''
        clen_dph = PRENESENA_DPH
        clen_kh = PRENESENA_KH
        popis_dokladu = 'Přenesená daňová povinnost'
        jasny_predpis = False
    elif zeme == 'zahranicni':
        typ = 'zahranicni'
        ucet_md = ZBOZI_MD
        clen_dph = ZAHRANICNI_DPH
        clen_kh = ZAHRANICNI_KH
        popis_dokladu = 'Zboží'
        jasny_predpis = True
    elif zeme == 'cz' and _je_sluzba(folded):
        typ = 'ceska_sluzba'
        ucet_md = ''
        clen_dph = CESKE_DPH
        clen_kh = CESKE_KH
        popis_dokladu = 'Služby'
        jasny_predpis = False
    elif zeme == 'cz':
        typ = 'ceske_zbozi'
        ucet_md = ZBOZI_MD
        clen_dph = CESKE_DPH
        clen_kh = CESKE_KH
        popis_dokladu = 'Zboží'
        jasny_predpis = True
    else:
        typ = 'nejasny'
        ucet_md = ''
        clen_dph = ''
        clen_kh = ''
        popis_dokladu = ''
        jasny_predpis = False

    if popis_override.strip():
        popis_dokladu = popis_override.strip()[:255]

    blokuje: list[str] = []
    doplnit: list[str] = []
    if not jasny_predpis:
        if typ == 'nejasny':
            blokuje.append('Nejasný typ dokladu. Návrh bez zápisu.')
        elif typ == 'prenesena':
            blokuje.append('Přenesená daňová povinnost zůstává ke kontrole.')
        else:
            blokuje.append('Nejasný účet MD. Návrh bez zápisu.')
    if not znamy:
        blokuje.append('Neznámý dodavatel. Návrh bez zápisu.')
    elif not kod:
        doplnit.append('firma_kod')
        blokuje.append('Chybí kód firmy ve Flexi.')
    if not (cislo or '').strip():
        blokuje.append('Chybí číslo došlé.')
    if not datum:
        blokuje.append('Chybí datum vystavení.')
    if base is None or vat is None or total is None:
        blokuje.append('Chybí základ, DPH nebo částka celkem.')
    elif total < 0 or base < 0:
        blokuje.append('Záporná částka patří do dobropisu, ne do přijaté faktury.')

    lze = jasny_predpis and znamy and bool(kod) and not any(
        item.startswith('Chybí') or item.startswith('Záporná') for item in blokuje
    )
    fields = None
    if jasny_predpis and base is not None and vat is not None and total is not None and total >= 0 and base >= 0:
        fields = _flexi_fields(
            cislo=cislo,
            vs=vs,
            datum=datum,
            splatnost=splatnost or datum,
            popis=popis_dokladu,
            base=base,
            vat=vat,
            total=total,
            firma_kod=kod,
            ico=ico,
            dodavatel=dodavatel,
            typ_dokl=typ_dokl,
            prim_ucet=prim_ucet,
            ucet_md=ucet_md,
            clen_dph=clen_dph,
            clen_kh=clen_kh,
        )
    duvod = blokuje[0] if blokuje else 'Lze založit přijatou fakturu.'
    akce = 'zapsat' if lze else 'navrh'
    return _vysledek(
        akce=akce,
        typ=typ,
        duvod=duvod,
        znamy=znamy,
        firma_kod=kod,
        lze=lze,
        blokuje=blokuje,
        doplnit=doplnit if znamy and jasny_predpis else [],
        base=base,
        vat=vat,
        total=total,
        fields=fields,
        ucet_md=ucet_md,
        clen_dph=clen_dph,
        clen_kh=clen_kh,
        popis_dokladu=popis_dokladu,
    )


def _flexi_fields(
    *,
    cislo: str,
    vs: str,
    datum: str,
    splatnost: str,
    popis: str,
    base: Decimal,
    vat: Decimal,
    total: Decimal,
    firma_kod: str,
    ico: str,
    dodavatel: str,
    typ_dokl: str,
    prim_ucet: str,
    ucet_md: str,
    clen_dph: str,
    clen_kh: str,
) -> dict:
    den = (datum or '')[:10]
    splat = (splatnost or den)[:10]
    fields = {
        'typDokl': f'code:{typ_dokl}',
        'cisDosle': (cislo or '')[:40],
        'varSym': _var_sym(vs, cislo),
        'datVyst': den,
        'duzpPuv': den,
        'duzpUcto': den,
        'datUcto': den,
        'datSplat': splat,
        'popis': (popis or 'Zboží')[:255],
        'bezPolozek': True,
        'sumZklZakl': _money(base),
        'sumDphZakl': _money(vat),
        'sumCelkem': _money(total),
    }
    if firma_kod:
        fields['firma'] = f'code:{firma_kod}'
    if (ico or '').strip():
        fields['ic'] = re.sub(r'\s+', '', ico)[:20]
    if (dodavatel or '').strip():
        fields['nazFirmy'] = dodavatel.strip()[:255]
    if clen_dph:
        fields['clenDph'] = f'code:{clen_dph}'
    if clen_kh:
        fields['clenKonVykDph'] = f'code:{clen_kh}'
    if prim_ucet:
        fields['primUcet'] = f'code:{prim_ucet}'
    if ucet_md:
        fields['protiUcet'] = f'code:{ucet_md}'
    return fields


def _text_castka(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return _money(value)


def _vysledek(
    *,
    akce: str,
    typ: str,
    duvod: str,
    znamy: bool,
    firma_kod: str,
    lze: bool,
    blokuje: list[str],
    doplnit: list[str],
    base: Decimal | None,
    vat: Decimal | None,
    total: Decimal | None,
    fields: dict | None,
    ucet_md: str,
    clen_dph: str,
    clen_kh: str,
    popis_dokladu: str,
) -> dict:
    return {
        'akce': akce,
        'typ': typ,
        'duvod': duvod,
        'lze_zapsat': lze,
        'znamy_dodavatel': znamy,
        'firma_kod': firma_kod,
        'doplnit': doplnit,
        'blokuje': blokuje,
        'ucet_md': ucet_md,
        'clen_dph': clen_dph,
        'clen_kon_vyk': clen_kh,
        'popis': popis_dokladu,
        'castka_bez_dph': _text_castka(base),
        'dph_castka': _text_castka(vat),
        'castka_celkem': _text_castka(total),
        'flexi_fields': fields,
    }
