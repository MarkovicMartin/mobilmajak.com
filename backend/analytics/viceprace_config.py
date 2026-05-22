"""
Vícepráce (Symplio kód P63615) – samostatná metrika mimo položky nad 100 Kč a body.

Řádky P63615 se nepočítají do polozky_nad_100 ani do 15 bodů/kus, i při ceně ≥ 100 Kč.
Metrika pro žebříček dýškařů = součet obratu (Počet_kusu × prodejní cena s DPH).
"""
from django.db.models import Q, Sum, Count, F

VICEPRACE_KOD = 'P63615'
VICEPRACE_METRIC_KEY = 'viceprace_obrat'
VICEPRACE_UI_LABEL = 'Vícepráce'


def viceprace_row_q():
    return Q(kod=VICEPRACE_KOD)


def polozky_nad_100_q():
    """Položky nad 100 Kč včetně kódu, bez víceprací P63615."""
    return (
        Q(cena_ks_vcl_dph__gte=100)
        & Q(kod__isnull=False)
        & ~Q(kod='')
        & ~viceprace_row_q()
    )


def viceprace_obrat_sum():
    """Agregace obratu víceprací (Kč s DPH) pro annotate()."""
    return Sum(
        F('pocet_kusu') * F('cena_ks_vcl_dph'),
        filter=viceprace_row_q(),
        default=0,
    )


def _round_obrat(value):
    return round(float(value or 0), 2)


def aggregate_viceprace(queryset):
    """Součet obratu víceprací v querysetu (Kč s DPH)."""
    result = queryset.filter(viceprace_row_q()).aggregate(
        obrat=viceprace_obrat_sum(),
        kusy=Sum('pocet_kusu', default=0),
        doklady=Count('doklad', distinct=True),
    )
    obrat = _round_obrat(result['obrat'])
    return {
        'obrat': obrat,
        'kusy': int(result['kusy'] or 0),
        'doklady': result['doklady'] or 0,
        'kod': VICEPRACE_KOD,
    }


def viceprace_leader_from_rows(rows):
    """Nejlepší dýškař – nejvyšší viceprace_obrat."""
    best = None
    best_obrat = 0.0
    for row in rows:
        obrat = float(row.get('viceprace_obrat') or row.get('obrat') or 0)
        if obrat > best_obrat:
            best_obrat = obrat
            best = row
    if not best or best_obrat <= 0:
        return None
    return {
        'id': best.get('id') or best.get('id_prodejce'),
        'prodejce': best.get('prodejce'),
        'obrat': _round_obrat(best_obrat),
    }
