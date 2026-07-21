"""Sdílená logika pro Mastersheet přihlášení (bez hesel v git/JSON)."""

import json
import re
from collections import defaultdict
from pathlib import Path

import openpyxl

DEFAULT_EXCEL = Path.home() / 'Downloads' / 'Mastersheet - prodejny.xlsx'
LOGINS_JSON = Path(__file__).resolve().parents[2] / 'docs' / 'mastersheet-prihlasovaci-loginy.json'

PLACEHOLDER_PASSWORD = 'DOPLNIT_RUCNE'

# URL vložené přímo do názvu služby (Mastersheet často dává celý odkaz do sloupce).
_URL_IN_TEXT = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)
# Doména / e-shop v názvu: alza.cz, www.sammobile.com, Hurtel.pl
_DOMAIN_LIKE = re.compile(
    r'^(?:www\.)?'
    r'[a-z0-9](?:[a-z0-9\-]*[a-z0-9])?'
    r'(?:\.[a-z0-9](?:[a-z0-9\-]*[a-z0-9])?)+'
    r'/?$',
    re.IGNORECASE,
)

# Známí dodavatelé bez domény v názvu → e-shop / B2B portál
SERVICE_URL_ALIASES = {
    'adart': 'https://www.adart.cz/',
    'alza': 'https://www.alza.cz/',
    'alza.cz': 'https://www.alza.cz/',
    'aukro': 'https://aukro.cz/',
    'aukro.cz': 'https://aukro.cz/',
    'bakr': 'https://www.bakr.cz/',
    'cpa': 'https://www.cpa.cz/',
    'c.p.a.': 'https://www.cpa.cz/',
    'datart': 'https://www.datart.cz/',
    'dpd': 'https://www.dpd.com/cz/',
    'emos': 'https://b2b.emos.cz/',
    'fixed': 'https://www.fixed.cz/',
    'fixshop.cz': 'https://www.fixshop.cz/',
    'heureka nová': 'https://sluzby.heureka.cz/',
    'heureka stara': 'https://sluzby.heureka.cz/',
    'homecredit': 'https://partner.homecredit.cz/',
    'homecredit - testovací': 'https://partner.homecredit.cz/',
    'homecredit samoobsluha': 'https://partner.homecredit.cz/',
    'ird': 'https://www.irdcz-shop.cz/',
    'kvapil': 'https://obchod.kvapil.cz/',
    'lcd partner': 'https://lcdpartner.com/cs/',
    'mall partner': 'https://partner.mall.cz/',
    'mall partner new': 'https://partner.mall.cz/',
    'mall.cz': 'https://www.mall.cz/',
    'mobil pro vás': 'https://www.mobilprovas.cz/',
    'mobilmax': 'https://www.mobilmax.cz/',
    'naše díly': 'https://www.nasedily.cz/',
    'našedíly': 'https://www.nasedily.cz/',
    'našedily.cz': 'https://www.nasedily.cz/',
    'nasedily.cz': 'https://www.nasedily.cz/',
    'packeta / zásilkovna': 'https://client.packeta.com/',
    'zásilkovna': 'https://client.packeta.com/',
    'zásilkovna přední': 'https://client.packeta.com/',
    'zásilkovna zadní': 'https://client.packeta.com/',
    'setos': 'https://eshop.setos.cz/',
    'setos eshop': 'https://eshop.setos.cz/',
    'setos admin': 'https://eshop.setos.cz/',
    'tfo': 'https://sklep.telforceone.pl/',
    'telforceone (polsko)': 'https://sklep.telforceone.pl/',
    'ts bohemia': 'https://www.tsbohemia.cz/',
    'tsbohemia.cz': 'https://www.tsbohemia.cz/',
    'tsbohemia.cz nové': 'https://www.tsbohemia.cz/',
    'unicorno': 'https://www.unicorno.cz/',
    'unicorno.cz': 'https://www.unicorno.cz/',
}

STORE_ALIASES = {
    'GLOBUS': 'Globus',
    'ZLÍN ČEPKOV': 'Čepkov',
    'ZLIN CEPKOV': 'Čepkov',
    'ČEPKOV': 'Čepkov',
    'ŠTERNBERK': 'Šternberk',
    'STERNBERK': 'Šternberk',
    'PŘEROV': 'Přerov',
    'PREROV': 'Přerov',
    'SENIMO': 'Senimo',
    'VSETÍN': 'Vsetín',
    'VSETIN': 'Vsetín',
    'LITOVELSKÁ': 'Litovelská',
    'LITOVELSKA': 'Litovelská',
}


def normalize_store(name: str) -> str:
    key = re.sub(r'\s+', ' ', (name or '').strip()).upper()
    return STORE_ALIASES.get(key, name.strip().title())


def normalize_key(store, service, username):
    return (
        normalize_store(store).lower(),
        re.sub(r'\s+', ' ', (service or '').strip()).lower(),
        (username or '').strip().lower(),
    )


