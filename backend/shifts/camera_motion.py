"""
Pilot pohybu na prodejně – bez streamu obrazu na server.

Brána (PC v LAN) čte události z NVR (ISAPI) a posílá jen boolean + čas na MOBILMAJAK.
"""
import hashlib
import hmac
import json
import os
import re
from datetime import timedelta

from django.utils import timezone

from stores.models import Prodejna

from .models import ProdejnaPohybUdalost

MOTION_WINDOW_MINUTES = int(os.getenv('CAMERA_MOTION_WINDOW_MINUTES', '15'))
EVENT_RETENTION_DAYS = int(os.getenv('CAMERA_MOTION_RETENTION_DAYS', '7'))
SIGNATURE_MAX_AGE_SECONDS = int(os.getenv('CAMERA_MOTION_SIGNATURE_MAX_AGE', '300'))


def _parse_secrets_json(raw):
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return {str(k): str(v) for k, v in data.items()}


def load_motion_secrets():
    """
    Mapa prodejna_id (str) -> shared secret.
    Env CAMERA_MOTION_SECRETS='{"12":"hex..."}' nebo soubor CAMERA_MOTION_SECRETS_FILE.
    """
    raw = os.getenv('CAMERA_MOTION_SECRETS', '').strip()
    if not raw:
        path = os.getenv('CAMERA_MOTION_SECRETS_FILE', '').strip()
        if path and os.path.isfile(path):
            with open(path, encoding='utf-8') as f:
                raw = f.read().strip()
    return _parse_secrets_json(raw)


def motion_pilot_prodejna_ids():
    secrets = load_motion_secrets()
    ids = []
    for key in secrets:
        if re.fullmatch(r'\d+', key):
            ids.append(int(key))
    return ids


def verify_motion_token(prodejna_id, token):
    """Token v URL pro Hikvision HTTP push (stejný secret jako u brány)."""
    import hmac

    secrets = load_motion_secrets()
    expected = secrets.get(str(prodejna_id))
    if not expected or not token:
        return False, 'Neplatný token nebo prodejna není v pilotu'
    if not hmac.compare_digest(expected, token.strip()):
        return False, 'Neplatný token'
    return True, None


def hikvision_webhook_url(prodejna_id, *, api_base=None):
    """Veřejná URL pro nastavení HTTP alarmu v NVR."""
    secrets = load_motion_secrets()
    token = secrets.get(str(prodejna_id))
    if not token:
        return None
    base = (api_base or os.getenv('MOBILMAJAK_PUBLIC_URL', 'https://mobilmajak.com')).rstrip('/')
    return f'{base}/api/shifts/camera-events/hikvision/{prodejna_id}/{token}/'


