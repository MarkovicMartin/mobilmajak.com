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


def _ascii_cz(text: str) -> str:
    """Pro porovnání klíčových slov bez ohledu na diakritiku."""
    for src, dst in (
        ('á', 'a'), ('č', 'c'), ('ď', 'd'), ('é', 'e'), ('ě', 'e'), ('í', 'i'),
        ('ň', 'n'), ('ó', 'o'), ('ř', 'r'), ('š', 's'), ('ť', 't'), ('ú', 'u'),
        ('ů', 'u'), ('ý', 'y'), ('ž', 'z'),
    ):
        text = text.replace(src, dst)
    return text


def _is_vykup(text: str) -> bool:
    """Výkup z kasy / Fio – Úhrada výkupky, bazar, Manuální výdej V26… Výkup."""
    t = _ascii_cz(text)
    if any(k in t for k in ('vykupka', 'uhrada vykupky', 'bazar')):
        return True
    if re.search(r'\bvykup\b', t):
        return True
    return False


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


def _is_mzda_vyplata(text: str) -> bool:
    """DPP, jména adminů, externí výplaty (Daňková, Staštný…)."""
    if _mzdy_admin(text):
        return True
    if re.search(r'\bdpp\b', text):
        return True
    if 'daňková' in text or 'dankova' in text:
        return True
    if 'poradenstv' in text and ('účetnictv' in text or 'ucetnictv' in text):
        return True
    if 'staštn' in text or 'stastny' in text or 'stastný' in text:
        return True
    if 'marketingov' in text and 'sluzb' in text:
        return True
    return False


def _apply_fio_builtin(text: str) -> KategorizaceVysledek | None:
    if 'prevod' in text and 'vlastn' in text:
        return KategorizaceVysledek(
            NakladPolozka.STAV_IGNOROVAT, None, None, True, True, 'fio:prevod_vlastni',
        )
    if _is_mzda_vyplata(text):
        kid = _kat('Mzdy – zaměstnanci')
        if kid:
            return KategorizaceVysledek(
                NakladPolozka.STAV_ZARAZENO, kid, None, False, True, 'fio:mzdy_vyplata',
            )
    if 'facebk' in text or 'facebook' in text:
        kid = _kat('Reklama – firma / online')
        if kid:
            return KategorizaceVysledek(
                NakladPolozka.STAV_ZARAZENO, kid, None, False, True, 'fio:facebook',
            )
    if ('eska posta' in text or 'ceska posta' in text or 'česká pošta' in text) and 'prepravne' in text:
        kid = _kat('Doprava – Zásilkovna / kurýr')
        if kid:
            return KategorizaceVysledek(
                NakladPolozka.STAV_ZARAZENO, kid, None, False, True, 'fio:ceska_posta',
            )
    if 'seznam.cz' in text or ('seznam' in text and ('kredit' in text or 'proklik' in text)):
        kid = _kat('Reklama – firma / online')
        if kid:
            return KategorizaceVysledek(
                NakladPolozka.STAV_ZARAZENO, kid, None, False, True, 'fio:seznam',
            )
    if 'webglobe' in text:
        kid = _kat('IT – hosting / domény')
        if kid:
            return KategorizaceVysledek(
                NakladPolozka.STAV_ZARAZENO, kid, None, False, True, 'fio:hosting',
            )
    if 'divadelni pikola' in text or ('promo' in text and 'olomouc' in text):
        kid = _kat('Spotřeba – občerstvení')
        if kid:
            return KategorizaceVysledek(
                NakladPolozka.STAV_ZARAZENO, kid, None, False, True, 'fio:porada_kava',
            )
    if 'aswo' in text and 'zbozi' in text:
        kid = _kat('Zboží – nákup sklad')
        if kid:
            return KategorizaceVysledek(
                NakladPolozka.STAV_ZARAZENO, kid, None, False, True, 'fio:aswo',
            )
    if 'moneylive' in text or ('ucetni' in text and 'uzaver' in text):
        kid = _kat('Účetnictví a právní')
        if kid:
            return KategorizaceVysledek(
                NakladPolozka.STAV_ZARAZENO, kid, None, False, True, 'fio:ucetnictvi',
            )
    return None


