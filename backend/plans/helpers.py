"""
Helper funkce pro plány – výpočet průměrných cen z WEB_PRODEJE_ALL.
"""
from decimal import Decimal
from django.db import connection

# Pevné výchozí hodnoty (Kč) pokud chybí historická data
VYCHOZI_PRUMERNE_CENY = {
    'NOVE_TELEFONY': Decimal('5000'),
    'BAZAROVE_TELEFONY': Decimal('2500'),
    'SERVIS': Decimal('800'),
    'SLUZBY': Decimal('300'),
    'PRISLUSENSTVI_SKLA': Decimal('400'),
    'PRISLUSENSTVI_OBALY': Decimal('400'),
    'PRISLUSENSTVI_OSTATNI': Decimal('400'),
    'OSTATNI': Decimal('500'),
}


def vypocti_prumerne_ceny(rok, mesic):
    """
    Vypočítá průměrné ceny za kus per kategorie z WEB_PRODEJE_ALL.
    - Primárně: předchozí kompletní měsíc (M-1)
    - Fallback: poslední 3 měsíce
    - Fallback 2: pevné výchozí hodnoty

    Returns: dict[kategorie_kod -> Decimal]
    """
    result = {}
    kategorie_kody = list(VYCHOZI_PRUMERNE_CENY.keys())

    # M-1: předchozí měsíc
    prev_mesic = mesic - 1
    prev_rok = rok
    if prev_mesic == 0:
        prev_mesic = 12
        prev_rok -= 1

    # 1. Zkus M-1
    avg_m1 = _prumerne_ceny_za_obdobi(prev_rok, prev_mesic, prev_rok, prev_mesic)
    for kod in kategorie_kody:
        if kod in avg_m1 and avg_m1[kod] is not None and avg_m1[kod] > 0:
            result[kod] = avg_m1[kod]

    # 2. Fallback: poslední 3 měsíce pro chybějící kategorie
    if len(result) < len(kategorie_kody):
        start_m, start_y = prev_mesic, prev_rok
        for _ in range(2):
            start_m -= 1
            if start_m == 0:
                start_m = 12
                start_y -= 1
        avg_3m = _prumerne_ceny_za_obdobi(start_y, start_m, prev_rok, prev_mesic)
        for kod in kategorie_kody:
            if kod not in result and kod in avg_3m and avg_3m[kod] is not None and avg_3m[kod] > 0:
                result[kod] = avg_3m[kod]

    # 3. Fallback 2: pevné výchozí hodnoty
    for kod in kategorie_kody:
        if kod not in result:
            result[kod] = VYCHOZI_PRUMERNE_CENY[kod]

    return result


def _prumerne_ceny_za_obdobi(rok_od, mesic_od, rok_do, mesic_do):
    """
    Vrátí AVG(Cena_ks_vcl_DPH) per kategorie_kod za dané období.
    Používá CASE mapování z WEB_PRODEJE_ALL.
    """
    sql = """
    SELECT
        CASE
            WHEN `KATEGORIE` = 'SERVIS' THEN 'SERVIS'
            WHEN `KATEGORIE` = 'NOVÉ TELEFONY' THEN 'NOVE_TELEFONY'
            WHEN `KATEGORIE` IN ('POUŽITÉ TELEFONY', '!Výkup bazaru') THEN 'BAZAROVE_TELEFONY'
            WHEN `KATEGORIE` = 'PŘÍSLUŠENSTVÍ' AND `KATEGORIE_1` = 'Skla a fólie' THEN 'PRISLUSENSTVI_SKLA'
            WHEN `KATEGORIE` = 'PŘÍSLUŠENSTVÍ' AND `KATEGORIE_1` = 'Pouzdra a kryty' THEN 'PRISLUSENSTVI_OBALY'
            WHEN `KATEGORIE` = 'PŘÍSLUŠENSTVÍ' THEN 'PRISLUSENSTVI_OSTATNI'
            WHEN `KATEGORIE_1` = 'Služby' OR `KATEGORIE` = 'Služby' THEN 'SLUZBY'
            ELSE 'OSTATNI'
        END AS kategorie_kod,
        AVG(`Cena_ks_vcl_DPH`) AS prumer
    FROM `WEB_PRODEJE_ALL`
    WHERE `Vystaveno` >= %s
      AND `Vystaveno` < %s
      AND `Cena_ks_vcl_DPH` IS NOT NULL
      AND `Cena_ks_vcl_DPH` > 0
    GROUP BY 1
    """
    from datetime import date
    start_date = date(rok_od, mesic_od, 1)
    end_month = mesic_do + 1
    end_year = rok_do
    if end_month > 12:
        end_month = 1
        end_year += 1
    end_date = date(end_year, end_month, 1)

    with connection.cursor() as cursor:
        cursor.execute(sql, [start_date, end_date])
        rows = cursor.fetchall()

    return {row[0]: Decimal(str(row[1])).quantize(Decimal('0.01')) if row[1] else None for row in rows}
