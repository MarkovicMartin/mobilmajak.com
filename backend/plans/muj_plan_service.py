"""
Sestavení payloadu pro endpoint muj-plan (osobní plán prodejce).
"""
from __future__ import annotations

import calendar
import math
from datetime import date
from decimal import Decimal

from shifts.models import Smena

from .category_mapping import (
    SELLER_HIDDEN_PLAN_KATEGORIE,
    SERVIS_NAZEV_HINT,
    seller_kategorie_nazev,
)
from .models import PlanMonth, PlanProdejce, KATEGORIE_CHOICES
from .plneni import plneni_prodejce, plneni_prodejce_do_data, plneni_prodejce_den

KATEGORIE_NAZVY = dict(KATEGORIE_CHOICES)

NAZVY_MESICU = {
    1: 'Leden', 2: 'Únor', 3: 'Březen', 4: 'Duben',
    5: 'Květen', 6: 'Červen', 7: 'Červenec', 8: 'Srpen',
    9: 'Září', 10: 'Říjen', 11: 'Listopad', 12: 'Prosinec',
}


def _smeny_prace_qs(user, rok, mesic):
    return Smena.objects.filter(
        user=user,
        datum__year=rok,
        datum__month=mesic,
        typ_smeny='prace',
        aktivni=True,
    )


def _hodiny_z_smen(smeny):
    total = 0.0
    for s in smeny:
        h = s.delka_smeny_hodin
        if h and h > 0:
            total += float(h)
    return round(total, 2)


def _hodiny_po_prodejnach(smeny, domaci_prodejna_id):
    """{prodejna_id: hodiny} – směny bez prodejny jdou pod domovskou."""
    out = {}
    for s in smeny:
        h = s.delka_smeny_hodin
        if not h or h <= 0:
            continue
        pid = s.prodejna_id or domaci_prodejna_id
        if not pid:
            continue
        out[pid] = out.get(pid, 0.0) + float(h)
    return {pid: round(h, 2) for pid, h in out.items()}


def _denni_kusy(mesicni_kusy: int, hodiny_cil: float, hodiny_zaklad: float) -> int:
    if mesicni_kusy <= 0 or hodiny_zaklad <= 0 or hodiny_cil <= 0:
        return 0
    return int(math.ceil(mesicni_kusy * hodiny_cil / hodiny_zaklad))


def _kategorie_radek(kod, data, plneni_data, plneni_dnes, trend_kategorie, denni_kusy=None):
    plan_k = data['pocet_kusu']
    skut_k = plneni_data.get(kod, 0)
    skut_dnes = plneni_dnes.get(kod, 0)
    cil = denni_kusy if denni_kusy is not None else plan_k
    pct = (skut_k / plan_k * 100) if plan_k > 0 else 0
    td = trend_kategorie.get(kod, {})
    trend_k = td.get('trend_kusy')
    trend_pct = (trend_k / plan_k * 100) if plan_k and trend_k is not None else None
    if trend_pct is not None:
        trend_pct = round(trend_pct, 1)
    row = {
        'kategorie_kod': kod,
        'kategorie_nazev': seller_kategorie_nazev(kod, KATEGORIE_NAZVY.get(kod, kod)),
        'pocet_kusu': plan_k if denni_kusy is None else cil,
        'castka': str(data['castka']),
        'skutecne_kusy': skut_k,
        'skutecne_dnes': skut_dnes,
        'plneni_procent': round(pct, 1),
        'trend_kusy': trend_k,
        'trend_procent': trend_pct,
    }
    if kod == 'SERVIS':
        row['napoveda'] = SERVIS_NAZEV_HINT
    return row


