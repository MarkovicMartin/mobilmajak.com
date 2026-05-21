"""
Bodové sazby pro prodejní metriky (produkty + služby).

Položky nad 100 Kč mají základ 15 bodů/kus. Služby s plnou provizí mají stejný
základ započtený v položkách nad 100 Kč – v řádcích služeb se proto počítá jen
příplatek nad 15 (plná provize minus 15).

CT300 je pouze informační metrika (počet kusů), nezapočítává se do bodů.
"""

POLOZKY_NAD_100_POINTS_PER_UNIT = 15

# Plná provize v bodech (původní sazby před odečtem základu 15) – bez ct300
SERVICE_FULL_POINTS = {
    'ct600': 50,
    'ct1200': 100,
    'akt': 30,
    'zah250': 30,
    'zah500': 50,
    'kop250': 30,
    'kop500': 50,
    'nap': 50,
    'pz1': 100,
    'knz': 30,
    'aligator': 0,
}

DISPLAY_ONLY_METRICS = ('ct300',)

_BASE = POLOZKY_NAD_100_POINTS_PER_UNIT


def _service_extra_rate(key, full_rate):
    return max(0, full_rate - _BASE)


SERVICE_EXTRA_POINT_RATES = {
    key: _service_extra_rate(key, full)
    for key, full in SERVICE_FULL_POINTS.items()
}

SERVICE_POINT_KEYS = tuple(SERVICE_EXTRA_POINT_RATES.keys())
POINTS_METRIC_KEYS = ('polozky_nad_100',) + SERVICE_POINT_KEYS


def normalize_points_metrics(source):
    """Dict nebo model (ProdejniData*) → slovník metrik pro výpočet bodů."""
    if source is None:
        return {k: 0 for k in POINTS_METRIC_KEYS}
    out = {}
    for key in POINTS_METRIC_KEYS:
        if isinstance(source, dict):
            val = source.get(key, 0)
        else:
            val = getattr(source, key, 0)
        out[key] = val or 0
    return out


def _count(data, key):
    if isinstance(data, dict):
        return data.get(key, 0) or 0
    return getattr(data, key, 0) or 0


def points_line(data, key, rate):
    count = _count(data, key)
    return {'count': count, 'points': count * rate}


def calculate_product_points(data):
    """Body z položek nad 100 Kč a služeb (příplatek nad základ 15), bez CT300."""
    points = _count(data, 'polozky_nad_100') * POLOZKY_NAD_100_POINTS_PER_UNIT
    for key, rate in SERVICE_EXTRA_POINT_RATES.items():
        points += _count(data, key) * rate
    return points


def build_product_points_breakdown(data):
    """Breakdown pro API / profil – CT300 jen count, points=0, informational."""
    breakdown = {
        'polozky_nad_100': points_line(
            data, 'polozky_nad_100', POLOZKY_NAD_100_POINTS_PER_UNIT
        ),
    }
    for key, rate in SERVICE_EXTRA_POINT_RATES.items():
        breakdown[key] = points_line(data, key, rate)
    for key in DISPLAY_ONLY_METRICS:
        count = _count(data, key)
        breakdown[key] = {
            'count': count,
            'points': 0,
            'informational': True,
        }
    return breakdown
