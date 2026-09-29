"""Seznam produktů ve Zbytku, claim uživatele a rozhodnutí o bodu."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from django.db import connection, transaction
from django.utils import timezone

from .audit_zbytek import _zbytek_audit_where_sql
from .category_mapping import PRACOVNI_KATEGORIE, is_pracovni_kategorie, kategorie_case_sql

BODY_ZA_KATEGORII = 1

PLAN_KODY = frozenset({
    'NOVE_TELEFONY',
    'BAZAROVE_TELEFONY',
    'PRISLUSENSTVI_SKLA',
    'PRISLUSENSTVI_OBALY',
    'SLUZBY',
    'SERVIS',
})


class ClaimObsazeny(Exception):
    pass


class UzPotvrzeno(Exception):
    pass


class NeniVAuditu(Exception):
    pass


def plan_kod_pro_kategorii(kategorie: str | None, kategorie_1: str | None) -> str:
    """Stejné pořadí jako kategorie_case_sql, bez SQL."""
    kat = (kategorie or '').strip()
    kat1 = (kategorie_1 or '').strip()
    kat_cf = kat.casefold()
    kat1_cf = kat1.casefold()
    if kat1_cf == 'služby' or kat_cf == 'služby':
        return 'SLUZBY'
    if '!servis' in kat_cf and not kat1_cf.startswith('služby') and kat1_cf != 'služby':
        return 'SERVIS'
    if kat_cf == 'nové telefony':
        return 'NOVE_TELEFONY'
    if kat_cf == 'použité telefony' or '!výkup bazaru' in kat_cf:
        return 'BAZAROVE_TELEFONY'
    if kat_cf == 'příslušenství' and kat1 == 'Skla a fólie':
        return 'PRISLUSENSTVI_SKLA'
    if kat_cf == 'příslušenství' and kat1 == 'Pouzdra a kryty':
        return 'PRISLUSENSTVI_OBALY'
    if kat_cf == 'příslušenství':
        return 'PRISLUSENSTVI_OSTATNI'
    if kat in PRACOVNI_KATEGORIE:
        return 'PRISLUSENSTVI_OSTATNI'
    return 'PRISLUSENSTVI_OSTATNI'


def kategorie_splnuje_plan(kategorie: str | None, kategorie_1: str | None) -> bool:
    """Pracovní záložka body nedá. Zbytek jen přes skutečné Příslušenství."""
    if is_pracovni_kategorie(kategorie):
        return False
    kod = plan_kod_pro_kategorii(kategorie, kategorie_1)
    if kod in PLAN_KODY:
        return True
    return kod == 'PRISLUSENSTVI_OSTATNI' and (kategorie or '').strip().casefold() == 'příslušenství'


def _stejne(a: str | None, b: str | None) -> bool:
    return (a or '').strip() == (b or '').strip()


def rozhodni_kategorii(pred_k, pred_k1, nova_k, nova_k1, *, konflikt=False, chybi=False):
    """Vrátí (stav, poznamka). stav je ceka / potvrzeno / nepotvrzeno."""
    if konflikt:
        return 'ceka', 'V exportu má kód dvě různé kategorie.'
    if chybi or not (nova_k or '').strip():
        return 'nepotvrzeno', 'Kód v exportu vybraného dne není.'
    if _stejne(pred_k, nova_k) and _stejne(pred_k1, nova_k1):
        return 'nepotvrzeno', 'Kategorie se oproti auditu nezměnila.'
    if not kategorie_splnuje_plan(nova_k, nova_k1):
        return 'nepotvrzeno', 'Nová kategorie není zařazená v plánech.'
    return 'potvrzeno', ''


def seskup_podle_kodu(radky: list[dict]) -> list[dict]:
    """Víc kategorií u jednoho kódu srazí na řádek s nejčastější kategorií."""
    by_kod: dict[str, dict] = {}
    for row in radky:
        kod = (row.get('kod') or '').strip()
        if not kod:
            continue
        slot = by_kod.get(kod)
        if slot is None:
            slot = {
                'kod': kod,
                'nazev': row.get('nazev') or '',
                'nalezy': 0,
                'kusy': 0,
                'posledni_den': None,
                'varianty': [],
            }
            by_kod[kod] = slot
        nalezy = int(row.get('nalezy') or 0)
        slot['nalezy'] += nalezy
        slot['kusy'] += int(row.get('kusy') or 0)
        nazev = row.get('nazev') or ''
        if len(nazev) > len(slot['nazev']):
            slot['nazev'] = nazev
        posledni = row.get('posledni_den')
        if posledni and (slot['posledni_den'] is None or posledni > slot['posledni_den']):
            slot['posledni_den'] = posledni
        slot['varianty'].append(row)

    out = []
    for slot in by_kod.values():
        best = max(slot['varianty'], key=lambda v: int(v.get('nalezy') or 0))
        varianty = {
            ((v.get('kategorie') or '').strip(), (v.get('kategorie_1') or '').strip())
            for v in slot['varianty']
        }
        out.append({
            'kod': slot['kod'],
            'nazev': slot['nazev'],
            'kategorie': best.get('kategorie') or '',
            'kategorie_1': best.get('kategorie_1') or '',
            'vice_kategorii': len(varianty) > 1,
            'nalezy': slot['nalezy'],
            'kusy': slot['kusy'],
            'posledni_den': slot['posledni_den'],
        })
    out.sort(key=lambda r: (-r['nalezy'], r['kod']))
    return out


def _audit_group_sql():
    case_sql = kategorie_case_sql()
    where_sql = _zbytek_audit_where_sql(case_sql)
    return f"""
        SELECT
            TRIM(Kod) AS kod,
            COALESCE(MAX(Nazev), '') AS nazev,
            KATEGORIE,
            COALESCE(KATEGORIE_1, '') AS kategorie_1,
            COUNT(*) AS nalezy,
            SUM(
                CASE WHEN COALESCE(Cena_ks_vcl_DPH, 0) >= 0
                THEN COALESCE(NULLIF(Pocet_kusu, 0), 1)
                ELSE -COALESCE(NULLIF(Pocet_kusu, 0), 1) END
            ) AS kusy,
            MAX(DATE(Vystaveno)) AS posledni_den
        FROM WEB_PRODEJE_ALL
        WHERE {where_sql}
          AND Kod IS NOT NULL AND TRIM(Kod) != ''
        GROUP BY TRIM(Kod), KATEGORIE, KATEGORIE_1
    """


def produkty_mesice(rok: int, mesic: int) -> list[dict]:
    from .plneni import _base_where_params

    start_d, end_d = _base_where_params(rok, mesic)
    sql = _audit_group_sql()
    raw = []
    with connection.cursor() as cursor:
        cursor.execute(sql, [start_d, end_d])
        for kod, nazev, kat, kat1, nalezy, kusy, posledni in cursor.fetchall():
            if isinstance(posledni, datetime):
                posledni = posledni.date()
            raw.append({
                'kod': kod or '',
                'nazev': nazev or '',
                'kategorie': kat or '',
                'kategorie_1': kat1 or '',
                'nalezy': int(nalezy or 0),
                'kusy': int(kusy or 0),
                'posledni_den': posledni,
            })
    return seskup_podle_kodu(raw)


def polozky_kodu(rok: int, mesic: int, kod: str, *, limit: int = 200) -> list[dict]:
    from .plneni import _base_where_params

    start_d, end_d = _base_where_params(rok, mesic)
    case_sql = kategorie_case_sql()
    where_sql = _zbytek_audit_where_sql(case_sql)
    limit = max(1, min(int(limit), 500))
    sql = f"""
        SELECT
            DATE(Vystaveno), Doklad, Objednavka, Kod, Nazev,
            COALESCE(NULLIF(Pocet_kusu, 0), 1),
            COALESCE(Cena_ks_bez_DPH, Cena_ks_vcl_DPH / 1.21, 0),
            Stredisko, ID_PRODEJCE, Spravce
        FROM WEB_PRODEJE_ALL
        WHERE {where_sql}
          AND TRIM(Kod) = %s
        ORDER BY Vystaveno DESC, Doklad
        LIMIT %s
    """
    items = []
    with connection.cursor() as cursor:
        cursor.execute(sql, [start_d, end_d, kod.strip(), limit])
        for row in cursor.fetchall():
            datum, doklad, objednavka, kod_r, nazev, pocet, cena_bez, stredisko, id_prodejce, spravce = row
            pocet_i = int(pocet or 0)
            cena_f = float(cena_bez or 0)
            items.append({
                'datum': datum.isoformat() if datum else '',
                'doklad': doklad or '',
                'objednavka': objednavka or '',
                'kod': kod_r or '',
                'nazev': nazev or '',
                'pocet_kusu': pocet_i,
                'obrat_bez_dph': round(pocet_i * cena_f, 2),
                'stredisko': stredisko or '',
                'id_prodejce': int(id_prodejce) if id_prodejce is not None else None,
                'prodejce': spravce or '',
            })
    return items


def _jmeno(user) -> str:
    return f'{user.jmeno} {user.prijmeni}'.strip()


def obohatit_o_claimy(radky: list[dict], user) -> list[dict]:
    from .models import KategorieZboziClaim

    kody = [r['kod'] for r in radky]
    if not kody:
        return radky
    ceka = {
        c.kod: c
        for c in KategorieZboziClaim.objects.filter(
            kod__in=kody, stav=KategorieZboziClaim.STAV_CEKA,
        ).select_related('user')
    }
    potvrzene = set(
        KategorieZboziClaim.objects.filter(
            kod__in=kody, stav=KategorieZboziClaim.STAV_POTVRZENO,
        ).values_list('kod', flat=True)
    )
    moje_fail = {}
    for c in KategorieZboziClaim.objects.filter(
        kod__in=kody,
        user=user,
        stav=KategorieZboziClaim.STAV_NEPOTVRZENO,
    ).order_by('vytvoreno'):
        moje_fail[c.kod] = c

    for row in radky:
        claim = ceka.get(row['kod'])
        fail = moje_fail.get(row['kod'])
        posledni = row.get('posledni_den')
        row['posledni_den'] = posledni.isoformat() if hasattr(posledni, 'isoformat') else (posledni or '')
        row['claim_id'] = claim.id if claim else None
        row['claim_stav'] = claim.stav if claim else ''
        row['claim_user_id'] = claim.user_id if claim else None
        row['claim_jmeno'] = _jmeno(claim.user) if claim else ''
        row['moje'] = bool(claim and claim.user_id == user.id)
        row['uz_potvrzeno'] = row['kod'] in potvrzene
        row['nepotvrzeno_poznamka'] = fail.poznamka if fail and not claim else ''
    return radky


def moje_body(user, rok: int, mesic: int) -> int:
    from .models import KategorieZboziClaim

    return KategorieZboziClaim.objects.filter(
        user=user,
        stav=KategorieZboziClaim.STAV_POTVRZENO,
        overeno__year=rok,
        overeno__month=mesic,
    ).count() * BODY_ZA_KATEGORII


def zaloz_claim(user, kod: str, rok: int, mesic: int):
    from .models import KategorieZboziClaim

    kod = (kod or '').strip()
    if not kod:
        raise NeniVAuditu()
    with transaction.atomic():
        otevreny = (
            KategorieZboziClaim.objects.select_for_update()
            .filter(kod=kod, stav=KategorieZboziClaim.STAV_CEKA)
            .first()
        )
        if otevreny:
            if otevreny.user_id != user.id:
                raise ClaimObsazeny()
            return otevreny
        if KategorieZboziClaim.objects.filter(
            kod=kod, stav=KategorieZboziClaim.STAV_POTVRZENO,
        ).exists():
            raise UzPotvrzeno()
        produkt = next((p for p in produkty_mesice(rok, mesic) if p['kod'] == kod), None)
        if not produkt:
            raise NeniVAuditu()
        return KategorieZboziClaim.objects.create(
            kod=kod,
            nazev=(produkt.get('nazev') or '')[:255],
            rok=rok,
            mesic=mesic,
            user=user,
            kategorie_pred=produkt.get('kategorie') or '',
            kategorie_1_pred=produkt.get('kategorie_1') or '',
        )


def zrus_claim(user, claim_id: int) -> bool:
    from .models import KategorieZboziClaim

    deleted, _ = KategorieZboziClaim.objects.filter(
        id=claim_id,
        user=user,
        stav=KategorieZboziClaim.STAV_CEKA,
    ).delete()
    return bool(deleted)


def aktualizuj_nazev_kodu(kod: str, nazev: str) -> int:
    """Přepíše název u všech prodejů daného P kódu, pokud se označení změnilo."""
    nazev = (nazev or '').strip()
    if not nazev:
        return 0
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE WEB_PRODEJE_ALL
            SET Nazev = %s
            WHERE TRIM(Kod) = %s
              AND NOT (Nazev <=> %s)
            """,
            [nazev, kod, nazev],
        )
        return cursor.rowcount