def verify_motion_signature(request, prodejna_id):
    secrets = load_motion_secrets()
    secret = secrets.get(str(prodejna_id))
    if not secret:
        return False, 'Prodejna není v pilotu kamer'

    sig = (request.headers.get('X-Mobilmajak-Signature') or '').strip().lower()
    ts_raw = (request.headers.get('X-Mobilmajak-Timestamp') or '').strip()
    if not sig or not ts_raw:
        return False, 'Chybí podpis nebo časová značka'

    try:
        ts = int(ts_raw)
    except ValueError:
        return False, 'Neplatná časová značka'

    now = int(timezone.now().timestamp())
    if abs(now - ts) > SIGNATURE_MAX_AGE_SECONDS:
        return False, 'Vypršela platnost požadavku'

    body = request.body or b''
    expected = hmac.new(
        secret.encode('utf-8'),
        f'{ts}.'.encode('utf-8') + body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return False, 'Neplatný podpis'

    return True, None


def record_motion_event(*, prodejna_id, pohyb, cas=None, zdroj='gateway'):
    Prodejna.objects.get(pk=prodejna_id)
    cas = cas or timezone.now()
    event = ProdejnaPohybUdalost.objects.create(
        prodejna_id=prodejna_id,
        pohyb=bool(pohyb),
        cas=cas,
        zdroj=zdroj[:32],
    )
    _prune_old_events(prodejna_id)
    return event


def _prune_old_events(prodejna_id):
    cutoff = timezone.now() - timedelta(days=EVENT_RETENTION_DAYS)
    ProdejnaPohybUdalost.objects.filter(prodejna_id=prodejna_id, cas__lt=cutoff).delete()


def motion_status_for_prodejna(prodejna_id, now=None):
    """
    Vrací dict: status (active|quiet|unknown), last_motion_at, last_event_at, in_pilot.
    """
    now = now or timezone.now()
    in_pilot = prodejna_id in motion_pilot_prodejna_ids()
    since = now - timedelta(minutes=MOTION_WINDOW_MINUTES)

    recent = list(
        ProdejnaPohybUdalost.objects.filter(
            prodejna_id=prodejna_id,
            cas__gte=since,
        ).order_by('-cas')[:50]
    )

    if not recent:
        return {
            'status': 'unknown',
            'label': 'Kamera nehlásí',
            'in_pilot': in_pilot,
            'last_motion_at': None,
            'last_event_at': None,
            'window_minutes': MOTION_WINDOW_MINUTES,
        }

    last = recent[0]
    has_motion = any(e.pohyb for e in recent)
    last_motion = next((e for e in recent if e.pohyb), None)

    if has_motion:
        return {
            'status': 'active',
            'label': 'Pohyb',
            'in_pilot': in_pilot,
            'last_motion_at': last_motion.cas.isoformat() if last_motion else None,
            'last_event_at': last.cas.isoformat(),
            'window_minutes': MOTION_WINDOW_MINUTES,
        }

    return {
        'status': 'quiet',
        'label': 'Bez pohybu',
        'in_pilot': in_pilot,
        'last_motion_at': None,
        'last_event_at': last.cas.isoformat(),
        'window_minutes': MOTION_WINDOW_MINUTES,
    }


def attach_motion_to_stores(store_rows, now=None):
    """Doplní motion a recent_events do slov prodejen v přehledu absent/ok."""
    now = now or timezone.now()
    pilot_ids = set(motion_pilot_prodejna_ids())
    for row in store_rows:
        pid = row['prodejna_id']
        row['motion'] = motion_status_for_prodejna(pid, now)
        if pid in pilot_ids:
            recent_qs = (
                ProdejnaPohybUdalost.objects.filter(prodejna_id=pid)
                .order_by('-cas')[:5]
            )
            row['recent_events'] = [
                {
                    'id': e.id,
                    'pohyb': e.pohyb,
                    'cas': e.cas.isoformat(),
                    'zdroj': e.zdroj,
                }
                for e in recent_qs
            ]
        else:
            row['recent_events'] = []


def build_pilot_motion_report(now=None):
    """Pilotní prodejny – stav kamer vždy viditelný (i bez aktivní směny)."""
    now = now or timezone.now()
    rows = []
    for pid in motion_pilot_prodejna_ids():
        try:
            prodejna = Prodejna.objects.get(pk=pid, aktivni=True)
        except Prodejna.DoesNotExist:
            continue
        recent_qs = (
            ProdejnaPohybUdalost.objects.filter(prodejna_id=pid)
            .order_by('-cas')[:10]
        )
        recent_events = [
            {
                'id': e.id,
                'pohyb': e.pohyb,
                'cas': e.cas.isoformat(),
                'zdroj': e.zdroj,
            }
            for e in recent_qs
        ]
        rows.append({
            'prodejna_id': pid,
            'prodejna_nazev': prodejna.nazev_kratkiy or prodejna.nazev,
            'prodejna_barva': prodejna.barva or '#0066cc',
            'motion': motion_status_for_prodejna(pid, now),
            'recent_events': recent_events,
        })
    return rows
