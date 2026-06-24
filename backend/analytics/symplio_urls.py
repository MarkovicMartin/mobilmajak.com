"""Odkazy do Symplio adminu (PDF detail dokladu)."""
from __future__ import annotations

SYMPLIO_ADMIN = 'https://www.mobilmajak.cz/admin'


def symplio_doklad_pdf_url(doklad: str | None) -> str | None:
    if not doklad:
        return None
    text = str(doklad).strip()
    if not text:
        return None
    return f'{SYMPLIO_ADMIN}/doklad-{text}.pdf?akce=open'


def symplio_sklad_doklady_day_url(datum_iso: str | None) -> str | None:
    if not datum_iso:
        return None
    return (
        f'{SYMPLIO_ADMIN}/sklady/doklady'
        f'?type%5B0%5D=sklad-vydejka'
        f'&date_range%5Bfrom%5D={datum_iso}'
        f'&date_range%5Bto%5D={datum_iso}'
    )


def symplio_prodej_polozky_day_url(datum_iso: str | None) -> str | None:
    if not datum_iso:
        return None
    return (
        f'{SYMPLIO_ADMIN}/doklady/polozky'
        f'?date_range%5Bfrom%5D={datum_iso}'
        f'&date_range%5Bto%5D={datum_iso}'
    )