def needs_password_update(password: str | None) -> bool:
    value = (password or '').strip()
    return not value or value == PLACEHOLDER_PASSWORD


def _clip_url(url: str, max_len: int = 500) -> str:
    url = (url or '').strip()
    if len(url) <= max_len:
        return url
    # Dlouhé tracking URL – zkusit bez query stringu
    base = url.split('?', 1)[0]
    if len(base) <= max_len:
        return base
    return base[:max_len]


def resolve_website_url(service: str | None) -> str:
    """
    Odvodí website_url z názvu služby Mastersheet.
    1) URL přímo v textu (https://…)
    2) Mapa známých dodavatelů
    3) Doména v názvu (alza.cz, www.foo.com)
    """
    raw = re.sub(r'\s+', ' ', (service or '').strip())
    if not raw:
        return ''

    match = _URL_IN_TEXT.search(raw)
    if match:
        return _clip_url(match.group(0).rstrip('.,);]'))

    key = raw.lower().rstrip(':').strip()
    alias = SERVICE_URL_ALIASES.get(key)
    if alias:
        return alias

    # „Mobiola www.eshop.mobiola.eu“ / „Můj účet - LCD-Displeje.cz“
    for token in re.split(r'[\s,;|/]+', raw):
        token = token.strip().rstrip('.,);]')
        if not token:
            continue
        token_key = token.lower()
        if token_key in SERVICE_URL_ALIASES:
            return SERVICE_URL_ALIASES[token_key]
        if _DOMAIN_LIKE.match(token):
            host = token if '://' in token else f'https://{token.lstrip("/")}'
            if not host.lower().startswith(('http://', 'https://')):
                host = f'https://{host}'
            return _clip_url(host)

    if _DOMAIN_LIKE.match(raw):
        host = raw if '://' in raw else f'https://{raw.lstrip("/")}'
        return _clip_url(host)

    return ''


def load_mastersheet_logins_from_json(json_path: Path):
    return json.loads(json_path.read_text(encoding='utf-8'))


def load_mastersheet_logins_from_excel(excel_path: Path, *, include_passwords: bool = False):
    wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    ws = wb['Přihl.údaje']
    logins = []
    current_store = None
    for row in ws.iter_rows(values_only=True):
        c0 = row[0] if row else None
        c1 = row[1] if len(row) > 1 else None
        c2 = row[2] if len(row) > 2 else None
        if c0 and str(c0).startswith('Prodejna'):
            current_store = str(c0).replace('Prodejna ', '').strip()
            continue
        if not current_store or not c1:
            continue
        service = str(c0).strip() if c0 else ''
        if 'příhlašovací' in service.lower():
            continue
        item = {
            'store': current_store,
            'service': service,
            'username': str(c1).strip(),
        }
        if include_passwords and c2 is not None:
            item['password'] = str(c2).strip()
        logins.append(item)
    wb.close()
    return logins


def load_mastersheet_logins(excel_path: Path, json_path: Path):
    if json_path.is_file():
        return load_mastersheet_logins_from_json(json_path)
    return load_mastersheet_logins_from_excel(excel_path, include_passwords=False)


def build_password_index(ms_logins):
    """normalize_key -> heslo z Mastersheet (poslední výskyt vyhrává)."""
    index = {}
    for item in ms_logins:
        password = (item.get('password') or '').strip()
        if not password:
            continue
        key = normalize_key(item['store'], item['service'], item['username'])
        index[key] = password
    return index


def plan_password_updates(db_rows, password_index):
    """
    Naplánuje aktualizace hesel pro DB záznamy s placeholderem nebo prázdným heslem.

    db_rows: iterable dictů s klíči store, company_name, username, password, id (volitelné)
    password_index: dict z build_password_index

    Vrací dict se seznamy updated, skipped_no_match, skipped_has_password, skipped_empty_excel.
    """
    updated = []
    skipped_no_match = []
    skipped_has_password = []
    skipped_empty_excel = []

    for row in db_rows:
        current = (row.get('password') or '').strip()
        if not needs_password_update(current):
            skipped_has_password.append(row)
            continue

        key = normalize_key(row['store'], row['company_name'], row['username'])
        new_password = password_index.get(key)
        if new_password is None:
            skipped_no_match.append(row)
            continue
        if not new_password.strip():
            skipped_empty_excel.append(row)
            continue

        updated.append({**row, 'new_password': new_password})

    return {
        'updated': updated,
        'skipped_no_match': skipped_no_match,
        'skipped_has_password': skipped_has_password,
        'skipped_empty_excel': skipped_empty_excel,
    }


def summarize_by_store(rows, store_field='store'):
    counts = defaultdict(int)
    for row in rows:
        store = normalize_store(row.get(store_field, ''))
        counts[store] += 1
    return dict(sorted(counts.items()))
