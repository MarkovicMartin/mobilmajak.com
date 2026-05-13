"""
Logika plnění plánu z WEB_PRODEJE_ALL.

Filtry:
- Vystaveno v daném měsíci
- Cena_ks_vcl_DPH > 14 NEBO < 0 (storno) – položky 0–14 Kč vyřazeny
- KATEGORIE vyplněná (ne prázdná, ne NULL, ne Nezařazeno)
- Storna odečítáme (záporná cena)

Mapování kategorií (pořadí důležité):
1. SERVIS, 2. NOVE_TELEFONY, 3. BAZAROVE_TELEFONY,
4. PRISLUSENSTVI_SKLA, 5. PRISLUSENSTVI_OBALY, 6. PRISLUSENSTVI_OSTATNI,
7. SLUZBY, 8. OSTATNI
"""
import calendar
from datetime import date, timedelta
from decimal import Decimal
from django.db import connection


def _kategorie_case_sql():
    """CASE výraz pro mapování řádku na plánovací kategorii."""
    return """
        CASE
            WHEN Objednavku_zalozil LIKE %s AND COALESCE(k_servisu,'') = 'ANO'
                 AND KATEGORIE LIKE %s
                 AND (KATEGORIE_1 IS NULL OR KATEGORIE_1 = '' OR KATEGORIE_1 NOT LIKE 'Služby%%')
            THEN 'SERVIS'
            WHEN KATEGORIE = 'NOVÉ TELEFONY' THEN 'NOVE_TELEFONY'
            WHEN KATEGORIE IN ('POUŽITÉ TELEFONY', '!Výkup bazaru') THEN 'BAZAROVE_TELEFONY'
            WHEN KATEGORIE = 'PŘÍSLUŠENSTVÍ' AND KATEGORIE_1 = 'Skla a fólie' THEN 'PRISLUSENSTVI_SKLA'
            WHEN KATEGORIE = 'PŘÍSLUŠENSTVÍ' AND KATEGORIE_1 = 'Pouzdra a kryty' THEN 'PRISLUSENSTVI_OBALY'
            WHEN KATEGORIE = 'PŘÍSLUŠENSTVÍ' THEN 'PRISLUSENSTVI_OSTATNI'
            WHEN KATEGORIE_1 = 'Služby' OR KATEGORIE = 'Služby' THEN 'SLUZBY'
            ELSE 'OSTATNI'
        END
    """


def _base_where_params(rok, mesic):
    """Vrátí (start_date, end_date) pro daný měsíc."""
    start_date = date(rok, mesic, 1)
    if mesic == 12:
        end_date = date(rok + 1, 1, 1)
    else:
        end_date = date(rok, mesic + 1, 1)
    return start_date.isoformat(), end_date.isoformat()


def plneni_firma_do_data(rok, mesic, end_date):
    """
    Vrátí plnění od 1. dne měsíce do end_date (včetně).
    Pro výpočet trendu – data jen do dneška.
    """
    start_d = date(rok, mesic, 1).isoformat()
    end_d = (end_date + timedelta(days=1)).isoformat()
    case_sql = _kategorie_case_sql()

    sql = f"""
        SELECT
            {case_sql} AS kategorie_kod,
            SUM(COALESCE(NULLIF(Pocet_kusu, 0), 1) * COALESCE(Cena_ks_vcl_DPH, 0)) AS obrat,
            SUM(
                CASE WHEN COALESCE(Cena_ks_vcl_DPH, 0) >= 0
                THEN COALESCE(NULLIF(Pocet_kusu, 0), 1)
                ELSE -COALESCE(NULLIF(Pocet_kusu, 0), 1)
                END
            ) AS kusy
        FROM WEB_PRODEJE_ALL
        WHERE Vystaveno >= %s AND Vystaveno < %s
        AND (
            Cena_ks_vcl_DPH > 14
            OR Cena_ks_vcl_DPH < 0
        )
        AND KATEGORIE IS NOT NULL
        AND TRIM(COALESCE(KATEGORIE,'')) != ''
        AND COALESCE(KATEGORIE,'') != 'Nezařazeno'
        GROUP BY kategorie_kod
    """

    params = ['%servis eda%', '%!Servis%', start_d, end_d]

    with connection.cursor() as cursor:
        cursor.execute(sql, params)

        rows = cursor.fetchall()

    result = {}
    for row in rows:
        kod, obrat, kusy = row
        if kod:
            result[kod] = {
                'obrat': Decimal(str(obrat)) if obrat else Decimal('0'),
                'kusy': int(kusy) if kusy is not None else 0,
            }
    return result


