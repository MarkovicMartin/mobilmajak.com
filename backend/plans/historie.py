"""
Výpočet plánu z historických dat (minulý rok, stejný měsíc) s aplikací růstu.
"""
from decimal import Decimal, ROUND_HALF_UP

from stores.models import Prodejna

from .plneni import plneni_celkem_firma, plneni_firma, plneni_prodejny

# Kategorie používané v plánech (stejné jako VYCHOZI_KATEGORIE v views)
KATEGORIE_PLANU = [
    'NOVE_TELEFONY', 'BAZAROVE_TELEFONY',
    'PRISLUSENSTVI_SKLA', 'PRISLUSENSTVI_OBALY', 'PRISLUSENSTVI_OSTATNI',
    'SLUZBY', 'SERVIS', 'OSTATNI',
]


class ChybejiciDataError(Exception):
    """Vyvoláno když pro minulý rok neexistují data."""
    pass


def historie_nahled(rok, mesic, rust_procent):
    """
    Vrátí náhled plánu z historie (bez vytvoření plánu).
    Pro zobrazení před vytvořením.
    """
    ref_rok = rok - 1
    ref_mesic = mesic
    obrat_ly = plneni_celkem_firma(ref_rok, ref_mesic)['obrat']
    obrat_ly_val = float(obrat_ly) if obrat_ly else 0
    navrh = obrat_ly_val * (1 + float(rust_procent) / 100) if obrat_ly_val else 0

    prodejny_data = plneni_prodejny(ref_rok, ref_mesic)
    firma_kat = plneni_firma(ref_rok, ref_mesic)
    aktivni = list(Prodejna.get_aktivni_prodejny())

    prodejny_nahled = []
    for p in aktivni:
        pd = prodejny_data.get(p.id, {'obrat': Decimal('0')})
        obrat_p = float(pd['obrat']) if pd['obrat'] else 0
        podil = (obrat_p / obrat_ly_val * 100) if obrat_ly_val else (100 / len(aktivni))
        prodejny_nahled.append({
            'prodejna_id': p.id,
            'prodejna_nazev': p.nazev,
            'obrat_minuly_rok': round(obrat_p, 2),
            'podil_procenta': round(podil, 2),
        })

    kategorie_firma = {}
    for kod, d in firma_kat.items():
        if obrat_ly_val and kod in KATEGORIE_PLANU:
            obrat_k = float(d['obrat']) if d['obrat'] else 0
            kategorie_firma[kod] = {
                'obrat': round(obrat_k, 2),
                'podil_procenta': round(obrat_k / obrat_ly_val * 100, 2),
            }

    return {
        'obrat_minuly_rok': round(obrat_ly_val, 2),
        'navrh_obrat': round(navrh, 2),
        'rust_procent': float(rust_procent),
        'prodejny': prodejny_nahled,
        'kategorie_firma': kategorie_firma,
    }


