"""Stažení Packeta provizí z admin.packeta.com přes Playwright (centrální admin účet)."""
from __future__ import annotations

import logging
import os
import re
import tempfile
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta

from django.utils import timezone

from packeta.models import PacketaProvizePolozka
from packeta.packeta_parser import (
    PACKETA_TYPE_LABELS,
    count_distinct_visits,
    parse_packeta_csv,
    type_values_for_preset,
)
from packeta.secrets import get_packeta_admin_for_fetch
from packeta.shift_assign import resolve_prodejce_for_packeta

logger = logging.getLogger(__name__)

PACKETA_CSV_ROW_LIMIT = 1000
PACKETA_SAFE_CHUNK_ITEMS = 850
PACKETA_LOGIN_URL = 'https://admin.packeta.com/sign/in'
PACKETA_COMMISSION_URL = 'https://admin.packeta.com/commission'

ROZPIS_LINK_RE = re.compile(r'Show breakdown|Ukázat rozpis|rozpis', re.I)
TRANSACTIONS_SECTION_RE = re.compile(
    r'List of all transactions|Výpis všech transakcí|všech transakcí', re.I,
)

_IGNORED_BRANCH_KEYWORDS = ('litovel', 'litovelska', 'litovelská')

_BRANCH_KEYWORDS: list[tuple[int, tuple[str, ...]]] = [
    (1, ('globus', 'prazska', 'pražská')),
    (2, ('pasteurova', 'senimo', 'od senimo')),
    (3, ('cepkov', 'čepkov', 'zlin', 'zlín', 'tyrsovo', 'tyršovo')),
    (4, ('prerov', 'přerov', 'cechova', 'čechova')),
    (5, ('vsetin', 'vsetín', 'smetanova')),
    (6, ('sternberk', 'šternberk', 'obchodni', 'obchodní')),
]


def _normalize_branch_text(text: str) -> str:
    s = unicodedata.normalize('NFKD', (text or '').lower())
    return ''.join(c for c in s if not unicodedata.combining(c))


def _is_ignored_branch(branch_name: str) -> bool:
    """Zrušené pobočky – tichě přeskočit (Litovelská už neexistuje)."""
    norm = _normalize_branch_text(branch_name)
    return any(_normalize_branch_text(kw) in norm for kw in _IGNORED_BRANCH_KEYWORDS)


def map_branch_to_prodejna(branch_name: str) -> tuple[int | None, str | None]:
    if _is_ignored_branch(branch_name):
        return None, None
    norm = _normalize_branch_text(branch_name)
    for prodejna_id, keywords in _BRANCH_KEYWORDS:
        for kw in keywords:
            kw_norm = _normalize_branch_text(kw)
            if kw_norm in norm:
                return prodejna_id, None
    return None, f'Neznámá pobočka „{branch_name}" – nelze mapovat na prodejna_id'


def date_range_for_days(days: int) -> tuple[date, date]:
    if days < 1:
        days = 1
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    return start, end


def iter_date_chunks(
    date_from: date,
    date_to: date,
    chunk_days: int = 7,
) -> list[tuple[date, date]]:
    """Rozdělí období na kousky (max chunk_days), aby CSV nepřekročilo limit 1000 řádků."""
    if chunk_days < 1:
        chunk_days = 1
    if date_from > date_to:
        return []
    chunks: list[tuple[date, date]] = []
    cur = date_from
    while cur <= date_to:
        chunk_end = min(cur + timedelta(days=chunk_days - 1), date_to)
        chunks.append((cur, chunk_end))
        cur = chunk_end + timedelta(days=1)
    return chunks


def date_range_today() -> tuple[date, date]:
    d = date.today()
    return d, d


def date_range_yesterday() -> tuple[date, date]:
    d = date.today() - timedelta(days=1)
    return d, d


def date_range_this_month() -> tuple[date, date]:
    today = date.today()
    end = today - timedelta(days=1)
    start = date(today.year, today.month, 1)
    if end < start:
        end = start
    return start, end


