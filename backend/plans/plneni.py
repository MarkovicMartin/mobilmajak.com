"""
Logika plnění plánu z WEB_PRODEJE_ALL.

Filtry:
- Vystaveno v daném měsíci
- Cena_ks_vcl_DPH > 14 NEBO < 0 (storno) – položky 0–14 Kč vyřazeny
- KATEGORIE vyplněná (ne prázdná, ne NULL, ne Nezařazeno)
- Storna odečítáme (záporná cena)

Mapování kategorií – viz category_mapping.py.
Plnění SERVIS u prodejce podle Technik – viz servis_plneni.py.
"""
import calendar
from datetime import date, timedelta
from decimal import Decimal
from django.db import connection

from .category_mapping import kategorie_case_params, kategorie_case_sql
from .servis_plneni import (
    apply_servis_to_plneni_detail,
    apply_servis_to_plneni_dict,
)


def _kategorie_case_sql():
    return kategorie_case_sql()


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

    params = [start_d, end_d]

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
    params = [start_d, end_d]
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
    params = [start_d, end_d]
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
    params = [start_d, end_d]

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
    params = [start_d, end_d, prodejce_id]
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
    result = {row[0]: int(row[1]) if row[1] is not None else 0 for row in rows if row[0]}
    return apply_servis_to_plneni_dict(result, prodejce_id, start_d, end_d)


def plneni_prodejce_s_detailem(rok, mesic, prodejce_id):
    """
    Vrátí plnění prodejce za celý měsíc: obrat celkem + obrat a kusy per kategorie.
    Returns: {obrat: Decimal, kategorie: {kod: {obrat: Decimal, kusy: int}}}
    """
    start_d, end_d = _base_where_params(rok, mesic)
    case_sql = _kategorie_case_sql()
    params = [start_d, end_d, prodejce_id]
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
    return apply_servis_to_plneni_detail(result, prodejce_id, start_d, end_d)


def plneni_prodejce_den(datum, prodejce_id):
    """
    Plnění prodejce za jeden konkrétní den: kusy per kategorie.
    Pro denní zobrazení Můj plán.
    """
    start_d = datum.isoformat()
    end_d = (datum + timedelta(days=1)).isoformat()
    case_sql = _kategorie_case_sql()
    params = [start_d, end_d, prodejce_id]
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
    result = {row[0]: int(row[1]) if row[1] else 0 for row in rows if row[0]}
    return apply_servis_to_plneni_dict(result, prodejce_id, start_d, end_d)


def plneni_prodejce_do_data(rok, mesic, end_date, prodejce_id):
    """Plnění prodejce od 1. dne do end_date – pro trend (kusy per kategorie)."""
    start_d = date(rok, mesic, 1).isoformat()
    end_d = (end_date + timedelta(days=1)).isoformat()
    case_sql = _kategorie_case_sql()
    params = [start_d, end_d, prodejce_id]
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
    result = {row[0]: int(row[1]) if row[1] else 0 for row in rows if row[0]}
    return apply_servis_to_plneni_dict(result, prodejce_id, start_d, end_d)


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


def _empty_prodejce_detail():
    return {'obrat': Decimal('0'), 'kategorie': {}}


def _apply_servis_detail(detail, servis):
    """Nahradí SERVIS z ID_PRODEJCE hodnotou podle Technik (předpočítaná dávka)."""
    if not servis:
        kat = dict(detail.get('kategorie') or {})
        old = kat.pop('SERVIS', None)
        if old:
            detail['obrat'] -= old.get('obrat', Decimal('0'))
        detail['kategorie'] = kat
        return detail
    kat = dict(detail.get('kategorie') or {})
    old = kat.pop('SERVIS', None)
    obrat = detail.get('obrat', Decimal('0'))
    if old:
        obrat -= old.get('obrat', Decimal('0'))
    kusy = servis.get('kusy', 0)
    servis_obrat = servis.get('obrat', Decimal('0'))
    if kusy:
        kat['SERVIS'] = {'obrat': servis_obrat, 'kusy': kusy}
        obrat += servis_obrat
    detail['obrat'] = obrat
    detail['kategorie'] = kat
    return detail


