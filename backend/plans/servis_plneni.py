"""
Plnění kategorie SERVIS podle sloupce Technik (kdo opravil), stejně jako výplaty.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import connection

from analytics.technik_utils import _load_technik_maps
from users.models import WebUser

# Stejné filtry jako servisní odměna ve výplatách (analytics.views)
_SERVIS_BASE_WHERE = """
    Objednavku_zalozil LIKE %s
    AND COALESCE(k_servisu, '') = 'ANO'
    AND KATEGORIE LIKE %s
    AND (
        KATEGORIE_1 IS NULL OR KATEGORIE_1 = ''
        OR (KATEGORIE_1 NOT LIKE 'Služby%%' AND KATEGORIE_1 != 'Služby')
    )
"""

_PLNENI_ROW_WHERE = """
    Vystaveno >= %s AND Vystaveno < %s
    AND (Cena_ks_vcl_DPH > 14 OR Cena_ks_vcl_DPH < 0)
    AND KATEGORIE IS NOT NULL AND TRIM(COALESCE(KATEGORIE, '')) != ''
    AND COALESCE(KATEGORIE, '') != 'Nezařazeno'
"""


def technik_variants_for_user(user) -> list[str]:
    if not user or not getattr(user, 'technik_id', None):
        return []
    name = f'{user.jmeno} {user.prijmeni}'.strip()
    if not name:
        return []
    _, name_to_variants = _load_technik_maps()
    return list(name_to_variants.get(name, {name}))


def _sql_in_technik(variants: list[str]) -> str:
    if not variants:
        return "''"
    parts = []
    for v in variants:
        esc = str(v).replace("'", "''")
        parts.append(f"'{esc}'")
    return ', '.join(parts)


def _prodejna_clause(prodejna_id: int | None) -> tuple[str, list]:
    if prodejna_id is None:
        return '', []
    return ' AND COALESCE(ID_PRODEJNY, 0) = %s', [prodejna_id]


def servis_plneni_kusy_for_user(
    user_id: int, start_d: str, end_d: str, prodejna_id: int | None = None,
) -> int:
    try:
        user = WebUser.objects.get(id=user_id)
    except WebUser.DoesNotExist:
        return 0
    variants = technik_variants_for_user(user)
    if not variants:
        return 0
    in_clause = _sql_in_technik(variants)
    prodejna_sql, prodejna_params = _prodejna_clause(prodejna_id)
    sql = f"""
        SELECT SUM(
            CASE WHEN COALESCE(Cena_ks_vcl_DPH, 0) >= 0
            THEN COALESCE(NULLIF(Pocet_kusu, 0), 1)
            ELSE -COALESCE(NULLIF(Pocet_kusu, 0), 1) END
        ) AS kusy
        FROM WEB_PRODEJE_ALL
        WHERE {_PLNENI_ROW_WHERE}
        AND {_SERVIS_BASE_WHERE}
        AND Technik IN ({in_clause}){prodejna_sql}
    """
    params = [start_d, end_d, '%servis eda%', '%!Servis%', *prodejna_params]
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def servis_plneni_detail_for_user(
    user_id: int, start_d: str, end_d: str, prodejna_id: int | None = None,
) -> tuple[int, Decimal]:
    try:
        user = WebUser.objects.get(id=user_id)
    except WebUser.DoesNotExist:
        return 0, Decimal('0')
    variants = technik_variants_for_user(user)
    if not variants:
        return 0, Decimal('0')
    in_clause = _sql_in_technik(variants)
    prodejna_sql, prodejna_params = _prodejna_clause(prodejna_id)
    sql = f"""
        SELECT
            SUM(COALESCE(NULLIF(Pocet_kusu, 0), 1) * COALESCE(Cena_ks_vcl_DPH, 0)) AS obrat,
            SUM(
                CASE WHEN COALESCE(Cena_ks_vcl_DPH, 0) >= 0
                THEN COALESCE(NULLIF(Pocet_kusu, 0), 1)
                ELSE -COALESCE(NULLIF(Pocet_kusu, 0), 1) END
            ) AS kusy
        FROM WEB_PRODEJE_ALL
        WHERE {_PLNENI_ROW_WHERE}
        AND {_SERVIS_BASE_WHERE}
        AND Technik IN ({in_clause}){prodejna_sql}
    """
    params = [start_d, end_d, '%servis eda%', '%!Servis%', *prodejna_params]
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
    if not row:
        return 0, Decimal('0')
    obrat = Decimal(str(row[0])) if row[0] else Decimal('0')
    kusy = int(row[1]) if row[1] is not None else 0
    return kusy, obrat


def apply_servis_to_plneni_dict(
    data: dict, user_id: int, start_d: str, end_d: str, prodejna_id: int | None = None,
) -> dict:
    """Nahradí SERVIS z ID_PRODEJCE hodnotou podle Technik."""
    out = dict(data)
    out.pop('SERVIS', None)
    kusy = servis_plneni_kusy_for_user(user_id, start_d, end_d, prodejna_id=prodejna_id)
    if kusy:
        out['SERVIS'] = kusy
    return out


def apply_servis_to_plneni_detail(
    result: dict, user_id: int, start_d: str, end_d: str, prodejna_id: int | None = None,
) -> dict:
    kat = dict(result.get('kategorie') or {})
    old = kat.pop('SERVIS', None)
    if old:
        result['obrat'] -= old.get('obrat', Decimal('0'))
    kusy, obrat = servis_plneni_detail_for_user(user_id, start_d, end_d, prodejna_id=prodejna_id)
    if kusy:
        kat['SERVIS'] = {'obrat': obrat, 'kusy': kusy}
        result['obrat'] = result.get('obrat', Decimal('0')) + obrat
    result['kategorie'] = kat
    return result


def technik_variant_to_user_id_map() -> dict[str, int]:
    """Raw hodnota Technik -> WebUser.id (pro dávkové plnění)."""
    _, name_to_variants = _load_technik_maps()
    out: dict[str, int] = {}
    for user in WebUser.objects.exclude(technik_id__isnull=True).exclude(technik_id=0):
        name = f'{user.jmeno} {user.prijmeni}'.strip()
        if not name:
            continue
        for raw in name_to_variants.get(name, {name}):
            out[raw] = user.id
    return out


def batch_servis_plneni_by_month(start_d: str, end_d: str, user_ids: list[int] | None = None) -> dict:
    """
    {(user_id, rok, mesic): kusy} pro SERVIS podle Technik.
    """
    variant_map = technik_variant_to_user_id_map()
    if not variant_map:
        return {}
    if user_ids is not None:
        allowed = set(int(u) for u in user_ids)
        variant_map = {k: v for k, v in variant_map.items() if v in allowed}
    if not variant_map:
        return {}

    result: dict[tuple[int, int, int], int] = {}
    by_user: dict[int, list[str]] = {}
    for raw, uid in variant_map.items():
        by_user.setdefault(uid, []).append(raw)

    for uid, variants in by_user.items():
        in_clause = _sql_in_technik(variants)
        sql = f"""
            SELECT YEAR(Vystaveno) AS rok, MONTH(Vystaveno) AS mesic,
                SUM(
                    CASE WHEN COALESCE(Cena_ks_vcl_DPH, 0) >= 0
                    THEN COALESCE(NULLIF(Pocet_kusu, 0), 1)
                    ELSE -COALESCE(NULLIF(Pocet_kusu, 0), 1) END
                ) AS kusy
            FROM WEB_PRODEJE_ALL
            WHERE {_PLNENI_ROW_WHERE}
            AND {_SERVIS_BASE_WHERE}
            AND Technik IN ({in_clause})
            GROUP BY YEAR(Vystaveno), MONTH(Vystaveno)
        """
        params = [start_d, end_d, '%servis eda%', '%!Servis%']
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            for rok, mesic, kusy in cursor.fetchall():
                if kusy:
                    result[(uid, int(rok), int(mesic))] = int(kusy)
    return result
