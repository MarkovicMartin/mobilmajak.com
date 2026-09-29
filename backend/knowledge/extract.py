"""Vytěžení textu z PDF, DOCX a TXT. Obrázky bez OCR."""
import os
import zipfile
from io import BytesIO
from xml.etree import ElementTree as ET

MAX_EXTRACT_CHARS = 200_000

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg', '.heic'}
TEXT_EXTENSIONS = {'.pdf', '.docx', '.txt'}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | TEXT_EXTENSIONS

_W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def extension_of(filename: str) -> str:
    if not filename or '.' not in filename:
        return ''
    return '.' + filename.rsplit('.', 1)[-1].lower()


def extract_text(data: bytes, filename: str) -> str:
    ext = extension_of(filename)
    if ext in IMAGE_EXTENSIONS or not data:
        return ''
    try:
        if ext == '.txt':
            text = _decode_text(data)
        elif ext == '.pdf':
            text = _pdf_text(data)
        elif ext == '.docx':
            text = _docx_text(data)
        else:
            text = ''
    except Exception:
        text = ''
    text = (text or '').replace('\x00', '').strip()
    return text[:MAX_EXTRACT_CHARS]


def _decode_text(data: bytes) -> str:
    for encoding in ('utf-8-sig', 'utf-8', 'cp1250'):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode('utf-8', errors='replace')


def _pdf_text(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or '')
    return '\n'.join(parts)


def _docx_text(data: bytes) -> str:
    with zipfile.ZipFile(BytesIO(data)) as archive:
        xml_bytes = archive.read('word/document.xml')
    root = ET.fromstring(xml_bytes)
    paragraphs = []
    for paragraph in root.iter(f'{{{_W_NS}}}p'):
        chunks = []
        for node in paragraph.iter(f'{{{_W_NS}}}t'):
            if node.text:
                chunks.append(node.text)
        line = ''.join(chunks).strip()
        if line:
            paragraphs.append(line)
    return '\n'.join(paragraphs)


def read_upload(uploaded) -> bytes:
    data = uploaded.read()
    if hasattr(uploaded, 'seek'):
        uploaded.seek(0)
    return data


def basename(filename: str) -> str:
    return os.path.basename(filename or '')
