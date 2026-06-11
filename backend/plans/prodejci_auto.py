"""
Automatické přiřazení plánů prodejcům podle směn v měsíci.

Prodejní kategorie: hodiny směn pozice=prodej (nebo všechny při legacy).
SERVIS: efektivní servisní hodiny (intervaly na Globusu, jinak dle pozice/úrovně),
legacy fallback = technik_id + všechny hodiny dokud není servisní směna v měsíci.
"""
import math
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from shifts.models import Smena

from users.models import WebUser
from .models import PlanProdejce, PlanProdejceKategorie, PlanCategory

VYCHODIL_USER_ID = 121

ZAUCENI_SERVIS_VAHA = Decimal('0.2')
VIKEND_PRODEJ_SERVIS_VAHA = Decimal('0.4')
TYDEN_SOUBEZ_PRODEJ_SERVIS_VAHA = Decimal('0.2')
SERVIS_UROVEN_VAHA = {
    'plny': Decimal('1'),
    'zauceni': ZAUCENI_SERVIS_VAHA,
    'zadna': Decimal('0'),
}


def _user_servis_uroven(user):
    return getattr(user, 'servis_uroven', None) or 'zadna'


def _schopny_servisu(user):
    return _user_servis_uroven(user) in ('zauceni', 'plny')


def _smeny_mesic_qs(rok, mesic, prodejna_id):
    return Smena.objects.filter(
        prodejna_id=prodejna_id,
        datum__year=rok,
        datum__month=mesic,
        typ_smeny='prace',
        aktivni=True,
    ).select_related('user')


def _ma_servis_smeny_v_mesici(rok, mesic, prodejna_id):
    return _smeny_mesic_qs(rok, mesic, prodejna_id).filter(pozice_smeny='servis').exists()


def _hodiny_na_prodejne(rok, mesic, prodejna_id, jen_prodej_pozice=False):
    """{user_id: součet hodin} za pracovní směny na prodejně v měsíci."""
    smeny = _smeny_mesic_qs(rok, mesic, prodejna_id)
    if jen_prodej_pozice:
        smeny = smeny.filter(pozice_smeny='prodej')
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


def _smena_interval_bounds(datum, cas_od, cas_do):
    start = datetime.combine(datum, cas_od)
    end = datetime.combine(datum, cas_do)
    if end <= start:
        end += timedelta(days=1)
    return start, end


def _active_in_segment(smena, seg_start, seg_end):
    s_start, s_end = _smena_interval_bounds(smena.datum, smena.cas_od, smena.cas_do)
    return s_start < seg_end and s_end > seg_start


def _iter_day_segments(smeny):
    if not smeny:
        return
    datum = smeny[0].datum
    points = set()
    for s in smeny:
        st, en = _smena_interval_bounds(datum, s.cas_od, s.cas_do)
        points.add(st)
        points.add(en)
    ordered = sorted(points)
    for i in range(len(ordered) - 1):
        seg_start, seg_end = ordered[i], ordered[i + 1]
        dur_h = (seg_end - seg_start).total_seconds() / 3600.0
        if dur_h <= 0:
            continue
        active = [s for s in smeny if _active_in_segment(s, seg_start, seg_end)]
        if active:
            yield dur_h, active


def _globus_segment_contributions(datum, active_smeny):
    """
    Efektivní hodiny per user v jednom časovém úseku (Globus – den v týdnu + okrajové směny).
    """
    is_weekend = datum.weekday() >= 5
    raw = defaultdict(lambda: Decimal('0'))
    solo_worker = len(active_smeny) == 1
    has_servis = any((s.pozice_smeny or 'prodej') == 'servis' for s in active_smeny)

    for s in active_smeny:
        uroven = _user_servis_uroven(s.user)
        if uroven == 'zadna':
            continue
        uroven_w = SERVIS_UROVEN_VAHA[uroven]
        pozice = s.pozice_smeny or 'prodej'

        if is_weekend:
            if pozice != 'prodej':
                continue
            raw[s.user_id] += VIKEND_PRODEJ_SERVIS_VAHA * uroven_w
            continue

        if pozice == 'servis':
            raw[s.user_id] += uroven_w
        elif pozice == 'prodej':
            if solo_worker:
                raw[s.user_id] += VIKEND_PRODEJ_SERVIS_VAHA * uroven_w
            elif has_servis:
                raw[s.user_id] += TYDEN_SOUBEZ_PRODEJ_SERVIS_VAHA * uroven_w
            else:
                raw[s.user_id] += uroven_w

    total_raw = sum(raw.values())
    if total_raw <= 0:
        return {}, True
    return {uid: float(w / total_raw) for uid, w in raw.items()}, False


