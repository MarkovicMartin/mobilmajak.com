"""Admin audit – co v měsíci spadlo do Zbytku z pracovních Symplio kategorií."""
from decimal import Decimal

from django.db import connection

from .category_mapping import PRACOVNI_KATEGORIE, is_pracovni_kategorie, kategorie_case_sql


def audit_zbytek_mesic(rok: int, mesic: int) -> dict:
    from .plneni import _base_where_params

    start_d, end_d = _base_where_params(rok, mesic)
    case_sql = kategorie_case_sql()
    pracovni_set = set(PRACOVNI_KATEGORIE)

    sql = f"""
        SELECT KATEGORIE, COALESCE(KATEGORIE_1, ''),
            SUM(
                CASE WHEN COALESCE(Cena_ks_vcl_DPH, 0) >= 0
                THEN COALESCE(NULLIF(Pocet_kusu, 0), 1)
                ELSE -COALESCE(NULLIF(Pocet_kusu, 0), 1) END
            ) AS kusy,
            SUM(COALESCE(NULLIF(Pocet_kusu, 0), 1) * COALESCE(Cena_ks_bez_DPH, Cena_ks_vcl_DPH / 1.21, 0)) AS obrat_bez
        FROM WEB_PRODEJE_ALL
        WHERE Vystaveno >= %s AND Vystaveno < %s
        AND (Cena_ks_vcl_DPH > 14 OR Cena_ks_vcl_DPH < 0)
        AND KATEGORIE IS NOT NULL AND TRIM(COALESCE(KATEGORIE, '')) != ''
        AND COALESCE(KATEGORIE, '') != 'Nezařazeno'
        AND ({case_sql}) = 'PRISLUSENSTVI_OSTATNI'
        AND (
            KATEGORIE IN ({', '.join("'" + k.replace("'", "''") + "'" for k in PRACOVNI_KATEGORIE)})
            OR KATEGORIE != 'PŘÍSLUŠENSTVÍ'
        )
        GROUP BY KATEGORIE, KATEGORIE_1
        ORDER BY kusy DESC
    """
    rows = []
    pracovni_kusy = 0
    pracovni_obrat = Decimal('0')
    ostatni_kusy = 0
    with connection.cursor() as cursor:
        cursor.execute(sql, [start_d, end_d])
        for kat, kat1, kusy, obrat in cursor.fetchall():
            kusy_i = int(kusy or 0)
            obrat_f = float(obrat or 0)
            je_pracovni = is_pracovni_kategorie(kat)
            rows.append({
                'kategorie': kat,
                'kategorie_1': kat1 or '',
                'kusy': kusy_i,
                'obrat_bez_dph': round(obrat_f, 2),
                'je_pracovni': je_pracovni,
            })
            if je_pracovni:
                pracovni_kusy += kusy_i
                pracovni_obrat += Decimal(str(obrat_f))
            else:
                ostatni_kusy += kusy_i

    total_zbytek_sql = f"""
        SELECT SUM(
            CASE WHEN COALESCE(Cena_ks_vcl_DPH, 0) >= 0
            THEN COALESCE(NULLIF(Pocet_kusu, 0), 1)
            ELSE -COALESCE(NULLIF(Pocet_kusu, 0), 1) END
        )
        FROM WEB_PRODEJE_ALL
        WHERE Vystaveno >= %s AND Vystaveno < %s
        AND (Cena_ks_vcl_DPH > 14 OR Cena_ks_vcl_DPH < 0)
        AND KATEGORIE IS NOT NULL AND TRIM(COALESCE(KATEGORIE, '')) != ''
        AND COALESCE(KATEGORIE, '') != 'Nezařazeno'
        AND ({case_sql}) = 'PRISLUSENSTVI_OSTATNI'
    """
    with connection.cursor() as cursor:
        cursor.execute(total_zbytek_sql, [start_d, end_d])
        total_zbytek = int(cursor.fetchone()[0] or 0)

    return {
        'rok': rok,
        'mesic': mesic,
        'celkem_zbytek_kusy': total_zbytek,
        'pracovni_kusy': pracovni_kusy,
        'pracovni_podil_procent': round(100 * pracovni_kusy / total_zbytek, 1) if total_zbytek else 0,
        'pracovni_obrat_bez_dph': float(pracovni_obrat.quantize(Decimal('0.01'))),
        'radky': rows,
        'pracovni_kategorie': list(pracovni_set),
    }
