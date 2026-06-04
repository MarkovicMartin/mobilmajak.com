"""
Historické plnění a signály pro řízení prodejců.
"""
from decimal import Decimal

from .models import PlanMonth
from .plneni import mesice_pred_planem, plneni_prodejce_s_detailem

NAZVY_MESICU = {
    1: 'Leden', 2: 'Únor', 3: 'Březen', 4: 'Duben',
    5: 'Květen', 6: 'Červen', 7: 'Červenec', 8: 'Srpen',
    9: 'Září', 10: 'Říjen', 11: 'Listopad', 12: 'Prosinec',
}


def _plan_kusy_prodejce(rok, mesic, user_id):
    plan = PlanMonth.objects.filter(rok=rok, mesic=mesic, je_aktualni=True).first()
    if not plan:
        return 0, {}
    total = 0
    per_kat = {}
    for ps in plan.prodejny.prefetch_related('plany_prodejcu__kategorie'):
        for pp in ps.plany_prodejcu.filter(uzivatel_id=user_id):
            for k in pp.kategorie.all():
                total += k.pocet_kusu
                per_kat[k.kategorie_kod] = per_kat.get(k.kategorie_kod, 0) + k.pocet_kusu
    return total, per_kat


def historie_plneni_prodejce(user_id, rok, mesic):
    """
    Plnění prodejce za 3 měsíce před (rok, mesic) + signály pro UI.
    """
    mesice = []
    pcts = []
    kat_silne = {}
    kat_slabe = {}

    for r, m in mesice_pred_planem(rok, mesic, 3):
        skut = plneni_prodejce_s_detailem(r, m, user_id)
        plan_kusy, plan_kat = _plan_kusy_prodejce(r, m, user_id)
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