def date_range_for_period(period: str, *, days: int | None = None) -> tuple[date, date]:
    if period == 'today':
        return date_range_today()
    if period == 'yesterday':
        return date_range_yesterday()
    if period == 'month':
        return date_range_this_month()
    if period == 'days':
        return date_range_for_days(days or 1)
    raise ValueError(f'Neznámé období: {period}')


def default_chunk_days(total_days: int) -> int:
    """Kratší kousky pro delší období – busy pobočky mají 1000+ řádků/týden."""
    if total_days <= 1:
        return 1
    if total_days <= 7:
        return 3
    return 7


@dataclass
class BranchFetchResult:
    branch_name: str
    prodejna_id: int | None = None
    csv_content: bytes | None = None
    warning: str | None = None
    error: str | None = None


@dataclass
class BranchImportResult:
    branch_name: str
    prodejna_id: int | None = None
    created: int = 0
    skipped: int = 0
    stats: dict = field(default_factory=dict)
    warning: str | None = None
    error: str | None = None


def import_packeta_rows(
    rows: list[dict],
    prodejna_id: int,
    batch: str | None = None,
    dry_run: bool = False,
) -> dict:
    batch = batch or timezone.now().strftime('%Y%m%d%H%M%S')
    created = skipped = assigned = 0
    for row in rows:
        id_prodejce = resolve_prodejce_for_packeta(prodejna_id, row['cas'])
        if dry_run:
            created += 1
            if id_prodejce:
                assigned += 1
            continue
        obj, was_created = PacketaProvizePolozka.objects.get_or_create(
            prodejna_id=prodejna_id,
            zasilka=row['zasilka'],
            typ_provize=row['typ_provize'],
            cas=row['cas'],
            defaults={
                'zasilka_raw': row['zasilka_raw'],
                'castka': row['castka'],
                'mena': row['mena'],
                'poznamka': row['poznamka'],
                'import_batch': batch,
                'id_prodejce': id_prodejce,
            },
        )
        if was_created:
            created += 1
            if id_prodejce:
                assigned += 1
        else:
            skipped += 1
            if id_prodejce and obj.id_prodejce is None:
                obj.id_prodejce = id_prodejce
                obj.save(update_fields=['id_prodejce'])
                assigned += 1
    stats = count_distinct_visits(rows)
    return {
        'created': created,
        'skipped': skipped,
        'assigned': assigned,
        'stats': stats,
        'import_batch': batch,
        'warning': None,
        'rows_total': len(rows),
    }


def _login_packeta(page, login: str, password: str) -> None:
    page.goto(PACKETA_LOGIN_URL, wait_until='domcontentloaded', timeout=90000)
    page.wait_for_timeout(1500)
    page.locator('#loginForm-email, input[name="email"]').first.fill(login)
    page.locator('#loginForm-password, input[type="password"]').first.fill(password)
    page.locator('input[type="submit"]').first.click()
    page.wait_for_timeout(5000)
    if 'sign/in' in page.url:
        raise RuntimeError('Packeta přihlášení selhalo – stále na přihlašovací stránce')


def _branch_name_from_row(row_locator) -> str:
    cells = row_locator.locator('td')
    if cells.count() == 0:
        return row_locator.inner_text().strip().split('\n')[0].strip()
    return cells.first.inner_text().strip()


def _transactions_date_picker(page):
    page.get_by_text(TRANSACTIONS_SECTION_RE).first.scroll_into_view_if_needed()
    picker = page.locator(
        '.date-range-picker:has([for*="branchCommissionGrid"]), '
        '.date-range-picker:has(label[for*="branchCommissionGrid"])',
    )
    if picker.count():
        return picker.first
    pickers = page.locator('.date-range-picker')
    return pickers.last if pickers.count() > 1 else pickers.first


def _transactions_grid(page):
    section = page.get_by_text(TRANSACTIONS_SECTION_RE).first
    grid = section.locator('xpath=following::div[contains(@class,"paginated-grid")][1]')
    if grid.count():
        return grid.first
    return page.locator('.paginated-grid').first


