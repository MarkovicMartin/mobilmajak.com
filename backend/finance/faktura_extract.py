"""Extrakce polí z PDF faktury (ISDOC + textová vrstva + OCR skenu)."""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path

logger = logging.getLogger(__name__)

_AMOUNT_RE = re.compile(
    r'(?P<num>\d{1,3}(?:[ \u00a0]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)',
)
_ICO_RE = re.compile(r'\bI[ČC]O\s*[:.]?\s*(?P<ico>\d{8})\b', re.I)
_DIC_RE = re.compile(
    r'\bDI[ČC]\b[^\n]{0,48}?(?P<dic>CZ\d{8,12})\b',
    re.I,
)
_FA_NUM_RE = re.compile(
    r'(?:č[ií]slo\s+)?faktury|faktura\s*č\.?|invoice\s*no\.?|doklad\s*č\.?|'
    r'č[ií]slo\s+dokladu|document\s*no\.?|'
    r'faktura\s*/\s*rechnung|rechnung\s*/\s*faktura',
    re.I,
)
_VS_RE = re.compile(
    r'(?:variabiln[iíl1]\s*symbol|var\.?\s*symbol|var\.?\s*sym\.?|\bVS\b|'
    r'variable\s*symbol|payment\s*reference)\s*[:.\-]?\s*'
    r'(?P<vs>[A-Za-z0-9][\w./\-]{1,31})',
    re.I | re.S,
)
_VS_LABEL_RE = re.compile(
    r'variabiln|var\.?\s*sym|\bVS\b|variable\s*symbol|payment\s*ref',
    re.I,
)

# Minimální délka textové vrstvy – kratší → zkus OCR (typicky sken s „prázdným“ textem).
_WEAK_TEXT_LEN = 80


@dataclass
class FakturaExtracted:
    dodavatel_nazev: str = ''
    dodavatel_ico: str = ''
    dodavatel_dic: str = ''
    cislo_faktury: str = ''
    vs: str = ''
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

    def field_score(self) -> int:
        score = 0
        if self.vs:
            score += 3
        if self.castka_celkem:
            score += 2
        if self.castka_bez_dph:
            score += 1
        if self.dph_castka:
            score += 1
        if self.cislo_faktury:
            score += 1
        if self.dodavatel_ico or self.dodavatel_nazev:
            score += 1
        return score