def aktualizuj_kategorii_kodu(kod: str, kategorie: str, kategorie_1: str, kategorie_2: str = '') -> int:
    """Přepíše kategorii u všech prodejů daného P kódu. Vrátí počet řádků."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE WEB_PRODEJE_ALL
            SET KATEGORIE = %s, KATEGORIE_1 = %s, KATEGORIE_2 = %s
            WHERE TRIM(Kod) = %s
              AND NOT (
                KATEGORIE <=> %s
                AND KATEGORIE_1 <=> %s
                AND KATEGORIE_2 <=> %s
              )
            """,
            [
                kategorie or None,
                kategorie_1 or None,
                kategorie_2 or None,
                kod,
                kategorie or None,
                kategorie_1 or None,
                kategorie_2 or None,
            ],
        )
        return cursor.rowcount


def zapis_odmenu(claim):
    from shifts.models import MzdovaOdmenaMesic

    when = claim.overeno or timezone.now()
    local = timezone.localtime(when) if timezone.is_aware(when) else when
    mesic = date(local.year, local.month, 1)
    nazev = (claim.nazev or '').strip()
    poznamka = f'Kategorie zboží: {claim.kod}'
    if nazev:
        poznamka = f'{poznamka} {nazev}'
    odmena = MzdovaOdmenaMesic.objects.create(
        user=claim.user,
        mesic=mesic,
        castka=Decimal(BODY_ZA_KATEGORII),
        poznamka=poznamka[:500],
        vytvoril=None,
    )
    claim.odmena = odmena
    claim.body = Decimal(BODY_ZA_KATEGORII)
    return odmena