def _pick_calendar_day(page, picker, target: date) -> None:
    cal = picker.locator('.dropdown-menu .rdp-root, .dropdown-menu.show .rdp').first
    cal.locator('select.rdp-years_dropdown').first.select_option(str(target.year))
    page.wait_for_timeout(200)
    cal.locator('select.rdp-months_dropdown').first.select_option(str(target.month - 1))
    page.wait_for_timeout(300)
    day_btn = cal.locator('.rdp-day:not(.rdp-disabled) button').filter(
        has_text=re.compile(rf'^{target.day}$'),
    )
    day_btn.first.click()


def _select_date_preset(page, date_from: date, date_to: date) -> bool:
    """Vyber období v date-range-picker. Vrací True pokud byl zvolen vlastní rozsah."""
    picker = _transactions_date_picker(page)
    picker.locator('.dropdown-toggle').click()
    page.wait_for_timeout(500)
    menu = picker.locator('.dropdown-menu.show')

    span_days = (date_to - date_from).days + 1
    today = date.today()
    yesterday = today - timedelta(days=1)
    use_today_preset = span_days == 1 and date_from == date_to == today
    use_yesterday_preset = span_days == 1 and date_from == date_to == yesterday

    if use_today_preset:
        for label in ('Today', 'Dnes'):
            item = menu.locator('.dropdown-item').filter(
                has_text=re.compile(rf'^{re.escape(label)}$', re.I),
            )
            if item.count():
                item.first.click()
                page.wait_for_timeout(300)
                return False

    if use_yesterday_preset:
        for label in ('Yesterday', 'Včera'):
            item = menu.locator('.dropdown-item').filter(
                has_text=re.compile(rf'^{re.escape(label)}$', re.I),
            )
            if item.count():
                item.first.click()
                page.wait_for_timeout(300)
                return False

    custom = menu.locator('.dropdown-item').filter(
        has_text=re.compile(r'^Custom$|^Vlastní$', re.I),
    )
    if not custom.count():
        raise RuntimeError('Nelze najít volbu datumového rozsahu')
    custom.first.click()
    page.wait_for_timeout(500)
    _pick_calendar_day(page, picker, date_from)
    page.wait_for_timeout(300)
    _pick_calendar_day(page, picker, date_to)
    return True


def _grid_row_count(page) -> int:
    grid = _transactions_grid(page)
    return grid.locator('table tbody tr:not(.branch-commission-grid__sum-row)').count()


def _grid_item_count_text(page) -> int | None:
    text = _transactions_grid(page).inner_text()
    for pattern in (
        r'Total\s+(\d+)\s+items',
        r'Počet položek[:\s]+(\d+)',
        r'Item count[:\s]+(\d+)',
        r'(\d+)\s+položek',
        r'(\d+)\s+items',
    ):
        m = re.search(pattern, text, re.I)
        if m:
            return int(m.group(1))
    if 'No items found' in text or 'Žádné položky' in text:
        return 0
    return None


def _click_grid_renew(page) -> None:
    grid = _transactions_grid(page)
    for loc in (
        grid.locator('.paginated-grid__reload-button:not([disabled])'),
        grid.locator('button:has-text("Renew"), button:has-text("Obnovit")'),
        grid.get_by_text(re.compile(r'^Renew$|^Obnovit$|^↻$', re.I)),
    ):
        if loc.count():
            loc.first.click()
            return
    for loc in (
        page.locator('text=Renew'),
        page.get_by_text(re.compile(r'^Renew$|^Obnovit$', re.I)),
    ):
        if loc.count():
            loc.first.click()
            return
    raise RuntimeError('Tlačítko Renew/Obnovit nenalezeno')


def _wait_for_grid_reload(page, rows_before: int | None = None) -> int:
    grid = _transactions_grid(page)
    try:
        grid.locator('.loading').first.wait_for(state='hidden', timeout=30000)
    except Exception:
        pass

    try:
        page.wait_for_load_state('networkidle', timeout=30000)
    except Exception:
        page.wait_for_timeout(4000)

    deadline = timezone.now() + timedelta(seconds=30)
    while timezone.now() < deadline:
        count_text = _grid_item_count_text(page)
        row_count = _grid_row_count(page)
        if count_text is not None and count_text <= 5000:
            return row_count
        if row_count > 0 and (rows_before is None or row_count < rows_before):
            return row_count
        if count_text == 0:
            return 0
        page.wait_for_timeout(500)

    row_count = _grid_row_count(page)
    count_text = _grid_item_count_text(page)
    if count_text is not None and count_text > 5000:
        raise RuntimeError(
            f'Po filtru období je stále {count_text} položek – filtr se pravděpodobně neaplikoval',
        )
    return row_count