def vypocitej_plan_z_historie(rok, mesic, rust_procent):
    """
    Vypočítá plán na základě historických dat ze stejného měsíce minulého roku.

    Args:
        rok: cílový rok plánu
        mesic: cílový měsíc (1-12)
        rust_procent: procento růstu oproti minulému roku (např. 10 = +10 %)

    Returns:
        tuple: (castka_celkem, seznam_prodejen)
        seznam_prodejen = [
            {
                'prodejna': Prodejna instance,
                'podil_procenta': Decimal,
                'castka_prodejna': Decimal,
                'kategorie': [{'kod': str, 'podil_procenta': Decimal, 'castka_kategorie': Decimal}, ...]
            },
            ...
        ]

    Raises:
        ChybejiciDataError: když obrat minulý rok je 0
    """
    ref_rok = rok - 1
    ref_mesic = mesic

    obrat_ly = plneni_celkem_firma(ref_rok, ref_mesic)['obrat']
    if obrat_ly is None or obrat_ly <= 0:
        raise ChybejiciDataError(
            'Pro minulý rok neexistují data. Použijte rovnoměrný plán nebo kopii z předchozího měsíce.'
        )

    castka_celkem = (obrat_ly * (1 + Decimal(str(rust_procent)) / 100)).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )

    prodejny_data = plneni_prodejny(ref_rok, ref_mesic)
    firma_kategorie = plneni_firma(ref_rok, ref_mesic)
    aktivni_prodejny = list(Prodejna.get_aktivni_prodejny())
    aktivni_ids = {p.id for p in aktivni_prodejny}
    obrat_firma = obrat_ly

    # Jen prodejny s daty, které jsou stále aktivní
    prodejny_s_daty = {
        pid: pd for pid, pd in prodejny_data.items()
        if pd['obrat'] > 0 and pid in aktivni_ids
    }

    # Globální podíly kategorií (pro nové prodejny a doplnění 0)
    glob_podil_kat = {}
    for kod, d in firma_kategorie.items():
        if obrat_firma and obrat_firma > 0 and kod in KATEGORIE_PLANU:
            glob_podil_kat[kod] = (d['obrat'] / obrat_firma * 100).quantize(
                Decimal('0.001'), rounding=ROUND_HALF_UP
            )
    # Normalizace globálních kategorií na 100 % (jen ty v KATEGORIE_PLANU)
    soucet_glob = sum(glob_podil_kat.get(k, Decimal('0')) for k in KATEGORIE_PLANU)
    if soucet_glob and soucet_glob > 0:
        for k in KATEGORIE_PLANU:
            if k in glob_podil_kat:
                glob_podil_kat[k] = (glob_podil_kat[k] / soucet_glob * 100).quantize(
                    Decimal('0.001'), rounding=ROUND_HALF_UP
                )
    # Doplnit chybějící kategorie rovnoměrně
    chybi = [k for k in KATEGORIE_PLANU if k not in glob_podil_kat or glob_podil_kat[k] == 0]
    if chybi:
        podil_na_chybi = (Decimal('100') / len(KATEGORIE_PLANU)).quantize(Decimal('0.001'))
        for k in chybi:
            glob_podil_kat[k] = podil_na_chybi
    # Finální normalizace glob_podil_kat na 100 %
    soucet_fin = sum(glob_podil_kat.get(k, Decimal('0')) for k in KATEGORIE_PLANU)
    if soucet_fin and soucet_fin > 0 and abs(soucet_fin - 100) > Decimal('0.01'):
        for k in KATEGORIE_PLANU:
            glob_podil_kat[k] = (glob_podil_kat.get(k, Decimal('0')) / soucet_fin * 100).quantize(
                Decimal('0.001'), rounding=ROUND_HALF_UP
            )

    # Rozdělení prodejen na ty s daty a nové
    prodejny_ids_s_daty = set(prodejny_s_daty.keys())
    nove_prodejny = [p for p in aktivni_prodejny if p.id not in prodejny_ids_s_daty]
    pocet_novych = len(nove_prodejny)
    pocet_vsech = len(aktivni_prodejny)

    # Podíl pro nové prodejny
    podil_novy = (Decimal('100') / pocet_vsech).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
    zbytek_pro_historicke = Decimal('100') - pocet_novych * podil_novy
    if zbytek_pro_historicke < 0:
        zbytek_pro_historicke = Decimal('0')

    # Historické podíly prodejen (jen ty s daty)
    soucet_historickych = sum(
        prodejny_s_daty[pid]['obrat'] for pid in prodejny_ids_s_daty
    )
    historicke_podily = {}
    if soucet_historickych and soucet_historickych > 0:
        for pid, pd in prodejny_s_daty.items():
            raw = (pd['obrat'] / soucet_historickych * 100)
            historicke_podily[pid] = raw.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
    else:
        soucet_historickych = Decimal('0')

    # Škálování historických podílů aby součet byl zbytek_pro_historicke
    if historicke_podily and sum(historicke_podily.values()) > 0:
        koef = zbytek_pro_historicke / sum(historicke_podily.values())
        for pid in historicke_podily:
            historicke_podily[pid] = (historicke_podily[pid] * koef).quantize(
                Decimal('0.001'), rounding=ROUND_HALF_UP
            )
        # Dorovnání zaokrouhlení na poslední
        diff = zbytek_pro_historicke - sum(historicke_podily.values())
        if historicke_podily and diff != 0:
            last_pid = list(historicke_podily.keys())[-1]
            historicke_podily[last_pid] += diff

    result = []
    for prodejna in aktivni_prodejny:
        pid = prodejna.id
        if pid in historicke_podily:
            podil = historicke_podily[pid]
        else:
            podil = podil_novy

        castka_p = (castka_celkem * podil / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Kategorie pro tuto prodejnu
        if pid in prodejny_s_daty and prodejny_s_daty[pid]['obrat'] > 0:
            obrat_p = prodejny_s_daty[pid]['obrat']
            kat_data = prodejny_s_daty[pid]['kategorie']
            kategorie_list = []
            for kod in KATEGORIE_PLANU:
                obrat_kat = kat_data.get(kod, {}).get('obrat', Decimal('0'))
                if obrat_kat and obrat_p > 0:
                    podil_kat = (obrat_kat / obrat_p * 100).quantize(
                        Decimal('0.001'), rounding=ROUND_HALF_UP
                    )
                else:
                    podil_kat = glob_podil_kat.get(kod, Decimal('0'))
                castka_kat = (castka_p * podil_kat / 100).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
                kategorie_list.append({
                    'kod': kod,
                    'podil_procenta': podil_kat,
                    'castka_kategorie': castka_kat,
                })
            # Normalizace součtu kategorií na 100 %
            soucet_kat = sum(k['podil_procenta'] for k in kategorie_list)
            if not soucet_kat or soucet_kat == 0:
                # Všechny 0 – použij globální
                kategorie_list = []
                for kod in KATEGORIE_PLANU:
                    podil_kat = glob_podil_kat.get(kod, Decimal('0'))
                    castka_kat = (castka_p * podil_kat / 100).quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP
                    )
                    kategorie_list.append({
                        'kod': kod,
                        'podil_procenta': podil_kat,
                        'castka_kategorie': castka_kat,
                    })
            elif abs(soucet_kat - 100) > Decimal('0.01'):
                koef_kat = Decimal('100') / soucet_kat
                for k in kategorie_list:
                    k['podil_procenta'] = (k['podil_procenta'] * koef_kat).quantize(
                        Decimal('0.001'), rounding=ROUND_HALF_UP
                    )
                    k['castka_kategorie'] = (castka_p * k['podil_procenta'] / 100).quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP
                    )
            # Dorovnání poslední kategorie
            soucet_castky = sum(k['castka_kategorie'] for k in kategorie_list)
            if kategorie_list and soucet_castky != castka_p:
                kategorie_list[-1]['castka_kategorie'] += castka_p - soucet_castky
        else:
            # Nová prodejna – globální podíly
            kategorie_list = []
            for kod in KATEGORIE_PLANU:
                podil_kat = glob_podil_kat.get(kod, Decimal('0'))
                castka_kat = (castka_p * podil_kat / 100).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
                kategorie_list.append({
                    'kod': kod,
                    'podil_procenta': podil_kat,
                    'castka_kategorie': castka_kat,
                })
            soucet_castky = sum(k['castka_kategorie'] for k in kategorie_list)
            if kategorie_list and soucet_castky != castka_p:
                kategorie_list[-1]['castka_kategorie'] += castka_p - soucet_castky

        result.append({
            'prodejna': prodejna,
            'podil_procenta': podil,
            'castka_prodejna': castka_p,
            'kategorie': kategorie_list,
        })

    # Dorovnání součtu podílů prodejen na 100 %
    soucet_podilu = sum(r['podil_procenta'] for r in result)
    if result and abs(soucet_podilu - 100) > Decimal('0.01'):
        diff = Decimal('100') - soucet_podilu
        result[-1]['podil_procenta'] += diff
        result[-1]['castka_prodejna'] = (
            castka_celkem * result[-1]['podil_procenta'] / 100
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        for k in result[-1]['kategorie']:
            k['castka_kategorie'] = (
                result[-1]['castka_prodejna'] * k['podil_procenta'] / 100
            ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return castka_celkem, result