def aplikuj_vysledek(claim, nova_k, nova_k1, nova_k2='', nazev='', *, konflikt=False, chybi=False):
    """Rozhodne claim, případně přepíše prodeje a připíše odměnu."""
    from .models import KategorieZboziClaim

    stav, poznamka = rozhodni_kategorii(
        claim.kategorie_pred,
        claim.kategorie_1_pred,
        nova_k,
        nova_k1,
        konflikt=konflikt,
        chybi=chybi,
    )
    if stav == 'ceka':
        claim.poznamka = poznamka
        claim.save(update_fields=['poznamka'])
        return stav

    zmena = not _stejne(claim.kategorie_pred, nova_k) or not _stejne(claim.kategorie_1_pred, nova_k1)
    prepsano = False
    if not chybi and not konflikt and (nova_k or '').strip() and zmena:
        aktualizuj_kategorii_kodu(claim.kod, nova_k, nova_k1, nova_k2)
        prepsano = True
    novy_nazev = (nazev or '').strip()
    if not chybi and not konflikt and novy_nazev and not _stejne(claim.nazev, novy_nazev):
        aktualizuj_nazev_kodu(claim.kod, novy_nazev)
        claim.nazev = novy_nazev

    claim.stav = (
        KategorieZboziClaim.STAV_POTVRZENO if stav == 'potvrzeno'
        else KategorieZboziClaim.STAV_NEPOTVRZENO
    )
    claim.kategorie_po = nova_k or ''
    claim.kategorie_1_po = nova_k1 or ''
    claim.prepsano = prepsano
    claim.poznamka = poznamka
    claim.overeno = timezone.now()
    if stav == 'potvrzeno':
        zapis_odmenu(claim)
    claim.save()
    return stav