def _apply_servis_dict(data, servis_kusy):
    """Nahradí SERVIS v dict {kod: kusy} hodnotou podle Technik."""
    out = dict(data)
    out.pop('SERVIS', None)
    if servis_kusy:
        out['SERVIS'] = servis_kusy
    return out


def plneni_prodejci_s_detailem_batch(prodejce_ids, rok, mesic, servis_detail=None):
    """
    Plnění všech prodejců za měsíc v jednom SQL dotazu.
    Returns: {prodejce_id: {obrat, kategorie: {kod: {obrat, kusy}}}}
    """
    if not prodejce_ids:
        return {}
    ids = list({int(x) for x in prodejce_ids})
    start_d, end_d = _base_where_params(rok, mesic)
    case_sql = _kategorie_case_sql()
    placeholders = ', '.join(['%s'] * len(ids))
    params = [start_d, end_d, *ids]
    sql = f"""
        SELECT ID_PRODEJCE, {case_sql} AS kategorie_kod,
            SUM(COALESCE(NULLIF(Pocet_kusu, 0), 1) * COALESCE(Cena_ks_vcl_DPH, 0)) AS obrat,
            SUM(CASE WHEN COALESCE(Cena_ks_vcl_DPH, 0) >= 0
                THEN COALESCE(NULLIF(Pocet_kusu, 0), 1)
                ELSE -COALESCE(NULLIF(Pocet_kusu, 0), 1) END) AS kusy
        FROM WEB_PRODEJE_ALL
        WHERE Vystaveno >= %s AND Vystaveno < %s
        AND (Cena_ks_vcl_DPH > 14 OR Cena_ks_vcl_DPH < 0)
        AND KATEGORIE IS NOT NULL AND TRIM(COALESCE(KATEGORIE,'')) != ''
        AND COALESCE(KATEGORIE,'') != 'Nezařazeno'
        AND ID_PRODEJCE IN ({placeholders})
        GROUP BY ID_PRODEJCE, kategorie_kod
    """
    result = {uid: _empty_prodejce_detail() for uid in ids}
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        for prodejce_id, kod, obrat, kusy in cursor.fetchall():
            if not kod or prodejce_id is None:
                continue
            uid = int(prodejce_id)
            if uid not in result:
                continue
            obrat_val = Decimal(str(obrat)) if obrat else Decimal('0')
            kusy_val = int(kusy) if kusy is not None else 0
            result[uid]['obrat'] += obrat_val
            result[uid]['kategorie'][kod] = {'obrat': obrat_val, 'kusy': kusy_val}
    if servis_detail is None:
        from .servis_plneni import batch_servis_plneni_detail
        servis_detail = batch_servis_plneni_detail(start_d, end_d, ids)
    for uid in ids:
        result[uid] = _apply_servis_detail(result[uid], servis_detail.get(uid))
    return result


def plneni_prodejci_do_data_batch(prodejce_ids, rok, mesic, end_date, servis_kusy=None):
    """Kusy per kategorie pro více prodejců od 1. dne měsíce do end_date."""
    if not prodejce_ids:
        return {}
    ids = list({int(x) for x in prodejce_ids})
    start_d = date(rok, mesic, 1).isoformat()
    end_d = (end_date + timedelta(days=1)).isoformat()
    case_sql = _kategorie_case_sql()
    placeholders = ', '.join(['%s'] * len(ids))
    params = [start_d, end_d, *ids]
    sql = f"""
        SELECT ID_PRODEJCE, {case_sql} AS kategorie_kod,
            SUM(CASE WHEN COALESCE(Cena_ks_vcl_DPH, 0) >= 0
                THEN COALESCE(NULLIF(Pocet_kusu, 0), 1)
                ELSE -COALESCE(NULLIF(Pocet_kusu, 0), 1) END) AS kusy
        FROM WEB_PRODEJE_ALL
        WHERE Vystaveno >= %s AND Vystaveno < %s
        AND (Cena_ks_vcl_DPH > 14 OR Cena_ks_vcl_DPH < 0)
        AND KATEGORIE IS NOT NULL AND TRIM(COALESCE(KATEGORIE,'')) != ''
        AND COALESCE(KATEGORIE,'') != 'Nezařazeno'
        AND ID_PRODEJCE IN ({placeholders})
        GROUP BY ID_PRODEJCE, kategorie_kod
    """
    result = {uid: {} for uid in ids}
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        for prodejce_id, kod, kusy in cursor.fetchall():
            if not kod or prodejce_id is None:
                continue
            uid = int(prodejce_id)
            if uid in result:
                result[uid][kod] = int(kusy) if kusy is not None else 0
    if servis_kusy is None:
        from .servis_plneni import batch_servis_plneni_detail
        servis_kusy = {
            uid: d.get('kusy', 0)
            for uid, d in batch_servis_plneni_detail(start_d, end_d, ids).items()
        }
    return {uid: _apply_servis_dict(result.get(uid, {}), servis_kusy.get(uid, 0)) for uid in ids}


