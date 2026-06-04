"""
Mapování řádků WEB_PRODEJE_ALL na plánovací kategorie.

Pořadí pravidel v CASE je kritické. Pracovní / skladové kategorie Symplio
padají do PRISLUSENSTVI_OSTATNI (Zbytek), ne do OSTATNI.
"""
from __future__ import annotations

from django.db.models import Case, CharField, Q, Value, When

# Symplio kategorie – dočasné záložky (audit admina, plnění v „Zbytek“)
PRACOVNI_KATEGORIE = (
    'Nově naskladněno',
    'ZALOŽENO RUČNĚ',
    'Zakládání',
    '!Import',
    '!SKLAD',
    'Bordel_neni_skladem',
)

# Skryté z plánu prodejce (admin dál vidí v plnění firmy)
SELLER_HIDDEN_PLAN_KATEGORIE = frozenset({'OSTATNI'})

SELLER_KATEGORIE_NAZVY = {
    'NOVE_TELEFONY': 'Telefony nové',
    'BAZAROVE_TELEFONY': 'Telefony bazarové',
    'PRISLUSENSTVI_SKLA': 'Skla',
    'PRISLUSENSTVI_OBALY': 'Obaly',
    'PRISLUSENSTVI_OSTATNI': 'Zbytek',
    'SLUZBY': 'Služby',
    'SERVIS': 'Servis',
}

SERVIS_NAZEV_HINT = (
    'Počítají se opravy, které jsi provedl jako technik — ne prodej na účtence.'
)


def _sql_literal_list(values):
    return ', '.join("'" + str(v).replace("'", "''") + "'" for v in values)


def kategorie_case_params():
    """Zpětná kompatibilita – CASE už nepoužívá parametry."""
    return []


def kategorie_case_sql():
    """SQL CASE … END pro mapování na kategorie_kod."""
    pracovni_in = _sql_literal_list(PRACOVNI_KATEGORIE)
    return f"""
        CASE
            WHEN KATEGORIE_1 = 'Služby' OR KATEGORIE = 'Služby' THEN 'SLUZBY'
            WHEN KATEGORIE LIKE '%%!Servis%%'
                 AND (
                     KATEGORIE_1 IS NULL OR KATEGORIE_1 = ''
                     OR (KATEGORIE_1 NOT LIKE 'Služby%%' AND KATEGORIE_1 != 'Služby')
                 )
            THEN 'SERVIS'
            WHEN KATEGORIE = 'NOVÉ TELEFONY' THEN 'NOVE_TELEFONY'
            WHEN KATEGORIE IN ('POUŽITÉ TELEFONY', '!Výkup bazaru') THEN 'BAZAROVE_TELEFONY'
            WHEN KATEGORIE = 'PŘÍSLUŠENSTVÍ' AND KATEGORIE_1 = 'Skla a fólie' THEN 'PRISLUSENSTVI_SKLA'
            WHEN KATEGORIE = 'PŘÍSLUŠENSTVÍ' AND KATEGORIE_1 = 'Pouzdra a kryty' THEN 'PRISLUSENSTVI_OBALY'
            WHEN KATEGORIE = 'PŘÍSLUŠENSTVÍ' THEN 'PRISLUSENSTVI_OSTATNI'
            WHEN KATEGORIE IN ({pracovni_in}) THEN 'PRISLUSENSTVI_OSTATNI'
            ELSE 'PRISLUSENSTVI_OSTATNI'
        END
    """


def is_pracovni_kategorie(kategorie: str | None) -> bool:
    return bool(kategorie) and kategorie in PRACOVNI_KATEGORIE


def plan_category_case_orm():
    """Django ORM Case – stejná logika jako kategorie_case_sql()."""
    pracovni_q = Q(kategorie__in=PRACOVNI_KATEGORIE)
    servis_q = (
        Q(kategorie__icontains='!Servis')
        & (
            Q(kategorie_1__isnull=True)
            | Q(kategorie_1='')
            | (~Q(kategorie_1__startswith='Služby') & ~Q(kategorie_1='Služby'))
        )
    )
    return Case(
        When(Q(kategorie_1='Služby') | Q(kategorie='Služby'), then=Value('SLUZBY')),
        When(servis_q, then=Value('SERVIS')),
        When(kategorie__iexact='NOVÉ TELEFONY', then=Value('NOVE_TELEFONY')),
        When(
            Q(kategorie__iexact='POUŽITÉ TELEFONY') | Q(kategorie__icontains='!Výkup bazaru'),
            then=Value('BAZAROVE_TELEFONY'),
        ),
        When(
            Q(kategorie__iexact='PŘÍSLUŠENSTVÍ') & Q(kategorie_1='Skla a fólie'),
            then=Value('PRISLUSENSTVI_SKLA'),
        ),
        When(
            Q(kategorie__iexact='PŘÍSLUŠENSTVÍ') & Q(kategorie_1='Pouzdra a kryty'),
            then=Value('PRISLUSENSTVI_OBALY'),
        ),
        When(Q(kategorie__iexact='PŘÍSLUŠENSTVÍ'), then=Value('PRISLUSENSTVI_OSTATNI')),
        When(pracovni_q, then=Value('PRISLUSENSTVI_OSTATNI')),
        default=Value('PRISLUSENSTVI_OSTATNI'),
        output_field=CharField(),
    )


def seller_kategorie_nazev(kod: str, default: str | None = None) -> str:
    return SELLER_KATEGORIE_NAZVY.get(kod, default or kod)


# Od června 2026 plán už nepoužívá samostatný řádek OSTATNI (jen Zbytek).
PLAN_ZBYTEK_OD = (2026, 6)
OSTATNI_KOD = 'OSTATNI'
ZBYTEK_KOD = 'PRISLUSENSTVI_OSTATNI'


def plan_skryt_ostatni(rok: int, mesic: int) -> bool:
    return (rok, mesic) >= PLAN_ZBYTEK_OD


def normalize_plan_kategorie_kod(kod: str, rok: int, mesic: int) -> str:
    """Sloučí OSTATNI do Zbytku pro měsíce od června 2026."""
    if kod == OSTATNI_KOD and plan_skryt_ostatni(rok, mesic):
        return ZBYTEK_KOD
    return kod

