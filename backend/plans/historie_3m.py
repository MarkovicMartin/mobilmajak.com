"""
Výpočet plánu z průměru posledních 3 kalendářních měsíců před cílovým měsícem.
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
    plneni_celkem_firma_za_obdobi,
    plneni_firma_za_obdobi,
    plneni_prodejny_za_obdobi,
)


def _obdobi_pro_plan(rok, mesic):
    months = mesice_pred_planem(rok, mesic, 3)
    if not months:
        raise ChybejiciDataError('Nelze určit referenční období.')
    return months[0][0], months[0][1], months[-1][0], months[-1][1], months


def historie_3m_nahled(rok, mesic, rust_procent):
    """Náhled plánu z průměru posledních 3 měsíců."""
    rok_od, mesic_od, rok_do, mesic_do, months = _obdobi_pro_plan(rok, mesic)
    celkem = plneni_celkem_firma_za_obdobi(rok_od, mesic_od, rok_do, mesic_do)
    obrat_avg = celkem['obrat']
    obrat_val = float(obrat_avg) if obrat_avg else 0
    navrh = obrat_val * (1 + float(rust_procent) / 100) if obrat_val else 0

    prodejny_data = plneni_prodejny_za_obdobi(rok_od, mesic_od, rok_do, mesic_do)
    firma_kat = plneni_firma_za_obdobi(rok_od, mesic_od, rok_do, mesic_do)
    aktivni = list(Prodejna.get_aktivni_prodejny())

    prodejny_nahled = []
    for p in aktivni:
        pd = prodejny_data.get(p.id, {'obrat': Decimal('0')})
        obrat_p = float(pd['obrat']) if pd['obrat'] else 0
        podil = (obrat_p / obrat_val * 100) if obrat_val else (100 / len(aktivni))
        prodejny_nahled.append({
            'prodejna_id': p.id,
            'prodejna_nazev': p.nazev,
            'obrat_prumer_3m': round(obrat_p, 2),
            'podil_procenta': round(podil, 2),
        })

    kategorie_firma = {}
    for kod, d in firma_kat.items():
        if obrat_val and kod in KATEGORIE_PLANU:
            obrat_k = float(d['obrat']) if d['obrat'] else 0
            kategorie_firma[kod] = {
                'obrat': round(obrat_k, 2),
                'podil_procenta': round(obrat_k / obrat_val * 100, 2),
            }

    mesice_popis = [
        {'rok': r, 'mesic': m} for r, m in months
    ]

    return {
        'obrat_prumer_3m': round(obrat_val, 2),
        'navrh_obrat': round(navrh, 2),
        'rust_procent': float(rust_procent),
        'pocet_mesicu': celkem.get('pocet_mesicu', 0),
        'mesice': mesice_popis,
        'prodejny': prodejny_nahled,
        'kategorie_firma': kategorie_firma,
    }


def vypocitej_plan_z_3_mesicu(rok, mesic, rust_procent):
    """Plán z průměru M−3 … M−1 + růst %."""
    rok_od, mesic_od, rok_do, mesic_do, _ = _obdobi_pro_plan(rok, mesic)
    celkem = plneni_celkem_firma_za_obdobi(rok_od, mesic_od, rok_do, mesic_do)
    obrat_avg = celkem['obrat']
    prodejny_data = plneni_prodejny_za_obdobi(rok_od, mesic_od, rok_do, mesic_do)
    firma_kategorie = plneni_firma_za_obdobi(rok_od, mesic_od, rok_do, mesic_do)
    return vypocitej_plan_z_baseline(obrat_avg, prodejny_data, firma_kategorie, rust_procent)
