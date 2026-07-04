#!/usr/bin/env python3
"""
Nastaví Hikvision NVR HTTP alarm → MOBILMAJAK (bez brány na prodejně).

Spusťte z Macu ve Wi‑Fi prodejny (dosah na NVR v LAN).

  python3 scripts/camera_motion_setup_nvr_http.py --config secrets/camera_motion_senimo.json
  python3 scripts/camera_motion_setup_nvr_http.py --config secrets/camera_motion_senimo.json --show-url
"""
from __future__ import annotations

import argparse
import json
import os
import sys

try:
    import requests
    from requests.auth import HTTPDigestAuth
except ImportError:
    print('pip install requests', file=sys.stderr)
    sys.exit(1)

def load_cfg(path: str) -> dict:
    with open(path, encoding='utf-8') as f:
        cfg = json.load(f)
    for key in ('MOBILMAJAK_API', 'PRODEJNA_ID', 'NVR_HOST', 'NVR_USER', 'NVR_PASS'):
        env = os.getenv(key)
        if env:
            cfg[key.lower()] = env
    return cfg


def build_http_host_xml(webhook_path: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<HttpHostNotificationList version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema">
  <HttpHostNotification>
    <id>1</id>
    <url>{webhook_path}</url>
    <protocolType>HTTPS</protocolType>
    <parameterFormatType>XML</parameterFormatType>
    <addressingFormatType>hostname</addressingFormatType>
    <hostName>mobilmajak.com</hostName>
    <portNo>443</portNo>
    <httpAuthenticationMethod>none</httpAuthenticationMethod>
    <eventType>VMD</eventType>
  </HttpHostNotification>
</HttpHostNotificationList>"""


def main():
    parser = argparse.ArgumentParser(description='NVR HTTP alarm → MOBILMAJAK')
    parser.add_argument('--config', required=True)
    parser.add_argument('--show-url', action='store_true', help='Jen vypiš webhook URL')
    args = parser.parse_args()

    cfg = load_cfg(args.config)
    prodejna_id = int(cfg['prodejna_id'])
    api_base = cfg.get('mobilmajak_api', 'https://mobilmajak.com')
    token = cfg.get('motion_secret') or os.getenv('MOTION_SECRET', '')
    if not token:
        print('Chybí motion_secret v configu', file=sys.stderr)
        sys.exit(1)
    webhook = f"{api_base.rstrip('/')}/api/shifts/camera-events/hikvision/{prodejna_id}/{token}/"

    print('Webhook URL pro NVR:')
    print(webhook)
    if args.show_url:
        return

    host = cfg.get('nvr_host')
    user = cfg.get('nvr_user', 'admin')
    password = cfg.get('nvr_pass', '')
    if not host or not password:
        parser.error('V configu chybí nvr_host / nvr_pass')

    from urllib.parse import urlparse

    path = urlparse(webhook).path
    xml = build_http_host_xml(path)
    url = f'http://{host}/ISAPI/Event/notification/httpHosts/1'
    auth = HTTPDigestAuth(user, password)
    print(f'Nastavuji {url} …')
    resp = requests.put(url, data=xml.encode('utf-8'), auth=auth, headers={'Content-Type': 'application/xml'}, timeout=15)
    print('HTTP', resp.status_code)
    print(resp.text[:500])
    if resp.ok:
        print('OK – v NVR ověřte Configuration → Event → HTTP notifikace, pak projděte před kamerou.')
    else:
        print('Pokud PUT selže, nastavte URL ručně v menu NVR (viz docs/secrets-setup.md).', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