def _apply_date_filter_and_renew(page, date_from: date, date_to: date) -> None:
    rows_before = _grid_row_count(page)
    used_custom = _select_date_preset(page, date_from, date_to)
    _click_grid_renew(page)
    if used_custom:
        page.wait_for_timeout(4000)
    _wait_for_grid_reload(page, rows_before=rows_before)


def _find_csv_export_button(page):
    """Najdi export tlačítko/link – Packeta používá .paginated-grid-export nebo text CSV export."""
    grid = _transactions_grid(page)
    scopes = [grid.locator('.grid-table__above'), grid, page.locator('.paginated-grid')]
    for scope in scopes:
        if not scope.count():
            continue
        for sel in ('button.paginated-grid-export', 'a.paginated-grid-export'):
            loc = scope.locator(sel)
            if loc.count():
                return loc.first
        text_loc = scope.get_by_text(re.compile(r'^CSV export$|^Export CSV$', re.I))
        if text_loc.count():
            return text_loc.first
        href_loc = scope.locator('a[href*="export" i][href*="csv" i], a[href*="/export" i]')
        if href_loc.count():
            return href_loc.first
    return None


def _wait_for_export_button(page, timeout_s: int = 45):
    """Po reloadu gridu počkej, až bude export dostupný."""
    deadline = timezone.now() + timedelta(seconds=timeout_s)
    while timezone.now() < deadline:
        btn = _find_csv_export_button(page)
        if btn is not None:
            try:
                btn.wait_for(state='visible', timeout=2000)
                if btn.is_enabled():
                    return btn
            except Exception:
                pass
        page.wait_for_timeout(500)
    raise RuntimeError('Export CSV se po načtení gridu neobjevil')


def _is_csv_export_response(response) -> bool:
    url = (response.url or '').lower()
    ctype = (response.headers.get('content-type') or '').lower()
    if not response.ok:
        return False
    if 'export' not in url and 'csv' not in url and 'commission' not in url:
        return False
    return (
        'csv' in ctype
        or 'text/plain' in ctype
        or 'octet-stream' in ctype
        or url.endswith('.csv')
        or 'format=csv' in url
        or 'export' in url
    )


def _save_download(download) -> bytes:
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
        tmp_path = tmp.name
    try:
        download.save_as(tmp_path)
        with open(tmp_path, 'rb') as f:
            return f.read()
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _download_csv_from_page(page, item_count: int | None = None) -> bytes:
    csv_btn = _wait_for_export_button(page)
    csv_btn.scroll_into_view_if_needed()
    page.wait_for_timeout(500)

    download_timeout = 25000
    if item_count is not None:
        download_timeout = min(120000, 25000 + item_count * 30)

    captured: list[bytes] = []

    def _on_response(response):
        if _is_csv_export_response(response):
            try:
                captured.append(response.body())
            except Exception:
                pass

    page.on('response', _on_response)
    try:
        try:
            with page.expect_download(timeout=download_timeout) as dl_info:
                csv_btn.click(force=True)
            return _save_download(dl_info.value)
        except Exception:
            page.wait_for_timeout(5000)
            if captured:
                return captured[-1]
            with page.expect_response(_is_csv_export_response, timeout=download_timeout):
                csv_btn.click(force=True)
            page.wait_for_timeout(2000)
            if captured:
                return captured[-1]
            raise RuntimeError('Klik na export CSV nevyvolal stažení ani CSV odpověď')
    finally:
        page.remove_listener('response', _on_response)


def _commission_type_select(page):
    page.get_by_text(TRANSACTIONS_SECTION_RE).first.scroll_into_view_if_needed()
    return page.locator('select#type, select[name="type"]').first


def _select_commission_type(page, type_value: str) -> None:
    _commission_type_select(page).select_option(value=type_value)
    page.wait_for_timeout(300)


