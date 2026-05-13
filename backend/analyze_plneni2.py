#!/usr/bin/env python
"""
Analýza 2 – plná CASE logika, různé měsíce, hledání 666.
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webapp.settings')
django.setup()

from django.db import connection
from datetime import date

CASE_SQL = """
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

BASE_WHERE = """
    WHERE Vystaveno >= %s AND Vystaveno < %s
    AND (Cena_ks_vcl_DPH > 14 OR Cena_ks_vcl_DPH < 0)
    AND KATEGORIE IS NOT NULL
    AND TRIM(COALESCE(KATEGORIE,'')) != ''
    AND COALESCE(KATEGORIE,'') != 'Nezařazeno'
"""

def run(rok, mesic):
    start_d = date(rok, mesic, 1).isoformat()
    end_d = date(rok, mesic + 1, 1).isoformat() if mesic < 12 else date(rok + 1, 1, 1).isoformat()
    params = ['%servis eda%', '%!Servis%', start_d, end_d]

    print(f"\n{'#'*60}")
    print(f"  MĚSÍC: {mesic}/{rok}")
    print('#'*60)

    # Firma – kategorie s plnou CASE logikou
    sql = f"""
        SELECT
            {CASE_SQL} AS kategorie_kod,
            SUM(COALESCE(NULLIF(Pocet_kusu,0),1)) AS kusy
        FROM WEB_PRODEJE_ALL
        {BASE_WHERE}
        GROUP BY kategorie_kod
    """
    with connection.cursor() as c:
        c.execute(sql, params)
        rows = c.fetchall()
    print("\nFIRMA – kusy per kategorie:")
    for r in rows:
        print(f"  {r[0]}: {r[1]} ks")

    # Prodejny – součet SLUZBY
    sql2 = f"""
        SELECT
            COALESCE(ID_PRODEJNY, 0) AS pid,
            {CASE_SQL} AS kategorie_kod,
            SUM(COALESCE(NULLIF(Pocet_kusu,0),1)) AS kusy
        FROM WEB_PRODEJE_ALL
        {BASE_WHERE}
        GROUP BY pid, kategorie_kod
    """
    with connection.cursor() as c:
        c.execute(sql2, params)
        rows2 = c.fetchall()
    sluzby_per_store = sum(r[2] for r in rows2 if r[1] == 'SLUZBY')
    sluzby_firma = next((r[1] for r in rows if r[0] == 'SLUZBY'), 0)
    print(f"\n  SLUZBY firma: {sluzby_firma}, součet prodejen: {sluzby_per_store}")

    # Co mapuje na SLUZBY – rozpad KATEGORIE, KATEGORIE_1
    sql3 = f"""
        SELECT KATEGORIE, KATEGORIE_1, COUNT(*), SUM(COALESCE(NULLIF(Pocet_kusu,0),1))
        FROM WEB_PRODEJE_ALL
        {BASE_WHERE}
        AND (KATEGORIE_1 = 'Služby' OR KATEGORIE = 'Služby')
        GROUP BY KATEGORIE, KATEGORIE_1
    """
    with connection.cursor() as c:
        c.execute(sql3, [start_d, end_d])
        rows3 = c.fetchall()
    print("\nŘádky mapující na SLUZBY (KATEGORIE, KATEGORIE_1):")
    for r in rows3:
        print(f"  {r}")

# Březen 2026
run(2026, 3)
# Únor 2026
run(2026, 2)
# Leden 2026
run(2026, 1)
