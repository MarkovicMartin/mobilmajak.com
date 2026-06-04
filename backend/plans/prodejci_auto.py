"""
Automatické přiřazení plánů prodejcům podle směn v měsíci.

Pravidla:
- Součet hodin práce (cas_od–cas_do) na prodejně za měsíc → podíly (např. 50 % / 40 % / 10 %).
- Kusy v každé kategorii plánu prodejny se rozdělí podle těchto podílů (součet = plán kategorie).
- Zapojeni jsou všichni se směnou typu prace (prodejce, vedoucí, brigádník).
- František Vychodil (id 121): nedostane kategorie kromě SERVIS; jeho „prodejní“ podíl
  jde ostatním (přepočtené podíly bez něj). SERVIS se dělí podle hodin včetně Vychodila.
"""
import math
from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from shifts.models import Smena

from users.models import WebUser
from .models import PlanProdejce, PlanProdejceKategorie, PlanCategory

VYCHODIL_USER_ID = 121


def _hodiny_na_prodejne(rok, mesic, prodejna_id):
    """
    {user_id: součet hodin} za pracovní směny na prodejně v měsíci.
    """
    smeny = Smena.objects.filter(
        prodejna_id=prodejna_id,
        datum__year=rok,
        datum__month=mesic,
        typ_smeny='prace',
        aktivni=True,
    ).select_related('user')
    hodiny = defaultdict(float)
    for s in smeny:
        if not s.user.aktivni:
            continue
        h = s.delka_smeny_hodin
        if h and h > 0:
            hodiny[s.user_id] += float(h)
    return dict(hodiny)


def _podily_z_hodin(hodiny, exclude_user_ids=None):
    """Normalizované podíly 0–1; exclude_user_ids se nezapočítají."""
    exclude = set(exclude_user_ids or [])
    filt = {uid: h for uid, h in hodiny.items() if uid not in exclude and h > 0}
    total = sum(filt.values())
    if total <= 0:
        return {}
    return {uid: h / total for uid, h in filt.items()}


def _rozdel_kusy(celkem, podily):
    """
    Rozdělí celkem kusů podle podílů (součet přesně celkem – největší zbytky).
    """
    celkem = int(celkem)
    if celkem <= 0 or not podily:
        return {}
    s = sum(podily.values())
    if s <= 0:
        return {uid: 0 for uid in podily}
    norm = {uid: p / s for uid, p in podily.items()}
    quotas = {uid: celkem * p for uid, p in norm.items()}
    base = {uid: int(math.floor(q)) for uid, q in quotas.items()}
    left = celkem - sum(base.values())
    order = sorted(
        ((quotas[uid] - base[uid], uid) for uid in norm),
        reverse=True,
    )
    for i in range(max(0, left)):
        base[order[i % len(order)][1]] += 1
    return base


def _domovsky_prodejce_prodejny(prodejna_id):
    """Záloha: domovský aktivní uživatel prodejny (bez Vychodila)."""
    u = WebUser.objects.filter(
        aktivni=True,
        prodejna_id=prodejna_id,
    ).exclude(id=VYCHODIL_USER_ID).order_by('id').first()
    return u.id if u else None


def _kategorie_plan_kusy(plan_prodejna):
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
    prirazeno = 0
    warnings = []
    ps.plany_prodejcu.all().delete()
    kat_kusy = _kategorie_plan_kusy(ps)
    if not kat_kusy:
        return prirazeno, warnings

    hodiny = _hodiny_na_prodejne(rok, mesic, ps.prodejna_id)
    if not hodiny or sum(hodiny.values()) <= 0:
        warnings.append(f'{ps.prodejna.nazev}: žádné odpracované hodiny na směnách.')
        return prirazeno, warnings

    podily_servis = _podily_z_hodin(hodiny)
    podily_prodej = _podily_z_hodin(hodiny, exclude_user_ids=[VYCHODIL_USER_ID])

    if not podily_prodej:
        dom = _domovsky_prodejce_prodejny(ps.prodejna_id)
        if dom:
            podily_prodej = {dom: 1.0}
            warnings.append(
                f'{ps.prodejna.nazev}: prodejní kategorie jen domovskému uživateli '
                f'(směny bez jiného prodejce než Vychodil).'
            )
        else:
            warnings.append(f'{ps.prodejna.nazev}: nelze rozdělit prodejní kategorie.')
            podily_prodej = {}

    prirazeni = defaultdict(dict)

    for kod, plan_k in kat_kusy.items():
        if kod == 'SERVIS':
            podily = podily_servis
        else:
            podily = podily_prodej
        if not podily:
            continue
        for uid, k in _rozdel_kusy(plan_k, podily).items():
            if k > 0:
                prirazeni[uid][kod] = k

    if not prirazeni:
        warnings.append(f'{ps.prodejna.nazev}: žádné přiřazení po rozdělení.')
        return prirazeno, warnings

    if len(hodiny) >= 2:
        celk_h = sum(hodiny.values())
        jmena = {
            u.id: f'{u.jmeno} {u.prijmeni}'.strip()
            for u in WebUser.objects.filter(id__in=hodiny.keys())
        }
        podily_info = ', '.join(
            f'{jmena.get(uid, uid)} {round(100 * h / celk_h, 1)} %'
            for uid, h in sorted(hodiny.items(), key=lambda x: -x[1])
        )
        warnings.append(f'{ps.prodejna.nazev}: podíly dle hodin – {podily_info}')

    for uid, kategorie in prirazeni.items():
        try:
            uzivatel = WebUser.objects.get(id=uid, aktivni=True)
        except WebUser.DoesNotExist:
            continue
        pp = PlanProdejce.objects.create(plan_prodejna=ps, uzivatel=uzivatel)
        for kod, pocet in kategorie.items():
            PlanProdejceKategorie.objects.create(
                plan_prodejce=pp,
                kategorie_kod=kod,
                pocet_kusu=pocet,
                castka=Decimal('0'),
            )
        prirazeno += 1

    return prirazeno, warnings


@transaction.atomic
def prirad_prodejce_automaticky(plan_month, plan_prodejna_id=None):
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
