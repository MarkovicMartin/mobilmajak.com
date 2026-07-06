"""Parsování dodavatele a čísla FA z popisu výdeje Symplio pokladny."""
from __future__ import annotations

import re
from decimal import Decimal

from .models import NakladPolozka

_VYDEJ_PREFIX = re.compile(r'^manu[aá]ln[ií]\s+v[yý]de[jj]\s+', re.I)
_ZBOZI_KW = re.compile(r'\b(servis|d[ií]ly|zb[oó]ž[ií]|zbozi)\b', re.I)
_SKIP_FA_TOKENS = frozenset({
    'servis', 'dily', 'díly', 'dily', 'zbozi', 'zboží', 'fa', 'faktura', 'fakt', 'č',
})


def parse_symplio_vydej_faktura(popis: str, castka: Decimal | None = None) -> dict | None:
    """
    Formát: Dodavatel [popis] - servis|díly|zboží … číslo_FA
    Částka = abs(castka) z pokladny (včetně DPH, DPH doplníme z přiložené FA).
    """
    raw = (popis or '').strip()
    if not raw or not _ZBOZI_KW.search(raw):
        return None

    text = _VYDEJ_PREFIX.sub('', raw).strip()
    dodavatel = ''
    detail = text

    if ' - ' in text:
        dodavatel, detail = text.split(' - ', 1)
        dodavatel = dodavatel.strip()
    else:
        m = _ZBOZI_KW.search(text)
        if m:
            dodavatel = text[:m.start()].strip(' -')
            detail = text[m.start():]

    cislo_faktury = _extract_cislo_faktury(detail)
    if not dodavatel or not cislo_faktury:
        return None

    result = {
        'dodavatel_nazev': dodavatel[:200],
        'cislo_faktury': cislo_faktury[:64],
        'zdroj_parse': 'symplio_popis',
    }
    if castka is not None:
        result['castka_celkem'] = str(abs(Decimal(str(castka))))
    return result


def _extract_cislo_faktury(detail: str) -> str:
    m = _ZBOZI_KW.search(detail)
    if not m:
        return ''
    tail = detail[m.end():].strip(' -:.')
    if not tail:
        return ''
    tokens = re.findall(r'[A-Za-z0-9][\w./\-]*', tail)
    for token in reversed(tokens):
        low = token.lower().rstrip('.')
        if low in _SKIP_FA_TOKENS or len(token) < 2:
            continue
        return token
    return ''


def faktura_hint_from_polozka(polozka: NakladPolozka) -> dict | None:
    if polozka.zdroj != NakladPolozka.ZDROJ_SYMPLIO_POKLADNA:
        return None
    return parse_symplio_vydej_faktura(polozka.popis, polozka.castka)
