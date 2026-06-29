#!/usr/bin/env python3
"""
Pilot brána: pohyb z Hikvision / HiLook NVR → MOBILMAJAK (bez streamu obrazu).

Spouštění na PC v síti prodejny (Windows/Linux). Konfigurace přes proměnné prostředí
nebo soubor JSON (viz --help).

Příklad testu bez NVR:
  export MOBILMAJAK_API=https://mobilmajak.com
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

MOTION_EVENT_TYPES = re.compile(
    r'^(VMD|motion|fielddetection|linedetection|intrusion|human|humanBody|alarm)$',
    re.IGNORECASE,
)

MOTION_KEYWORDS = re.compile(
    r'(motion|vmd|linedetection|fielddetection|intrusion|human|body|alarm)',
    re.IGNORECASE,
)

SUBSCRIBE_EVENT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<SubscribeEvent xmlns="http://www.isapi.org/ver20/XMLSchema" version="2.0">
  <heartbeat>5</heartbeat>
  <channelMode>list</channelMode>
  <eventMode>list</eventMode>
  <EventList>
    <Event><type>VMD</type></Event>
    <Event><type>motion</type></Event>
    <Event><type>fielddetection</type></Event>
    <Event><type>linedetection</type></Event>
    <Event><type>intrusion</type></Event>
    <Event><type>human</type></Event>
  </EventList>
</SubscribeEvent>"""


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


def _event_type_from_chunk(chunk: str) -> Optional[str]:
    try:
        root = ElementTree.fromstring(chunk)
    except ElementTree.ParseError:
        return None
    for el in root.iter():
        if el.tag.endswith('eventType') and el.text:
            return el.text.strip()
    return None


def parse_alert_xml(chunk: str) -> Optional[bool]:
    """
    True = začátek pohybu, False = konec pohybu, None = ignorovat (heartbeat / jiná událost).
    """
    if not chunk.strip():
        return None
    try:
        root = ElementTree.fromstring(chunk)
    except ElementTree.ParseError:
        return True if MOTION_KEYWORDS.search(chunk) else None

    fields = {}
    for el in root.iter():
        tag = el.tag.split('}')[-1] if '}' in el.tag else el.tag
        if tag in ('eventType', 'eventState', 'eventDescription') and el.text:
            fields[tag] = el.text.strip()

    event_type = fields.get('eventType', '')
    event_state = (fields.get('eventState') or '').lower()
    blob = chunk + ' ' + ' '.join(fields.values())

    if event_type and not MOTION_EVENT_TYPES.match(event_type):
        if not MOTION_KEYWORDS.search(blob):
            return None

    if event_state in ('inactive', 'stop', 'stopped', 'off'):
        return False
    if event_state in ('active', 'start', 'started', 'on'):
        return True

    if event_type and MOTION_EVENT_TYPES.match(event_type):
        return True
    if MOTION_KEYWORDS.search(blob):
        return True
    return None


def subscribe_nvr_events(device_base: str, auth: HTTPDigestAuth) -> None:
    """Některé NVR vyžadují subscribe před alertStream."""
    url = f'{device_base}/ISAPI/Event/notification/subscribeEvent'
    headers = {'Content-Type': 'application/xml'}
    for method in ('POST', 'PUT'):
        try:
            resp = requests.request(
                method,
                url,
                data=SUBSCRIBE_EVENT_XML.encode('utf-8'),
                auth=auth,
                headers=headers,
                timeout=8,
                verify=False,
            )
            if resp.status_code in (200, 201):
                print(f'Odběr událostí: {method} subscribeEvent → OK', flush=True)
                return
            print(f'Odběr událostí: {method} → HTTP {resp.status_code}', flush=True)
        except requests.RequestException as exc:
            print(f'Odběr událostí: {method} selhal ({exc})', flush=True)


def _multipart_boundary(content_type: str) -> Optional[str]:
    if not content_type:
        return None
    m = re.search(r'boundary=([^;\s]+)', content_type, re.IGNORECASE)
    return m.group(1).strip('"') if m else None


