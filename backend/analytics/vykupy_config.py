"""
Výkupy (WEB_VYKUPY) – odměna prodejci, který výkup přijal (sloupec ID_PRODEJCE).
"""

from django.db.models import Sum

from .models import WebVykupy

VYKUPY_METRIC_KEY = 'vykupy'
VYKUPY_UI_LABEL = 'Výkupy'
VYKUPY_POINTS_PER_UNIT = 50


def vykupy_counts_map(*, typ_exact=None, typ_month_prefix=None):
    """Počet kusů výkupů podle id_prodejce (pro žebříček / agregace)."""
    qs = WebVykupy.objects.filter(id_prodejce__isnull=False)
    if typ_exact is not None:
        qs = qs.filter(vystaveno=typ_exact)
    elif typ_month_prefix:
        qs = qs.filter(vystaveno__startswith=typ_month_prefix)
    rows = qs.values('id_prodejce').annotate(pocet=Sum('pocet_kusů', default=0))
    return {
        int(row['id_prodejce']): int(row['pocet'] or 0)
        for row in rows
        if row['id_prodejce'] is not None
    }


def vykupy_pocet_for_prodejce(user_id, *, typ_exact=None, typ_month_prefix=None):
    """Počet vykoupených kusů přiřazených prodejci."""
    qs = WebVykupy.objects.filter(id_prodejce=int(user_id))
    if typ_exact is not None:
        qs = qs.filter(vystaveno=typ_exact)
    elif typ_month_prefix:
        qs = qs.filter(vystaveno__startswith=typ_month_prefix)
    agg = qs.aggregate(total=Sum('pocet_kusů', default=0))
    total = int(agg['total'] or 0)
    if total:
        return total
    return qs.count()


def calculate_vykupy_points(count):
    return int(count or 0) * VYKUPY_POINTS_PER_UNIT