def build_muj_plan_payload(user, rok: int, mesic: int):
    today = date.today()
    domaci_id = getattr(user, 'prodejna_id', None)

    smeny_mesic = list(_smeny_prace_qs(user, rok, mesic))
    pracovnich_dni = len({s.datum for s in smeny_mesic})
    hodiny_mesic = _hodiny_z_smen(smeny_mesic)
    hodiny_po_prodejnach = _hodiny_po_prodejnach(smeny_mesic, domaci_id)

    smen_dnes = 0
    hodiny_dnes = 0.0
    hodiny_dnes_po_prodejnach = {}
    plneni_dnes = {}
    if rok == today.year and mesic == today.month:
        smeny_dnes = [s for s in smeny_mesic if s.datum == today]
        smen_dnes = len(smeny_dnes)
        hodiny_dnes = _hodiny_z_smen(smeny_dnes)
        hodiny_dnes_po_prodejnach = _hodiny_po_prodejnach(smeny_dnes, domaci_id)
        plneni_dnes = plneni_prodejce_den(today, user.id)

    empty = {
        'rok': rok,
        'mesic': mesic,
        'mesic_nazev': NAZVY_MESICU.get(mesic, ''),
        'celkem_polozek': 0,
        'celkem_castka': '0.00',
        'kategorie': [],
        'prodejny': [],
        'denni': None,
        'pracovnich_dni': pracovnich_dni,
        'hodiny_mesic': hodiny_mesic,
        'hodiny_dnes': hodiny_dnes,
        'smen_dnes': smen_dnes,
        'plneni': None,
    }

    plan_mesic = PlanMonth.objects.filter(rok=rok, mesic=mesic, je_aktualni=True).first()
    if not plan_mesic:
        return empty

    plany_pp = list(
        PlanProdejce.objects.filter(
            uzivatel=user,
            plan_prodejna__plan_mesic=plan_mesic,
        ).select_related('plan_prodejna__prodejna').prefetch_related('kategorie')
    )

    agregace = {}
    prodejny_raw = []
    for pp in plany_pp:
        p = pp.plan_prodejna.prodejna
        store_kat = {}
        store_polozek = 0
        store_castka = Decimal('0')
        for k in pp.kategorie.all():
            kod = k.kategorie_kod
            if kod in SELLER_HIDDEN_PLAN_KATEGORIE:
                continue
            store_kat[kod] = {
                'pocet_kusu': k.pocet_kusu,
                'castka': k.castka,
            }
            store_polozek += k.pocet_kusu
            store_castka += k.castka
            if kod not in agregace:
                agregace[kod] = {'pocet_kusu': 0, 'castka': Decimal('0')}
            agregace[kod]['pocet_kusu'] += k.pocet_kusu
            agregace[kod]['castka'] += k.castka

        if store_polozek <= 0:
            continue

        pid = p.id
        h_mesic = hodiny_po_prodejnach.get(pid, 0.0)
        h_dnes = hodiny_dnes_po_prodejnach.get(pid, 0.0)
        prodejny_raw.append({
            'prodejna_id': pid,
            'prodejna_nazev': (p.nazev_kratkiy or p.nazev or '').strip(),
            'je_domaci': domaci_id == pid if domaci_id else False,
            'celkem_polozek': store_polozek,
            'celkem_castka': str(store_castka),
            'hodiny_mesic': h_mesic,
            'hodiny_dnes': h_dnes,
            'kategorie': store_kat,
        })

    prodejce_id = user.id
    plneni_data = plneni_prodejce(rok, mesic, prodejce_id)
    trend_kategorie = {}
    je_aktualni_mesic = (rok == today.year and mesic == today.month)
    if je_aktualni_mesic:
        prvni_den = date(rok, mesic, 1)
        pocet_dni = (today - prvni_den).days + 1
        dni_v_mesici = calendar.monthrange(rok, mesic)[1]
        if pocet_dni >= 2:
            do_dnes = plneni_prodejce_do_data(rok, mesic, today, prodejce_id)
            for kod, kusy_d in do_dnes.items():
                prumer = kusy_d / pocet_dni if pocet_dni else 0
                trend_kategorie[kod] = {
                    'trend_kusy': round(prumer * dni_v_mesici),
                    'trend_procent': None,
                }

    kategorie = []
    celkem_skutecne = 0
    celkem_polozek = 0
    celkem_castka = Decimal('0')
    for kod, data in sorted(agregace.items()):
        plan_k = data['pocet_kusu']
        celkem_skutecne += plneni_data.get(kod, 0)
        celkem_polozek += plan_k
        celkem_castka += data['castka']
        kategorie.append(_kategorie_radek(kod, data, plneni_data, plneni_dnes, trend_kategorie))

    prodejny = []
    for row in sorted(prodejny_raw, key=lambda r: (not r['je_domaci'], r['prodejna_nazev'])):
        kat_rows = []
        for kod, kd in sorted(row['kategorie'].items()):
            kat_rows.append({
                'kategorie_kod': kod,
                'kategorie_nazev': seller_kategorie_nazev(kod, KATEGORIE_NAZVY.get(kod, kod)),
                'pocet_kusu': kd['pocet_kusu'],
            })
        prodejny.append({
            'prodejna_id': row['prodejna_id'],
            'prodejna_nazev': row['prodejna_nazev'],
            'je_domaci': row['je_domaci'],
            'celkem_polozek': row['celkem_polozek'],
            'celkem_castka': row['celkem_castka'],
            'hodiny_mesic': row['hodiny_mesic'],
            'hodiny_dnes': row['hodiny_dnes'],
            'kategorie': kat_rows,
        })

    denni = None
    if je_aktualni_mesic and celkem_polozek > 0:
        if hodiny_mesic > 0 and hodiny_dnes > 0:
            denni_celkem = _denni_kusy(celkem_polozek, hodiny_dnes, hodiny_mesic)
            denni_kat = []
            for kod, data in sorted(agregace.items()):
                dk = _denni_kusy(data['pocet_kusu'], hodiny_dnes, hodiny_mesic)
                if dk > 0:
                    denni_kat.append(_kategorie_radek(
                        kod, data, plneni_data, plneni_dnes, trend_kategorie, denni_kusy=dk,
                    ))
            denni_prodejny = []
            for row in prodejny_raw:
                h_m = row['hodiny_mesic']
                h_d = row['hodiny_dnes']
                if h_m <= 0:
                    continue
                d_store = _denni_kusy(row['celkem_polozek'], h_d if h_d > 0 else h_m, h_m)
                if d_store > 0:
                    denni_prodejny.append({
                        'prodejna_id': row['prodejna_id'],
                        'prodejna_nazev': row['prodejna_nazev'],
                        'je_domaci': row['je_domaci'],
                        'celkem_polozek': d_store,
                        'hodiny_dnes': h_d,
                    })
            denni = {
                'hodiny_dnes': hodiny_dnes,
                'hodiny_mesic': hodiny_mesic,
                'celkem_polozek': denni_celkem,
                'kategorie': denni_kat,
                'prodejny': sorted(
                    denni_prodejny,
                    key=lambda r: (not r['je_domaci'], r['prodejna_nazev']),
                ),
            }
        elif pracovnich_dni > 0:
            # Záloha: rovnoměrně podle počtu pracovních dnů
            denni_celkem = int(math.ceil(celkem_polozek / pracovnich_dni))
            denni_kat = []
            for kod, data in sorted(agregace.items()):
                dk = int(math.ceil(data['pocet_kusu'] / pracovnich_dni)) if data['pocet_kusu'] else 0
                if dk > 0:
                    denni_kat.append(_kategorie_radek(
                        kod, data, plneni_data, plneni_dnes, trend_kategorie, denni_kusy=dk,
                    ))
            denni = {
                'hodiny_dnes': hodiny_dnes,
                'hodiny_mesic': hodiny_mesic,
                'celkem_polozek': denni_celkem,
                'kategorie': denni_kat,
                'prodejny': [],
                'odhad': True,
            }

    plneni_celkem_pct = (celkem_skutecne / celkem_polozek * 100) if celkem_polozek > 0 else 0
    visible_kody = list(agregace.keys())
    trend_celkem = (
        sum(trend_kategorie.get(kod, {}).get('trend_kusy', 0) for kod in visible_kody)
        if trend_kategorie else 0
    )
    trend_celkem_pct = (
        round((trend_celkem / celkem_polozek * 100), 1)
        if celkem_polozek and trend_kategorie else None
    )
    celkem_dnes = sum(plneni_dnes.get(kod, 0) for kod in visible_kody)

    return {
        'rok': rok,
        'mesic': mesic,
        'mesic_nazev': NAZVY_MESICU.get(mesic, ''),
        'celkem_polozek': celkem_polozek,
        'celkem_castka': str(celkem_castka),
        'kategorie': kategorie,
        'prodejny': prodejny,
        'denni': denni,
        'pracovnich_dni': pracovnich_dni,
        'hodiny_mesic': hodiny_mesic,
        'hodiny_dnes': hodiny_dnes,
        'smen_dnes': smen_dnes,
        'plneni': {
            'celkem_skutecne': celkem_skutecne,
            'celkem_dnes': celkem_dnes,
            'plneni_procent': round(plneni_celkem_pct, 1),
            'trend_kusy': trend_celkem if je_aktualni_mesic and trend_kategorie else None,
            'trend_procent': trend_celkem_pct,
        },
    }