def _servis_interval_contributions_globus(datum, smeny_na_den):
    """{user_id: efektivni_h} za den; vrací i nezaplněné hodiny."""
    result = defaultdict(float)
    uncovered_h = 0.0
    for dur_h, active in _iter_day_segments(smeny_na_den):
        contrib, uncovered = _globus_segment_contributions(datum, active)
        if uncovered:
            uncovered_h += dur_h
            continue
        for uid, share in contrib.items():
            result[uid] += dur_h * share
    return dict(result), uncovered_h


def _efektivni_servis_hodin_jednoduche(smeny):
    """Ostatní prodejny: bez vlivu dne v týdnu, dle pozice a servis_uroven."""
    result = defaultdict(float)
    for s in smeny:
        if not s.user.aktivni:
            continue
        uroven = _user_servis_uroven(s.user)
        if uroven == 'zadna':
            continue
        h = s.delka_smeny_hodin
        if not h or h <= 0:
            continue
        result[s.user_id] += float(h) * float(SERVIS_UROVEN_VAHA[uroven])
    return dict(result)


def _efektivni_servis_hodin_mesic(rok, mesic, prodejna):
    """
    Měsíční efektivní servisní hodiny. None = použít legacy (technik_id).
    Vrací (hodiny_dict, meta) kde meta má uncovered_h, pouzito_globus_pravidla.
    """
    smeny = [
        s for s in _smeny_mesic_qs(rok, mesic, prodejna.id)
        if s.user.aktivni
    ]
    if not _ma_servis_smeny_v_mesici(rok, mesic, prodejna.id):
        return None, {}

    meta = {'uncovered_h': 0.0, 'pouzito_globus_pravidla': False}
    result = defaultdict(float)

    if prodejna.povolena_pozice_servis and prodejna.nazev == 'Globus':
        meta['pouzito_globus_pravidla'] = True
        by_day = defaultdict(list)
        for s in smeny:
            by_day[s.datum].append(s)
        for datum, day_smeny in sorted(by_day.items()):
            day_contrib, unc = _servis_interval_contributions_globus(datum, day_smeny)
            meta['uncovered_h'] += unc
            for uid, h in day_contrib.items():
                result[uid] += h
    elif prodejna.povolena_pozice_servis:
        simple = _efektivni_servis_hodin_jednoduche(smeny)
        for uid, h in simple.items():
            result[uid] += h
    else:
        return None, meta

    return dict(result), meta


def _legacy_podily_servis(hodiny_vse):
    technik_ids = set(
        WebUser.objects.filter(
            id__in=hodiny_vse.keys(),
            aktivni=True,
        ).exclude(technik_id__isnull=True).exclude(technik_id=0).values_list('id', flat=True)
    )
    hodiny_technici = {uid: h for uid, h in hodiny_vse.items() if uid in technik_ids}
    return _podily_z_hodin(hodiny_technici)


def _format_podily_info(hodiny, jmena):
    celk_h = sum(hodiny.values())
    if celk_h <= 0:
        return ''
    return ', '.join(
        f'{jmena.get(uid, uid)} {round(100 * h / celk_h, 1)} %'
        for uid, h in sorted(hodiny.items(), key=lambda x: -x[1])
    )