def plneni_prodejci_obrat_do_data_batch(prodejce_ids, rok, mesic, end_date):
    """Obrat per prodejce od 1. dne měsíce do end_date (bez úpravy SERVIS)."""
    if not prodejce_ids:
        return {}
    ids = list({int(x) for x in prodejce_ids})
    start_d = date(rok, mesic, 1).isoformat()
    end_d = (end_date + timedelta(days=1)).isoformat()
    placeholders = ', '.join(['%s'] * len(ids))
    params = [start_d, end_d, *ids]
    sql = f"""
        SELECT ID_PRODEJCE,
            SUM(COALESCE(NULLIF(Pocet_kusu, 0), 1) * COALESCE(Cena_ks_vcl_DPH, 0)) AS obrat
        FROM WEB_PRODEJE_ALL
        WHERE Vystaveno >= %s AND Vystaveno < %s
        AND (Cena_ks_vcl_DPH > 14 OR Cena_ks_vcl_DPH < 0)
        AND KATEGORIE IS NOT NULL AND TRIM(COALESCE(KATEGORIE,'')) != ''
        AND COALESCE(KATEGORIE,'') != 'Nezařazeno'
        AND ID_PRODEJCE IN ({placeholders})
        GROUP BY ID_PRODEJCE
    """
    result = {uid: Decimal('0') for uid in ids}
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        for prodejce_id, obrat in cursor.fetchall():
            if prodejce_id is None:
                continue
            uid = int(prodejce_id)
            if uid in result:
                result[uid] = Decimal(str(obrat)) if obrat else Decimal('0')
    return result


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


def _web_prodeje_base_where(extra=''):
    return f"""
        AND (
            Cena_ks_vcl_DPH > 14
            OR Cena_ks_vcl_DPH < 0
        )
        AND KATEGORIE IS NOT NULL
        AND TRIM(COALESCE(KATEGORIE,'')) != ''
        AND COALESCE(KATEGORIE,'') != 'Nezařazeno'
        {extra}
    """