def plneni_firma(rok, mesic):
    """
    Vrátí plnění na úrovni firmy za celý měsíc: obrat a kusy per kategorie.
    """
    start_d, end_d = _base_where_params(rok, mesic)
    case_sql = _kategorie_case_sql()
    params = ['%servis eda%', '%!Servis%', start_d, end_d]
    sql = f"""
        SELECT {case_sql} AS kategorie_kod,
            SUM(COALESCE(NULLIF(Pocet_kusu, 0), 1) * COALESCE(Cena_ks_vcl_DPH, 0)) AS obrat,
            SUM(CASE WHEN COALESCE(Cena_ks_vcl_DPH, 0) >= 0
                THEN COALESCE(NULLIF(Pocet_kusu, 0), 1)
                ELSE -COALESCE(NULLIF(Pocet_kusu, 0), 1) END) AS kusy
        FROM WEB_PRODEJE_ALL
        WHERE Vystaveno >= %s AND Vystaveno < %s
        AND (Cena_ks_vcl_DPH > 14 OR Cena_ks_vcl_DPH < 0)
        AND KATEGORIE IS NOT NULL AND TRIM(COALESCE(KATEGORIE,'')) != ''
        AND COALESCE(KATEGORIE,'') != 'Nezařazeno'
        GROUP BY kategorie_kod
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
    result = {}
    for row in rows:
        kod, obrat, kusy = row
        if kod:
            result[kod] = {
                'obrat': Decimal(str(obrat)) if obrat else Decimal('0'),
                'kusy': int(kusy) if kusy is not None else 0,
            }
    return result


def plneni_prodejny_do_data(rok, mesic, end_date):
    """
    Vrátí plnění per prodejna od 1. dne měsíce do end_date (včetně).
    Pro výpočet trendu u prodejen.
    """
    start_d = date(rok, mesic, 1).isoformat()
    end_d = (end_date + timedelta(days=1)).isoformat()
    case_sql = _kategorie_case_sql()
    params = ['%servis eda%', '%!Servis%', start_d, end_d]
    sql = f"""
        SELECT COALESCE(ID_PRODEJNY, 0) AS prodejna_id,
            {case_sql} AS kategorie_kod,
            SUM(COALESCE(NULLIF(Pocet_kusu, 0), 1) * COALESCE(Cena_ks_vcl_DPH, 0)) AS obrat,
            SUM(CASE WHEN COALESCE(Cena_ks_vcl_DPH, 0) >= 0
                THEN COALESCE(NULLIF(Pocet_kusu, 0), 1)
                ELSE -COALESCE(NULLIF(Pocet_kusu, 0), 1) END) AS kusy
        FROM WEB_PRODEJE_ALL
        WHERE Vystaveno >= %s AND Vystaveno < %s
        AND (Cena_ks_vcl_DPH > 14 OR Cena_ks_vcl_DPH < 0)
        AND KATEGORIE IS NOT NULL AND TRIM(COALESCE(KATEGORIE,'')) != ''
        AND COALESCE(KATEGORIE,'') != 'Nezařazeno'
        GROUP BY prodejna_id, kategorie_kod
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
    result = {}
    for row in rows:
        prodejna_id, kod, obrat, kusy = row
        pid = int(prodejna_id) if prodejna_id is not None else 0
        if pid not in result:
            result[pid] = {'obrat': Decimal('0'), 'kusy': 0, 'kategorie': {}}
        result[pid]['obrat'] += Decimal(str(obrat)) if obrat else Decimal('0')
        result[pid]['kusy'] += int(kusy) if kusy is not None else 0
        if kod:
            if kod not in result[pid]['kategorie']:
                result[pid]['kategorie'][kod] = {'obrat': Decimal('0'), 'kusy': 0}
            result[pid]['kategorie'][kod]['obrat'] += Decimal(str(obrat)) if obrat else Decimal('0')
            result[pid]['kategorie'][kod]['kusy'] += int(kusy) if kusy is not None else 0
    return result


