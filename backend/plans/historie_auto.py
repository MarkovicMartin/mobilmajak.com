"""
Hybridní výpočet plánu: YoY celkový obrat, 6m průměr prodejen, 3m průměr kategorií.
"""
from decimal import Decimal

from stores.models import Prodejna

from .historie import (
    KATEGORIE_PLANU,
    ChybejiciDataError,
    vypocitej_plan_z_baseline,
)
from .plneni import (
    mesice_pred_planem,
    plneni_celkem_firma,
    plneni_firma_za_obdobi,
    plneni_prodejny_za_obdobi,
)


def _obdobi_z_mesicu(months):
    if not months:
        raise ChybejiciDataError('Nelze určit referenční období.')
    return months[0][0], months[0][1], months[-1][0], months[-1][1], months


def _sloucit_prodejny_hybrid(prodejny_6m, prodejny_3m):
    """Obrat z 6m průměru, kategorie z 3m průměru per prodejna."""
    all_pids = set(prodejny_6m.keys()) | set(prodejny_3m.keys())
    merged = {}
    for pid in all_pids:
        p6 = prodejny_6m.get(pid, {'obrat': Decimal('0'), 'kusy': 0, 'kategorie': {}})
        p3 = prodejny_3m.get(pid, {'obrat': Decimal('0'), 'kusy': 0, 'kategorie': {}})
        merged[pid] = {
            'obrat': p6.get('obrat', Decimal('0')),
            'kusy': p6.get('kusy', 0),
            'kategorie': dict(p3.get('kategorie', {})),
        }
    return merged


def vypocitej_plan_automaticky(rok, mesic, rust_procent=10):
    """
    YoY obrat (stejný měsíc rok-1) + růst %, podíly prodejen z 6m, kategorie z 3m.
    """
    ref_rok = rok - 1
    obrat_baseline = plneni_celkem_firma(ref_rok, mesic)['obrat']

    months_6 = mesice_pred_planem(rok, mesic, 6)
    months_3 = mesice_pred_planem(rok, mesic, 3)
    rok_od6, mesic_od6, rok_do6, mesic_do6, _ = _obdobi_z_mesicu(months_6)
    rok_od3, mesic_od3, rok_do3, mesic_do3, _ = _obdobi_z_mesicu(months_3)

    prodejny_6m = plneni_prodejny_za_obdobi(rok_od6, mesic_od6, rok_do6, mesic_do6)
    prodejny_3m = plneni_prodejny_za_obdobi(rok_od3, mesic_od3, rok_do3, mesic_do3)
    firma_kategorie = plneni_firma_za_obdobi(rok_od3, mesic_od3, rok_do3, mesic_do3)
    prodejny_data = _sloucit_prodejny_hybrid(prodejny_6m, prodejny_3m)

    return vypocitej_plan_z_baseline(obrat_baseline, prodejny_data, firma_kategorie, rust_procent)


def historie_auto_nahled(rok, mesic, rust_procent=10):
    """Náhled hybridního plánu bez zápisu do DB."""
    ref_rok = rok - 1
    obrat_ly = plneni_celkem_firma(ref_rok, mesic)['obrat']
    obrat_ly_val = float(obrat_ly) if obrat_ly else 0
    navrh = obrat_ly_val * (1 + float(rust_procent) / 100) if obrat_ly_val else 0

    months_6 = mesice_pred_planem(rok, mesic, 6)
    months_3 = mesice_pred_planem(rok, mesic, 3)
    rok_od6, mesic_od6, rok_do6, mesic_do6, mesice_6 = _obdobi_z_mesicu(months_6)
    rok_od3, mesic_od3, rok_do3, mesic_do3, mesice_3 = _obdobi_z_mesicu(months_3)

    prodejny_6m = plneni_prodejny_za_obdobi(rok_od6, mesic_od6, rok_do6, mesic_do6)
    prodejny_3m = plneni_prodejny_za_obdobi(rok_od3, mesic_od3, rok_do3, mesic_do3)
    prodejny_data = _sloucit_prodejny_hybrid(prodejny_6m, prodejny_3m)
    firma_kat = plneni_firma_za_obdobi(rok_od3, mesic_od3, rok_do3, mesic_do3)
    aktivni = list(Prodejna.get_aktivni_prodejny())

    soucet_6m = sum(float(pd['obrat']) for pd in prodejny_6m.values() if pd.get('obrat'))
    prodejny_nahled = []
    for p in aktivni:
        pd = prodejny_data.get(p.id, {'obrat': Decimal('0')})
        obrat_p = float(pd['obrat']) if pd['obrat'] else 0
        podil = (obrat_p / soucet_6m * 100) if soucet_6m else (100 / len(aktivni) if aktivni else 0)
        prodejny_nahled.append({
            'prodejna_id': p.id,
            'prodejna_nazev': p.nazev,
            'obrat_prumer_6m': round(float(prodejny_6m.get(p.id, {}).get('obrat', 0) or 0), 2),
            'podil_procenta': round(podil, 2),
        })

    kategorie_firma = {}
    obrat_3m_firma = sum(float(d['obrat']) for d in firma_kat.values())
    for kod, d in firma_kat.items():
        if obrat_3m_firma and kod in KATEGORIE_PLANU:
            obrat_k = float(d['obrat']) if d['obrat'] else 0
            kategorie_firma[kod] = {
                'obrat': round(obrat_k, 2),
                'podil_procenta': round(obrat_k / obrat_3m_firma * 100, 2),
            }

    return {
        'obrat_minuly_rok': round(obrat_ly_val, 2),
        'navrh_obrat': round(navrh, 2),
        'rust_procent': float(rust_procent),
        'mesice_prodejny_6m': [{'rok': r, 'mesic': m} for r, m in mesice_6],
        'mesice_kategorie_3m': [{'rok': r, 'mesic': m} for r, m in mesice_3],
        'prodejny': prodejny_nahled,
        'kategorie_firma': kategorie_firma,
        'zdroj': 'hybrid_yoy_6m_3m',
    }