def body_podle_uzivatele(od: date, do: date) -> dict[int, int]:
    from django.db.models import Count

    from .models import KategorieZboziClaim

    rows = (
        KategorieZboziClaim.objects.filter(
            stav=KategorieZboziClaim.STAV_POTVRZENO,
            overeno__date__gte=od,
            overeno__date__lte=do,
        )
        .values('user_id')
        .annotate(pocet=Count('id'))
    )
    return {int(row['user_id']): int(row['pocet']) * BODY_ZA_KATEGORII for row in rows}


def body_podle_prodejny(od: date, do: date) -> dict[int, int]:
    from django.db.models import Count

    from .models import KategorieZboziClaim

    rows = (
        KategorieZboziClaim.objects.filter(
            stav=KategorieZboziClaim.STAV_POTVRZENO,
            overeno__date__gte=od,
            overeno__date__lte=do,
            user__prodejna_id__isnull=False,
        )
        .values('user__prodejna_id')
        .annotate(pocet=Count('id'))
    )
    return {
        int(row['user__prodejna_id']): int(row['pocet']) * BODY_ZA_KATEGORII
        for row in rows
    }


def _kat_text(kat: str, kat1: str) -> str:
    kat = (kat or '').strip()
    kat1 = (kat1 or '').strip()
    if kat and kat1:
        return f'{kat} · {kat1}'
    return kat or kat1