def iter_stream_events(buffer: str, boundary: Optional[str]):
    """Rozdělí multipart stream na jednotlivé XML události."""
    markers = []
    if boundary:
        markers.append(f'--{boundary}')
    markers.extend(('--MIME_boundary', '--boundary', '</EventNotificationAlert>'))

    while buffer:
        split_at = -1
        split_len = 0
        for marker in markers:
            idx = buffer.find(marker)
            if idx == -1:
                continue
            end = idx + (len('</EventNotificationAlert>') if marker == '</EventNotificationAlert>' else len(marker))
            if split_at == -1 or idx < split_at:
                split_at = idx
                split_len = end if marker == '</EventNotificationAlert>' else idx

        if split_at == -1:
            break

        part = buffer[:split_len if markers[0] and split_at == 0 else split_at]
        if marker := '</EventNotificationAlert>':
            if '</EventNotificationAlert>' in buffer[:split_len + 20]:
                end_idx = buffer.find('</EventNotificationAlert>')
                part = buffer[: end_idx + len('</EventNotificationAlert>')]
                buffer = buffer[end_idx + len('</EventNotificationAlert>') :]
                if part.strip():
                    yield part
                continue

        buffer = buffer[split_len:]
        if part.strip() and '<' in part:
            yield part

    return buffer


def run_alert_stream_loop(
    *,
    nvr_host: str,
    nvr_user: str,
    nvr_pass: str,
    api_base: str,
    prodejna_id: int,
    secret: str,
    quiet_after_seconds: int,
    motion_cooldown_seconds: int,
    nvr_port: Optional[int] = None,
    nvr_use_https: bool = False,
    reconnect_min_seconds: int = 15,
    reconnect_max_seconds: int = 300,
) -> None:
    """Drží bránu nonstop – po výpadku NVR/sítě znovu připojí."""
    delay = reconnect_min_seconds
    while True:
        started = time.time()
        try:
            run_alert_stream(
                nvr_host=nvr_host,
                nvr_user=nvr_user,
                nvr_pass=nvr_pass,
                api_base=api_base,
                prodejna_id=prodejna_id,
                secret=secret,
                quiet_after_seconds=quiet_after_seconds,
                motion_cooldown_seconds=motion_cooldown_seconds,
                nvr_port=nvr_port,
                nvr_use_https=nvr_use_https,
            )
            ran_for = time.time() - started
            if ran_for >= 60:
                delay = reconnect_min_seconds
            print(
                f'[{datetime.now().isoformat(timespec="seconds")}] '
                f'alertStream ukoncen po {int(ran_for)}s, reconnect za {delay}s',
                flush=True,
            )
        except KeyboardInterrupt:
            print('Ukonceno uzivatelem.', flush=True)
            raise
        except Exception as exc:
            print(
                f'[{datetime.now().isoformat(timespec="seconds")}] '
                f'chyba: {exc}, reconnect za {delay}s',
                flush=True,
            )
            import traceback
            traceback.print_exc()
        time.sleep(delay)
        delay = min(int(delay * 1.5) or reconnect_min_seconds, reconnect_max_seconds)


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
    nvr_port: Optional[int] = None,
    nvr_use_https: bool = False,
) -> None:
    device_base, _ = probe_isapi_device(
        nvr_host, nvr_user, nvr_pass, port=nvr_port, use_https=nvr_use_https, raise_on_fail=True,
    )
    url = f'{device_base}/ISAPI/Event/notification/alertStream'
    auth = HTTPDigestAuth(nvr_user, nvr_pass)
    last_motion_post = 0.0
    last_quiet_post = 0.0
    motion_session_active = False
    last_motion_signal_at = 0.0

    subscribe_nvr_events(device_base, auth)
    print(f'Připojuji alertStream {url} …', flush=True)

    with requests.get(url, auth=auth, stream=True, timeout=(10, None), verify=False) as resp:
        resp.raise_for_status()
        boundary = _multipart_boundary(resp.headers.get('Content-Type', ''))
        print(
            f'Připojeno (HTTP {resp.status_code}, boundary={boundary or "?"}). '
            f'Čekám na události pohybu z NVR…',
            flush=True,
        )
        print(
            'V NVR u Motion Detection zapněte Linkage → Notify Surveillance Center, '
            'pak projděte před kamerou.',
            flush=True,
        )
        last_heartbeat = time.time()
        buffer = ''
        print(
            f'[{datetime.now().isoformat(timespec="seconds")}] nasloucham (heartbeat kazdych 60s)',
            flush=True,
        )
        for chunk in resp.iter_content(chunk_size=4096):
            now = time.time()
            if now - last_heartbeat >= 60:
                print(
                    f'[{datetime.now().isoformat(timespec="seconds")}] stale nasloucham…',
                    flush=True,
                )
                last_heartbeat = now
            if not chunk:
                continue
            buffer += chunk.decode('utf-8', errors='replace')
            while '</EventNotificationAlert>' in buffer:
                part, buffer = buffer.split('</EventNotificationAlert>', 1)
                part += '</EventNotificationAlert>'
                event_type = _event_type_from_chunk(part)
                event_state = None
                try:
                    _root = ElementTree.fromstring(part)
                    for _el in _root.iter():
                        _tag = _el.tag.split('}')[-1] if '}' in _el.tag else _el.tag
                        if _tag == 'eventState' and _el.text:
                            event_state = _el.text.strip()
                            break
                except ElementTree.ParseError:
                    pass
                if event_type:
                    detail = f'{event_type}' + (f' ({event_state})' if event_state else '')
                    print(
                        f'[{datetime.now().isoformat(timespec="seconds")}] událost: {detail}',
                        flush=True,
                    )
                motion_flag = parse_alert_xml(part)
                if motion_flag is None:
                    continue
                now = time.time()
                if motion_flag is False:
                    if motion_session_active:
                        post_motion(
                            api_base=api_base,
                            prodejna_id=prodejna_id,
                            secret=secret,
                            motion=False,
                            source='gateway',
                        )
                        last_quiet_post = now
                        print(f'[{datetime.now().isoformat(timespec="seconds")}] → klid (NVR stop)', flush=True)
                    motion_session_active = False
                    last_motion_signal_at = 0.0
                    continue

                if motion_session_active:
                    continue

                if now - last_motion_post < motion_cooldown_seconds:
                    continue

                post_motion(
                    api_base=api_base,
                    prodejna_id=prodejna_id,
                    secret=secret,
                    motion=True,
                    source='gateway',
                )
                last_motion_post = now
                last_motion_signal_at = now
                motion_session_active = True
                print(f'[{datetime.now().isoformat(timespec="seconds")}] → pohyb (odesláno)', flush=True)

            now = time.time()
            if (
                motion_session_active
                and last_motion_signal_at
                and now - last_motion_signal_at >= quiet_after_seconds
                and now - last_quiet_post >= quiet_after_seconds
            ):
                post_motion(
                    api_base=api_base,
                    prodejna_id=prodejna_id,
                    secret=secret,
                    motion=False,
                    source='gateway',
                )
                last_quiet_post = now
                motion_session_active = False
                last_motion_signal_at = 0.0
                print(f'[{datetime.now().isoformat(timespec="seconds")}] → klid (timeout)', flush=True)


