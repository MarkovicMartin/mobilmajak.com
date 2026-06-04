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


def kategorie_case_params():
    """Parametry pro _kategorie_case_sql (SERVIS podmínky)."""
    return ['%servis eda%', '%!Servis%']


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
    return result


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
