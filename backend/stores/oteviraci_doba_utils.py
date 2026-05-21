"""Normalizace JSON otevírací doby Po–Ne."""

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
