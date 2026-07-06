"""Extrakce polí z PDF faktury (textová vrstva + ISDOC)."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation, InvalidOperation
from pathlib import Path

_AMOUNT_RE = re.compile(
    r'(?P<num>\d{1,3}(?:[ \u00a0]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)',
)
_ICO_RE = re.compile(r'\bI[ČC]O\s*[:.]?\s*(?P<ico>\d{8})\b', re.I)
_DIC_RE = re.compile(r'\bDI[ČC]\s*[:.]?\s*(?P<dic>CZ\d{8,10})\b', re.I)
_FA_NUM_RE = re.compile(
    r'(?:číslo\s+)?faktury|faktura\s*č\.?|invoice\s*no\.?|doklad\s*č\.?',
    re.I,
)


@dataclass
class FakturaExtracted:
    dodavatel_nazev: str = ''
    dodavatel_ico: str = ''
    dodavatel_dic: str = ''
    cislo_faktury: str = ''
    datum_vystaveni: str = ''
    castka_bez_dph: str | None = None
    dph_castka: str | None = None
    dph_sazba: int | None = None
    castka_celkem: str | None = None
    zdroj: str = ''
    raw_text_len: int = 0
    chyby: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def extract_faktura_from_file(path: Path) -> tuple[FakturaExtracted, str, dict]:
    """
    Vrátí (extrahovaná pole, raw_text pro debug, metadata).
  metadata: method=isdoc|pdf_text|image_ocr|none
    """
    suffix = path.suffix.lower()
    if suffix == '.pdf':
        return _extract_pdf(path)
    if suffix in {'.jpg', '.jpeg', '.png', '.webp'}:
        return _extract_image(path)
    result = FakturaExtracted(zdroj='none', chyby=['Nepodporovaný formát souboru'])
    return result, '', {'method': 'none'}


def _extract_pdf(path: Path) -> tuple[FakturaExtracted, str, dict]:
    raw_bytes = path.read_bytes()
    isdoc = _parse_isdoc_from_bytes(raw_bytes)
    if isdoc:
        return isdoc, '', {'method': 'isdoc'}

    text = _pdf_text(path)
    if not text.strip():
        result = FakturaExtracted(
            zdroj='pdf_text',
            raw_text_len=0,
            chyby=['PDF neobsahuje čitelný text (nebo chybí knihovna pypdf na serveru)'],
        )
        return result, '', {'method': 'pdf_text_empty'}

    parsed = _parse_text_fields(text)
    parsed.zdroj = 'pdf_text'
    parsed.raw_text_len = len(text)
    return parsed, text[:8000], {'method': 'pdf_text'}


def _extract_image(path: Path) -> tuple[FakturaExtracted, str, dict]:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        result = FakturaExtracted(
            zdroj='image_ocr',
            chyby=['OCR pro fotky není na serveru nakonfigurován (pytesseract)'],
        )
        return result, '', {'method': 'image_ocr_unavailable'}

    try:
        text = pytesseract.image_to_string(Image.open(path), lang='ces+eng')
    except Exception as exc:
        result = FakturaExtracted(zdroj='image_ocr', chyby=[f'OCR selhalo: {exc}'])
        return result, '', {'method': 'image_ocr_error'}

    parsed = _parse_text_fields(text)
    parsed.zdroj = 'image_ocr'
    parsed.raw_text_len = len(text)
    return parsed, text[:8000], {'method': 'image_ocr'}


def _pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ''

    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or '')
    return '\n'.join(parts)


def _parse_isdoc_from_bytes(data: bytes) -> FakturaExtracted | None:
    start = data.find(b'<Invoice')
    if start < 0:
        start = data.find(b'<isdoc:Invoice')
    if start < 0:
        return None
    end = data.find(b'</Invoice>', start)
    if end < 0:
        return None
    chunk = data[start:end + len(b'</Invoice>')]
    try:
        root = ET.fromstring(chunk)
    except ET.ParseError:
        return None

    def find_text(*tags: str) -> str:
        for tag in tags:
            for el in root.iter():
                local = el.tag.split('}')[-1] if '}' in el.tag else el.tag
                if local == tag and el.text and el.text.strip():
                    return el.text.strip()
        return ''

    result = FakturaExtracted(zdroj='isdoc')
    result.dodavatel_nazev = find_text('PartyName', 'Name')
    result.dodavatel_ico = find_text('CompanyID')
    result.dodavatel_dic = find_text('TaxID', 'VATIdentificationNumber')
    result.cislo_faktury = find_text('ID', 'DocumentID')
    result.datum_vystaveni = find_text('IssueDate')
    tax_exclusive = find_text('TaxExclusiveAmount', 'TaxableAmount')
    tax_amount = find_text('TaxAmount')
    payable = find_text('PayableAmount', 'TaxInclusiveAmount', 'GrandTotalAmount')
    if tax_exclusive:
        result.castka_bez_dph = _normalize_amount_str(tax_exclusive)
    if tax_amount:
        result.dph_castka = _normalize_amount_str(tax_amount)
    if payable:
        result.castka_celkem = _normalize_amount_str(payable)
    if result.castka_bez_dph and result.dph_castka and not result.castka_celkem:
        try:
            result.castka_celkem = str(
                Decimal(result.castka_bez_dph) + Decimal(result.dph_castka),
            )
        except InvalidOperation:
            pass
    return result if result.cislo_faktury or result.castka_celkem else None


def _parse_text_fields(text: str) -> FakturaExtracted:
    result = FakturaExtracted()
    ico = _ICO_RE.search(text)
    if ico:
        result.dodavatel_ico = ico.group('ico')
    dic = _DIC_RE.search(text)
    if dic:
        result.dodavatel_dic = dic.group('dic')

    result.cislo_faktury = _find_cislo_faktury(text)
    result.castka_celkem = _find_amount_near(text, (
        'celkem k úhradě', 'celkem k uhrade', 'k úhradě', 'k uhrade',
        'celkem', 'total', 'amount due',
    ))
    result.castka_bez_dph = _find_amount_near(text, (
        'základ daně', 'zaklad dane', 'základ', 'zaklad', 'bez dph', 'tax base',
    ))
    result.dph_castka = _find_amount_near(text, (
        'dph 21%', 'dph 12%', 'dph 21', 'dph 12', 'dph', 'daň', 'vat',
    ), skip_percent_rates=True)
    if result.dph_castka:
        if '21' in text.lower():
            result.dph_sazba = 21
        elif '12' in text.lower():
            result.dph_sazba = 12

    result.dodavatel_nazev = _guess_dodavatel_nazev(text)
    return result


def _find_cislo_faktury(text: str) -> str:
    for line in text.splitlines():
        if _FA_NUM_RE.search(line):
            tokens = re.findall(r'[A-Za-z0-9][\w./\-]{2,}', line)
            for token in reversed(tokens):
                low = token.lower()
                if low in ('faktury', 'faktura', 'invoice', 'doklad', 'č', 'číslo'):
                    continue
                return token[:64]
    m = re.search(r'(?:FA|FV)[\s\-:/]*([A-Za-z0-9][\w./\-]{2,})', text, re.I)
    return m.group(1)[:64] if m else ''


def _find_amount_near(text: str, keywords: tuple[str, ...], *, skip_percent_rates: bool = False) -> str | None:
    lower = text.lower()
    for kw in keywords:
        idx = lower.find(kw)
        if idx < 0:
            continue
        snippet = text[idx:idx + 80]
        matches = list(_AMOUNT_RE.finditer(snippet))
        for m in matches:
            val = _normalize_amount_str(m.group('num'))
            if not val:
                continue
            if skip_percent_rates:
                try:
                    d = Decimal(val)
                    if d in (Decimal('21'), Decimal('12'), Decimal('15')):
                        continue
                except InvalidOperation:
                    pass
            return val
    return None


def _normalize_amount_str(value: str) -> str | None:
    s = (value or '').replace('\u00a0', ' ').replace(' ', '').replace(',', '.')
    try:
        return str(Decimal(s).quantize(Decimal('0.01')))
    except InvalidOperation:
        return None


def _guess_dodavatel_nazev(text: str) -> str:
    for line in text.splitlines()[:12]:
        line = line.strip()
        if len(line) < 3 or len(line) > 120:
            continue
        if _ICO_RE.search(line) or _DIC_RE.search(line):
            continue
        if re.search(r'faktura|invoice|dodavatel|supplier', line, re.I):
            continue
        if re.search(r's\.r\.o\.|s\.r\.o|a\.s\.|spol', line, re.I):
            return line[:200]
    return ''
