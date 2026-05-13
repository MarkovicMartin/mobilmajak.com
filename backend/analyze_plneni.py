#!/usr/bin/env python
"""
Analýza WEB_PRODEJE_ALL – hledání příčiny rozdílu firma vs. prodejny u Služeb.
Spustit: cd backend && python analyze_plneni.py
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webapp.settings')
django.setup()

from django.db import connection
from datetime import date

# Aktuální měsíc (březen 2026)
ROK, MESIC = 2026, 3
start_d = date(ROK, MESIC, 1).isoformat()
end_d = date(ROK, MESIC + 1, 1).isoformat() if MESIC < 12 else date(ROK + 1, 1, 1).isoformat()

BASE_WHERE = """
    WHERE Vystaveno >= %s AND Vystaveno < %s
    AND (Cena_ks_vcl_DPH > 14 OR Cena_ks_vcl_DPH < 0)
    AND KATEGORIE IS NOT NULL
    AND TRIM(COALESCE(KATEGORIE,'')) != ''
    AND COALESCE(KATEGORIE,'') != 'Nezařazeno'
"""

def run_query(title, sql, params=None):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)
    with connection.cursor() as c:
        c.execute(sql, params or [start_d, end_d])
        rows = c.fetchall()
        for r in rows:
            print(r)
    return rows

# 1. Služby – rozpad podle ID_PRODEJNY
run_query("1. SLUŽBY – kusy podle ID_PRODEJNY (KATEGORIE_1='Služby' OR KATEGORIE='Služby')", f"""
    SELECT 
        COALESCE(ID_PRODEJNY, -999) AS prodejna_id,
        COUNT(*) AS pocet_radku,
        SUM(COALESCE(NULLIF(Pocet_kusu,0),1)) AS kusy
    FROM WEB_PRODEJE_ALL
    {BASE_WHERE}
    AND (KATEGORIE_1 = 'Služby' OR KATEGORIE = 'Služby')
    GROUP BY COALESCE(ID_PRODEJNY, -999)
    ORDER BY kusy DESC
""")

# 2. Služby s NULL/0 ID_PRODEJNY – detail
run_query("2. SLUŽBY s ID_PRODEJNY NULL nebo 0 – kolik?", f"""
    SELECT 
        ID_PRODEJNY,
        Marketingovy_kanal,
        Dropshipping,
        COUNT(*) AS pocet_radku,
        SUM(COALESCE(NULLIF(Pocet_kusu,0),1)) AS kusy
    FROM WEB_PRODEJE_ALL
    {BASE_WHERE}
    AND (KATEGORIE_1 = 'Služby' OR KATEGORIE = 'Služby')
    AND (ID_PRODEJNY IS NULL OR ID_PRODEJNY = 0)
    GROUP BY ID_PRODEJNY, Marketingovy_kanal, Dropshipping
""")

# 3. Všechny unikátní ID_PRODEJNY v plánu vs. v datech
run_query("3. Všechna ID_PRODEJNY v datech za měsíc", f"""
    SELECT DISTINCT ID_PRODEJNY
    FROM WEB_PRODEJE_ALL
    {BASE_WHERE}
    ORDER BY ID_PRODEJNY
""")

# 4. Služby – rozpad podle Marketingovy_kanal
run_query("4. SLUŽBY – rozpad podle Marketingovy_kanal", f"""
    SELECT 
        COALESCE(Marketingovy_kanal, '(NULL)') AS kanal,
        COUNT(*) AS pocet_radku,
        SUM(COALESCE(NULLIF(Pocet_kusu,0),1)) AS kusy
    FROM WEB_PRODEJE_ALL
    {BASE_WHERE}
    AND (KATEGORIE_1 = 'Služby' OR KATEGORIE = 'Služby')
    GROUP BY Marketingovy_kanal
    ORDER BY kusy DESC
""")

# 5. Součet kusů Služeb na prodejnách (jen ty s platným ID)
run_query("5. Součet SLUŽEB jen tam kde ID_PRODEJNY IN (prodejny z plánu)", f"""
    SELECT SUM(kusy) AS celkem
    FROM (
        SELECT 
            COALESCE(ID_PRODEJNY, 0) AS pid,
            SUM(COALESCE(NULLIF(Pocet_kusu,0),1)) AS kusy
        FROM WEB_PRODEJE_ALL
        {BASE_WHERE}
        AND (KATEGORIE_1 = 'Služby' OR KATEGORIE = 'Služby')
        AND ID_PRODEJNY IS NOT NULL AND ID_PRODEJNY != 0
        GROUP BY ID_PRODEJNY
    ) t
""")

# 6. Celkový počet Služeb (firma)
run_query("6. CELKEM Služeb (firma – bez filtru na prodejnu)", f"""
    SELECT SUM(COALESCE(NULLIF(Pocet_kusu,0),1)) AS kusy
    FROM WEB_PRODEJE_ALL
    {BASE_WHERE}
    AND (KATEGORIE_1 = 'Služby' OR KATEGORIE = 'Služby')
""")

print("\n" + "="*60)
print("  KONEC ANALÝZY")
print("="*60)
