"""
Přepočet přiřazení prodejců podle směn (hodiny v měsíci).

- Po založení plánů na rok: hned pro všech 12 měsíců (kde plán existuje).
- Od 15. dne v měsíci: denně aktuální + příští měsíc (cron).
- Před 15.: jen příští měsíc (směny pro běžící měsíc se ještě doplňují).
"""
from datetime import date

from .models import PlanMonth
from .prodejci_auto import prirad_prodejce_automaticky


def mesice_pro_denni_prepocet(reference=None):
    """
    Které měsíce přepočítat při denním běhu.
    Od 15. včetně: aktuální + příští; před 15.: jen příští.
    """
    ref = reference or date.today()
    r, m = ref.year, ref.month

    def next_month(rok, mesic):
        if mesic == 12:
            return rok + 1, 1
        return rok, mesic + 1

    if ref.day >= 15:
        return [(r, m), next_month(r, m)]
    return [next_month(r, m)]


def prepocet_prodejci_mesic(rok, mesic):
    """
    Přepíše PlanProdejce podle směn v daném měsíci.
    Vrací dict s výsledkem (plan existuje / warnings).
    """
    plan = PlanMonth.objects.filter(rok=rok, mesic=mesic, je_aktualni=True).first()
    if not plan:
        return {
            'rok': rok,
            'mesic': mesic,
            'prepocet': False,
            'reason': 'no_plan',
            'warnings': [],
        }
    res = prirad_prodejce_automaticky(plan)
    return {
        'rok': rok,
        'mesic': mesic,
        'prepocet': True,
        'plan_id': plan.id,
        'prirazeno_prodejen': res.get('prirazeno_prodejen', 0),
        'warnings': res.get('warnings', []),
    }


def prepocet_prodejci_mesice(mesice, reference=None):
    """Smyčka měsíců; souhrn pro API / command."""
    warnings = []
    vysledky = []
    for rok, mesic in mesice:
        out = prepocet_prodejci_mesic(rok, mesic)
        vysledky.append(out)
        warnings.extend(out.get('warnings', []))
    prepocetano = sum(1 for v in vysledky if v.get('prepocet'))
    return {
        'vysledky': vysledky,
        'pocet_prepocet': prepocetano,
        'warnings': warnings,
        'mesice': mesice_pro_denni_prepocet(reference) if reference else None,
    }