def _prirad_prodejce_prodejna(ps, rok, mesic):
    prirazeno = 0
    warnings = []
    ps.plany_prodejcu.all().delete()
    kat_kusy = _kategorie_plan_kusy(ps)
    if not kat_kusy:
        return prirazeno, warnings

    prodejna = ps.prodejna
    pouzit_novou_logiku = (
        prodejna.povolena_pozice_servis
        and _ma_servis_smeny_v_mesici(rok, mesic, prodejna.id)
    )

    if pouzit_novou_logiku:
        hodiny_prodej = _hodiny_na_prodejne(rok, mesic, prodejna.id, jen_prodej_pozice=True)
    else:
        hodiny_prodej = _hodiny_na_prodejne(rok, mesic, prodejna.id)

    hodiny_vse = _hodiny_na_prodejne(rok, mesic, prodejna.id)
    if not hodiny_vse or sum(hodiny_vse.values()) <= 0:
        warnings.append(f'{prodejna.nazev}: žádné odpracované hodiny na směnách.')
        return prirazeno, warnings

    efektivni_servis, servis_meta = _efektivni_servis_hodin_mesic(rok, mesic, prodejna)
    if efektivni_servis is None:
        podily_servis = _legacy_podily_servis(hodiny_vse)
        if pouzit_novou_logiku is False and prodejna.povolena_pozice_servis:
            warnings.append(
                f'{prodejna.nazev}: žádná směna pozice=servis v měsíci – SERVIS legacy (technik_id).'
            )
    else:
        podily_servis = _podily_z_hodin(efektivni_servis)
        if servis_meta.get('uncovered_h', 0) > 0.05:
            warnings.append(
                f'{prodejna.nazev}: {round(servis_meta["uncovered_h"], 1)} h bez servisního pokrytí.'
            )
        if efektivni_servis:
            jmena = {
                u.id: f'{u.jmeno} {u.prijmeni}'.strip()
                for u in WebUser.objects.filter(id__in=efektivni_servis.keys())
            }
            info = _format_podily_info(efektivni_servis, jmena)
            if info:
                warnings.append(f'{prodejna.nazev}: SERVIS efektivní hodiny – {info}')

    podily_prodej = _podily_z_hodin(hodiny_prodej, exclude_user_ids=[VYCHODIL_USER_ID])

    if not podily_prodej:
        dom = _domovsky_prodejce_prodejny(prodejna.id)
        if dom:
            podily_prodej = {dom: 1.0}
            warnings.append(
                f'{prodejna.nazev}: prodejní kategorie jen domovskému uživateli '
                f'(směny bez jiného prodejce než Vychodil).'
            )
        else:
            warnings.append(f'{prodejna.nazev}: nelze rozdělit prodejní kategorie.')
            podily_prodej = {}

    # Varování: zaškolení bez technik_id
    if pouzit_novou_logiku:
        zauceni_bez_eda = WebUser.objects.filter(
            id__in=set(hodiny_vse.keys()) | set((efektivni_servis or {}).keys()),
            servis_uroven='zauceni',
        ).filter(Q(technik_id__isnull=True) | Q(technik_id=0))
        for u in zauceni_bez_eda:
            warnings.append(
                f'{prodejna.nazev}: {u.jmeno} {u.prijmeni} – zaškolení servis, doplnit technik_id (EDA).'
            )

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
        warnings.append(f'{prodejna.nazev}: žádné přiřazení po rozdělení.')
        return prirazeno, warnings

    if len(hodiny_vse) >= 2:
        jmena = {
            u.id: f'{u.jmeno} {u.prijmeni}'.strip()
            for u in WebUser.objects.filter(id__in=hodiny_vse.keys())
        }
        podily_info = _format_podily_info(hodiny_prodej if pouzit_novou_logiku else hodiny_vse, jmena)
        if podily_info:
            label = 'prodejní hodiny' if pouzit_novou_logiku else 'hodiny'
            warnings.append(f'{prodejna.nazev}: podíly dle {label} – {podily_info}')

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


def porovnej_servis_rozdeleni(rok, mesic, prodejna_id):
    """
    Dry-run: porovná legacy SERVIS podíly vs novou logiku (pro report před deployem).
    """
    from stores.models import Prodejna

    prodejna = Prodejna.objects.get(id=prodejna_id)
    hodiny_vse = _hodiny_na_prodejne(rok, mesic, prodejna_id)
    legacy = _legacy_podily_servis(hodiny_vse)
    efektivni, meta = _efektivni_servis_hodin_mesic(rok, mesic, prodejna)
    nova = _podily_z_hodin(efektivni) if efektivni is not None else legacy

    jmena = {
        u.id: f'{u.jmeno} {u.prijmeni}'.strip()
        for u in WebUser.objects.filter(id__in=set(legacy.keys()) | set(nova.keys()))
    }

    from .models import PlanMonth, PlanStore

    servis_kusy = 0
    pm = PlanMonth.objects.filter(rok=rok, mesic=mesic, je_aktualni=True).first()
    if pm:
        ps = PlanStore.objects.filter(plan_mesic=pm, prodejna_id=prodejna_id).first()
        if ps:
            servis_kusy = _kategorie_plan_kusy(ps).get('SERVIS', 0)

    legacy_kusy = _rozdel_kusy(servis_kusy, legacy) if servis_kusy else {}
    nova_kusy = _rozdel_kusy(servis_kusy, nova) if servis_kusy else {}

    return {
        'prodejna': prodejna.nazev,
        'rok': rok,
        'mesic': mesic,
        'ma_servis_smeny': _ma_servis_smeny_v_mesici(rok, mesic, prodejna_id),
        'servis_kusy_plan': servis_kusy,
        'legacy_podily_pct': {jmena.get(u, u): round(p * 100, 1) for u, p in legacy.items()},
        'nova_podily_pct': {jmena.get(u, u): round(p * 100, 1) for u, p in nova.items()},
        'legacy_kusy': {jmena.get(u, u): k for u, k in legacy_kusy.items()},
        'nova_kusy': {jmena.get(u, u): k for u, k in nova_kusy.items()},
        'meta': meta,
    }
