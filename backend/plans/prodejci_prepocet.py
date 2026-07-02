"""
Přepočet přiřazení prodejců podle směn (hodiny v měsíci).

- Po založení plánů na rok: hned pro všech 12 měsíců (kde plán existuje).
- Denně (cron): jen běžící měsíc; poslední den měsíce navíc příští měsíc.
"""
import calendar
from datetime import date

from .models import PlanMonth
from .prodejci_auto import prirad_prodejce_automaticky


def _next_month(rok, mesic):
    if mesic == 12:
        return rok + 1, 1
    return rok, mesic + 1


def mesice_pro_denni_prepocet(reference=None):
    """
    Které měsíce přepočítat při denním běhu (cron).

    Příští měsíc se neřeší dopředu – až poslední den předchozího
    (příprava na start měsíce) se přepočte i on.
    """
    ref = reference or date.today()
    r, m = ref.year, ref.month
    mesice = [(r, m)]
    if ref.day == calendar.monthrange(r, m)[1]:
        mesice.append(_next_month(r, m))
    return mesice


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
