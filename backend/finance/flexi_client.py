"""ABRA Flexi REST klient – hledání přijaté FA, nový doklad a upload přílohy."""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import requests

from .secrets import get_flexi_config

logger = logging.getLogger(__name__)


def parse_flexi_create_response(data: dict) -> dict[str, str]:
    """Z odpovědi PUT faktura-prijata vytáhne id a kód. Suchý běh (id -1) není zápis."""
    w = data.get('winstrom') or {}
    if str(w.get('success', '')).lower() != 'true':
        message = w.get('message') or 'Flexi zápis selhal'
        raise FlexiError(str(message)[:500])
    results = w.get('results') or []
    if isinstance(results, dict):
        results = [results]
    row = results[0] if results else {}
    errors = row.get('errors') if isinstance(row, dict) else None
    if errors:
        if isinstance(errors, list) and errors:
            first = errors[0]
            message = first.get('message') if isinstance(first, dict) else str(first)
        else:
            message = str(errors)
        raise FlexiError(str(message)[:500])
    content = row.get('content') if isinstance(row, dict) else None
    fa = {}
    if isinstance(content, dict):
        fa = content.get('faktura-prijata') or {}
        if isinstance(fa, list):
            fa = fa[0] if fa else {}
        if not isinstance(fa, dict):
            fa = {}
    flexi_id = str((row.get('id') if isinstance(row, dict) else '') or fa.get('id') or '').strip()
    if flexi_id == '-1':
        flexi_id = ''
    kod = str(fa.get('kod') or (row.get('kod') if isinstance(row, dict) else '') or '').strip()
    if not flexi_id:
        raise FlexiError('Flexi nevrátilo id nového dokladu')
    return {'flexi_id': flexi_id, 'flexi_kod': kod}


class FlexiError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class FlexiClient:
    def __init__(self, config: dict | None = None):
        self.config = config or get_flexi_config()
        if not self.config:
            raise FlexiError('Flexi není nakonfigurované (secrets/mobilmajak-finance.json).')
        self.session = requests.Session()
        self.session.auth = (self.config['username'], self.config['password'])
        self.session.headers.update({'Accept': 'application/json'})

    def _url(self, path: str) -> str:
        return f"{self.config['base_url']}{path}"

    def _company_path(self, suffix: str) -> str:
        return f"/c/{self.config['company']}/{suffix.lstrip('/')}"

    def find_faktura_prijata(
        self,
        *,
        field: str,
        value: str,
        op: str = 'eq',
        limit: int = 5,
        firma_code: str | None = None,
    ) -> list[dict]:
        value = (value or '').strip()
        if not value:
            return []
        # Flexi filtr – apostrof v hodnotě escapovat zdvojením
        safe = value.replace("'", "''")
        op_norm = (op or 'eq').strip().lower()
        if op_norm == 'like':
            expr = f"{field} like '{safe}'"
        elif op_norm in ('like_similar', 'like similar'):
            expr = f"{field} like similar '{safe}'"
        else:
            expr = f"{field} eq '{safe}'"
        firma = (firma_code or '').strip()
        if firma.lower().startswith('code:'):
            firma = firma[5:]
        firma = firma.replace("'", "''")
        if firma:
            expr = f"({expr}) and firma='code:{firma}'"
        filt = quote(expr)
        url = self._url(self._company_path(
            f"faktura-prijata/({filt}).json"
        ))
        params = {
            'detail': 'custom:id,kod,cisDosle,varSym,popis,sumCelkem,datVyst',
            'limit': limit,
        }
        try:
            resp = self.session.get(url, params=params, timeout=45)
        except requests.RequestException as exc:
            raise FlexiError(f'Flexi síťová chyba: {exc}') from exc
        if resp.status_code >= 400:
            raise FlexiError(
                f'Flexi hledání selhalo ({resp.status_code}): {resp.text[:300]}',
                status_code=resp.status_code,
            )
        items = (resp.json().get('winstrom') or {}).get('faktura-prijata') or []
        if isinstance(items, dict):
            items = [items]
        return items

    def upload_priloha(
        self,
        faktura_id: str | int,
        *,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> dict[str, Any]:
        safe_name = (filename or 'doklad.pdf').replace('/', '_').replace('\\', '_')
        url = self._url(self._company_path(
            f'faktura-prijata/{faktura_id}/prilohy/new/{quote(safe_name)}'
        ))
        try:
            resp = self.session.put(
                url,
                data=content,
                headers={'Content-Type': content_type or 'application/octet-stream'},
                timeout=90,
            )
        except requests.RequestException as exc:
            raise FlexiError(f'Flexi upload selhal: {exc}') from exc
        if resp.status_code not in (200, 201):
            raise FlexiError(
                f'Flexi upload HTTP {resp.status_code}: {resp.text[:400]}',
                status_code=resp.status_code,
            )
        data = {}
        try:
            data = resp.json()
        except ValueError:
            pass
        results = (data.get('winstrom') or {}).get('results') or []
        priloha_id = None
        if results and isinstance(results, list):
            priloha_id = results[0].get('id')
        elif results and isinstance(results, dict):
            priloha_id = results.get('id')
        return {
            'priloha_id': str(priloha_id) if priloha_id is not None else None,
            'location': resp.headers.get('Location') or '',
            'status_code': resp.status_code,
        }

    def create_faktura_prijata(self, fields: dict) -> dict[str, str]:
        """Nová přijatá faktura / ODD. fields jsou vlastnosti dokladu, ne obálka winstrom."""
        url = self._url(self._company_path('faktura-prijata.json'))
        body = {'winstrom': {'faktura-prijata': fields}}
        try:
            resp = self.session.put(url, json=body, timeout=60)
        except requests.RequestException as exc:
            raise FlexiError(f'Flexi zápis selhal: {exc}') from exc
        try:
            data = resp.json()
        except ValueError as exc:
            raise FlexiError(
                f'Flexi zápis HTTP {resp.status_code}: {resp.text[:400]}',
                status_code=resp.status_code,
            ) from exc
        if resp.status_code not in (200, 201):
            message = (data.get('winstrom') or {}).get('message') or resp.text[:400]
            raise FlexiError(
                f'Flexi zápis HTTP {resp.status_code}: {message}',
                status_code=resp.status_code,
            )
        created = parse_flexi_create_response(data)
        if not created.get('flexi_kod'):
            created['flexi_kod'] = self._faktura_kod(created['flexi_id'])
        return created

    def _faktura_kod(self, faktura_id: str) -> str:
        url = self._url(self._company_path(f'faktura-prijata/{faktura_id}.json'))
        try:
            resp = self.session.get(
                url,
                params={'detail': 'custom:id,kod'},
                timeout=45,
            )
        except requests.RequestException as exc:
            logger.warning('Flexi kod dokladu %s se nepodařilo načíst: %s', faktura_id, exc)
            return ''
        if resp.status_code >= 400:
            logger.warning('Flexi kod dokladu %s HTTP %s', faktura_id, resp.status_code)
            return ''
        try:
            item = (resp.json().get('winstrom') or {}).get('faktura-prijata') or {}
        except ValueError:
            return ''
        if isinstance(item, list):
            item = item[0] if item else {}
        if not isinstance(item, dict):
            return ''
        return str(item.get('kod') or '')