def _rows_to_csv_bytes(rows: list[dict]) -> bytes:
    if not rows:
        return b''
    lines = ['Datum a \u010das;Z\xe1silka;Typ provize;\u010c\xe1stka;M\u011bna;Pozn\xe1mka']
    for row in rows:
        cas_str = row['cas'].strftime('%d. %m. %Y, %H:%M')
        castka = f'{row["castka"]:.2f}'.replace('.', ',')
        lines.append(
            f'"{cas_str}";"{row["zasilka_raw"]}";"{row["typ_provize"]}";'
            f'"{castka}";"{row["mena"]}";"{row["poznamka"] or "–"}"'
        )
    return '\n'.join(lines).encode('utf-8')


def _fetch_branch_rows_by_types(
    page,
    rozpis_link,
    date_from: date,
    date_to: date,
    type_values: tuple[str, ...],
    on_progress=None,
) -> list[dict]:
    """Jedna pobočka: nastav období, pak pro každý typ provize export CSV."""
    rozpis_link.click()
    page.wait_for_load_state('domcontentloaded', timeout=60000)
    page.wait_for_timeout(2000)
    page.get_by_text(TRANSACTIONS_SECTION_RE).first.scroll_into_view_if_needed()
    _apply_date_filter_and_renew(page, date_from, date_to)

    all_rows: list[dict] = []
    for type_value in type_values:
        label = PACKETA_TYPE_LABELS.get(type_value, type_value)
        if on_progress:
            on_progress(f'  typ {label}')
        _select_commission_type(page, type_value)
        _click_grid_renew(page)
        page.wait_for_timeout(2000)
        _wait_for_grid_reload(page)

        count = _grid_item_count_text(page)
        if count == 0:
            continue
        if count is not None and count > PACKETA_CSV_ROW_LIMIT:
            raise RuntimeError(
                f'Typ „{label}“ má {count} položek – zúžte období',
            )
        csv_bytes = _download_csv_from_page(page, item_count=count)
        if csv_bytes.strip():
            all_rows.extend(parse_packeta_csv(csv_bytes))

    return all_rows


def fetch_single_branch(
    prodejna_id: int,
    period: str = 'month',
    typ_preset: str = 'baliky',
    headless: bool = True,
    on_progress=None,
) -> BranchFetchResult:
    """Zjednodušený fetch: jedna pobočka, kalendářní měsíc, filtr typu v UI."""
    creds = get_packeta_admin_for_fetch()
    if not creds:
        raise RuntimeError('Packeta admin přihlašovací údaje nejsou nakonfigurovány (packeta_admin."0")')

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            'Playwright není nainstalován. Spusťte: pip install playwright && playwright install chromium'
        ) from exc

    if period in ('month', 'yesterday', 'today'):
        date_from, date_to = date_range_for_period(period)
    else:
        raise RuntimeError(f'Neznámé období: {period}')

    type_values = type_values_for_preset(typ_preset)
    target_name = None

    def _progress(msg: str) -> None:
        if on_progress:
            on_progress(msg)
        else:
            logger.info(msg)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        try:
            _login_packeta(page, creds['login'], creds['password'])
            page.goto(PACKETA_COMMISSION_URL, wait_until='domcontentloaded', timeout=90000)
            page.wait_for_timeout(3000)
            try:
                page.wait_for_load_state('networkidle', timeout=20000)
            except Exception:
                pass

            branch_entries = _collect_branch_entries(page)
            target_link = None
            for name, link in branch_entries:
                pid, _ = map_branch_to_prodejna(name)
                if pid == prodejna_id:
                    target_name = name
                    target_link = link
                    break

            if target_link is None:
                return BranchFetchResult(
                    branch_name=f'prodejna {prodejna_id}',
                    prodejna_id=prodejna_id,
                    error=f'Pobočka pro prodejna_id={prodejna_id} nenalezena',
                )

            _progress(
                f'{target_name} (id {prodejna_id}), '
                f'{date_from}–{date_to}, typy: {typ_preset}',
            )
            rows = _fetch_branch_rows_by_types(
                page, target_link, date_from, date_to, type_values, on_progress=_progress,
            )
            return BranchFetchResult(
                branch_name=target_name,
                prodejna_id=prodejna_id,
                csv_content=_rows_to_csv_bytes(rows),
            )
        except Exception as exc:
            logger.exception('Packeta fetch selhal pro prodejna %s', prodejna_id)
            return BranchFetchResult(
                branch_name=target_name or f'prodejna {prodejna_id}',
                prodejna_id=prodejna_id,
                error=str(exc),
            )
        finally:
            browser.close()


