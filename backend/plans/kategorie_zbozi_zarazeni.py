"""Rozhodnutí, kam přesunout položku ze stránky Kategorie zboží.

Jisté je jen sklo, kryt nebo telefon, když každý model v názvu sedí
na existující list. Všechno ostatní zůstává nejisté a na seznamu.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent / 'data' / 'kategorie_listy.json'

VETEV = {
    's': 'PŘÍSLUŠENSTVÍ / Skla a fólie',
    'p': 'PŘÍSLUŠENSTVÍ / Pouzdra a kryty',
    'n': 'NOVÉ TELEFONY',
    'u': 'POUŽITÉ TELEFONY',
}

_SUFFIX = frozenset({
    'pro', 'max', 'plus', 'ultra', 'fe', 'mini', 'lite', 'se', 'air',
    'note', 'edge', 'play', 'power', 'stylus',
})
_IGNORUJ_TOKEN = frozenset({'5d', '6d', '9h', '3d', '4g', '5g', '3g', '2g'})
_BRAND_PREFIX = (
    'galaxy', 'iphone', 'xiaomi', 'redmi', 'poco', 'honor', 'vivo',
    'nokia', 'huawei', 'samsung', 'motorola', 'sony', 'xperia',
)
_JINE = (
    'kabel', 'cable', ' otg', 'adapter', 'nabijec', 'charger', 'baterie',
    'battery', 'service pack', 'sim kart', 'predplac', 'taska', 'svitil',
    'remin', 'naramek', 'sluchat', ' stylus', ' s pen', 'drzak', 'popsocket',
    'airpods', ' powerbank', 'redukce', ' pcb',
)
_JINE_SLOVO = frozenset({'watch', 'buds', 'flex', 'otg', 'pcb', 'sim'})
_KRATKY_SMI = frozenset({
    'iphone', 'galaxy', 'redmi', 'poco', 'xiaomi', 'honor', 'vivo', 'pixel', 'xperia', 'xcover',
})
_KRYT = re.compile(r'\b(pouzdro|obal|case|kryt|krytu|cover|book|flip|magsafe)\b|field notes')
_SKLO = re.compile(r'\b(sklo|skla|glass|tempered)\b')
_KAMERA = re.compile(r'(cock|cocek|sklo kamery|ochrana cock)')


def _norm(text: str) -> str:
    text = unicodedata.normalize('NFKD', text or '')
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace('&gt;', ' ').replace('&amp;', ' ')
    text = re.sub(r'\d+[.,]\d+', ' ', text)
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _pokracuje(text: str, za: int) -> bool:
    """Další slovo patří ke stejnému modelu (Pro, Max, ročník), ne k dalšímu modelu za lomítkem."""
    rest = text[za:].strip()
    if not rest:
        return False
    nxt = rest.split(' ', 1)[0]
    if nxt in _SUFFIX:
        return True
    return bool(re.fullmatch(r'(19|20)\d{2}', nxt))


def _obsahuje(text: str, alias: str) -> bool:
    start = 0
    while True:
        i = text.find(alias, start)
        if i < 0:
            return False
        pred = i == 0 or text[i - 1] == ' '
        za = i + len(alias)
        konec = za == len(text) or text[za] == ' '
        if pred and konec and not _pokracuje(text, za):
            return True
        start = i + 1


def _aliasy(nazev: str) -> list[str]:
    parts = [_norm(p) for p in re.split(r'\s*/\s*', nazev or '')]
    parts = [p for p in parts if p]
    if not parts:
        return []
    base = parts[0]
    out = [base]
    base_tokens = base.split()
    digit_at = [i for i, tok in enumerate(base_tokens) if re.search(r'\d', tok)]
    for part in parts[1:]:
        if re.search(r'\d', part) and digit_at:
            out.append(' '.join(base_tokens[:digit_at[-1]] + part.split()))
        elif not re.search(r'\d', part):
            out.append(f'{base} {part}')
        else:
            out.append(part)
    videno = []
    for alias in out:
        if alias not in videno and (re.search(r'\d', alias) or alias.endswith(' air')):
            videno.append(alias)
    return videno


def _model_tokeny(text: str) -> list[str]:
    tokens = text.split()
    skip = set()
    for i, tok in enumerate(tokens):
        if tok == 'gb':
            skip.add(i)
            if i > 0:
                skip.add(i - 1)
            if i > 1 and tokens[i - 2].isdigit():
                skip.add(i - 2)
        if re.fullmatch(r'\d+(gb|mm|w)', tok):
            skip.add(i)
        if tok.isdigit() and i + 2 < len(tokens) and tokens[i + 1] == 'v' and tokens[i + 2].isdigit():
            skip.add(i)
            skip.add(i + 2)
    out = []
    for i, tok in enumerate(tokens):
        if i in skip or tok in _IGNORUJ_TOKEN:
            continue
        if re.fullmatch(r'v\d+', tok):
            continue
        if tok == 'air' and i > 0 and tokens[i - 1] == 'iphone':
            out.append(tok)
        elif re.search(r'\d', tok):
            out.append(tok)
    return out


def _druh(text: str, kod: str) -> str | None:
    padded = f' {text} '
    if any(k in padded for k in _JINE):
        return None
    if any(re.search(rf'\b{w}\b', text) for w in _JINE_SLOVO):
        return None
    kamera = bool(_KAMERA.search(text))
    sklo = bool(_SKLO.search(text)) or kamera
    kryt = bool(_KRYT.search(text)) and not kamera
    if sklo and kryt:
        return None
    if sklo:
        return 's'
    if kryt:
        return 'p'
    if (kod or '').upper().startswith('V') or 'pouzit' in text:
        return 'u'
    if re.search(r'\d+\s*gb', text):
        return 'n'
    return None


def _nacti(katalog) -> list[dict]:
    # Stejný název ve větvi bývá rodič i list. Bere se novější id.
    nejnovejsi = {}
    for row in katalog or []:
        key = (row.get('v'), _norm(row.get('n') or ''))
        if key not in nejnovejsi or int(row['id']) > int(nejnovejsi[key]['id']):
            nejnovejsi[key] = row
    listy = []
    for row in nejnovejsi.values():
        nazev = row.get('n') or ''
        aliasy = []
        for alias in _aliasy(nazev):
            aliasy.append(alias)
            for brand in _BRAND_PREFIX:
                if alias.startswith(brand + ' '):
                    zbytek = alias[len(brand) + 1:]
                    slova = zbytek.split()
                    if (
                        len(zbytek) >= 3
                        and re.search(r'\d', zbytek)
                        and (re.match(r'^[a-z]\d', zbytek) or any(w in _KRATKY_SMI for w in slova))
                    ):
                        aliasy.append(zbytek)
                    break
        listy.append({
            'id': int(row['id']),
            'v': row['v'],
            'n': nazev,
            'aliasy': aliasy,
        })
    return listy


def _nejlepsi_alias(text: str, leaf: dict) -> str:
    """Celý název listu, nebo zkrácený model, když název značku už jednou řekl."""
    hits = [a for a in leaf['aliasy'] if _obsahuje(text, a)]
    for alias in leaf['aliasy']:
        for brand in _BRAND_PREFIX:
            if not alias.startswith(brand + ' '):
                continue
            if f' {brand} ' not in f' {text} ':
                break
            tail = alias[len(brand) + 1:]
            if ' ' in tail and _obsahuje(text, tail):
                hits.append(tail)
            break
    return max(hits, key=len) if hits else ''


def _jen_zacatek(text: str, span: str, nalezene, leaf) -> bool:
    for _delka, dalsi in nalezene:
        if dalsi is leaf:
            continue
        for jiny in dalsi['aliasy']:
            if not jiny.startswith(span + ' ') or not _obsahuje(text, jiny):
                continue
            extra = jiny[len(span):]
            start = 0
            samostatne = False
            while True:
                i = text.find(span, start)
                if i < 0:
                    break
                pred = i == 0 or text[i - 1] == ' '
                za = i + len(span)
                if pred and (za == len(text) or text[za] == ' ') and not text[za:].startswith(extra):
                    samostatne = True
                    break
                start = i + 1
            if not samostatne:
                return True
    return False


def rozhodni(nazev: str, kod: str = '', katalog=None) -> dict:
    text = _norm(nazev)
    druh = _druh(text, kod)
    if not druh:
        return {'stav': 'nejiste', 'duvod': 'nerozpoznano', 'kategorie': []}
    tokeny = _model_tokeny(text)
    if not tokeny:
        return {'stav': 'nejiste', 'duvod': 'chybi_model', 'kategorie': []}

    nalezene = []
    for leaf in _nacti(katalog):
        if leaf['v'] != druh:
            continue
        span = _nejlepsi_alias(text, leaf)
        if span:
            nalezene.append((len(span), leaf))
    if not nalezene:
        return {'stav': 'nejiste', 'duvod': 'chybi_list', 'kategorie': []}

    # „iPhone 18 Pro“ u názvu „18 Pro Max“ je jen začátek delšího listu.
    # U „18 Pro / 18 Pro Max“ zůstávají oba.
    nejdelsi = []
    for _delka, leaf in nalezene:
        span = _nejlepsi_alias(text, leaf)
        if _jen_zacatek(text, span, nalezene, leaf):
            continue
        nejdelsi.append(leaf)

    podle_id = {}
    for leaf in nejdelsi:
        podle_id[leaf['id']] = leaf
    kandidati = list(podle_id.values())
    vybrane = []
    for leaf in kandidati:
        span = _nejlepsi_alias(text, leaf)
        sirsi_kos = any(
            other is not leaf
            and _nejlepsi_alias(text, other) == span
            and len(other['aliasy']) < len(leaf['aliasy'])
            for other in kandidati
        )
        if not sirsi_kos:
            vybrane.append(leaf)

    pokryto = set()
    for leaf in vybrane:
        spojen = ' ' + ' '.join(leaf['aliasy']) + ' '
        for tok in tokeny:
            if f' {tok} ' in spojen:
                pokryto.add(tok)
    chybi = [tok for tok in tokeny if tok not in pokryto]
    if chybi:
        return {
            'stav': 'nejiste',
            'duvod': 'nepokryty_model',
            'kategorie': [{'id': leaf['id'], 'nazev': leaf['n']} for leaf in vybrane],
            'chybi': chybi,
        }
    return {
        'stav': 'jiste',
        'duvod': druh,
        'vetev': VETEV[druh],
        'kategorie': [{'id': leaf['id'], 'nazev': leaf['n']} for leaf in vybrane],
    }


def nacti_katalog(path: Path | None = None) -> list[dict]:
    raw = json.loads((path or DATA_PATH).read_text(encoding='utf-8'))
    return [{'id': int(r[0]), 'v': r[1], 'n': r[2]} for r in raw]
