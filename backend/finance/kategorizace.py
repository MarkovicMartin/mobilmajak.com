"""Vestavěná kategorizace Fio + Symplio pokladna (doplňuje DB pravidla)."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .models import NakladKategorie, NakladPolozka

# Zásilkovna suffix v poznámce: „prepravne - Glo“
_ZASILKOVNA_SUFFIX = {
    'glo': 1,
    'ste': 6,
    'sen': 2,
    'vse': 5,
    'zl': 3,
    'zli': 3,
    'pre': 4,
    'prer': 4,
}

_NAJEM_KEYWORDS = (
    ('globus', 1, 'Nájem – Globus (GL)'),
    ('senimo', 2, 'Nájem – Senimo (SEN)'),
    ('galerie prerov', 4, 'Nájem – Přerov (PŘE)'),
    ('prerov', 4, 'Nájem – Přerov (PŘE)'),
    ('vset', 5, 'Nájem – Vsetín (VSE)'),
    ('tesco', 3, 'Nájem – Zlín (ZL)'),
    ('kaufland', 3, 'Nájem – Zlín (ZL)'),
    ('zlin', 3, 'Nájem – Zlín (ZL)'),
    ('sternberk', 6, 'Nájem – Šternberk (ŠT)'),
)


@dataclass(frozen=True)
class KategorizaceVysledek:
    stav: str
    kategorie_id: int | None
    prodejna_id: int | None
    ignorovat: bool
    zarazeno_automaticky: bool
    pravidlo: str = ''


def _text_blob(row: dict) -> str:
    return f'{row.get("popis") or ""} {row.get("zprava") or ""}'.strip().lower()


def _kat(nazev: str) -> int | None:
    return NakladKategorie.objects.filter(nazev=nazev, aktivni=True).values_list('id', flat=True).first()


def _ensure_vykup_kategorie() -> int | None:
    existing = _kat('Výkup')
    if existing:
        return existing
    parent = NakladKategorie.objects.filter(nazev='Zboží / sklad').first()
    row, _ = NakladKategorie.objects.get_or_create(
        nazev='Výkup',
        defaults={
            'poradi': 903,
            'typ_dph': NakladKategorie.TYP_DPH_BEZ,
            'parent': parent,
            'aktivni': True,
        },
    )
    return row.id


def _zasilkovna_prodejna(text: str) -> int | None:
    m = re.search(r'prepravne\s*-\s*(\w+)', text, re.I)
    if not m:
        return None
    return _ZASILKOVNA_SUFFIX.get(m.group(1).lower()[:4])


def _najem_match(text: str) -> tuple[int | None, str | None]:
    for needle, prodejna_id, kat_nazev in _NAJEM_KEYWORDS:
        if needle in text:
            return prodejna_id, kat_nazev
    if 'najem' in text or 'nájem' in text:
        return None, 'Nájem – sklad / kancelář'
    return None, None


def _mzdy_admin(text: str) -> bool:
    needles = (
        'martin markovic', 'radek bulandra', 'jan bajtek', 'michaela smrck',
        'ing. jan bajtek',
    )
    return any(n in text for n in needles)


def apply_builtin_rules(row: dict, zdroj: str = '', prodejna_id: int | None = None) -> KategorizaceVysledek | None:
    """Vrátí výsledek nebo None (= žádné vestavěné pravidlo)."""
    text = _text_blob(row)

    if zdroj == NakladPolozka.ZDROJ_FIO:
        if 'prevod' in text and 'vlastn' in text:
            return KategorizaceVysledek(
                NakladPolozka.STAV_IGNOROVAT, None, None, True, True, 'fio:prevod_vlastni',
            )

    if zdroj == NakladPolozka.ZDROJ_SYMPLIO_POKLADNA:
        if 'převod do pokladny' in text or 'prevod do pokladny' in text:
            return KategorizaceVysledek(
                NakladPolozka.STAV_IGNOROVAT, None, prodejna_id, True, True, 'symplio:prevod_pokladna',
            )
        if text.startswith('storno '):
            return KategorizaceVysledek(
                NakladPolozka.STAV_IGNOROVAT, None, prodejna_id, True, True, 'symplio:storno',
            )

    if any(k in text for k in ('vykupka', 'vykup', 'úhrada výkupky', 'uhrada vykupky', 'bazar')):
        kid = _ensure_vykup_kategorie()
        return KategorizaceVysledek(
            NakladPolozka.STAV_ZARAZENO, kid, prodejna_id, False, True, 'vykup',
        )

    if 's e t o s' in text or 'setos' in text:
        kid = _kat('Zboží – nákup sklad')
        if kid:
            return KategorizaceVysledek(
                NakladPolozka.STAV_ZARAZENO, kid, None, False, True, 'setos',
            )

    if 'zasilkovna' in text or 'zásilkovna' in text:
        kid = _kat('Doprava – Zásilkovna / kurýr')
        if kid:
            return KategorizaceVysledek(
                NakladPolozka.STAV_ZARAZENO, kid, _zasilkovna_prodejna(text), False, True, 'zasilkovna',
            )

    if 'ossz' in text or 'socia' in text and 'pojist' in text:
        kid = _kat('Odvody – sociální')
        if kid:
            return KategorizaceVysledek(
                NakladPolozka.STAV_ZARAZENO, kid, None, False, True, 'ossz',
            )

    if re.search(r'\bhpp\b', text) or 'zdravotn' in text and 'pojist' in text:
        kid = _kat('Odvody – zdravotní')
        if kid:
            return KategorizaceVysledek(
                NakladPolozka.STAV_ZARAZENO, kid, None, False, True, 'hpp',
            )

    if _mzdy_admin(text):
        kid = _kat('Mzdy – zaměstnanci')
        if kid:
            return KategorizaceVysledek(
                NakladPolozka.STAV_ZARAZENO, kid, None, False, True, 'mzdy_admin',
            )

    if 'codaruina' in text and ('splátka' in text or 'splatka' in text or 'úvěr' in text or 'uver' in text):
        kid = _kat('Leasing – technika') or _kat('Ostatní')
        if kid:
            return KategorizaceVysledek(
                NakladPolozka.STAV_ZARAZENO, kid, None, False, True, 'codaruina_splatka',
            )

    najem_prodejna, najem_kat = _najem_match(text)
    if najem_kat:
        kid = _kat(najem_kat)
        if kid:
            return KategorizaceVysledek(
                NakladPolozka.STAV_ZARAZENO, kid, najem_prodejna, False, True, 'najem',
            )

    return None


def apply_all_rules(row: dict, zdroj: str = '', prodejna_id: int | None = None) -> dict:
    """Stejné rozhraní jako apply_categorization_rules – builtin + DB pravidla."""
    from .services import apply_categorization_rules

    builtin = apply_builtin_rules(row, zdroj=zdroj, prodejna_id=prodejna_id)
    if builtin:
        return {
            'stav': builtin.stav,
            'kategorie_id': builtin.kategorie_id,
            'prodejna_id': builtin.prodejna_id if builtin.prodejna_id is not None else prodejna_id,
            'ignorovat': builtin.ignorovat,
            'zarazeno_automaticky': builtin.zarazeno_automaticky,
        }
    db = apply_categorization_rules(row)
    if db.get('prodejna_id') is None and prodejna_id is not None:
        db['prodejna_id'] = prodejna_id
    return db


def polozka_as_row(p: NakladPolozka) -> dict:
    return {
        'popis': p.popis,
        'zprava': p.zprava,
        'protiucet': p.protiucet,
        'vs': p.vs,
        'castka': p.castka,
    }


def apply_rules_to_polozka(p: NakladPolozka, dry_run: bool = False) -> str | None:
    """Zařadí nezařazenou položku. Vrátí název pravidla nebo None."""
    if p.stav not in (NakladPolozka.STAV_NEZARAZENO,):
        return None
    row = polozka_as_row(p)
    builtin = apply_builtin_rules(row, zdroj=p.zdroj, prodejna_id=p.prodejna_id)
    if not builtin:
        from .services import apply_categorization_rules

        db = apply_categorization_rules(row)
        if db['stav'] == NakladPolozka.STAV_NEZARAZENO:
            return None
        builtin = KategorizaceVysledek(
            db['stav'], db['kategorie_id'], db['prodejna_id'], db['ignorovat'],
            db['zarazeno_automaticky'], 'db_pravidlo',
        )

    if dry_run:
        return builtin.pravidlo or 'db_pravidlo'

    p.stav = builtin.stav
    p.kategorie_id = builtin.kategorie_id
    p.prodejna_id = builtin.prodejna_id if builtin.prodejna_id is not None else p.prodejna_id
    p.ignorovat = builtin.ignorovat
    p.zarazeno_automaticky = True
    from .services import resolve_dph_stav

    p.dph_stav = resolve_dph_stav(p.kategorie_id, p.typ_platby)
    p.save(update_fields=[
        'stav', 'kategorie_id', 'prodejna_id', 'ignorovat',
        'zarazeno_automaticky', 'dph_stav',
    ])
    return builtin.pravidlo or 'db_pravidlo'
