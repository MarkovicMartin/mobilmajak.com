"""Admin audit – co v měsíci spadlo do Zbytku z pracovních Symplio kategorií."""
from decimal import Decimal

from django.db import connection

from .category_mapping import PRACOVNI_KATEGORIE, is_pracovni_kategorie, kategorie_case_sql

MAX_POLOZKY_LIMIT = 2000


def _zbytek_audit_where_sql(case_sql: str) -> str:
    pracovni_in = ', '.join("'" + k.replace("'", "''") + "'" for k in PRACOVNI_KATEGORIE)
    return f"""
        Vystaveno >= %s AND Vystaveno < %s
        AND (Cena_ks_vcl_DPH > 14 OR Cena_ks_vcl_DPH < 0)
        AND KATEGORIE IS NOT NULL AND TRIM(COALESCE(KATEGORIE, '')) != ''
        AND COALESCE(KATEGORIE, '') != 'Nezařazeno'
        AND ({case_sql}) = 'PRISLUSENSTVI_OSTATNI'
        AND (
            KATEGORIE IN ({pracovni_in})
            OR KATEGORIE != 'PŘÍSLUŠENSTVÍ'
        )
    """


def audit_zbytek_mesic(rok: int, mesic: int) -> dict:
    from .plneni import _base_where_params

    start_d, end_d = _base_where_params(rok, mesic)
    case_sql = kategorie_case_sql()
    pracovni_set = set(PRACOVNI_KATEGORIE)

    where_sql = _zbytek_audit_where_sql(case_sql)
    sql = f"""
        SELECT KATEGORIE, COALESCE(KATEGORIE_1, ''),
            SUM(
                CASE WHEN COALESCE(Cena_ks_vcl_DPH, 0) >= 0
                THEN COALESCE(NULLIF(Pocet_kusu, 0), 1)
                ELSE -COALESCE(NULLIF(Pocet_kusu, 0), 1) END
            ) AS kusy,
            SUM(COALESCE(NULLIF(Pocet_kusu, 0), 1) * COALESCE(Cena_ks_bez_DPH, Cena_ks_vcl_DPH / 1.21, 0)) AS obrat_bez
        FROM WEB_PRODEJE_ALL
        WHERE {where_sql}
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
        WHERE {where_sql}
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


def audit_zbytek_polozky(
    rok: int,
    mesic: int,
    kategorie: str,
    kategorie_1: str = '',
    *,
    limit: int = 500,
    offset: int = 0,
) -> dict:
    """Položky WEB_PRODEJE_ALL pro jeden řádek auditu (kategorie + podkategorie)."""
    from .plneni import _base_where_params

    start_d, end_d = _base_where_params(rok, mesic)
    case_sql = kategorie_case_sql()
    where_sql = _zbytek_audit_where_sql(case_sql)
    limit = max(1, min(int(limit), MAX_POLOZKY_LIMIT))
    offset = max(0, int(offset))

    base_params = [start_d, end_d, kategorie, kategorie_1 or '']

    count_sql = f"""
        SELECT COUNT(*)
        FROM WEB_PRODEJE_ALL
        WHERE {where_sql}
        AND KATEGORIE = %s
        AND COALESCE(KATEGORIE_1, '') = %s
    """
    items_sql = f"""
        SELECT
            DATE(Vystaveno) AS datum,
            Doklad,
            Objednavka,
            Kod,
            Nazev,
            COALESCE(NULLIF(Pocet_kusu, 0), 1) AS pocet_kusu,
            COALESCE(Cena_ks_bez_DPH, Cena_ks_vcl_DPH / 1.21, 0) AS cena_ks_bez_dph,
            Stredisko,
            ID_PRODEJCE,
            Spravce
        FROM WEB_PRODEJE_ALL
        WHERE {where_sql}
        AND KATEGORIE = %s
        AND COALESCE(KATEGORIE_1, '') = %s
        ORDER BY Vystaveno DESC, Doklad, Kod
        LIMIT %s OFFSET %s
    """

    with connection.cursor() as cursor:
        cursor.execute(count_sql, base_params)
        total = int(cursor.fetchone()[0] or 0)
        cursor.execute(items_sql, base_params + [limit, offset])
        rows = cursor.fetchall()

    items = []
    for row in rows:
        datum, doklad, objednavka, kod, nazev, pocet, cena_bez, stredisko, id_prodejce, spravce = row
        pocet_i = int(pocet or 0)
        cena_f = float(cena_bez or 0)
        items.append({
            'datum': datum.isoformat() if datum else '',
            'doklad': doklad or '',
            'objednavka': objednavka or '',
            'kod': kod or '',
            'nazev': nazev or '',
            'pocet_kusu': pocet_i,
            'cena_ks_bez_dph': round(cena_f, 2),
            'obrat_bez_dph': round(pocet_i * cena_f, 2),
            'stredisko': stredisko or '',
            'id_prodejce': int(id_prodejce) if id_prodejce is not None else None,
            'prodejce': spravce or '',
        })

    return {
        'rok': rok,
        'mesic': mesic,
        'kategorie': kategorie,
        'kategorie_1': kategorie_1 or '',
        'total': total,
        'limit': limit,
        'offset': offset,
        'has_more': offset + len(items) < total,
        'polozky': items,
    }