def _is_prevod_pokladny(text: str) -> bool:
    return any(
        p in text
        for p in (
            'převod do pokladny',
            'prevod do pokladny',
            'převod z pokladny',
            'prevod z pokladny',
            'převod mezi pokladnami',
            'prevod mezi pokladnami',
        )
    )


def _is_vklad_na_ucet(text: str) -> bool:
    """Výdej z kasy = vklad na účet / bankomat – ne náklad, páruje se s Fio."""
    return any(
        p in text
        for p in (
            'vklad hotovosti na účet',
            'vklad hotovosti na ucet',
            'převod na účet',
            'prevod na ucet',
            'vklad na účet',
            'vklad na ucet',
        )
    )


def _is_nakup_zbozi(text: str) -> bool:
    """Dodavatel + servis / díly / zboží + č. FA v názvu výdeje."""
    return bool(re.search(r'\b(servis|dily|díly|zbozi|zboží)\b', text, re.I))


def _is_spotreba_prodejny(text: str) -> bool:
    return bool(re.search(r'\bspotřeba\b|\bspotreba\b', text, re.I))


def apply_builtin_rules(row: dict, zdroj: str = '', prodejna_id: int | None = None) -> KategorizaceVysledek | None:
    """Vrátí výsledek nebo None (= žádné vestavěné pravidlo)."""
    text = _text_blob(row)

    if zdroj == NakladPolozka.ZDROJ_FIO:
        fio = _apply_fio_builtin(text)
        if fio:
            return fio

    if zdroj == NakladPolozka.ZDROJ_SYMPLIO_POKLADNA:
        if _is_prevod_pokladny(text):
            return KategorizaceVysledek(
                NakladPolozka.STAV_IGNOROVAT, None, prodejna_id, True, True, 'symplio:prevod_pokladna',
            )
        if _is_vklad_na_ucet(text):
            return KategorizaceVysledek(
                NakladPolozka.STAV_IGNOROVAT, None, prodejna_id, True, True, 'symplio:vklad_na_ucet',
            )
        if text.startswith('storno '):
            return KategorizaceVysledek(
                NakladPolozka.STAV_IGNOROVAT, None, prodejna_id, True, True, 'symplio:storno',
            )
        if _is_vykup(text):
            kid = _ensure_vykup_kategorie()
            return KategorizaceVysledek(
                NakladPolozka.STAV_ZARAZENO, kid, prodejna_id, False, True, 'symplio:vykup',
            )
        if _is_spotreba_prodejny(text):
            kid = _kat('Spotřeba prodejny')
            if kid:
                return KategorizaceVysledek(
                    NakladPolozka.STAV_ZARAZENO, kid, prodejna_id, False, True, 'symplio:spotreba',
                )
        if _is_nakup_zbozi(text):
            kid = _kat('Zboží – nákup sklad')
            if kid:
                return KategorizaceVysledek(
                    NakladPolozka.STAV_ZARAZENO, kid, prodejna_id, False, True, 'symplio:zbozi',
                )

    if _is_vykup(text):
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

    if _is_mzda_vyplata(text):
        kid = _kat('Mzdy – zaměstnanci')
        if kid:
            return KategorizaceVysledek(
                NakladPolozka.STAV_ZARAZENO, kid, None, False, True, 'mzdy_vyplata',
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
            'auto_pravidlo': builtin.pravidlo or '',
        }
    db = apply_categorization_rules(row)
    if db.get('prodejna_id') is None and prodejna_id is not None:
        db['prodejna_id'] = prodejna_id
    if db.get('zarazeno_automaticky'):
        db['auto_pravidlo'] = 'db_pravidlo'
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
    p.auto_pravidlo = (builtin.pravidlo or 'db_pravidlo')[:64]
    from .services import resolve_dph_stav

    p.dph_stav = resolve_dph_stav(p.kategorie_id, p.typ_platby)
    p.save(update_fields=[
        'stav', 'kategorie_id', 'prodejna_id', 'ignorovat',
        'zarazeno_automaticky', 'auto_pravidlo', 'dph_stav',
    ])
    return builtin.pravidlo or 'db_pravidlo'
