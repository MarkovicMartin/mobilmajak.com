"""
Historické plnění a signály pro řízení prodejců.
"""
from decimal import Decimal

from .models import PlanMonth
from .plneni import mesice_pred_planem, plneni_prodejci_s_detailem_batch

NAZVY_MESICU = {
    1: 'Leden', 2: 'Únor', 3: 'Březen', 4: 'Duben',
    5: 'Květen', 6: 'Červen', 7: 'Červenec', 8: 'Srpen',
    9: 'Září', 10: 'Říjen', 11: 'Listopad', 12: 'Prosinec',
}



def _plan_kusy_vsech_prodejcu(user_ids, months):
    """
    Plánované kusy pro více prodejců a měsíců.
    Returns: {(user_id, rok, mesic): (total_kusy, {kod: kusy})}
    """
    if not user_ids or not months:
        return {}
    ids = set(int(u) for u in user_ids)
    month_set = set((int(r), int(m)) for r, m in months)
    roky = {r for r, _ in month_set}
    result = {}

    plans = PlanMonth.objects.filter(
        je_aktualni=True,
        rok__in=roky,
    ).prefetch_related(
        'prodejny__plany_prodejcu__kategorie',
        'prodejny__plany_prodejcu__uzivatel',
    )
    for plan in plans:
        key_month = (plan.rok, plan.mesic)
        if key_month not in month_set:
            continue
        for ps in plan.prodejny.all():
            for pp in ps.plany_prodejcu.all():
                uid = pp.uzivatel_id
                if uid not in ids:
                    continue
                user_key = (uid, plan.rok, plan.mesic)
                total, per_kat = result.get(user_key, (0, {}))
                per_kat = dict(per_kat)
                for k in pp.kategorie.all():
                    total += k.pocet_kusu
                    per_kat[k.kategorie_kod] = per_kat.get(k.kategorie_kod, 0) + k.pocet_kusu
                result[user_key] = (total, per_kat)
    return result


def _historie_z_dat(user_id, hist_months, skut_by_month, plan_by_month):
    """Sestaví historii pro jednoho prodejce z předpočítaných dat."""
    mesice = []
    pcts = []
    kat_silne = {}
    kat_slabe = {}

    for r, m in hist_months:
        skut = skut_by_month.get((r, m), {}).get(
            user_id, {'obrat': Decimal('0'), 'kategorie': {}},
        )
        plan_kusy, plan_kat = plan_by_month.get((user_id, r, m), (0, {}))
        skut_kusy = sum(k['kusy'] for k in skut['kategorie'].values())
        pct = round((skut_kusy / plan_kusy * 100), 1) if plan_kusy > 0 else None
        if pct is not None:
            pcts.append(pct)

        kat_detail = []
        for kod, sk in skut['kategorie'].items():
            pk = plan_kat.get(kod, 0)
            pct_k = round((sk['kusy'] / pk * 100), 1) if pk > 0 else None
            kat_detail.append({
                'kategorie_kod': kod,
                'plneni_procent': pct_k,
                'skutecne_kusy': sk['kusy'],
                'plan_kusy': pk,
            })
            if pct_k is not None:
                if pct_k >= 100:
                    kat_silne[kod] = kat_silne.get(kod, 0) + 1
                elif pct_k < 85:
                    kat_slabe[kod] = kat_slabe.get(kod, 0) + 1

        mesice.append({
            'rok': r,
            'mesic': m,
            'mesic_nazev': NAZVY_MESICU.get(m, ''),
            'plneni_procent_kusy': pct,
            'skutecne_kusy': skut_kusy,
            'plan_kusy': plan_kusy,
            'skutecny_obrat': round(float(skut['obrat']), 2),
            'kategorie': kat_detail,
        })

    systematicky_pod = len(pcts) >= 3 and all(p < 85 for p in pcts)
    silne = [k for k, c in kat_silne.items() if c >= 2]
    slabe = [k for k, c in kat_slabe.items() if c >= 2]
    prumer_pct = round(sum(pcts) / len(pcts), 1) if pcts else None

    return {
        'mesice': mesice,
        'signaly': {
            'systematicky_pod_planem': systematicky_pod,
            'silne_kategorie': silne,
            'slabe_kategorie': slabe,
        },
        'prumer_plneni_3m': prumer_pct,
    }


def historie_plneni_prodejci_batch(user_ids, rok, mesic):
    """
    Historie 3 měsíců pro více prodejců – dávkové SQL místo N×3 dotazů.
    Returns: {user_id: historie_dict}
    """
    if not user_ids:
        return {}
    ids = list({int(u) for u in user_ids})
    hist_months = mesice_pred_planem(rok, mesic, 3)
    skut_by_month = {}
    for r, m in hist_months:
        skut_by_month[(r, m)] = plneni_prodejci_s_detailem_batch(ids, r, m)
    plan_by_month = _plan_kusy_vsech_prodejcu(ids, hist_months)
    return {uid: _historie_z_dat(uid, hist_months, skut_by_month, plan_by_month) for uid in ids}


def historie_plneni_prodejce(user_id, rok, mesic):
    """
    Plnění prodejce za 3 měsíce před (rok, mesic) + signály pro UI.
    """
    batch = historie_plneni_prodejci_batch([user_id], rok, mesic)
    return batch.get(
        int(user_id),
        {
            'mesice': [],
            'signaly': {
                'systematicky_pod_planem': False,
                'silne_kategorie': [],
                'slabe_kategorie': [],
            },
            'prumer_plneni_3m': None,
        },
    )