def audit_radky(rok: int, mesic: int) -> list[dict]:
    """Všechna odškrtnutí v měsíci pro admin kontrolu zařazení."""
    from .models import KategorieZboziClaim

    claims = (
        KategorieZboziClaim.objects.filter(rok=rok, mesic=mesic)
        .select_related('user')
        .order_by('-vytvoreno')
    )
    radky = []
    for claim in claims:
        radky.append({
            'id': claim.id,
            'kod': claim.kod,
            'nazev': claim.nazev,
            'prodejce': _jmeno(claim.user),
            'stav': claim.stav,
            'kategorie_pred': _kat_text(claim.kategorie_pred, claim.kategorie_1_pred),
            'kategorie_po': _kat_text(claim.kategorie_po, claim.kategorie_1_po),
            'prepsano': bool(claim.prepsano),
            'zkontrolovano': bool(claim.zkontrolovano),
            'body': int(claim.body or 0),
            'poznamka': claim.poznamka,
            'vytvoreno': claim.vytvoreno.isoformat() if claim.vytvoreno else '',
            'overeno': claim.overeno.isoformat() if claim.overeno else '',
        })
    return radky


def oznac_audit(ids: list[int], zkontrolovano: bool) -> int:
    from .models import KategorieZboziClaim

    if not ids:
        return 0
    return KategorieZboziClaim.objects.filter(id__in=ids).update(
        zkontrolovano=zkontrolovano,
        zkontrolovano_kdy=timezone.now() if zkontrolovano else None,
    )


def cekajici_claimy():
    from .models import KategorieZboziClaim

    return list(
        KategorieZboziClaim.objects.filter(stav=KategorieZboziClaim.STAV_CEKA)
        .select_related('user')
        .order_by('vytvoreno')
    )
