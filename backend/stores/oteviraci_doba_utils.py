"""Normalizace JSON otevírací doby Po–Ne."""
from datetime import date, datetime, timedelta

DNY_KLICE = ('po', 'ut', 'st', 'ct', 'pa', 'so', 'ne')
VYCHOZI_OD = '08:00'
VYCHOZI_DO = '20:00'


def default_oteviraci_doba():
    return {
        'stejne_pro_vsechny': True,
        'vychozi': {'od': VYCHOZI_OD, 'do': VYCHOZI_DO},
        'dny': {k: None for k in DNY_KLICE},
    }


def normalize_oteviraci_doba(raw):
    if not raw or not isinstance(raw, dict):
        return default_oteviraci_doba()
    out = default_oteviraci_doba()
    out['stejne_pro_vsechny'] = bool(raw.get('stejne_pro_vsechny', True))
    vychozi = raw.get('vychozi') or {}
    out['vychozi'] = {
        'od': (vychozi.get('od') or VYCHOZI_OD)[:5],
        'do': (vychozi.get('do') or VYCHOZI_DO)[:5],
    }
    dny_in = raw.get('dny') or {}
    dny_out = {}
    for k in DNY_KLICE:
        day = dny_in.get(k)
        if day is None or day == '':
            dny_out[k] = None
        elif isinstance(day, dict):
            if day.get('zavreno'):
                dny_out[k] = {'zavreno': True}
            else:
                dny_out[k] = {
                    'od': (day.get('od') or out['vychozi']['od'])[:5],
                    'do': (day.get('do') or out['vychozi']['do'])[:5],
                }
        else:
            dny_out[k] = None
    out['dny'] = dny_out
    return out


def resolve_den_hours(oteviraci_doba, den_key):
    """Vrátí (od, do) nebo None pokud je den zavřený."""
    cfg = normalize_oteviraci_doba(oteviraci_doba)
    day = (cfg.get('dny') or {}).get(den_key)
    if day and day.get('zavreno'):
        return None
    if day and day.get('od') and day.get('do'):
        return day['od'], day['do']
    v = cfg.get('vychozi') or {}
    return v.get('od'), v.get('do')


def _parse_hm(value):
    try:
        h, m = value.split(':')[:2]
        return int(h), int(m)
    except (AttributeError, TypeError, ValueError):
        return None


def opening_window_for_date(oteviraci_doba, day: date, tz):
    """Aware (od, do) pro kalendářní den, nebo None (zavřeno / neplatné)."""
    den_key = DNY_KLICE[day.weekday()]
    pair = resolve_den_hours(oteviraci_doba, den_key)
    if not pair or not pair[0] or not pair[1]:
        return None
    od_hm = _parse_hm(pair[0])
    do_hm = _parse_hm(pair[1])
    if not od_hm or not do_hm:
        return None
    start = datetime(day.year, day.month, day.day, od_hm[0], od_hm[1], tzinfo=tz)
    end = datetime(day.year, day.month, day.day, do_hm[0], do_hm[1], tzinfo=tz)
    if end <= start:
        return None
    return start, end


def clip_interval_to_opening_hours(start, end, oteviraci_doba, tz):
    """Průnik [start, end] s otevíracími okny (po dnech)."""
    if end <= start:
        return []
    local_start = start.astimezone(tz)
    local_end = end.astimezone(tz)
    segments = []
    day = local_start.date()
    last_day = local_end.date()
    while day <= last_day:
        window = opening_window_for_date(oteviraci_doba, day, tz)
        day += timedelta(days=1)
        if not window:
            continue
        seg_start = max(local_start, window[0])
        seg_end = min(local_end, window[1])
        if seg_end > seg_start:
            segments.append((seg_start, seg_end))
    return segments
