"""
Automatické přiřazení plánů prodejcům podle směn.

Pravidla:
- Brigádník nedostane cíle.
- Hlavní prodejce = PRODEJCE/VEDOUCI s nejvíce směnami na prodejně → 100 % kusů z plánu prodejny.
- František Vychodil (id 121): při ≥2 lidech se směnou na prodejně jen SERVIS z 3m průměru.
"""
import math
from decimal import Decimal

from django.db import transaction
from shifts.models import Smena

from users.models import WebUser
from .models import PlanProdejce, PlanProdejceKategorie, PlanCategory
from .plneni import mesice_pred_planem, plneni_prodejce_za_obdobi

VYCHODIL_USER_ID = 121
GOAL_ROLES = ('PRODEJCE', 'VEDOUCI')


def _pocet_smen_na_prodejne(rok, mesic, prodejna_id, user_id):
    return Smena.objects.filter(
        user_id=user_id,
        prodejna_id=prodejna_id,
        datum__year=rok,
        datum__month=mesic,
        typ_smeny='prace',
        aktivni=True,
    ).count()


def _lide_se_smenou_na_prodejne(rok, mesic, prodejna_id):
    """Distinct user_id s alespoň jednou pracovní směnou."""
    qs = Smena.objects.filter(
        prodejna_id=prodejna_id,
        datum__year=rok,
        datum__month=mesic,
        typ_smeny='prace',
        aktivni=True,
    ).values_list('user_id', flat=True).distinct()
    return set(qs)


def _hlavni_prodejce_id(rok, mesic, prodejna_id, exclude_user_ids=None):
    exclude = set(exclude_user_ids or [])
    counts = {}
    for uid in _lide_se_smenou_na_prodejne(rok, mesic, prodejna_id):
        if uid in exclude:
            continue
        try:
            user = WebUser.objects.get(id=uid, aktivni=True)
        except WebUser.DoesNotExist:
            continue
        if user.role not in GOAL_ROLES:
            continue
        c = _pocet_smen_na_prodejne(rok, mesic, prodejna_id, uid)
        if c > 0:
            counts[uid] = c
    if not counts:
        return None
    return max(counts, key=counts.get)


def _servis_kusy_vychodil(rok, mesic, prodejna_id):
    months = mesice_pred_planem(rok, mesic, 3)
    if not months:
        return 0
    rok_od, mesic_od = months[0]
    rok_do, mesic_do = months[-1]
    det = plneni_prodejce_za_obdobi(
        VYCHODIL_USER_ID, rok_od, mesic_od, rok_do, mesic_do, prodejna_id=prodejna_id
    )
    return max(0, round(det.get('kategorie', {}).get('SERVIS', {}).get('kusy', 0)))


def _kategorie_plan_kusy(plan_prodejna):
    """{kategorie_kod: pocet_kusu} z PlanCategory."""
    result = {}
    for pk in PlanCategory.objects.filter(plan_prodejna=plan_prodejna):
        if pk.prumerna_cena_za_kus and pk.prumerna_cena_za_kus > 0:
            kusy = math.ceil(float(pk.castka_kategorie) / float(pk.prumerna_cena_za_kus))
        else:
            kusy = 0
        if kusy > 0:
            result[pk.kategorie_kod] = kusy
    return result


def _prirad_prodejce_prodejna(ps, rok, mesic):
    """Přiřadí prodejce pro jednu PlanStore. Returns (prirazeno_count, warnings)."""
    prirazeno = 0
    warnings = []
    ps.plany_prodejcu.all().delete()
    kat_kusy = _kategorie_plan_kusy(ps)
    if not kat_kusy:
        return prirazeno, warnings

    lide = _lide_se_smenou_na_prodejne(rok, mesic, ps.prodejna_id)
    vychodil_aktivni = VYCHODIL_USER_ID in lide
    dvojobsazeni = len(lide) >= 2

    if vychodil_aktivni and dvojobsazeni:
        servis_kusy = _servis_kusy_vychodil(rok, mesic, ps.prodejna_id)
        if servis_kusy > 0 and 'SERVIS' in kat_kusy:
            vychodil_pp = PlanProdejce.objects.create(
                plan_prodejna=ps,
                uzivatel_id=VYCHODIL_USER_ID,
            )
            PlanProdejceKategorie.objects.create(
                plan_prodejce=vychodil_pp,
                kategorie_kod='SERVIS',
                pocet_kusu=servis_kusy,
                castka=Decimal('0'),
            )
            prirazeno += 1

    exclude = [VYCHODIL_USER_ID] if vychodil_aktivni and dvojobsazeni else []
    hlavni_id = _hlavni_prodejce_id(rok, mesic, ps.prodejna_id, exclude_user_ids=exclude)
    if not hlavni_id:
        warnings.append(f'{ps.prodejna.nazev}: nenalezen hlavní prodejce se směnami.')
        return prirazeno, warnings

    hlavni_pp = PlanProdejce.objects.create(plan_prodejna=ps, uzivatel_id=hlavni_id)
    for kod, kusy in kat_kusy.items():
        if vychodil_aktivni and dvojobsazeni and hlavni_id != VYCHODIL_USER_ID and kod == 'SERVIS':
            continue
        PlanProdejceKategorie.objects.create(
            plan_prodejce=hlavni_pp,
            kategorie_kod=kod,
            pocet_kusu=kusy,
            castka=Decimal('0'),
        )
    prirazeno += 1
    return prirazeno, warnings


@transaction.atomic
def prirad_prodejce_automaticky(plan_month, plan_prodejna_id=None):
    """
    Pro každou (nebo jednu) prodejnu v plánu nastaví PlanProdejce dle směn.
    """
    rok, mesic = plan_month.rok, plan_month.mesic
    qs = plan_month.prodejny.select_related('prodejna').prefetch_related('kategorie')
    if plan_prodejna_id is not None:
        qs = qs.filter(id=plan_prodejna_id)
    prirazeno = 0
    warnings = []
    for ps in qs:
        p, w = _prirad_prodejce_prodejna(ps, rok, mesic)
        prirazeno += p
        warnings.extend(w)
    return {'prirazeno_prodejen': prirazeno, 'warnings': warnings}
