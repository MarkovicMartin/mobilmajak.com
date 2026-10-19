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
from zoneinfo import ZoneInfo

from django.utils import timezone

from stores.models import Prodejna
from stores.oteviraci_doba_utils import clip_interval_to_opening_hours, opening_window_for_date

from .models import ProdejnaPohybUdalost

PRAGUE_TZ = ZoneInfo('Europe/Prague')

MOTION_WINDOW_MINUTES = int(os.getenv('CAMERA_MOTION_WINDOW_MINUTES', '15'))
MOTION_ACTIVE_MINUTES = int(os.getenv('CAMERA_MOTION_ACTIVE_MINUTES', '5'))
EVENT_RETENTION_DAYS = int(os.getenv('CAMERA_MOTION_RETENTION_DAYS', '60'))
LOG_MARGIN_MINUTES = int(os.getenv('CAMERA_MOTION_LOG_MARGIN_MINUTES', '30'))
QUIET_LOG_MIN_MINUTES = int(os.getenv('CAMERA_MOTION_QUIET_LOG_MINUTES', '10'))
QUIET_LOG_MAX_PERIODS = int(os.getenv('CAMERA_MOTION_QUIET_LOG_MAX', '400'))
# Minutové vzorky. Díra delší než tohle už není „zavřeno“, ale výpadek brány.
SAMPLE_LINK_SECONDS = int(os.getenv('CAMERA_MOTION_SAMPLE_LINK_SECONDS', '90'))
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


def motion_log_bounds(oteviraci_doba, moment):
    """Okno zápisu: otevírací doba ± LOG_MARGIN_MINUTES. None = ten den zavřeno."""
    local = moment.astimezone(PRAGUE_TZ)
    window = opening_window_for_date(oteviraci_doba, local.date(), PRAGUE_TZ)
    if not window:
        return None
    margin = timedelta(minutes=LOG_MARGIN_MINUTES)
    return window[0] - margin, window[1] + margin


def within_motion_log_window(oteviraci_doba, moment) -> bool:
    bounds = motion_log_bounds(oteviraci_doba, moment)
    if not bounds:
        return False
    local = moment.astimezone(PRAGUE_TZ)
    return bounds[0] <= local < bounds[1]


def record_motion_event(*, prodejna_id, pohyb, cas=None, zdroj='gateway'):
    """Zapíše minutový vzorek. Mimo okno otevírací doby vrátí None a nic neukládá."""
    store = Prodejna.objects.only('id', 'oteviraci_doba').get(pk=prodejna_id)
    cas = cas or timezone.now()
    if timezone.is_naive(cas):
        cas = timezone.make_aware(cas, PRAGUE_TZ)
    if not within_motion_log_window(store.oteviraci_doba, cas):
        return None
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


def _false_runs(events, now):
    """Souvislé řady pohyb=False. Díra mezi vzorky > SAMPLE_LINK_SECONDS řadu utne.

    Vrací (start, end, ongoing). ongoing = poslední vzorek je čerstvý a pohyb se nevrátil.
    """
    link = timedelta(seconds=SAMPLE_LINK_SECONDS)
    runs = []
    n = len(events)
    i = 0
    while i < n:
        start, pohyb = events[i]
        if pohyb:
            i += 1
            continue
        j = i
        while j + 1 < n:
            nxt_cas, nxt_pohyb = events[j + 1]
            if nxt_pohyb or nxt_cas - events[j][0] > link:
                break
            j += 1
        last = events[j][0]
        closed_by_motion = (
            j + 1 < n
            and events[j + 1][1]
            and events[j + 1][0] - last <= link
        )
        if closed_by_motion:
            end = events[j + 1][0]
            ongoing = False
        else:
            ongoing = (now - last) <= link
            end = now if ongoing else last + timedelta(seconds=60)
        if end > start:
            runs.append((start, end, ongoing))
        i = j + 1
    return runs


