"""ABRA Flexi REST klient – hledání přijaté FA a upload přílohy."""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import requests

from .secrets import get_flexi_config

logger = logging.getLogger(__name__)


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