ISAPI_PROBE_PATHS = (
    '/ISAPI/System/deviceInfo',
    '/ISAPI/System/status',
    '/ISAPI/System/capabilities',
    '/doc/page/login.asp',
)

NVR_DEVICE_MARKERS = re.compile(
    r'<deviceType>\s*(NVR|DVR|HCVR|XVR|Embedded)',
    re.IGNORECASE,
)
IPC_DEVICE_MARKERS = re.compile(
    r'<deviceType>\s*IPC',
    re.IGNORECASE,
)


def _local_lan_subnets(extra=None):
    """Odhad lokálních /24 sítí podle IP tohoto PC."""
    import ipaddress
    import socket

    subnets = set(extra or [])
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(('8.8.8.8', 80))
        ip = sock.getsockname()[0]
        sock.close()
        net = ipaddress.ip_network(f'{ip}/24', strict=False)
        subnets.add(str(net))
    except OSError:
        pass
    subnets.update({'192.168.1.0/24', '192.168.0.0/24', '192.168.254.0/24'})
    return sorted(subnets)


def _classify_hikvision_device(device_info_xml: str, host: str, auth: HTTPDigestAuth) -> str:
    """Vrací nvr | ipc | unknown."""
    text = device_info_xml or ''
    if IPC_DEVICE_MARKERS.search(text):
        return 'ipc'
    if NVR_DEVICE_MARKERS.search(text):
        return 'nvr'
    if 'ipc' in text.lower() and 'nvr' not in text.lower():
        return 'ipc'
    url = f'http://{host}/ISAPI/Event/notification/alertStream'
    try:
        resp = requests.get(url, auth=auth, timeout=2, stream=True, verify=False)
        code = resp.status_code
        resp.close()
        if code in (200, 403):
            return 'nvr'
    except requests.RequestException:
        pass
    return 'unknown'