def plneni_prodejny(rok, mesic):
    """
    Vrátí plnění per prodejna a per kategorie v prodejně.
    Returns: dict { prodejna_id: { obrat: Decimal, kusy: int, kategorie: { kod: { obrat, kusy } } } }
    """
    start_d, end_d = _base_where_params(rok, mesic)
    case_sql = _kategorie_case_sql()

    sql = f"""
        SELECT
            COALESCE(ID_PRODEJNY, 0) AS prodejna_id,
            {case_sql} AS kategorie_kod,
            SUM(COALESCE(NULLIF(Pocet_kusu, 0), 1) * COALESCE(Cena_ks_vcl_DPH, 0)) AS obrat,
            SUM(
                CASE WHEN COALESCE(Cena_ks_vcl_DPH, 0) >= 0
                THEN COALESCE(NULLIF(Pocet_kusu, 0), 1)
                ELSE -COALESCE(NULLIF(Pocet_kusu, 0), 1)
                END
            ) AS kusy
        FROM WEB_PRODEJE_ALL
        WHERE Vystaveno >= %s AND Vystaveno < %s
        AND (
            Cena_ks_vcl_DPH > 14
            OR Cena_ks_vcl_DPH < 0
        )
        AND KATEGORIE IS NOT NULL
        AND TRIM(COALESCE(KATEGORIE,'')) != ''
        AND COALESCE(KATEGORIE,'') != 'Nezařazeno'
        GROUP BY prodejna_id, kategorie_kod
    """
    params = ['%servis eda%', '%!Servis%', start_d, end_d]

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    result = {}
    for row in rows:
        prodejna_id, kod, obrat, kusy = row
        pid = int(prodejna_id) if prodejna_id is not None else 0
        if pid not in result:
            result[pid] = {'obrat': Decimal('0'), 'kusy': 0, 'kategorie': {}}
        result[pid]['obrat'] += Decimal(str(obrat)) if obrat else Decimal('0')
        result[pid]['kusy'] += int(kusy) if kusy is not None else 0
        if kod:
            if kod not in result[pid]['kategorie']:
                result[pid]['kategorie'][kod] = {'obrat': Decimal('0'), 'kusy': 0}
            result[pid]['kategorie'][kod]['obrat'] += Decimal(str(obrat)) if obrat else Decimal('0')
            result[pid]['kategorie'][kod]['kusy'] += int(kusy) if kusy is not None else 0

    return result