def fetch_and_import_branch(
    prodejna_id: int,
    period: str = 'month',
    typ_preset: str = 'baliky',
    dry_run: bool = False,
    on_progress=None,
) -> dict:
    fr = fetch_single_branch(
        prodejna_id,
        period=period,
        typ_preset=typ_preset,
        on_progress=on_progress,
    )
    batch = timezone.now().strftime('%Y%m%d%H%M%S')
    start, end = date_range_for_period(period)

    entry: dict = {
        'branch_name': fr.branch_name,
        'prodejna_id': fr.prodejna_id,
        'warning': fr.warning,
        'error': fr.error,
        'period': period,
        'typ_preset': typ_preset,
    }
    if fr.error or fr.prodejna_id is None:
        return {
            'import_batch': batch,
            'date_from': start.isoformat(),
            'date_to': end.isoformat(),
            'branches': [entry],
            'dry_run': dry_run,
            'typ_preset': typ_preset,
        }
    if not fr.csv_content:
        entry.update({
            'created': 0, 'skipped': 0, 'rows_total': 0,
            'stats': {'navstevy_celkem': 0, 'vydane': 0, 'prijate': 0, 'radku_csv': 0},
            'warning': (entry.get('warning') or '') + ' Žádné transakce ve zvoleném období.',
        })
    else:
        try:
            rows = parse_packeta_csv(fr.csv_content)
            imp = import_packeta_rows(rows, fr.prodejna_id, batch=batch, dry_run=dry_run)
            entry.update(imp)
        except ValueError as exc:
            entry['error'] = str(exc)

    return {
        'import_batch': batch,
        'date_from': start.isoformat(),
        'date_to': end.isoformat(),
        'branches': [entry],
        'dry_run': dry_run,
        'typ_preset': typ_preset,
    }