def discover_lan_devices(
    user: str,
    password: str,
    *,
    subnets=None,
    port: Optional[int] = None,
    use_https: bool = False,
) -> dict:
    """
    Projede lokální síť a vrátí nalezená Hikvision zařízení (NVR, IPC, unknown).
    """
    import ipaddress
    from concurrent.futures import ThreadPoolExecutor, as_completed

    auth = HTTPDigestAuth(user, password)
    networks = _local_lan_subnets(subnets)
    hosts = []
    for net in networks:
        try:
            for ip in ipaddress.ip_network(net, strict=False).hosts():
                hosts.append(str(ip))
        except ValueError:
            continue

    print(
        f'Sken LAN: sítě {", ".join(networks)} ({len(hosts)} adres)…',
        flush=True,
    )

    def probe(ip: str):
        for base in _device_base_urls(ip, port=port, use_https=use_https):
            url = f'{base}/ISAPI/System/deviceInfo'
            try:
                resp = requests.get(url, auth=auth, timeout=1.8, verify=False)
            except requests.RequestException:
                return None
            if resp.status_code == 401:
                return {'kind': 'bad_auth', 'ip': ip, 'name': '', 'device_type': ''}
            if resp.status_code != 200:
                return None
            kind = _classify_hikvision_device(resp.text, ip, auth)
            name_m = re.search(r'<deviceName>([^<]+)', resp.text or '')
            type_m = re.search(r'<deviceType>([^<]+)', resp.text or '')
            return {
                'kind': kind,
                'ip': ip,
                'name': (name_m.group(1).strip() if name_m else ''),
                'device_type': (type_m.group(1).strip() if type_m else ''),
            }
        return None

    buckets = {'nvr': [], 'ipc': [], 'unknown': [], 'bad_auth': []}
    with ThreadPoolExecutor(max_workers=40) as pool:
        futures = [pool.submit(probe, ip) for ip in hosts]
        for fut in as_completed(futures):
            result = fut.result()
            if not result:
                continue
            kind = result['kind']
            if kind in buckets:
                buckets[kind].append(result)

    for key in buckets:
        seen = set()
        unique = []
        for row in sorted(buckets[key], key=lambda r: r['ip']):
            if row['ip'] in seen:
                continue
            seen.add(row['ip'])
            unique.append(row)
        buckets[key] = unique
    return buckets


def list_nvr_ip_cameras(
    host: str,
    user: str,
    password: str,
    port: Optional[int] = None,
    use_https: bool = False,
) -> list:
    """IP kamery připojené k NVR (ISAPI InputProxy / video inputs)."""
    auth = HTTPDigestAuth(user, password)
    paths = (
        '/ISAPI/ContentMgmt/InputProxy/channels',
        '/ISAPI/System/Video/inputs/channels',
    )
    cameras = []
    for base in _device_base_urls(host, port=port, use_https=use_https):
        for path in paths:
            url = f'{base}{path}'
            try:
                resp = requests.get(url, auth=auth, timeout=8, verify=False)
            except requests.RequestException:
                continue
            if resp.status_code != 200:
                continue
            text = resp.text or ''
            for block in re.findall(r'<InputProxyChannel[^>]*>.*?</InputProxyChannel>', text, re.DOTALL):
                if re.search(r'<online>\s*false\s*</online>', block, re.IGNORECASE):
                    continue
                ip_m = re.search(r'<ipAddress>([^<]+)</ipAddress>', block)
                if not ip_m:
                    continue
                cam_ip = ip_m.group(1).strip()
                if not cam_ip or cam_ip in ('0.0.0.0', '127.0.0.1'):
                    continue
                ch_m = re.search(r'<id>(\d+)</id>', block)
                name_m = re.search(r'<name>([^<]+)</name>', block)
                cameras.append({
                    'channel': int(ch_m.group(1)) if ch_m else None,
                    'ip': cam_ip,
                    'name': name_m.group(1).strip() if name_m else '',
                })
            if cameras:
                return cameras
    return cameras


def discover_nvr_host(
    user: str,
    password: str,
    *,
    subnets=None,
    port: Optional[int] = None,
    use_https: bool = False,
) -> Optional[str]:
    """
    Projede lokální síť a najde Hikvision NVR (ne IP kameru).
    """
    devices = discover_lan_devices(
        user, password, subnets=subnets, port=port, use_https=use_https,
    )
    found_nvr = [row['ip'] for row in devices['nvr']]
    if len(found_nvr) == 1:
        print(f'NVR nalezen: {found_nvr[0]}', flush=True)
        return found_nvr[0]
    if len(found_nvr) > 1:
        print(f'Nalezeno více NVR: {found_nvr} – použita první', flush=True)
        return found_nvr[0]
    print('NVR v LAN nenalezen – doplňte nvr_host do config.json', flush=True)
    return None