def plneni_prodejce(rok, mesic, prodejce_id):
    """
    Vrátí plnění pro konkrétního prodejce za celý měsíc: kusy per kategorie.
    """
    start_d, end_d = _base_where_params(rok, mesic)
    case_sql = _kategorie_case_sql()
    params = ['%servis eda%', '%!Servis%', start_d, end_d, prodejce_id]
    sql = f"""
        SELECT {case_sql} AS kategorie_kod,
            SUM(CASE WHEN COALESCE(Cena_ks_vcl_DPH, 0) >= 0
                THEN COALESCE(NULLIF(Pocet_kusu, 0), 1)
                ELSE -COALESCE(NULLIF(Pocet_kusu, 0), 1) END) AS kusy
        FROM WEB_PRODEJE_ALL
        WHERE Vystaveno >= %s AND Vystaveno < %s
        AND (Cena_ks_vcl_DPH > 14 OR Cena_ks_vcl_DPH < 0)
        AND KATEGORIE IS NOT NULL AND TRIM(COALESCE(KATEGORIE,'')) != ''
        AND COALESCE(KATEGORIE,'') != 'Nezařazeno'
        AND ID_PRODEJCE = %s
        GROUP BY kategorie_kod
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
    return {row[0]: int(row[1]) if row[1] is not None else 0 for row in rows if row[0]}


def plneni_prodejce_s_detailem(rok, mesic, prodejce_id):
    """
    Vrátí plnění prodejce za celý měsíc: obrat celkem + obrat a kusy per kategorie.
    Returns: {obrat: Decimal, kategorie: {kod: {obrat: Decimal, kusy: int}}}
    """
    start_d, end_d = _base_where_params(rok, mesic)
    case_sql = _kategorie_case_sql()
    params = ['%servis eda%', '%!Servis%', start_d, end_d, prodejce_id]
    sql = f"""
        SELECT {case_sql} AS kategorie_kod,
            SUM(COALESCE(NULLIF(Pocet_kusu, 0), 1) * COALESCE(Cena_ks_vcl_DPH, 0)) AS obrat,
            SUM(CASE WHEN COALESCE(Cena_ks_vcl_DPH, 0) >= 0
                THEN COALESCE(NULLIF(Pocet_kusu, 0), 1)
                ELSE -COALESCE(NULLIF(Pocet_kusu, 0), 1) END) AS kusy
        FROM WEB_PRODEJE_ALL
        WHERE Vystaveno >= %s AND Vystaveno < %s
        AND (Cena_ks_vcl_DPH > 14 OR Cena_ks_vcl_DPH < 0)
        AND KATEGORIE IS NOT NULL AND TRIM(COALESCE(KATEGORIE,'')) != ''
        AND COALESCE(KATEGORIE,'') != 'Nezařazeno'
        AND ID_PRODEJCE = %s
        GROUP BY kategorie_kod
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
    result = {'obrat': Decimal('0'), 'kategorie': {}}
    for row in rows:
        kod, obrat, kusy = row
        if kod:
            obrat_val = Decimal(str(obrat)) if obrat else Decimal('0')
            kusy_val = int(kusy) if kusy is not None else 0
            result['obrat'] += obrat_val
            result['kategorie'][kod] = {'obrat': obrat_val, 'kusy': kusy_val}
    return result