def _open_minutes(start, end, oteviraci):
    total = 0
    segments = []
    for seg_start, seg_end in clip_interval_to_opening_hours(start, end, oteviraci, PRAGUE_TZ):
        total += int((seg_end - seg_start).total_seconds() // 60)
        segments.append((seg_start, seg_end))
    return total, segments


def motion_status_for_prodejna(prodejna_id, now=None):
    """
    Vrací dict: status (active|quiet|unknown), last_motion_at, last_event_at, in_pilot.
    Poslední minutový vzorek rozhoduje. Vzorek starší než 15 min = kamera nehlásí.
    """
    now = now or timezone.now()
    in_pilot = prodejna_id in motion_pilot_prodejna_ids()
    stale_after = timedelta(minutes=MOTION_WINDOW_MINUTES)

    last_event = (
        ProdejnaPohybUdalost.objects.filter(prodejna_id=prodejna_id)
        .order_by('-cas')
        .first()
    )

    if not last_event or now - last_event.cas > stale_after:
        last_motion = (
            ProdejnaPohybUdalost.objects.filter(prodejna_id=prodejna_id, pohyb=True)
            .order_by('-cas')
            .values_list('cas', flat=True)
            .first()
        )
        return {
            'status': 'unknown',
            'label': 'Kamera nehlásí',
            'in_pilot': in_pilot,
            'last_motion_at': last_motion.isoformat() if last_motion else None,
            'last_event_at': last_event.cas.isoformat() if last_event else None,
            'quiet_minutes': None,
            'active_minutes': MOTION_ACTIVE_MINUTES,
            'window_minutes': MOTION_WINDOW_MINUTES,
        }

    if last_event.pohyb:
        return {
            'status': 'active',
            'label': 'Pohyb',
            'in_pilot': in_pilot,
            'last_motion_at': last_event.cas.isoformat(),
            'last_event_at': last_event.cas.isoformat(),
            'quiet_minutes': None,
            'active_minutes': MOTION_ACTIVE_MINUTES,
            'window_minutes': MOTION_WINDOW_MINUTES,
        }

    try:
        oteviraci = Prodejna.objects.only('oteviraci_doba').get(pk=prodejna_id).oteviraci_doba
    except Prodejna.DoesNotExist:
        oteviraci = {}
    since = now - timedelta(hours=16)
    events = list(
        ProdejnaPohybUdalost.objects.filter(prodejna_id=prodejna_id, cas__gte=since)
        .order_by('cas')
        .values_list('cas', 'pohyb')
    )
    quiet_minutes = None
    runs = _false_runs(events, now)
    if runs and runs[-1][2]:
        quiet_minutes, _segs = _open_minutes(runs[-1][0], runs[-1][1], oteviraci)
        if not quiet_minutes:
            quiet_minutes = None
    last_motion = (
        ProdejnaPohybUdalost.objects.filter(prodejna_id=prodejna_id, pohyb=True)
        .order_by('-cas')
        .values_list('cas', flat=True)
        .first()
    )
    label = (
        f'Bez pohybu {quiet_minutes} min'
        if quiet_minutes and quiet_minutes >= MOTION_ACTIVE_MINUTES
        else 'Bez pohybu'
    )
    return {
        'status': 'quiet',
        'label': label,
        'in_pilot': in_pilot,
        'last_motion_at': last_motion.isoformat() if last_motion else None,
        'last_event_at': last_event.cas.isoformat(),
        'quiet_minutes': quiet_minutes,
        'active_minutes': MOTION_ACTIVE_MINUTES,
        'window_minutes': MOTION_WINDOW_MINUTES,
    }


def motion_detail_for_prodejna(prodejna_id, now=None, lookback_hours=None):
    """Souvislé minuty bez pohybu (vzorky klidu) uvnitř otevírací doby.

    Díra bez vzorků je výpadek brány, ne zavření.
    """
    now = now or timezone.now()
    if lookback_hours is None:
        lookback_hours = EVENT_RETENTION_DAYS * 24
    since = now - timedelta(hours=lookback_hours)

    try:
        store = Prodejna.objects.only('id', 'oteviraci_doba').get(pk=prodejna_id)
        oteviraci = store.oteviraci_doba
    except Prodejna.DoesNotExist:
        oteviraci = {}

    events = list(
        ProdejnaPohybUdalost.objects.filter(prodejna_id=prodejna_id, cas__gte=since)
        .order_by('cas')
        .values_list('cas', 'pohyb')
    )

    quiet_periods = []
    current_quiet_minutes = None
    for start, end, ongoing in _false_runs(events, now):
        _total, segments = _open_minutes(start, end, oteviraci)
        for seg_start, seg_end in segments:
            minutes = int((seg_end - seg_start).total_seconds() // 60)
            if minutes < QUIET_LOG_MIN_MINUTES:
                continue
            seg_ongoing = bool(ongoing and seg_end >= now)
            quiet_periods.append({
                'from': seg_start.isoformat(),
                'to': None if seg_ongoing else seg_end.isoformat(),
                'minutes': minutes,
                'ongoing': seg_ongoing,
            })
            if seg_ongoing and (current_quiet_minutes is None or minutes > current_quiet_minutes):
                current_quiet_minutes = minutes

    quiet_periods.sort(key=lambda p: p['from'], reverse=True)

    return {
        'quiet_periods': quiet_periods[:QUIET_LOG_MAX_PERIODS],
        'current_quiet_minutes': current_quiet_minutes,
        'active_minutes': MOTION_ACTIVE_MINUTES,
        'quiet_log_min_minutes': QUIET_LOG_MIN_MINUTES,
    }


def attach_motion_to_stores(store_rows, now=None):
    """Doplní motion a motion_detail do slov prodejen."""
    now = now or timezone.now()
    pilot_ids = set(motion_pilot_prodejna_ids())
    for row in store_rows:
        pid = row['prodejna_id']
        # Virtuální dlaždice (backoffice / home office) nemají kameru
        if not isinstance(pid, int):
            row['motion'] = {
                'status': 'unknown',
                'label': None,
                'in_pilot': False,
                'last_motion_at': None,
                'last_event_at': None,
                'quiet_minutes': None,
                'active_minutes': MOTION_ACTIVE_MINUTES,
                'window_minutes': MOTION_WINDOW_MINUTES,
            }
            row['motion_detail'] = None
            row.pop('recent_events', None)
            continue
        row['motion'] = motion_status_for_prodejna(pid, now)
        if pid in pilot_ids:
            row['motion_detail'] = motion_detail_for_prodejna(pid, now)
        else:
            row['motion_detail'] = None
        row.pop('recent_events', None)


def build_pilot_motion_report(now=None):
    """Pilotní prodejny – stav kamer vždy viditelný (i bez aktivní směny)."""
    now = now or timezone.now()
    rows = []
    for pid in motion_pilot_prodejna_ids():
        try:
            prodejna = Prodejna.objects.get(pk=pid, aktivni=True)
        except Prodejna.DoesNotExist:
            continue
        rows.append({
            'prodejna_id': pid,
            'prodejna_nazev': prodejna.nazev_kratkiy or prodejna.nazev,
            'prodejna_barva': prodejna.barva or '#0066cc',
            'motion': motion_status_for_prodejna(pid, now),
            'motion_detail': motion_detail_for_prodejna(pid, now),
        })
    return rows
