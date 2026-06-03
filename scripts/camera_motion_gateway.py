#!/usr/bin/env python3
"""
Pilot brána: pohyb z Hikvision / HiLook NVR → MOBILMAJAK (bez streamu obrazu).

Spouštění na PC v síti prodejny (Windows/Linux). Konfigurace přes proměnné prostředí
nebo soubor JSON (viz --help).

Příklad testu bez NVR:
  export MOBILMAJAK_API=https://staging.example.com
  export PRODEJNA_ID=12
  export MOTION_SECRET=your_hex_secret
  python3 scripts/camera_motion_gateway.py --test-motion true
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Optional
from xml.etree import ElementTree

try:
    import requests
    from requests.auth import HTTPDigestAuth
except ImportError:
    print('Chybí balíček requests: pip install requests', file=sys.stderr)
    sys.exit(1)

MOTION_KEYWORDS = re.compile(
    r'(motion|vmd|linedetection|fielddetection|intrusion)',
    re.IGNORECASE,
)


def sign_body(secret: str, timestamp: int, body: bytes) -> str:
    return hmac.new(
        secret.encode('utf-8'),
        f'{timestamp}.'.encode('utf-8') + body,
        hashlib.sha256,
    ).hexdigest()


def post_motion(
    *,
    api_base: str,
    prodejna_id: int,
    secret: str,
    motion: bool,
    source: str = 'gateway',
) -> dict:
    api_base = api_base.rstrip('/')
    url = f'{api_base}/api/shifts/camera-events/'
    payload = {
        'prodejna_id': prodejna_id,
        'motion': motion,
        'at': datetime.now(timezone.utc).astimezone().isoformat(),
        'source': source,
    }
    body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    ts = int(time.time())
    headers = {
        'Content-Type': 'application/json',
        'X-Mobilmajak-Timestamp': str(ts),
        'X-Mobilmajak-Signature': sign_body(secret, ts, body),
    }
    resp = requests.post(url, data=body, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def parse_alert_xml(chunk: str) -> bool:
    if not chunk.strip():
        return False
    try:
        root = ElementTree.fromstring(chunk)
    except ElementTree.ParseError:
        return bool(MOTION_KEYWORDS.search(chunk))
    text = ElementTree.tostring(root, encoding='unicode', method='text')
    blob = chunk + ' ' + text
    for tag in ('eventType', 'eventDescription', 'eventState'):
        for el in root.iter():
            if el.tag.endswith(tag) and el.text and MOTION_KEYWORDS.search(el.text):
                return True
    return bool(MOTION_KEYWORDS.search(blob))


def run_alert_stream(
    *,
    nvr_host: str,
    nvr_user: str,
    nvr_pass: str,
    api_base: str,
    prodejna_id: int,
    secret: str,
    quiet_after_seconds: int,
    motion_cooldown_seconds: int,
) -> None:
    url = f'http://{nvr_host}/ISAPI/Event/notification/alertStream'
    auth = HTTPDigestAuth(nvr_user, nvr_pass)
    last_motion_post = 0.0
    last_any_motion = 0.0
    last_quiet_post = 0.0

    print(f'Připojuji alertStream {url} …', flush=True)

    with requests.get(url, auth=auth, stream=True, timeout=(10, None)) as resp:
        resp.raise_for_status()
        buffer = ''
        for chunk in resp.iter_content(chunk_size=None):
            if not chunk:
                continue
            buffer += chunk.decode('utf-8', errors='replace')
            while '--MIME_boundary' in buffer or '</EventNotificationAlert>' in buffer:
                if '</EventNotificationAlert>' in buffer:
                    part, buffer = buffer.split('</EventNotificationAlert>', 1)
                    part += '</EventNotificationAlert>'
                else:
                    break
                if parse_alert_xml(part):
                    now = time.time()
                    last_any_motion = now
                    if now - last_motion_post >= motion_cooldown_seconds:
                        post_motion(
                            api_base=api_base,
                            prodejna_id=prodejna_id,
                            secret=secret,
                            motion=True,
                        )
                        last_motion_post = now
                        print(f'[{datetime.now().isoformat(timespec="seconds")}] → pohyb', flush=True)

            now = time.time()
            if (
                last_any_motion
                and now - last_any_motion >= quiet_after_seconds
                and now - last_quiet_post >= quiet_after_seconds
            ):
                post_motion(
                    api_base=api_base,
                    prodejna_id=prodejna_id,
                    secret=secret,
                    motion=False,
                )
                last_quiet_post = now
                last_any_motion = 0.0
                print(f'[{datetime.now().isoformat(timespec="seconds")}] → klid', flush=True)


def load_config(path: Optional[str]) -> dict:
    cfg = {}
    if path and os.path.isfile(path):
        with open(path, encoding='utf-8') as f:
            cfg = json.load(f)
    for key in (
        'MOBILMAJAK_API',
        'PRODEJNA_ID',
        'MOTION_SECRET',
        'NVR_HOST',
        'NVR_USER',
        'NVR_PASS',
    ):
        if os.getenv(key):
            cfg[key.lower()] = os.getenv(key)
    return cfg


def main():
    parser = argparse.ArgumentParser(description='Brána pohybu NVR → MOBILMAJAK')
    parser.add_argument('--config', help='JSON konfigurace')
    parser.add_argument('--test-motion', choices=('true', 'false'), help='Jednorázový test POST')
    parser.add_argument('--quiet-after', type=int, default=300, help='Sekund bez pohybu → klid')
    parser.add_argument('--motion-cooldown', type=int, default=60, help='Min. interval mezi POST pohyb')
    args = parser.parse_args()

    cfg = load_config(args.config)
    api_base = cfg.get('mobilmajak_api') or os.getenv('MOBILMAJAK_API', '')
    prodejna_id = int(cfg.get('prodejna_id') or os.getenv('PRODEJNA_ID', '0'))
    secret = cfg.get('motion_secret') or os.getenv('MOTION_SECRET', '')
    nvr_host = cfg.get('nvr_host') or os.getenv('NVR_HOST', '')
    nvr_user = cfg.get('nvr_user') or os.getenv('NVR_USER', 'admin')
    nvr_pass = cfg.get('nvr_pass') or os.getenv('NVR_PASS', '')

    if not api_base or not prodejna_id or not secret:
        parser.error('Vyžadováno: MOBILMAJAK_API, PRODEJNA_ID, MOTION_SECRET')

    if args.test_motion is not None:
        result = post_motion(
            api_base=api_base,
            prodejna_id=prodejna_id,
            secret=secret,
            motion=args.test_motion == 'true',
            source='test',
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if not nvr_host or not nvr_pass:
        parser.error('Pro alertStream nastavte NVR_HOST a NVR_PASS (nebo --test-motion)')

    run_alert_stream(
        nvr_host=nvr_host,
        nvr_user=nvr_user,
        nvr_pass=nvr_pass,
        api_base=api_base,
        prodejna_id=prodejna_id,
        secret=secret,
        quiet_after_seconds=args.quiet_after,
        motion_cooldown_seconds=args.motion_cooldown,
    )


if __name__ == '__main__':
    main()
