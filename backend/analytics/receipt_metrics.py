"""
Metriky účtenek: průměr položek/účtenku (varianta 1) a průměrná hodnota účtenky.
"""
from django.db.models import Q, Sum, Count, F


def qualifying_polozka_q():
    """Řádek počítaný do čitatele průměru pol./účt. a do aktivních dokladů (≥29 Kč, s kódem)."""
    return (
        Q(cena_ks_vcl_dph__gte=29)
        & Q(kod__isnull=False)
        & ~Q(kod='')
    )


def leaderboard_doklad_q():
    return Q(doklad__isnull=False) & ~Q(doklad='')


def active_receipt_filter_q():
    """Filtr řádků pro výpočet aktivních účtenek (varianta 1)."""
    return leaderboard_doklad_q() & qualifying_polozka_q()


def count_active_receipts(queryset):
    """Počet unikátních dokladů s alespoň jednou qualifying položkou."""
    return (
        queryset.filter(active_receipt_filter_q())
        .values('doklad')
        .distinct()
        .count()
    )


def sum_obrat_s_dph(queryset):
    """Celkový obrat s DPH včetně storn (záporné ceny)."""
    return queryset.aggregate(
        total=Sum(F('pocet_kusu') * F('cena_ks_vcl_dph'), default=0),
    )['total'] or 0


def prumer_polozek_uctu(polozky_nad_29, unikatni_doklady):
    if not unikatni_doklady:
        return 0
    return round((polozky_nad_29 or 0) / unikatni_doklady, 2)


def prumer_hodnota_uctenky(celkovy_obrat, unikatni_doklady):
    if not unikatni_doklady:
        return 0
    return round(float(celkovy_obrat or 0) / unikatni_doklady, 2)


def leaderboard_prumer_polozek(item):
    return prumer_polozek_uctu(
        item.get('polozky_nad_29'),
        item.get('unikatni_doklady'),
    )


def leaderboard_prumer_hodnota_uctenky(item):
    return prumer_hodnota_uctenky(
        item.get('celkovy_obrat'),
        item.get('unikatni_doklady'),
    )