def _fetch_branch_rows_for_range(
    page,
    date_from: date,
    date_to: date,
    depth: int = 0,
) -> list[dict]:
    """Stáhne řádky pro období; při >850 položkách rozdělí na menší kousky."""
    page.get_by_text(TRANSACTIONS_SECTION_RE).first.scroll_into_view_if_needed()
    _apply_date_filter_and_renew(page, date_from, date_to)
    count = _grid_item_count_text(page)
    if count == 0:
        return []

    span_days = (date_to - date_from).days + 1
    if count is not None and count > PACKETA_SAFE_CHUNK_ITEMS and span_days > 1 and depth < 8:
        split_at = date_from + timedelta(days=span_days // 2 - 1)
        left = _fetch_branch_rows_for_range(page, date_from, split_at, depth=depth + 1)
        page.goto(page.url, wait_until='domcontentloaded', timeout=60000)
        page.wait_for_timeout(1500)
        right = _fetch_branch_rows_for_range(page, split_at + timedelta(days=1), date_to, depth=depth + 1)
        return left + right

    if count is not None and count > PACKETA_CSV_ROW_LIMIT:
        raise RuntimeError(
            f'Příliš mnoho položek ({count}) pro jeden den – export by ztratil data',
        )

    csv_bytes = _download_csv_from_page(page, item_count=count)
    if not csv_bytes.strip():
        return []
    return parse_packeta_csv(csv_bytes)


def _fetch_branch_csv_chunk(page, date_from: date, date_to: date) -> bytes:
    rows = _fetch_branch_rows_for_range(page, date_from, date_to)
    if not rows:
        return b''

    lines = ['Datum a \u010das;Z\xe1silka;Typ provize;\u010c\xe1stka;M\u011bna;Pozn\xe1mka']
    for row in rows:
        cas_str = row['cas'].strftime('%d. %m. %Y, %H:%M')
        castka = f'{row["castka"]:.2f}'.replace('.', ',')
        lines.append(
            f'"{cas_str}";"{row["zasilka_raw"]}";"{row["typ_provize"]}";'
            f'"{castka}";"{row["mena"]}";"{row["poznamka"] or "–"}"'
        )
    return '\n'.join(lines).encode('utf-8')


def _fetch_branch_csv(
    page,
    rozpis_link,
    date_from: date,
    date_to: date,
    chunk_days: int = 7,
    on_chunk=None,
) -> bytes:
    """Stáhne CSV pro pobočku; delší období rozdělí na týdenní kousky a sloučí řádky."""
    rozpis_link.click()
    page.wait_for_load_state('domcontentloaded', timeout=60000)
    page.wait_for_timeout(2000)

    chunks = iter_date_chunks(date_from, date_to, chunk_days=chunk_days)
    all_rows: list[dict] = []

    for idx, (chunk_from, chunk_to) in enumerate(chunks, start=1):
        if on_chunk:
            on_chunk(idx, len(chunks), chunk_from, chunk_to)
        csv_bytes = _fetch_branch_csv_chunk(page, chunk_from, chunk_to)
        if not csv_bytes.strip():
            continue
        rows = parse_packeta_csv(csv_bytes)
        if not rows:
            continue
        all_rows.extend(rows)
        if idx < len(chunks):
            page.goto(page.url, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(1500)

    if not all_rows:
        return b''

    lines = ['Datum a \u010das;Z\xe1silka;Typ provize;\u010c\xe1stka;M\u011bna;Pozn\xe1mka']
    for row in all_rows:
        cas_str = row['cas'].strftime('%d. %m. %Y, %H:%M')
        castka = f'{row["castka"]:.2f}'.replace('.', ',')
        lines.append(
            f'"{cas_str}";"{row["zasilka_raw"]}";"{row["typ_provize"]}";'
            f'"{castka}";"{row["mena"]}";"{row["poznamka"] or "–"}"'
        )
    return '\n'.join(lines).encode('utf-8')


def _collect_branch_entries(page) -> list[tuple[str, object]]:
    deadline = timezone.now() + timedelta(seconds=45)
    rozpis_links = []
    while timezone.now() < deadline:
        rozpis_links = page.get_by_role('link', name=ROZPIS_LINK_RE).all()
        if not rozpis_links:
            rozpis_links = page.locator(
                'a:has-text("Show breakdown"), a:has-text("Ukázat rozpis")',
            ).all()
        if rozpis_links:
            break
        page.wait_for_timeout(1000)

    if not rozpis_links:
        raise RuntimeError('Na stránce /commission nejsou odkazy na rozpis provizí')

    entries = []
    for link in rozpis_links:
        row = link.locator('xpath=ancestor::tr[1]')
        if row.count() == 0:
            row = link.locator('xpath=ancestor::*[self::tr or self::div][1]')
        name = _branch_name_from_row(row) if row.count() else link.inner_text()
        if _is_ignored_branch(name):
            continue
        entries.append((name, link))
    return entries


def fetch_all_branch_csvs(
    days: int = 1,
    headless: bool = True,
    chunk_days: int | None = None,
    prodejna_id_filter: int | None = None,
    on_progress=None,
) -> list[BranchFetchResult]:
    creds = get_packeta_admin_for_fetch()
    if not creds:
        raise RuntimeError('Packeta admin přihlašovací údaje nejsou nakonfigurovány (packeta_admin."0")')

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            'Playwright není nainstalován. Spusťte: pip install playwright && playwright install chromium'
        ) from exc

    date_from, date_to = date_range_for_days(days)
    if chunk_days is None:
        chunk_days = default_chunk_days(days)
    results: list[BranchFetchResult] = []

    def _progress(msg: str) -> None:
        if on_progress:
            on_progress(msg)
        else:
            logger.info(msg)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        try:
            _login_packeta(page, creds['login'], creds['password'])
            page.goto(PACKETA_COMMISSION_URL, wait_until='domcontentloaded', timeout=90000)
            page.wait_for_timeout(3000)
            try:
                page.wait_for_load_state('networkidle', timeout=20000)
            except Exception:
                pass

            branch_entries = _collect_branch_entries(page)

            for branch_name, _link in branch_entries:
                if _is_ignored_branch(branch_name):
                    continue
                prodejna_id, warning = map_branch_to_prodejna(branch_name)
                if prodejna_id is None:
                    if warning:
                        results.append(BranchFetchResult(
                            branch_name=branch_name,
                            prodejna_id=None,
                            warning=warning,
                        ))
                    continue
                if prodejna_id_filter is not None and prodejna_id != prodejna_id_filter:
                    continue

                _progress(f'Pobočka {branch_name} (id {prodejna_id}), období {date_from}–{date_to}, kousky po {chunk_days} dnech')

                page.goto(PACKETA_COMMISSION_URL, wait_until='domcontentloaded', timeout=90000)
                page.wait_for_timeout(3000)
                current_entries = _collect_branch_entries(page)

                target_link = None
                for name, clink in current_entries:
                    if name == branch_name:
                        target_link = clink
                        break
                if target_link is None:
                    mapped = [e for e in current_entries if map_branch_to_prodejna(e[0])[0] == prodejna_id]
                    if mapped:
                        target_link = mapped[0][1]

                if target_link is None:
                    results.append(BranchFetchResult(
                        branch_name=branch_name,
                        prodejna_id=prodejna_id,
                        error=f'Nelze najít odkaz rozpis pro „{branch_name}"',
                        warning=warning,
                    ))
                    continue

                try:
                    def _chunk_cb(i, total, cf, ct):
                        _progress(f'  kousek {i}/{total}: {cf} – {ct}')

                    csv_bytes = _fetch_branch_csv(
                        page,
                        target_link,
                        date_from,
                        date_to,
                        chunk_days=chunk_days,
                        on_chunk=_chunk_cb,
                    )
                    results.append(BranchFetchResult(
                        branch_name=branch_name,
                        prodejna_id=prodejna_id,
                        csv_content=csv_bytes,
                        warning=warning,
                    ))
                except Exception as exc:
                    logger.exception('Packeta fetch selhal pro %s', branch_name)
                    results.append(BranchFetchResult(
                        branch_name=branch_name,
                        prodejna_id=prodejna_id,
                        error=str(exc),
                        warning=warning,
                    ))
        finally:
            browser.close()

    return results


def fetch_and_import_all_branches(
    days: int = 1,
    dry_run: bool = False,
    chunk_days: int | None = None,
    prodejna_id: int | None = None,
    on_progress=None,
) -> dict:
    fetch_results = fetch_all_branch_csvs(
        days=days,
        chunk_days=chunk_days,
        prodejna_id_filter=prodejna_id,
        on_progress=on_progress,
    )
    batch = timezone.now().strftime('%Y%m%d%H%M%S')
    branches: list[dict] = []
    start, end = date_range_for_days(days)

    for fr in fetch_results:
        entry: dict = {
            'branch_name': fr.branch_name,
            'prodejna_id': fr.prodejna_id,
            'warning': fr.warning,
            'error': fr.error,
        }
        if fr.error or fr.prodejna_id is None:
            branches.append(entry)
            continue
        if not fr.csv_content:
            entry.update({
                'created': 0,
                'skipped': 0,
                'rows_total': 0,
                'stats': {'navstevy_celkem': 0, 'vydane': 0, 'prijate': 0, 'radku_csv': 0},
                'warning': (entry.get('warning') or '') + ' Žádné transakce ve zvoleném období.',
            })
            branches.append(entry)
            continue
        try:
            rows = parse_packeta_csv(fr.csv_content)
            if not rows:
                entry['warning'] = (entry.get('warning') or '') + ' CSV bez dat pro zvolené období.'
            imp = import_packeta_rows(rows, fr.prodejna_id, batch=batch, dry_run=dry_run)
            entry.update(imp)
        except ValueError as exc:
            entry['error'] = str(exc)
        branches.append(entry)

    return {
        'import_batch': batch,
        'days': days,
        'chunk_days': chunk_days or default_chunk_days(days),
        'date_from': start.isoformat(),
        'date_to': end.isoformat(),
        'branches': branches,
        'dry_run': dry_run,
    }