def dostupne_roky_z_prodeje():
    """Min/max rok z WEB_PRODEJE_ALL (stejné filtry jako plnění)."""
    sql = f"""
        SELECT MIN(YEAR(Vystaveno)), MAX(YEAR(Vystaveno))
        FROM WEB_PRODEJE_ALL
        WHERE Vystaveno IS NOT NULL
        {_web_prodeje_base_where()}
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()
    if not row or row[0] is None or row[1] is None:
        y = date.today().year
        return {'rok_od': y, 'rok_do': y, 'roky': [y]}
    rok_od, rok_do = int(row[0]), int(row[1])
    return {
        'rok_od': rok_od,
        'rok_do': rok_do,
        'roky': list(range(rok_do, rok_od - 1, -1)),
    }


def plneni_celkem_firma_mesicne(rok_od, mesic_od, rok_do, mesic_do, prodejna_id=None, prodejna_ids=None):
    """
    Jeden dotaz: celkový obrat a kusy pro každý kalendářní měsíc v intervalu.
    Vrací {(rok, mesic): {'obrat': Decimal, 'kusy': int}}.
    """
    start_d = date(rok_od, mesic_od, 1).isoformat()
    if mesic_do == 12:
        end_d = date(rok_do + 1, 1, 1).isoformat()
    else:
        end_d = date(rok_do, mesic_do + 1, 1).isoformat()

    extra = ''
    params = [start_d, end_d]
    ids = None
    if prodejna_ids:
        ids = [int(x) for x in prodejna_ids if x is not None]
    elif prodejna_id is not None:
        ids = [int(prodejna_id)]
    if ids:
        placeholders = ','.join(['%s'] * len(ids))
        extra = f' AND COALESCE(ID_PRODEJNY, 0) IN ({placeholders})'
        params.extend(ids)

    sql = f"""
        SELECT
            YEAR(Vystaveno) AS rok,
            MONTH(Vystaveno) AS mesic,
            SUM(COALESCE(NULLIF(Pocet_kusu, 0), 1) * COALESCE(Cena_ks_vcl_DPH, 0)) AS obrat,
            SUM(
                CASE WHEN COALESCE(Cena_ks_vcl_DPH, 0) >= 0
                THEN COALESCE(NULLIF(Pocet_kusu, 0), 1)
                ELSE -COALESCE(NULLIF(Pocet_kusu, 0), 1)
                END
            ) AS kusy
        FROM WEB_PRODEJE_ALL
        WHERE Vystaveno >= %s AND Vystaveno < %s
        {_web_prodeje_base_where(extra)}
        GROUP BY YEAR(Vystaveno), MONTH(Vystaveno)
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    result = {}
    for row in rows:
        if not row or row[0] is None or row[1] is None:
            continue
        key = (int(row[0]), int(row[1]))
        result[key] = {
            'obrat': Decimal(str(row[2])) if row[2] else Decimal('0'),
            'kusy': int(row[3]) if row[3] is not None else 0,
        }
    return result


def pobocky_bez_dat_v_mesici(rok, mesic):
    """
    Aktivní prodejny bez obratu nebo bez směn v daném měsíci (pro náhled ve výhledu).
    """
    from stores.models import Prodejna
    from .prodejci_auto import _hodiny_na_prodejne

    pd = plneni_prodejny(rok, mesic)
    chybi = []
    for p in Prodejna.get_aktivni_prodejny():
        obrat = float(pd.get(p.id, {}).get('obrat', 0) or 0)
        hodiny = _hodiny_na_prodejne(rok, mesic, p.id)
        h_sum = sum(hodiny.values()) if hodiny else 0
        if obrat <= 0 and h_sum <= 0:
            chybi.append({'id': p.id, 'nazev': p.nazev, 'duvod': 'bez_obratu_i_smen'})
        elif obrat <= 0:
            chybi.append({'id': p.id, 'nazev': p.nazev, 'duvod': 'bez_obratu'})
        elif h_sum <= 0:
            chybi.append({'id': p.id, 'nazev': p.nazev, 'duvod': 'bez_smen'})
    return chybi


def _prev_month(rok, mesic):
    """Vrátí (rok, mesic) předchozího kalendářního měsíce."""
    if mesic == 1:
        return rok - 1, 12
    return rok, mesic - 1


def mesice_pred_planem(rok, mesic, pocet=3):
    """
    M−pocet … M−1 vůči cílovému plánovanému měsíci (rok, mesic).
    Např. plán na červen 2026 → březen, duben, květen 2026.
    """
    result = []
    r, m = rok, mesic
    for _ in range(pocet):
        r, m = _prev_month(r, m)
        result.append((r, m))
    result.reverse()
    return result


def plneni_firma_za_obdobi(rok_od, mesic_od, rok_do, mesic_do):
    """
    Průměrné měsíční plnění firmy za období (součet měsíců / počet měsíců s obratem > 0).
    Returns: dict kategorie_kod -> {obrat, kusy} (průměrné měsíční).
    """
    months = _iter_months_inclusive(rok_od, mesic_od, rok_do, mesic_do)
    if not months:
        return {}
    per_month = []
    for r, m in months:
        kat = plneni_firma(r, m)
        total_obrat = sum(d['obrat'] for d in kat.values())
        if total_obrat > 0:
            per_month.append(kat)
    if not per_month:
        return {}
    n = len(per_month)
    result = {}
    all_kody = set()
    for pm in per_month:
        all_kody.update(pm.keys())
    for kod in all_kody:
        obraty = [pm.get(kod, {}).get('obrat', Decimal('0')) for pm in per_month]
        kusy = [pm.get(kod, {}).get('kusy', 0) for pm in per_month]
        result[kod] = {
            'obrat': (sum(obraty, Decimal('0')) / n).quantize(Decimal('0.01')),
            'kusy': round(sum(kusy) / n),
        }
    return result


