"""
Idempotentní vytvoření měsíčního plánu (hybridní auto nebo projekční baseline).
"""
from datetime import date

from .historie import ChybejiciDataError
from .historie_auto import vypocitej_plan_automaticky
from .models import PlanMonth


def mesice_bez_aktualniho_planu(rok):
    """Čísla měsíců 1–12 bez aktivního plánu (je_aktualni=True)."""
    existujici = set(
        PlanMonth.objects.filter(rok=rok, je_aktualni=True).values_list('mesic', flat=True),
    )
    return [m for m in range(1, 13) if m not in existujici]


def je_mesic_auto_povoleny(rok, mesic, reference=None):
    """Auto plán jen pro aktuální a budoucí měsíce (ne retroaktivně)."""
    ref = reference or date.today()
    return (rok, mesic) >= (ref.year, ref.month)


def ensure_plan_mesic(
    rok,
    mesic,
    user,
    rust_procent=10,
    allow_past=False,
    baseline_fn=None,
):
    """
    Pokud existuje aktivní PlanMonth → {created: False, ...}.
    Jinak vytvoří plán (hybrid auto nebo baseline_fn(rok, mesic, rust_procent)).

    baseline_fn: volitelně (rok, mesic, rust_procent) -> (castka, prodejny_data)
    """
    if not allow_past and not je_mesic_auto_povoleny(rok, mesic):
        return {
            'created': False,
            'skipped': True,
            'reason': 'past_month',
            'plan': None,
            'warnings': [],
        }

    existujici = PlanMonth.objects.filter(rok=rok, mesic=mesic, je_aktualni=True).first()
    if existujici:
        from .views import serialize_plan
        return {
            'created': False,
            'skipped': True,
            'reason': 'already_exists',
            'plan': serialize_plan(existujici),
            'warnings': [],
        }

    try:
        if baseline_fn is not None:
            castka_celkem, prodejny_data = baseline_fn(rok, mesic, rust_procent)
        else:
            castka_celkem, prodejny_data = vypocitej_plan_automaticky(rok, mesic, rust_procent)
    except ChybejiciDataError as e:
        return {
            'created': False,
            'skipped': True,
            'reason': 'missing_data',
            'error': str(e),
            'plan': None,
            'warnings': [],
        }

    from .views import _vytvor_plan_z_prodejny_data
    plan, out = _vytvor_plan_z_prodejny_data(
        rok, mesic, castka_celkem, prodejny_data, user, auto_prodejci=True,
    )
    warnings = list(out.get('auto_prodejci_warnings', []))
    return {
        'created': True,
        'skipped': False,
        'plan': out,
        'plan_id': plan.id,
        'warnings': warnings,
    }


def ensure_plans_bulk(
    mesice,
    user,
    rust_procent=10,
    skip_existing=True,
    baseline_fn=None,
    prepocet_prodejci=True,
):
    """Smyčka ensure_plan_mesic; volitelně přepočet prodejců u všech měsíců v seznamu."""
    vytvoreno = []
    preskoceno = []
    warnings = []
    chyby = []

    for rok, mesic in mesice:
        if skip_existing:
            if PlanMonth.objects.filter(rok=rok, mesic=mesic, je_aktualni=True).exists():
                preskoceno.append({'rok': rok, 'mesic': mesic, 'reason': 'already_exists'})
                continue

        res = ensure_plan_mesic(
            rok, mesic, user, rust_procent=rust_procent,
            allow_past=True, baseline_fn=baseline_fn,
        )
        if res.get('created'):
            vytvoreno.append({'rok': rok, 'mesic': mesic, 'plan_id': res.get('plan_id')})
            warnings.extend(res.get('warnings', []))
        elif res.get('reason') == 'missing_data':
            chyby.append({'rok': rok, 'mesic': mesic, 'error': res.get('error')})
            preskoceno.append({'rok': rok, 'mesic': mesic, 'reason': 'missing_data'})
        else:
            preskoceno.append({'rok': rok, 'mesic': mesic, 'reason': res.get('reason', 'skipped')})

    out = {
        'vytvoreno': vytvoreno,
        'preskoceno': preskoceno,
        'warnings': warnings,
        'chyby': chyby,
        'pocet_vytvoreno': len(vytvoreno),
        'pocet_preskoceno': len(preskoceno),
    }

    if prepocet_prodejci and vytvoreno:
        from .prodejci_prepocet import prepocet_prodejci_mesice
        unique = sorted({(x['rok'], x['mesic']) for x in vytvoreno})
        pr = prepocet_prodejci_mesice(unique)
        out['prodejci_prepocet'] = pr['vysledky']
        out['pocet_prepocet_prodejci'] = pr['pocet_prepocet']
        out['warnings'] = list(out['warnings']) + list(pr.get('warnings', []))

    return out