def resolve_nvr_host(cfg: dict, nvr_user: str, nvr_pass: str) -> str:
    host = (cfg.get('nvr_host') or os.getenv('NVR_HOST', '')).strip()
    autodiscover = str(
        cfg.get('autodiscover_nvr') or os.getenv('AUTODISCOVER_NVR', '')
    ).lower() in ('1', 'true', 'yes')
    if host:
        return host
    if not autodiscover:
        return ''
    subnets = cfg.get('autodiscover_subnets')
    return discover_nvr_host(nvr_user, nvr_pass, subnets=subnets) or ''


def _device_base_urls(host: str, port: Optional[int] = None, use_https: bool = False):
    schemes = ('https', 'http') if use_https else ('http', 'https')
    ports = (port,) if port else (80, 443, 8000)
    seen = set()
    for scheme in schemes:
        for p in ports:
            if (scheme == 'http' and p == 443) or (scheme == 'https' and p == 80):
                continue
            base = f'{scheme}://{host}' if p in (80, 443) else f'{scheme}://{host}:{p}'
            if base not in seen:
                seen.add(base)
                yield base


def probe_isapi_device(
    host: str,
    user: str,
    password: str,
    port: Optional[int] = None,
    use_https: bool = False,
    *,
    raise_on_fail: bool = False,
):
    """
    Najde funkční ISAPI / Hikvision web endpoint.
    Vrací (base_url, path) nebo ukončí proces s návodem.
    """
    def _fail(msg: str, code: int = 1) -> None:
        if raise_on_fail:
            raise RuntimeError(msg)
        print(msg)
        sys.exit(code)
    auth = HTTPDigestAuth(user, password)
    reachable = False
    saw_401 = False
    print(f'Prohledávám {host} (ISAPI / Hikvision)…', flush=True)

    for base in _device_base_urls(host, port=port, use_https=use_https):
        for path in ISAPI_PROBE_PATHS:
            url = f'{base}{path}'
            try:
                resp = requests.get(url, auth=auth, timeout=8, verify=False)
            except requests.RequestException as exc:
                print(f'  × {url} – {exc}')
                continue
            reachable = True
            print(f'  · {url} → HTTP {resp.status_code}')
            if resp.status_code == 401:
                saw_401 = True
            if resp.status_code == 200 and (
                path.endswith('login.asp')
                or 'DeviceInfo' in resp.text
                or 'deviceName' in resp.text
                or 'statusString' in resp.text
                or resp.text.strip().startswith('<?xml')
            ):
                print(f'OK – nalezeno: {url}')
                return base, path
        # alertStream – jen ověříme, že endpoint existuje (může viset)
        for base in (base,):
            url = f'{base}/ISAPI/Event/notification/alertStream'
            try:
                resp = requests.get(url, auth=auth, timeout=3, stream=True, verify=False)
                code = resp.status_code
                resp.close()
                print(f'  · {url} → HTTP {code}')
                if code in (200, 403):
                    print(f'OK – alertStream dostupný na {base}')
                    return base, '/ISAPI/Event/notification/alertStream'
            except requests.RequestException:
                pass

    if not reachable:
        _fail('CHYBA: host neodpovida na HTTP/HTTPS (porty 80, 443, 8000).')
    if saw_401:
        _fail('CHYBA: 401 – spatne nvr_user / nvr_pass v configu.')
    _fail(
        'CHYBA: zarizeni odpovida, ale neni to Hikvision ISAPI na teto IP. '
        f'Zkuste http://{host}/ v prohlizeci.'
    )


def test_isapi_device(host: str, user: str, password: str, port: Optional[int] = None, use_https: bool = False) -> None:
    probe_isapi_device(host, user, password, port=port, use_https=use_https)


