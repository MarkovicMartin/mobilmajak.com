"""Stav OCR závislostí pro vyčítání faktur."""
from __future__ import annotations

import os
import shutil
import subprocess

# Gunicorn systemd unit má PATH jen venv/bin – shutil.which by tesseract nenašlo.
_OCR_BIN_FALLBACKS = {
    'tesseract': ('/usr/bin/tesseract', '/usr/local/bin/tesseract'),
    'pdftoppm': ('/usr/bin/pdftoppm', '/usr/local/bin/pdftoppm'),
}


def which_ocr_bin(name: str) -> str | None:
    """Najde tesseract/pdftoppm i když PATH obsahuje jen venv/bin."""
    found = shutil.which(name)
    if found:
        return found
    for path in _OCR_BIN_FALLBACKS.get(name, (f'/usr/bin/{name}',)):
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def configure_pytesseract() -> str | None:
    tess = which_ocr_bin('tesseract')
    if not tess:
        return None
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = tess
    except ImportError:
        pass
    return tess


def check_finance_ocr_deps() -> dict:
    """
    Vrátí dict ready=bool, components={...}, missing=[...], notes=[...].
    """
    missing: list[str] = []
    notes: list[str] = []
    components: dict = {}

    tess = which_ocr_bin('tesseract')
    components['tesseract'] = bool(tess)
    if not tess:
        missing.append('tesseract-ocr')

    langs: list[str] = []
    if tess:
        try:
            out = subprocess.run(
                [tess, '--list-langs'],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            langs = [
                line.strip()
                for line in (out.stdout or out.stderr or '').splitlines()
                if line.strip() and not line.startswith('List')
            ]
        except (OSError, subprocess.SubprocessError, TimeoutError) as exc:
            notes.append(f'tesseract --list-langs: {exc}')
    components['tesseract_langs'] = langs
    if tess and 'ces' not in langs:
        missing.append('tesseract-ocr-ces')
        notes.append('Chybí český jazykový balíček tesseract (ces)')
    if tess and 'eng' not in langs:
        notes.append('Doporučeno tesseract-ocr-eng')

    poppler = which_ocr_bin('pdftoppm')
    components['pdftoppm'] = bool(poppler)
    if not poppler:
        missing.append('poppler-utils')

    try:
        import pytesseract  # noqa: F401
        components['pytesseract'] = True
    except ImportError:
        components['pytesseract'] = False
        missing.append('pytesseract (pip)')

    try:
        from PIL import Image  # noqa: F401
        components['pillow'] = True
    except ImportError:
        components['pillow'] = False
        missing.append('Pillow')

    try:
        from pypdf import PdfReader  # noqa: F401
        components['pypdf'] = True
    except ImportError:
        components['pypdf'] = False
        missing.append('pypdf')

    # OCR skenů potřebuje tesseract + (pdftoppm NEBO embedded images) + pytesseract + pillow
    scan_ready = (
        components.get('tesseract')
        and components.get('pytesseract')
        and components.get('pillow')
        and ('ces' in langs or 'eng' in langs)
    )
    text_ready = bool(components.get('pypdf'))
    ready = text_ready and (scan_ready or True)  # text PDF always; scan optional but flagged

    return {
        'ready': text_ready and scan_ready and components.get('pdftoppm'),
        'text_pdf_ready': text_ready,
        'scan_ocr_ready': bool(scan_ready and components.get('pdftoppm')),
        'components': components,
        'missing': missing,
        'notes': notes,
    }
