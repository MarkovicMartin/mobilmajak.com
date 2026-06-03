"""
SUNSHINE fólie – příplatek nad běžnou odměnu za položku nad 100 Kč.

Počítání kusů: řádek v prodejních datech, kde název obsahuje „SUNSHINE“
(stejná logika jako v analytice Prodejny → položky).

Každá fólie: +15 bodů/kus navíc k 15 bodům z „Položky nad 100 Kč“ (pokud řádek
splní podmínku polozky_nad_100_q). Celkem tedy typicky 30 bodů/kus oproti 15 u běžné položky.
"""
from django.db.models import Q, Sum

SUNSHINE_METRIC_KEY = 'sunshine'
SUNSHINE_UI_LABEL = 'SUNSHINE fólie'
SUNSHINE_POINTS_PER_UNIT = 15


def sunshine_row_q():
    """Filtr řádků SUNSHINE fólií v WebProdejeAll."""
    return Q(nazev__icontains='SUNSHINE')


def sunshine_kusy_sum():
    """Agregace počtu kusů (Pocet_kusu) pro annotate() – stejně jako položky nad 100 Kč."""
    return Sum('pocet_kusu', filter=sunshine_row_q(), default=0)


def calculate_sunshine_points(count):
    """Příplatek za SUNSHINE – navíc k položkám nad 100 Kč a službám."""
    return int(count or 0) * SUNSHINE_POINTS_PER_UNIT