def load_config(path: Optional[str]) -> dict:
    cfg = {}
    if path and os.path.isfile(path):
        with open(path, encoding='utf-8-sig') as f:
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
    parser.add_argument('--test-isapi', action='store_true', help='Ověření přihlášení ke kameře/NVR v LAN')
    parser.add_argument('--discover-nvr', action='store_true', help='Jen autodetekce NVR v LAN')
    parser.add_argument(
        '--discover-lan',
        action='store_true',
        help='Sken LAN: NVR, IPC kamery a kamery v NVR (bez monitoru)',
    )
    parser.add_argument('--quiet-after', type=int, default=300, help='Sekund bez pohybu → klid')
    parser.add_argument('--motion-cooldown', type=int, default=60, help='Min. interval mezi POST pohyb')
    parser.add_argument('--reconnect-min', type=int, default=15, help='Min. cekani pred reconnect (s)')
    parser.add_argument('--reconnect-max', type=int, default=300, help='Max. cekani pred reconnect (s)')
    args = parser.parse_args()

    cfg = load_config(args.config)
    api_base = cfg.get('mobilmajak_api') or os.getenv('MOBILMAJAK_API', '')
    prodejna_id = int(cfg.get('prodejna_id') or os.getenv('PRODEJNA_ID', '0'))
    secret = cfg.get('motion_secret') or os.getenv('MOTION_SECRET', '')
    nvr_host = cfg.get('nvr_host') or os.getenv('NVR_HOST', '')
    nvr_user = cfg.get('nvr_user') or os.getenv('NVR_USER', 'admin')
    nvr_pass = cfg.get('nvr_pass') or os.getenv('NVR_PASS', '')
    nvr_port_raw = cfg.get('nvr_port') or os.getenv('NVR_PORT', '')
    nvr_port = int(nvr_port_raw) if str(nvr_port_raw).strip().isdigit() else None
    nvr_use_https = str(cfg.get('nvr_use_https') or os.getenv('NVR_USE_HTTPS', '')).lower() in ('1', 'true', 'yes')

    if not api_base or not prodejna_id or not secret:
        parser.error('Vyžadováno: MOBILMAJAK_API, PRODEJNA_ID, MOTION_SECRET')

    if args.discover_nvr:
        if not nvr_pass:
            parser.error('Pro --discover-nvr nastavte nvr_pass v configu')
        found = discover_nvr_host(
            nvr_user,
            nvr_pass,
            subnets=cfg.get('autodiscover_subnets'),
        )
        if not found:
            sys.exit(1)
        print(json.dumps({'nvr_host': found}, indent=2))
        return

    if args.discover_lan:
        if not nvr_pass:
            parser.error('Pro --discover-lan nastavte nvr_pass v configu')
        devices = discover_lan_devices(
            nvr_user,
            nvr_pass,
            subnets=cfg.get('autodiscover_subnets'),
            port=nvr_port,
            use_https=nvr_use_https,
        )
        out = {
            'subnets_scanned': _local_lan_subnets(cfg.get('autodiscover_subnets')),
            'nvr': devices['nvr'],
            'ipc': devices['ipc'],
            'unknown_hikvision': devices['unknown'],
            'bad_auth': devices['bad_auth'],
            'nvr_channels': [],
        }
        nvr_ip = (devices['nvr'][0]['ip'] if devices['nvr'] else nvr_host) or ''
        if nvr_ip:
            out['nvr_channels'] = list_nvr_ip_cameras(
                nvr_ip, nvr_user, nvr_pass, port=nvr_port, use_https=nvr_use_https,
            )
            if out['nvr_channels']:
                print(f'Kamery v NVR {nvr_ip}:', flush=True)
                for cam in out['nvr_channels']:
                    print(f"  kanál {cam.get('channel')}: {cam['ip']} {cam.get('name', '')}", flush=True)
        print(json.dumps(out, indent=2, ensure_ascii=False))
        if not devices['nvr'] and not devices['ipc'] and not out['nvr_channels']:
            sys.exit(1)
        return

    nvr_host = resolve_nvr_host(cfg, nvr_user, nvr_pass)

    if args.test_isapi:
        if not nvr_host or not nvr_pass:
            parser.error('Pro --test-isapi nastavte nvr_host (nebo autodiscover_nvr) a nvr_pass')
        test_isapi_device(nvr_host, nvr_user, nvr_pass, port=nvr_port, use_https=nvr_use_https)
        return

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

    if not nvr_pass:
        parser.error('Pro alertStream nastavte nvr_pass (nebo --test-motion)')
    if not nvr_host:
        parser.error('NVR nenalezen – doplňte nvr_host nebo zapněte autodiscover_nvr v configu')

    run_alert_stream_loop(
        nvr_host=nvr_host,
        nvr_user=nvr_user,
        nvr_pass=nvr_pass,
        api_base=api_base,
        prodejna_id=prodejna_id,
        secret=secret,
        quiet_after_seconds=args.quiet_after,
        motion_cooldown_seconds=args.motion_cooldown,
        nvr_port=nvr_port,
        nvr_use_https=nvr_use_https,
        reconnect_min_seconds=args.reconnect_min,
        reconnect_max_seconds=args.reconnect_max,
    )


if __name__ == '__main__':
    main()
