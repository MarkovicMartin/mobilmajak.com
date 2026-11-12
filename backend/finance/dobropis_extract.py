"""Vyčtení opravného dokladu Partnertele (correction / dobropis WDT)."""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from .faktura_extract import (
    FakturaExtracted,
    _normalize_amount_str,
    _pdf_text,
    extract_faktura_from_file,
)

_CISLO_RE = re.compile(
    r'correction\s+(\d{1,6}/\d{2}/\d{2}/[A-Z0-9]+)',
    re.I,
)
_TO_PAY_RE = re.compile(
    r'To pay:\s*(-?\d{1,3}(?:[ \u00a0]\d{3})*(?:[.,]\d{2})|-?\d+(?:[.,]\d{2}))',
    re.I,
)
_DIFF_RE = re.compile(
    r'Difference\s+(-?\d{1,3}(?:[ \u00a0]\d{3})*(?:[.,]\d{2})|-?\d+(?:[.,]\d{2}))'
    r'\s+0%\s+0[,.]00\s+'
    r'(-?\d{1,3}(?:[ \u00a0]\d{3})*(?:[.,]\d{2})|-?\d+(?:[.,]\d{2}))',
    re.I,
)
_DOC_DATE_RE = re.compile(
    r'Doc\.\s*date:\s*([A-Za-z]{3,9})\s+(\d{1,2}),\s*(\d{4})',
    re.I,
)
_MONTHS = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}


def parse_partnertele_dobropis(text: str) -> FakturaExtracted:
    """
    Číslo je za „correction“, částka je „To pay“ (u vzoru 100/07/26/KFWZDWV a -43,55).
    Původní faktura v „Refers to“ se nebere.
    """
    result = FakturaExtracted(zdroj='partnertele')
    raw = text or ''
    cislo = _CISLO_RE.search(raw)
    if cislo:
        result.cislo_faktury = cislo.group(1)
        digits = re.sub(r'\D', '', result.cislo_faktury)
        if digits:
            result.vs = digits[:30]

    amount = None
    pay = _TO_PAY_RE.search(raw)
    if pay:
        amount = _normalize_amount_str(pay.group(1))
    if not amount:
        diff = _DIFF_RE.search(raw)
        if diff:
            amount = _normalize_amount_str(diff.group(2))
    if amount:
        result.castka_celkem = amount
        result.castka_bez_dph = amount
        # Na dokladu je 0 % (reverse charge). Do Flexi patří česká DPH 21 % ze základu,
        # celkem k úhradě zůstává základ – stejně jako u ostatních ODD Partnertele.
        zaklad = Decimal(amount)
        dph = (zaklad * Decimal('21') / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        result.dph_castka = f'{dph:.2f}'
        result.dph_sazba = 21

    doc_date = _DOC_DATE_RE.search(raw)
    if doc_date:
        month = _MONTHS.get(doc_date.group(1)[:3].lower())
        if month:
            try:
                result.datum_vystaveni = date(
                    int(doc_date.group(3)), month, int(doc_date.group(2)),
                ).isoformat()
            except ValueError:
                result.chyby.append('Datum vystavení z dokladu nejde přečíst.')

    if re.search(r'PARTNER TELE', raw, re.I):
        result.dodavatel_nazev = 'PARTNER TELE.COM SP. Z O.O. S.K'
        result.dodavatel_dic = 'PL6792675514'

    if not result.cislo_faktury:
        result.chyby.append('V dobropisu chybí číslo za correction.')
    if not result.castka_celkem:
        result.chyby.append('V dobropisu chybí částka To pay.')
    return result


def extract_dobropis_file(path: Path) -> tuple[FakturaExtracted, str, dict]:
    text = _pdf_text(path) if path.suffix.lower() == '.pdf' else ''
    parsed = parse_partnertele_dobropis(text) if text.strip() else FakturaExtracted(zdroj='partnertele')
    if parsed.cislo_faktury and parsed.castka_celkem:
        parsed.zdroj = 'pdf_text'
        parsed.raw_text_len = len(text)
        return parsed, text[:8000], {'method': 'pdf_text'}

    _generic, raw, meta = extract_faktura_from_file(path)
    alt_text = raw or text
    alt = parse_partnertele_dobropis(alt_text) if alt_text.strip() else FakturaExtracted(zdroj='partnertele')
    if alt.cislo_faktury or alt.castka_celkem:
        alt.zdroj = meta.get('method') or 'pdf_ocr'
        alt.raw_text_len = len(alt_text)
        return alt, alt_text[:8000], meta
    if parsed.cislo_faktury or parsed.castka_celkem:
        parsed.zdroj = 'pdf_text'
        parsed.raw_text_len = len(text)
        return parsed, text[:8000], {'method': 'pdf_text'}

    empty = parsed if text.strip() else alt
    if not empty.chyby:
        empty.chyby.append('Z dobropisu se nepodařilo vyčíst číslo nebo částku k úhradě.')
    empty.zdroj = meta.get('method') or 'none'
    return empty, (alt_text or '')[:8000], meta