def plneni_celkem_firma_za_obdobi(rok_od, mesic_od, rok_do, mesic_do):
    """Průměrný měsíční obrat a kusy firmy za období."""
    months = _iter_months_inclusive(rok_od, mesic_od, rok_do, mesic_do)
    obraty = []
    kusy_list = []
    for r, m in months:
        t = plneni_celkem_firma(r, m)
        if t['obrat'] > 0:
            obraty.append(t['obrat'])
            kusy_list.append(t['kusy'])
    if not obraty:
        return {'obrat': Decimal('0'), 'kusy': 0, 'pocet_mesicu': 0}
    n = len(obraty)
    return {
        'obrat': (sum(obraty, Decimal('0')) / n).quantize(Decimal('0.01')),
        'kusy': round(sum(kusy_list) / n),
        'pocet_mesicu': n,
    }


def plneni_prodejny_za_obdobi(rok_od, mesic_od, rok_do, mesic_do):
    """
    Průměrné měsíční plnění per prodejna za období.
    Stejná struktura jako plneni_prodejny().
    """
    months = _iter_months_inclusive(rok_od, mesic_od, rok_do, mesic_do)
    monthly = []
    for r, m in months:
        pd = plneni_prodejny(r, m)
        has_data = any(d.get('obrat', 0) > 0 for d in pd.values())
        if has_data:
            monthly.append(pd)
    if not monthly:
        return {}
    n = len(monthly)
    result = {}
    all_pids = set()
    for pm in monthly:
        all_pids.update(pm.keys())
    for pid in all_pids:
        obraty = []
        kusy_total = []
        kat_acc = {}
        for pm in monthly:
            d = pm.get(pid, {'obrat': Decimal('0'), 'kusy': 0, 'kategorie': {}})
            obraty.append(d.get('obrat', Decimal('0')))
            kusy_total.append(d.get('kusy', 0))
            for kod, kd in d.get('kategorie', {}).items():
                if kod not in kat_acc:
                    kat_acc[kod] = {'obrat': [], 'kusy': []}
                kat_acc[kod]['obrat'].append(kd.get('obrat', Decimal('0')))
                kat_acc[kod]['kusy'].append(kd.get('kusy', 0))
        kategorie = {}
        for kod, acc in kat_acc.items():
            kategorie[kod] = {
                'obrat': (sum(acc['obrat'], Decimal('0')) / n).quantize(Decimal('0.01')),
                'kusy': round(sum(acc['kusy']) / n),
            }
        result[pid] = {
            'obrat': (sum(obraty, Decimal('0')) / n).quantize(Decimal('0.01')),
            'kusy': round(sum(kusy_total) / n),
            'kategorie': kategorie,
        }
    return result


def plneni_prodejce_za_obdobi(prodejce_id, rok_od, mesic_od, rok_do, mesic_do, prodejna_id=None):
    """
    Průměrné měsíční plnění prodejce za období (volitelně jen na prodejně).
    Returns: {obrat, kusy, kategorie: {kod: {obrat, kusy}}}
    """
    months = _iter_months_inclusive(rok_od, mesic_od, rok_do, mesic_do)
    monthly = []
    for r, m in months:
        det = plneni_prodejce_s_detailem(r, m, prodejce_id)
        if prodejna_id is not None:
            det = _filter_prodejce_detail_prodejna(det, r, m, prodejce_id, prodejna_id)
        if det['obrat'] > 0 or det['kategorie']:
            monthly.append(det)
    if not monthly:
        return {'obrat': Decimal('0'), 'kusy': 0, 'kategorie': {}}
    n = len(monthly)
    obraty = [d['obrat'] for d in monthly]
    kusy_celkem = [sum(k['kusy'] for k in d['kategorie'].values()) for d in monthly]
    kat_acc = {}
    for d in monthly:
        for kod, kd in d['kategorie'].items():
            if kod not in kat_acc:
                kat_acc[kod] = {'obrat': [], 'kusy': []}
            kat_acc[kod]['obrat'].append(kd['obrat'])
            kat_acc[kod]['kusy'].append(kd['kusy'])
    kategorie = {}
    for kod, acc in kat_acc.items():
        kategorie[kod] = {
            'obrat': (sum(acc['obrat'], Decimal('0')) / n).quantize(Decimal('0.01')),
            'kusy': round(sum(acc['kusy']) / n),
        }
    return {
        'obrat': (sum(obraty, Decimal('0')) / n).quantize(Decimal('0.01')),
        'kusy': round(sum(kusy_celkem) / n),
        'kategorie': kategorie,
    }