def extract_faktura_from_file(path: Path) -> tuple[FakturaExtracted, str, dict]:
    """
    Vrátí (extrahovaná pole, raw_text pro debug, metadata).
    metadata.method: isdoc|pdf_text|pdf_ocr|pdf_text+ocr|image_ocr|none
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
    text_parsed = _parse_text_fields(text) if text.strip() else FakturaExtracted()
    if text.strip():
        text_parsed.zdroj = 'pdf_text'
        text_parsed.raw_text_len = len(text)

    need_ocr = (
        not text.strip()
        or len(text.strip()) < _WEAK_TEXT_LEN
        or text_parsed.field_score() < 3
    )

    if not need_ocr:
        return text_parsed, text[:8000], {'method': 'pdf_text'}

    ocr_text, ocr_meta = _try_pdf_page_ocr(path)
    if not ocr_text.strip():
        if text.strip() and text_parsed.field_score() > 0:
            return text_parsed, text[:8000], {'method': 'pdf_text', **ocr_meta}
        result = FakturaExtracted(
            zdroj='pdf_text',
            raw_text_len=len(text),
            chyby=[
                'PDF je sken bez použitelné textové vrstvy – OCR nevyčetlo údaje. '
                'Doplňte VS a částky ručně (pak půjde párovat s Fio).',
            ],
        )
        if ocr_meta.get('ocr'):
            result.chyby.append(f"OCR stav: {ocr_meta['ocr']}")
        return result, '', {'method': 'pdf_text_empty', **ocr_meta}

    ocr_parsed = _parse_text_fields(ocr_text)
    ocr_parsed.zdroj = 'pdf_ocr'
    ocr_parsed.raw_text_len = len(ocr_text)

    if text.strip() and text_parsed.field_score() > 0:
        merged = _merge_extracted(text_parsed, ocr_parsed)
        merged.zdroj = 'pdf_text+ocr'
        merged.raw_text_len = max(len(text), len(ocr_text))
        preview = (text + '\n---OCR---\n' + ocr_text)[:8000]
        return merged, preview, {'method': 'pdf_text+ocr', **ocr_meta}

    return ocr_parsed, ocr_text[:8000], {'method': 'pdf_ocr', **ocr_meta}


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

    if not shutil.which('tesseract'):
        result = FakturaExtracted(
            zdroj='image_ocr',
            chyby=['Na serveru chybí tesseract – spusťte scripts/install-finance-ocr.sh'],
        )
        return result, '', {'method': 'image_ocr_unavailable'}

    try:
        img = _prepare_ocr_image(Image.open(path))
        text = _tesseract_image(img)
    except Exception as exc:
        result = FakturaExtracted(zdroj='image_ocr', chyby=[f'OCR selhalo: {exc}'])
        return result, '', {'method': 'image_ocr_error'}

    parsed = _parse_text_fields(text)
    parsed.zdroj = 'image_ocr'
    parsed.raw_text_len = len(text)
    if parsed.field_score() == 0:
        parsed.chyby.append('OCR text nevyčetl VS ani částky – doplňte ručně.')
    return parsed, text[:8000], {'method': 'image_ocr'}


def _pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ''

    try:
        reader = PdfReader(str(path))
    except Exception:
        return ''
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or '')
    return '\n'.join(parts)


def _try_pdf_page_ocr(path: Path) -> tuple[str, dict]:
    """OCR skenu: pdftoppm (300 DPI) + tesseract, jinak vložené obrázky z PDF."""
    try:
        import pytesseract  # noqa: F401
        from PIL import Image
    except ImportError:
        return '', {'ocr': 'pytesseract_unavailable'}

    if not shutil.which('tesseract'):
        return '', {'ocr': 'tesseract_unavailable'}

    images: list = []
    meta: dict = {}

    if shutil.which('pdftoppm'):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                prefix = Path(tmp) / 'page'
                subprocess.run(
                    [
                        'pdftoppm', '-png', '-r', '300',
                        '-f', '1', '-l', '2',
                        str(path), str(prefix),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=90,
                )
                for img_path in sorted(Path(tmp).glob('page*.png')):
                    images.append(_prepare_ocr_image(Image.open(img_path)))
            meta['ocr'] = 'pdftoppm_300'
        except (subprocess.SubprocessError, OSError, TimeoutError) as exc:
            logger.info('pdftoppm OCR skipped: %s', exc)
            meta['ocr'] = f'pdftoppm_error:{exc}'

    if not images:
        raw_imgs = _pdf_embedded_images(path)
        images = [_prepare_ocr_image(img) for img in raw_imgs]
        if images:
            meta['ocr'] = 'embedded_images'

    if not images:
        return '', {**meta, 'ocr': meta.get('ocr') or 'no_images'}

    parts = []
    for img in images[:2]:
        try:
            parts.append(_tesseract_image(img))
        except Exception as exc:
            logger.info('tesseract page failed: %s', exc)
    return '\n'.join(parts), meta


def _prepare_ocr_image(img):
    """Grayscale + upscale + autocontrast pro lepší tesseract."""
    from PIL import Image, ImageOps

    if img.mode not in ('L', 'RGB', 'RGBA'):
        img = img.convert('RGB')
    img = img.convert('L')
    w, h = img.size
    if min(w, h) < 1400:
        scale = 1400 / float(min(w, h))
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    img = ImageOps.autocontrast(img, cutoff=1)
    return img


def _tesseract_image(img) -> str:
    import pytesseract

    langs = _tesseract_langs()
    config = '--oem 3 --psm 6'
    try:
        return pytesseract.image_to_string(img, lang=langs, config=config) or ''
    except Exception:
        return pytesseract.image_to_string(img, lang='eng', config=config) or ''


def _tesseract_langs() -> str:
    """Preferuj ces+eng, fallback eng."""
    try:
        import pytesseract
        available = set(pytesseract.get_languages(config=''))
    except Exception:
        available = set()
    if 'ces' in available and 'eng' in available:
        return 'ces+eng'
    if 'ces' in available:
        return 'ces'
    return 'eng'


def _pdf_embedded_images(path: Path) -> list:
    try:
        from pypdf import PdfReader
        from PIL import Image
    except ImportError:
        return []

    out = []
    try:
        reader = PdfReader(str(path))
    except Exception:
        return []

    for page in reader.pages[:2]:
        try:
            resources = page.get('/Resources') or {}
            xobject = resources.get('/XObject')
            if xobject is None:
                continue
            xobject = xobject.get_object()
            for key in xobject:
                obj = xobject[key].get_object()
                if obj.get('/Subtype') != '/Image':
                    continue
                data = obj.get_data()
                width = int(obj.get('/Width') or 0)
                height = int(obj.get('/Height') or 0)
                if width < 200 or height < 200:
                    continue
                color = obj.get('/ColorSpace')
                filt = obj.get('/Filter')
                try:
                    if filt == '/DCTDecode' or (isinstance(filt, list) and '/DCTDecode' in filt):
                        out.append(Image.open(BytesIO(data)))
                    elif color in ('/DeviceRGB', '/DeviceGray') and width and height:
                        mode = 'RGB' if color == '/DeviceRGB' else 'L'
                        out.append(Image.frombytes(mode, (width, height), data))
                except Exception:
                    continue
        except Exception:
            continue
    return out


def _merge_extracted(primary: FakturaExtracted, secondary: FakturaExtracted) -> FakturaExtracted:
    """Doplní prázdná pole z OCR (secondary) do textové extrakce (primary)."""
    out = FakturaExtracted()
    for field_name in (
        'dodavatel_nazev', 'dodavatel_ico', 'dodavatel_dic',
        'cislo_faktury', 'vs', 'datum_vystaveni',
    ):
        setattr(out, field_name, getattr(primary, field_name) or getattr(secondary, field_name) or '')
    for field_name in ('castka_bez_dph', 'dph_castka', 'castka_celkem', 'dph_sazba'):
        val = getattr(primary, field_name)
        if val in (None, ''):
            val = getattr(secondary, field_name)
        setattr(out, field_name, val)
    out.chyby = list(primary.chyby) + [c for c in secondary.chyby if c not in primary.chyby]
    return out


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
    result.vs = find_text(
        'VariableSymbol', 'VariableSymbolID', 'PaymentID', 'PaymentReference',
    )[:32]
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
    if not result.vs and result.cislo_faktury:
        digits = re.sub(r'\D', '', result.cislo_faktury)
        if len(digits) >= 4:
            result.vs = digits[:32]
    return result if result.cislo_faktury or result.castka_celkem else None


def _normalize_ocr_noise(text: str) -> str:
    """Lehké opravy častých OCR chyb u českých FA."""
    t = text.replace('\u00a0', ' ')
    # „VariabiIni“ / „Variabiľní“ → variabilní (pro label match)
    t = re.sub(r'variabi[l1ií]n[ií1l]', 'variabilní', t, flags=re.I)
    t = re.sub(r'\bce[l1]kem\b', 'celkem', t, flags=re.I)
    t = re.sub(r'\b[uú]hrad[eě]\b', 'úhradě', t, flags=re.I)
    return t


def _parse_text_fields(text: str) -> FakturaExtracted:
    text = _normalize_ocr_noise(text or '')
    result = FakturaExtracted()
    ico = _ICO_RE.search(text)
    if ico:
        result.dodavatel_ico = ico.group('ico')
    dic = _DIC_RE.search(text)
    if dic:
        result.dodavatel_dic = dic.group('dic')

    result.cislo_faktury = _find_cislo_faktury(text)
    result.vs = _find_vs(text)
    result.castka_celkem = _find_amount_near(text, (
        'celkem k úhradě', 'celkem k uhrade', 'k úhradě', 'k uhrade',
        'celkem včetně dph', 'celkem vč. dph', 'celkem vč dph',
        'amount due', 'total amount', 'grand total',
        'celkem', 'total',
    ), prefer_largest=True)
    result.castka_bez_dph = _find_amount_near(text, (
        'základ daně', 'zaklad dane', 'základ DPH', 'zaklad dph',
        'základ', 'zaklad', 'bez dph', 'bez DPH', 'tax base', 'net amount',
    ))
    result.dph_castka = _find_amount_near(text, (
        'celkem dph', 'celkem DPH', 'výše dph', 'vyse dph',
        'dph 21%', 'dph 12%', 'dph 21', 'dph 12',
        'vat amount', 'mwst',
        'dph', 'daň', 'vat',
    ), skip_percent_rates=True)
    if result.dph_castka:
        low = text.lower()
        if re.search(r'\b21\s*%', low) or 'dph 21' in low:
            result.dph_sazba = 21
        elif re.search(r'\b12\s*%', low) or 'dph 12' in low:
            result.dph_sazba = 12
        elif re.search(r'\b15\s*%', low):
            result.dph_sazba = 15

    result.dodavatel_nazev = _guess_dodavatel_nazev(text)
    if not result.vs and result.cislo_faktury:
        digits = re.sub(r'\D', '', result.cislo_faktury)
        if len(digits) >= 4:
            result.vs = digits[:32]

    # Dopočet DPH / celkem ze zbylých dvou částek (spolehlivější než OCR u sloupců)
    try:
        bez = Decimal(result.castka_bez_dph) if result.castka_bez_dph else None
        dph = Decimal(result.dph_castka) if result.dph_castka else None
        celk = Decimal(result.castka_celkem) if result.castka_celkem else None
        if bez is not None and celk is not None:
            computed_dph = (celk - bez).quantize(Decimal('0.01'))
            if computed_dph > 0 and (
                dph is None or dph == bez or abs(dph - computed_dph) > Decimal('1.00')
            ):
                result.dph_castka = str(computed_dph)
                dph = computed_dph
        if not result.castka_celkem and bez is not None and dph is not None:
            result.castka_celkem = str((bez + dph).quantize(Decimal('0.01')))
    except InvalidOperation:
        pass
    return result


def _find_cislo_faktury(text: str) -> str:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not _FA_NUM_RE.search(line):
            continue
        candidates = re.findall(r'[A-Za-z0-9][\w./\-]{2,}', line)
        skip = {
            'faktury', 'faktura', 'invoice', 'doklad', 'č', 'číslo', 'cislo',
            'document', 'rechnung', 'lieferant', 'zahlungsreferenz',
            'dodavatel', 'odběratel', 'supplier', 'empfänger', 'empfaenger',
        }
        for token in reversed(candidates):
            if token.lower() in skip:
                continue
            # Preferuj číselné / alfanumerické doklady, ne úryvky slov
            if re.fullmatch(r'\d{4,}', token) or (
                re.search(r'\d', token) and len(token) >= 4
            ):
                return token[:64]
        for j in range(i + 1, min(i + 3, len(lines))):
            nums = re.findall(r'\b(\d{4,16})\b', lines[j])
            if nums:
                return nums[0][:64]
        # Bez čísla na řádku – zkus další výskyt labelu (např. „Faktura / Rechnung“ bez čísla)
    # FA/FV/VF jako samostatný kód (ne začátek slova „Faktura“)
    m = re.search(r'\b(?:FA|FV|VF)[\s\-:/]+([A-Za-z0-9][\w./\-]{2,})', text, re.I)
    return m.group(1)[:64] if m else ''


def _find_vs(text: str) -> str:
    m = _VS_RE.search(text or '')
    if m:
        vs = m.group('vs').strip(' .:/-')
        low = vs.lower()
        if low not in ('symbol', 'sym', 'vs', 'č', 'cislo', 'číslo', 'zahlungsreferenz'):
            digits = re.sub(r'\D', '', vs)
            if len(digits) >= 4:
                return digits[:32]
            return vs[:32]
    lines = (text or '').splitlines()
    for i, line in enumerate(lines):
        if not _VS_LABEL_RE.search(line):
            continue
        for j in range(i, min(i + 4, len(lines))):
            nums = re.findall(r'\b(\d{4,16})\b', lines[j])
            if nums:
                return nums[-1][:32]
    return ''


def _find_amount_near(
    text: str,
    keywords: tuple[str, ...],
    *,
    skip_percent_rates: bool = False,
    prefer_largest: bool = False,
) -> str | None:
    lower = text.lower()
    for kw in keywords:
        start = 0
        while True:
            idx = lower.find(kw, start)
            if idx < 0:
                break
            end = min(len(text), idx + 160)
            line_end = text.find('\n', end)
            if line_end > 0:
                snippet = text[idx:min(len(text), line_end + 80)]
            else:
                snippet = text[idx:end]
            values: list[Decimal] = []
            for m in _AMOUNT_RE.finditer(snippet):
                val = _normalize_amount_str(m.group('num'))
                if not val:
                    continue
                try:
                    d = Decimal(val)
                except InvalidOperation:
                    continue
                if skip_percent_rates and d in (
                    Decimal('21'), Decimal('12'), Decimal('15'), Decimal('10'),
                ):
                    continue
                # Datum / měsíc / pořadí (např. „období 7/2026“) u DPH sloupců
                if skip_percent_rates and d == d.to_integral_value() and d < Decimal('50'):
                    continue
                if d < Decimal('1'):
                    continue
                values.append(d)
            if values:
                chosen = max(values) if prefer_largest else values[0]
                return str(chosen.quantize(Decimal('0.01')))
            start = idx + len(kw)
    return None


def _normalize_amount_str(value: str) -> str | None:
    s = (value or '').replace('\u00a0', ' ').replace(' ', '').replace(',', '.')
    # OCR: 1.210.00 → 1210.00 (tisíce tečkami)
    if s.count('.') > 1:
        parts = s.split('.')
        s = ''.join(parts[:-1]) + '.' + parts[-1]
    try:
        return str(Decimal(s).quantize(Decimal('0.01')))
    except InvalidOperation:
        return None


def _guess_dodavatel_nazev(text: str) -> str:
    for line in text.splitlines()[:15]:
        line = line.strip()
        if len(line) < 3 or len(line) > 120:
            continue
        if _ICO_RE.search(line) or _DIC_RE.search(line):
            continue
        if re.search(r'faktura|invoice|dodavatel|supplier|odběratel|lieferant', line, re.I):
            continue
        if re.search(r's\.r\.o\.|s\.r\.o|a\.s\.|v\.o\.s\.|spol', line, re.I):
            return line[:200]
    return ''
