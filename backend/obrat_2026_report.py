#!/usr/bin/env python
"""
Skript pro výpočet % obratu podle prodejen a kategorií za rok 2026 z WEB_PRODEJE_ALL.
Spustit: python manage.py shell < obrat_2026_report.py
Nebo: cd backend && python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webapp.settings')
django.setup()
exec(open('obrat_2026_report.py').read())
"
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webapp.settings')
django.setup()

from django.db import connection

def run_report():
    with connection.cursor() as cursor:
        # Obrat = Pocet_kusu * Cena_ks_vcl_DPH (cena za kus × počet)
        # Pro řádky kde Pocet_kusu je NULL bereme 1
        obrat_expr = "COALESCE(NULLIF(Pocet_kusu, 0), 1) * COALESCE(Cena_ks_vcl_DPH, 0)"
        
        # Filtr roku 2026 - Vystaveno může být DATE nebo VARCHAR
        year_filter = """
            WHERE (
                (YEAR(Vystaveno) = 2026)
                OR (Vystaveno LIKE '2026-%')
            )
            AND COALESCE(Cena_ks_vcl_DPH, 0) != 0
        """
        
        # 1. Celkový obrat za 2026
        cursor.execute(f"""
            SELECT SUM({obrat_expr}) as celkovy_obrat
            FROM WEB_PRODEJE_ALL
            {year_filter}
        """)
        total = cursor.fetchone()[0]
        total = float(total) if total else 0
        
        print("=" * 60)
        print("OBRAT 2026 - WEB_PRODEJE_ALL")
        print("=" * 60)
        print(f"\nCelkový obrat firmy 2026: {total:,.2f} Kč")
        
        if total == 0:
            print("\n⚠️ Žádná data za rok 2026 v tabulce WEB_PRODEJE_ALL.")
            return
        
        # 2. Obrat podle prodejen (Stredisko - sloupec 8)
        print("\n" + "-" * 60)
        print("1. PODÍL PRODEJEN NA CELKOVÉM OBRATU (%)")
        print("-" * 60)
        
        cursor.execute(f"""
            SELECT 
                COALESCE(Stredisko, '(prázdné)') as prodejna,
                SUM({obrat_expr}) as obrat
            FROM WEB_PRODEJE_ALL
            {year_filter}
            GROUP BY Stredisko
            ORDER BY obrat DESC
        """)
        rows = cursor.fetchall()
        
        for prodejna, obrat in rows:
            pct = (float(obrat) / total * 100) if total else 0
            print(f"  {prodejna}: {float(obrat):,.2f} Kč  ({pct:.1f} %)")
        
        # 3. Obrat podle kategorií (KATEGORIE - sloupec 23)
        print("\n" + "-" * 60)
        print("2. PODÍL KATEGORIÍ NA CELKOVÉM OBRATU (%)")
        print("-" * 60)
        
        cursor.execute(f"""
            SELECT 
                COALESCE(KATEGORIE, '(prázdné)') as kategorie,
                SUM({obrat_expr}) as obrat
            FROM WEB_PRODEJE_ALL
            {year_filter}
            GROUP BY KATEGORIE
            ORDER BY obrat DESC
        """)
        rows = cursor.fetchall()
        
        for kategorie, obrat in rows:
            pct = (float(obrat) / total * 100) if total else 0
            print(f"  {kategorie}: {float(obrat):,.2f} Kč  ({pct:.1f} %)")
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    run_report()