def _filter_prodejce_detail_prodejna(det, rok, mesic, prodejce_id, prodejna_id):
    """Ořízne plnění prodejce na jednu prodejnu (SQL agregace)."""
    start_d, end_d = _base_where_params(rok, mesic)
    case_sql = _kategorie_case_sql()
    params = kategorie_case_params() + [start_d, end_d, prodejce_id, prodejna_id]
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
        AND ID_PRODEJCE = %s AND COALESCE(ID_PRODEJNY, 0) = %s
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
    return apply_servis_to_plneni_detail(result, prodejce_id, start_d, end_d, prodejna_id=prodejna_id)


def plneni_polozky(rok, mesic, kategorie_kod, prodejna_id=None, prodejce_id=None, limit=50):
    """
    Položky (Kod + Nazev) prodané v dané plánovací kategorii za měsíc.
    """
    start_d, end_d = _base_where_params(rok, mesic)
    case_sql = _kategorie_case_sql()
    extra = []
    params = list(kategorie_case_params()) + [start_d, end_d]
    if prodejna_id is not None:
        extra.append('AND COALESCE(ID_PRODEJNY, 0) = %s')
        params.append(prodejna_id)
    if prodejce_id is not None:
        extra.append('AND ID_PRODEJCE = %s')
        params.append(prodejce_id)
    extra_sql = ' '.join(extra)
    params.append(kategorie_kod)
    params.append(limit)
    sql = f"""
        SELECT
            COALESCE(NULLIF(TRIM(Kod), ''), '(bez kódu)') AS kod,
            MAX(COALESCE(Nazev, '')) AS nazev,
            SUM(COALESCE(NULLIF(Pocet_kusu, 0), 1) * COALESCE(Cena_ks_vcl_DPH, 0)) AS obrat,
            SUM(CASE WHEN COALESCE(Cena_ks_vcl_DPH, 0) >= 0
                THEN COALESCE(NULLIF(Pocet_kusu, 0), 1)
                ELSE -COALESCE(NULLIF(Pocet_kusu, 0), 1) END) AS kusy
        FROM WEB_PRODEJE_ALL
        WHERE Vystaveno >= %s AND Vystaveno < %s
        AND (Cena_ks_vcl_DPH > 14 OR Cena_ks_vcl_DPH < 0)
        AND KATEGORIE IS NOT NULL AND TRIM(COALESCE(KATEGORIE,'')) != ''
        AND COALESCE(KATEGORIE,'') != 'Nezařazeno'
        {extra_sql}
        AND ({case_sql}) = %s
        GROUP BY kod
        ORDER BY obrat DESC
        LIMIT %s
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
    result = []
    for kod, nazev, obrat, kusy in rows:
        result.append({
            'kod': kod,
            'nazev': (nazev or '')[:200],
            'obrat': round(float(obrat or 0), 2),
            'kusy': int(kusy) if kusy is not None else 0,
        })
    return result


def _iter_months_inclusive(rok_od, mesic_od, rok_do, mesic_do):
    """Všechny kalendářní měsíce v intervalu včetně krajů."""
    months = []
    r, m = rok_od, mesic_od
    while (r, m) <= (rok_do, mesic_do):
        months.append((r, m))
        if m == 12:
            r, m = r + 1, 1
        else:
            m += 1
    return months