def plneni_prodejce_den(datum, prodejce_id):
    """
    Plnění prodejce za jeden konkrétní den: kusy per kategorie.
    Pro denní zobrazení Můj plán.
    """
    start_d = datum.isoformat()
    end_d = (datum + timedelta(days=1)).isoformat()
    case_sql = _kategorie_case_sql()
    params = ['%servis eda%', '%!Servis%', start_d, end_d, prodejce_id]
    sql = f"""
        SELECT {case_sql} AS kategorie_kod,
            SUM(CASE WHEN COALESCE(Cena_ks_vcl_DPH, 0) >= 0
                THEN COALESCE(NULLIF(Pocet_kusu, 0), 1)
                ELSE -COALESCE(NULLIF(Pocet_kusu, 0), 1) END) AS kusy
        FROM WEB_PRODEJE_ALL
        WHERE Vystaveno >= %s AND Vystaveno < %s
        AND (Cena_ks_vcl_DPH > 14 OR Cena_ks_vcl_DPH < 0)
        AND KATEGORIE IS NOT NULL AND TRIM(COALESCE(KATEGORIE,'')) != ''
        AND COALESCE(KATEGORIE,'') != 'Nezařazeno'
        AND ID_PRODEJCE = %s
        GROUP BY kategorie_kod
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
    return {row[0]: int(row[1]) if row[1] else 0 for row in rows if row[0]}


def plneni_prodejce_do_data(rok, mesic, end_date, prodejce_id):
    """Plnění prodejce od 1. dne do end_date – pro trend (kusy per kategorie)."""
    start_d = date(rok, mesic, 1).isoformat()
    end_d = (end_date + timedelta(days=1)).isoformat()
    case_sql = _kategorie_case_sql()
    params = ['%servis eda%', '%!Servis%', start_d, end_d, prodejce_id]
    sql = f"""
        SELECT {case_sql} AS kategorie_kod,
            SUM(CASE WHEN COALESCE(Cena_ks_vcl_DPH, 0) >= 0
                THEN COALESCE(NULLIF(Pocet_kusu, 0), 1)
                ELSE -COALESCE(NULLIF(Pocet_kusu, 0), 1) END) AS kusy
        FROM WEB_PRODEJE_ALL
        WHERE Vystaveno >= %s AND Vystaveno < %s
        AND (Cena_ks_vcl_DPH > 14 OR Cena_ks_vcl_DPH < 0)
        AND KATEGORIE IS NOT NULL AND TRIM(COALESCE(KATEGORIE,'')) != ''
        AND COALESCE(KATEGORIE,'') != 'Nezařazeno'
        AND ID_PRODEJCE = %s
        GROUP BY kategorie_kod
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
    return {row[0]: int(row[1]) if row[1] else 0 for row in rows if row[0]}


def plneni_prodejce_obrat_do_data(rok, mesic, end_date, prodejce_id):
    """Obrat prodejce od 1. dne do end_date – pro trend."""
    start_d = date(rok, mesic, 1).isoformat()
    end_d = (end_date + timedelta(days=1)).isoformat()
    params = [start_d, end_d, prodejce_id]
    sql = """
        SELECT SUM(COALESCE(NULLIF(Pocet_kusu, 0), 1) * COALESCE(Cena_ks_vcl_DPH, 0)) AS obrat
        FROM WEB_PRODEJE_ALL
        WHERE Vystaveno >= %s AND Vystaveno < %s
        AND (Cena_ks_vcl_DPH > 14 OR Cena_ks_vcl_DPH < 0)
        AND KATEGORIE IS NOT NULL AND TRIM(COALESCE(KATEGORIE,'')) != ''
        AND COALESCE(KATEGORIE,'') != 'Nezařazeno'
        AND ID_PRODEJCE = %s
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
    return Decimal(str(row[0])) if row and row[0] else Decimal('0')


def plneni_celkem_firma(rok, mesic):
    """Celkový obrat a kusy za firmu v daném měsíci."""
    start_d, end_d = _base_where_params(rok, mesic)
    case_sql = _kategorie_case_sql()

    sql = f"""
        SELECT
            SUM(COALESCE(NULLIF(Pocet_kusu, 0), 1) * COALESCE(Cena_ks_vcl_DPH, 0)) AS obrat,
            SUM(
                CASE WHEN COALESCE(Cena_ks_vcl_DPH, 0) >= 0
                THEN COALESCE(NULLIF(Pocet_kusu, 0), 1)
                ELSE -COALESCE(NULLIF(Pocet_kusu, 0), 1)
                END
            ) AS kusy
        FROM WEB_PRODEJE_ALL
        WHERE Vystaveno >= %s AND Vystaveno < %s
        AND (
            Cena_ks_vcl_DPH > 14
            OR Cena_ks_vcl_DPH < 0
        )
        AND KATEGORIE IS NOT NULL
        AND TRIM(COALESCE(KATEGORIE,'')) != ''
        AND COALESCE(KATEGORIE,'') != 'Nezařazeno'
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [start_d, end_d])
        row = cursor.fetchone()

    obrat = Decimal(str(row[0])) if row and row[0] else Decimal('0')
    kusy = int(row[1]) if row and row[1] is not None else 0
    return {'obrat': obrat, 'kusy': kusy}
