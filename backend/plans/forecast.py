"""
Roční predikce tržeb a podílů – sezónní průměr stejného měsíce + omezený YoY trend.
K proběhlým / probíhajícím měsícům doplní skutečné plnění a uložený plán.

Výhled (predikce_rok) používá jeden hromadný dotaz na měsíční obraty + cache
pro uzavřené měsíce; plné rozpadové predikce jen pro založení plánů.
"""
import calendar
import time
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from stores.models import Prodejna

from .historie import KATEGORIE_PLANU, vypocitej_plan_z_baseline
from .plneni import (
    _prev_month,
    dostupne_roky_z_prodeje,
    plneni_celkem_firma,
    plneni_celkem_firma_mesicne,
    pobocky_bez_dat_v_mesici,
    plneni_firma,
    plneni_prodejny,
    plneni_prodejny_za_obdobi,
    plneni_firma_za_obdobi,
    mesice_pred_planem,
)
from .models import PlanMonth, PlanStore


def _round_kc(v):
    return int(round(float(v or 0)))


def _round_pct(v):
    if v is None:
        return None
    return int(round(float(v)))


def _plan_castka_prodejny(rok, mesic, prodejna_ids):
    """Součet plánovaného obratu vybraných prodejen (nebo celé firmy)."""
    plan = PlanMonth.objects.filter(rok=rok, mesic=mesic, je_aktualni=True).first()
    if not plan:
        return None
    if not prodejna_ids:
        if not plan.castka_celkem:
            return None
        return float(plan.castka_celkem)
    qs = PlanStore.objects.filter(plan_mesic=plan, prodejna_id__in=prodejna_ids)
    total = sum(float(ps.castka_prodejna or 0) for ps in qs)
    return total if total > 0 else None

# Cache uzavřených měsíců (minulé roky se nemění) – TTL 24 h
_OBRAT_MESICNE_CACHE = {}
_OBRAT_CACHE_TTL = 86400

TREND_MIN = -0.05
TREND_MAX = 0.25
PODIL_TREND_MAX_PP = Decimal('2')  # max ±2 p. b. / měsíc na podílu


def _mesice_zpet(pocet, od_rok=None, od_mesic=None):
    """Posledních `pocet` kalendářních měsíců před od_rok/od_mesic (nebo před dneškem)."""
    if od_rok is None:
        d = date.today()
        rok, mesic = d.year, d.month
    else:
        rok, mesic = od_rok, od_mesic
    r, m = _prev_month(rok, mesic)
    result = []
    for _ in range(pocet):
        result.append((r, m))
        r, m = _prev_month(r, m)
    result.reverse()
    return result


def _mesice_do_cile(cilovy_rok, cilovy_mesic):
    """Počet měsíců od aktuálního kalendářního měsíce do cíle (0 = tento měsíc)."""
    today = date.today()
    r, m = today.year, today.month
    count = 0
    while (r, m) < (cilovy_rok, cilovy_mesic):
        count += 1
        if m == 12:
            r, m = r + 1, 1
        else:
            m += 1
    return count


def serie_obrat_firma(mesice_zpet=36):
    months = _mesice_zpet(mesice_zpet)
    out = []
    for r, m in months:
        t = plneni_celkem_firma(r, m)
        out.append({
            'rok': r,
            'mesic': m,
            'obrat': float(t['obrat']) if t['obrat'] else 0.0,
        })
    return out


def serie_podil_prodejen(mesice_zpet=36):
    months = _mesice_zpet(mesice_zpet)
    serie = []
    for r, m in months:
        pd = plneni_prodejny(r, m)
        celkem = sum(float(d['obrat']) for d in pd.values() if d.get('obrat'))
        podily = {}
        if celkem > 0:
            for pid, d in pd.items():
                o = float(d.get('obrat', 0) or 0)
                if o > 0:
                    podily[pid] = round(o / celkem * 100, 3)
        serie.append({'rok': r, 'mesic': m, 'podily': podily, 'obrat_celkem': celkem})
    return serie


def serie_podil_kategorii(mesice_zpet=36, prodejna_id=None):
    months = _mesice_zpet(mesice_zpet)
    serie = []
    for r, m in months:
        if prodejna_id is not None:
            pd = plneni_prodejny(r, m).get(prodejna_id, {'obrat': Decimal('0'), 'kategorie': {}})
            kat = pd.get('kategorie', {})
            celkem = float(pd.get('obrat', 0) or 0)
        else:
            kat = plneni_firma(r, m)
            celkem = sum(float(d['obrat']) for d in kat.values())
        podily = {}
        if celkem > 0:
            for kod, d in kat.items():
                if kod in KATEGORIE_PLANU:
                    o = float(d.get('obrat', 0) or 0)
                    if o > 0:
                        podily[kod] = round(o / celkem * 100, 3)
        serie.append({'rok': r, 'mesic': m, 'podily': podily})
    return serie


def _obrat_mesicne_map_cached(rok_od, mesic_od, rok_do, mesic_do, reference=None, prodejna_ids=None):
    """Mapa měsíčních obratů; uzavřené intervaly cache 24 h."""
    ref = reference or date.today()
    immutable = (rok_do, mesic_do) < (ref.year, ref.month)
    key = (rok_od, mesic_od, rok_do, mesic_do, tuple(prodejna_ids) if prodejna_ids else None)
    if immutable and key in _OBRAT_MESICNE_CACHE:
        exp, data = _OBRAT_MESICNE_CACHE[key]
        if exp > time.time():
            return data
    data = plneni_celkem_firma_mesicne(
        rok_od, mesic_od, rok_do, mesic_do, prodejna_ids=prodejna_ids,
    )
    if immutable:
        _OBRAT_MESICNE_CACHE[key] = (time.time() + _OBRAT_CACHE_TTL, data)
    return data


def _mesice_potrebne_pro_rok(cilovy_rok, mesice_historie, reference):
    """Všechny (rok, mesic) potřebné pro výhled jednoho roku."""
    ref = reference
    needed = set()
    for r, m in _mesice_zpet(min(mesice_historie, 24), ref.year, ref.month):
        needed.add((r, m))
        needed.add((r - 1, m))
    for mesic in range(1, 13):
        for y in range(cilovy_rok - 3, cilovy_rok):
            if y >= 2000:
                needed.add((y, mesic))
        needed.add((cilovy_rok - 1, mesic))
        if (cilovy_rok, mesic) <= (ref.year, ref.month):
            needed.add((cilovy_rok, mesic))
    return needed


def _mesice_pro_vyhled(hlavni_rok, compare_roky, mesice_historie, reference):
    """Sjednocená množina měsíců pro hlavní rok + roky v grafu."""
    ref = reference
    needed = _mesice_potrebne_pro_rok(hlavni_rok, mesice_historie, ref)
    for rok in compare_roky or []:
        if rok == hlavni_rok:
            continue
        for mesic in range(1, 13):
            needed.add((rok, mesic))
            if rok >= 2001:
                needed.add((rok - 1, mesic))
        if rok >= ref.year:
            needed |= _mesice_potrebne_pro_rok(rok, mesice_historie, ref)
    return needed


class ForecastContext:
    """Sdílená mapa obratů + trend – jeden SQL dotaz na výhled."""

    def __init__(self, cilovy_rok, mesice_historie=36, reference=None, compare_roky=None, prodejna_ids=None):
        self.cilovy_rok = cilovy_rok
        self.ref = reference or date.today()
        self.compare_roky = list(compare_roky or [])
        self.prodejna_ids = [int(x) for x in prodejna_ids] if prodejna_ids else None
        needed = _mesice_pro_vyhled(
            cilovy_rok, self.compare_roky, mesice_historie, self.ref,
        )
        if not needed:
            self.obrat_map = {}
        else:
            sorted_m = sorted(needed)
            rok_od, mesic_od = sorted_m[0]
            rok_do, mesic_do = sorted_m[-1]
            self.obrat_map = _obrat_mesicne_map_cached(
                rok_od, mesic_od, rok_do, mesic_do,
                reference=self.ref, prodejna_ids=self.prodejna_ids,
            )
        self._trend_pct = None
        self._plans_cache = {}
        self._load_plans(cilovy_rok)

    def _load_plans(self, rok):
        self._plans_cache[rok] = {
            p.mesic: p
            for p in PlanMonth.objects.filter(
                rok=rok, je_aktualni=True,
            ).only('mesic', 'castka_celkem')
        }

    def for_rok(self, rok):
        """Kontext pro jiný predikční rok se stejnou mapou obratů."""
        other = ForecastContext.__new__(ForecastContext)
        other.cilovy_rok = rok
        other.ref = self.ref
        other.compare_roky = self.compare_roky
        other.prodejna_ids = self.prodejna_ids
        other.obrat_map = self.obrat_map
        other._trend_pct = None
        other._plans_cache = self._plans_cache
        if rok not in other._plans_cache:
            other._load_plans(rok)
        return other

    @property
    def _plans(self):
        return self._plans_cache.get(self.cilovy_rok, {})

    def obrat(self, rok, mesic):
        row = self.obrat_map.get((rok, mesic), {})
        return row.get('obrat', Decimal('0'))

    def kusy(self, rok, mesic):
        row = self.obrat_map.get((rok, mesic), {})
        return row.get('kusy', 0)

    def yoy_trend_pct(self, mesice_historie=36):
        if self._trend_pct is not None:
            return self._trend_pct
        months = _mesice_zpet(min(mesice_historie, 24), self.ref.year, self.ref.month)
        growths = []
        for r, m in months:
            cur = self.obrat(r, m)
            prev = self.obrat(r - 1, m)
            if cur and prev and prev > 0 and cur > 0:
                growths.append(float((cur - prev) / prev))
        if not growths:
            self._trend_pct = 0.0
        else:
            avg = sum(growths) / len(growths)
            self._trend_pct = max(TREND_MIN, min(TREND_MAX, avg))
        return self._trend_pct

    def seasonal_obrat(self, mesic, max_years=3):
        values = []
        for y in range(self.cilovy_rok - max_years, self.cilovy_rok):
            if y < 2000:
                continue
            t = self.obrat(y, mesic)
            if t and t > 0:
                values.append(t)
        if not values:
            return Decimal('0'), 0
        avg = (sum(values, Decimal('0')) / len(values)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP,
        )
        return avg, len(values)


def _yoy_trend_pct(mesice_historie=36):
    ctx = ForecastContext(date.today().year, mesice_historie)
    return ctx.yoy_trend_pct(mesice_historie)


def _seasonal_obrat(cilovy_rok, mesic, max_years=3):
    ctx = ForecastContext(cilovy_rok)
    return ctx.seasonal_obrat(mesic, max_years)


def _confidence(history_count):
    if history_count < 2:
        return 'low'
    if history_count < 3:
        return 'medium'
    return 'high'


def _posledni_podily_prodejen(mesice=6):
    months = mesice_pred_planem(date.today().year, date.today().month, mesice)
    if not months:
        months = _mesice_zpet(mesice)
    rok_od, mes_od = months[0]
    rok_do, mes_do = months[-1]
    pd = plneni_prodejny_za_obdobi(rok_od, mes_od, rok_do, mes_do)
    celkem = sum(float(d['obrat']) for d in pd.values() if d.get('obrat'))
    if celkem <= 0:
        return {}
    return {
        pid: float(d['obrat']) / celkem * 100
        for pid, d in pd.items() if d.get('obrat', 0) > 0
    }


def _trend_podily(base_podily, slope_per_month, mesice_dopredu):
    """Omezený posun podílů; normalizace na 100 %."""
    if not base_podily:
        return {}
    shift = float(slope_per_month) * mesice_dopredu
    shift = max(-float(PODIL_TREND_MAX_PP) * mesice_dopredu,
                min(float(PODIL_TREND_MAX_PP) * mesice_dopredu, shift))
    raw = {}
    for pid, pct in base_podily.items():
        raw[pid] = max(0.0, pct + shift * (pct / 100.0))
    total = sum(raw.values())
    if total <= 0:
        n = len(base_podily)
        return {pid: 100.0 / n for pid in base_podily}
    return {pid: round(v / total * 100, 3) for pid, v in raw.items()}


def _posledni_podily_kategorii_firma(mesice=3):
    months = mesice_pred_planem(date.today().year, date.today().month, mesice)
    if not months:
        months = _mesice_zpet(mesice)
    rok_od, mes_od = months[0]
    rok_do, mes_do = months[-1]
    fk = plneni_firma_za_obdobi(rok_od, mes_od, rok_do, mes_do)
    celkem = sum(float(d['obrat']) for d in fk.values())
    if celkem <= 0:
        return {}
    return {
        kod: float(d['obrat']) / celkem * 100
        for kod, d in fk.items() if kod in KATEGORIE_PLANU and d.get('obrat', 0) > 0
    }


def predikce_mesic(cilovy_rok, mesic, rust_procent=None, mesice_historie=36):
    """
    Projekční baseline pro jeden měsíc – struktura kompatibilní s vypocitej_plan_z_baseline.
    """
    seasonal, hist_n = _seasonal_obrat(cilovy_rok, mesic)
    trend = _yoy_trend_pct(mesice_historie)
    mesice_dopredu = _mesice_do_cile(cilovy_rok, mesic)

    if rust_procent is not None:
        rust = float(rust_procent) / 100
    else:
        rust = trend * (1 + mesice_dopredu * 0.1)
        rust = max(TREND_MIN, min(TREND_MAX, rust))

    obrat_pred = (seasonal * (1 + Decimal(str(rust)))).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP,
    ) if seasonal > 0 else Decimal('0')

    ly = plneni_celkem_firma(cilovy_rok - 1, mesic)['obrat']
    obrat_ly = float(ly) if ly else 0

    base_podily = _posledni_podily_prodejen(6)
    podily_pred = _trend_podily(base_podily, 0.0, mesice_dopredu)

    aktivni = list(Prodejna.get_aktivni_prodejny())
    soucet_podilu = sum(podily_pred.values())
    prodejny_data = {}
    for p in aktivni:
        pct = podily_pred.get(p.id, 100.0 / len(aktivni) if aktivni else 0)
        obrat_p = (obrat_pred * Decimal(str(pct)) / 100).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP,
        ) if obrat_pred > 0 else Decimal('0')
        kat_pct = _posledni_podily_kategorii_firma(3)
        kat_data = {}
        for kod in KATEGORIE_PLANU:
            kp = kat_pct.get(kod, 100.0 / len(KATEGORIE_PLANU))
            kat_data[kod] = {
                'obrat': (obrat_p * Decimal(str(kp)) / 100).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP,
                ),
                'kusy': 0,
            }
        prodejny_data[p.id] = {
            'obrat': obrat_p,
            'kusy': 0,
            'kategorie': kat_data,
        }

    firma_kat_pct = _posledni_podily_kategorii_firma(3)
    firma_kategorie = {}
    for kod in KATEGORIE_PLANU:
        kp = firma_kat_pct.get(kod, 100.0 / len(KATEGORIE_PLANU))
        firma_kategorie[kod] = {
            'obrat': (obrat_pred * Decimal(str(kp)) / 100).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP,
            ),
            'kusy': 0,
        }

    return {
        'rok': cilovy_rok,
        'mesic': mesic,
        'obrat_pred': float(obrat_pred),
        'obrat_ly': obrat_ly,
        'delta_pct_ly': round((float(obrat_pred) / obrat_ly - 1) * 100, 1) if obrat_ly else None,
        'rust_pouzity_pct': round(rust * 100, 2),
        'confidence': _confidence(hist_n),
        'history_months_same': hist_n,
        'prodejny_podily': podily_pred,
        'obrat_baseline': obrat_pred,
        'prodejny_data': prodejny_data,
        'firma_kategorie': firma_kategorie,
    }


def vypocitej_plan_z_projekce(rok, mesic, rust_procent=None, mesice_historie=36):
    """(castka, prodejny_data) z predikce – pro ensure_plan_mesic / bulk."""
    pred = predikce_mesic(rok, mesic, rust_procent=rust_procent, mesice_historie=mesice_historie)
    if pred['obrat_baseline'] <= 0:
        from .historie import ChybejiciDataError
        raise ChybejiciDataError(
            f'Nedostatek historie pro {mesic}/{rok}. Založte plán ručně nebo zvolte jiný rok.'
        )
    rust = pred['rust_pouzity_pct']
    return vypocitej_plan_z_baseline(
        pred['obrat_baseline'],
        pred['prodejny_data'],
        pred['firma_kategorie'],
        rust,
    )


def stav_mesice(rok, mesic, reference=None):
    """budouci | probiha | ukonceny vůči kalendářnímu dni."""
    ref = reference or date.today()
    if (rok, mesic) > (ref.year, ref.month):
        return 'budouci'
    if (rok, mesic) == (ref.year, ref.month):
        return 'probiha'
    return 'ukonceny'


def dopln_plneni_k_mesici(pm, reference=None, ctx=None):
    """
    Ke měsíci z predikce přidá stav a plnění (skutečnost z WEB_PRODEJE_ALL).
    U probíhajícího měsíce i lineární trend do konce měsíce.
    """
    ref = reference or date.today()
    rok, mesic = pm['rok'], pm['mesic']
    stav = stav_mesice(rok, mesic, ref)
    pm['stav'] = stav

    if stav == 'budouci':
        pm['plneni'] = None
        return pm

    if ctx is not None:
        obrat_sk = float(ctx.obrat(rok, mesic) or 0)
        kusy = ctx.kusy(rok, mesic)
        if ctx.prodejna_ids:
            plan_obrat = _plan_castka_prodejny(rok, mesic, ctx.prodejna_ids)
            ma_plan = plan_obrat is not None
        else:
            plan_row = ctx._plans.get(mesic)
            ma_plan = plan_row is not None
            plan_obrat = float(plan_row.castka_celkem) if plan_row else None
    else:
        skutecnost = plneni_celkem_firma(rok, mesic)
        obrat_sk = float(skutecnost['obrat']) if skutecnost['obrat'] else 0.0
        kusy = skutecnost['kusy']
        plan_row = PlanMonth.objects.filter(rok=rok, mesic=mesic, je_aktualni=True).first()
        ma_plan = plan_row is not None
        plan_obrat = float(plan_row.castka_celkem) if plan_row else None
    pred = pm.get('obrat_pred') or 0
    ly_sk = pm.get('obrat_ly') or 0

    plneni = {
        'obrat': _round_kc(obrat_sk),
        'kusy': kusy,
        'ma_plan': ma_plan,
        'plan_obrat': _round_kc(plan_obrat) if plan_obrat is not None else None,
        'pct_predikce': _round_pct(obrat_sk / pred * 100) if pred > 0 else None,
        'pct_plan': _round_pct(obrat_sk / plan_obrat * 100) if plan_obrat and plan_obrat > 0 else None,
        'odchylka_pred_kc': _round_kc(obrat_sk - pred) if pred else None,
        'odchylka_plan_kc': _round_kc(obrat_sk - plan_obrat) if plan_obrat is not None else None,
        'odchylka_ly_kc': _round_kc(obrat_sk - ly_sk) if ly_sk else None,
        'pct_vs_ly': _round_pct(obrat_sk / ly_sk * 100) if ly_sk > 0 else None,
        'odchylka_ly_pct': _round_pct((obrat_sk / ly_sk - 1) * 100) if ly_sk > 0 else None,
    }

    if stav == 'probiha':
        dni_v_mesici = calendar.monthrange(rok, mesic)[1]
        den = ref.day
        plneni['den_v_mesici'] = den
        plneni['dni_v_mesici'] = dni_v_mesici
        if den > 0 and obrat_sk > 0:
            trend_k_mesici = _round_kc(obrat_sk / den * dni_v_mesici)
            plneni['trend_k_mesici'] = trend_k_mesici
            plneni['pct_predikce_trend'] = (
                _round_pct(trend_k_mesici / pred * 100) if pred > 0 else None
            )
            if plan_obrat and plan_obrat > 0:
                plneni['pct_plan_trend'] = _round_pct(trend_k_mesici / plan_obrat * 100)

    pm['plneni'] = plneni
    return pm


def _pct_delta(sk, base):
    if not base or base <= 0:
        return None, None
    pct = _round_pct(sk / base * 100)
    delta_pct = _round_pct((sk / base - 1) * 100)
    return pct, delta_pct


def _souhrn_plneni_roku(mesice):
    """Agregace plnění vs predikce/plán pro ukončené a probíhající měsíce."""
    s_plneni = [m for m in mesice if m.get('plneni')]
    if not s_plneni:
        return None
    obrat_sk = sum(m['plneni']['obrat'] for m in s_plneni)
    obrat_pred = sum(m['obrat_pred'] for m in s_plneni)
    obrat_ly = sum(m.get('obrat_ly') or 0 for m in s_plneni)
    s_planem = [m for m in s_plneni if m['plneni'].get('plan_obrat')]
    obrat_plan = sum(m['plneni']['plan_obrat'] for m in s_planem)
    pct_pred, delta_pred = _pct_delta(obrat_sk, obrat_pred)
    pct_plan, delta_plan = _pct_delta(obrat_sk, obrat_plan) if s_planem else (None, None)
    pct_ly, delta_ly = _pct_delta(obrat_sk, obrat_ly)
    return {
        'pocet_mesicu': len(s_plneni),
        'obrat_skutecny': _round_kc(obrat_sk),
        'obrat_predikce': _round_kc(obrat_pred),
        'obrat_ly': _round_kc(obrat_ly),
        'obrat_plan': _round_kc(obrat_plan) if s_planem else None,
        'pct_predikce': pct_pred,
        'pct_plan': pct_plan,
        'pct_vs_ly': pct_ly,
        'odchylka_pred_pct': delta_pred,
        'odchylka_plan_pct': delta_plan,
        'odchylka_ly_pct': delta_ly,
        'odchylka_pred_kc': _round_kc(obrat_sk - obrat_pred),
        'odchylka_ly_kc': _round_kc(obrat_sk - obrat_ly) if obrat_ly else None,
        'odchylka_plan_kc': _round_kc(obrat_sk - obrat_plan) if s_planem else None,
        'mesicu_s_planem': len(s_planem),
    }


def _souhrn_roku_kompletni(mesice, reference=None):
    """Roční souhrn: celý rok + za ukončené/probíhající období."""
    ref = reference or date.today()
    obdobi = [m for m in mesice if m.get('stav') in ('ukonceny', 'probiha')]
    s_plneni = [m for m in obdobi if m.get('plneni')]

    celkem_pred_rok = _round_kc(sum(m['obrat_pred'] for m in mesice))
    celkem_ly_rok = _round_kc(sum(m.get('obrat_ly') or 0 for m in mesice))

    za_obdobi = None
    if s_plneni:
        sk = sum(m['plneni']['obrat'] for m in s_plneni)
        pred = sum(m['obrat_pred'] for m in s_plneni)
        ly = sum(m.get('obrat_ly') or 0 for m in s_plneni)
        s_planem = [m for m in s_plneni if m['plneni'].get('plan_obrat')]
        plan = sum(m['plneni']['plan_obrat'] for m in s_planem)
        pct_pred, delta_pred = _pct_delta(sk, pred)
        pct_ly, delta_ly = _pct_delta(sk, ly)
        pct_plan, delta_plan = _pct_delta(sk, plan) if s_planem else (None, None)
        za_obdobi = {
            'mesicu': len(s_plneni),
            'obrat_skutecny': _round_kc(sk),
            'obrat_predikce': _round_kc(pred),
            'obrat_ly': _round_kc(ly),
            'obrat_plan': _round_kc(plan) if s_planem else None,
            'pct_vs_predikce': pct_pred,
            'odchylka_pred_pct': delta_pred,
            'odchylka_pred_kc': _round_kc(sk - pred),
            'pct_vs_ly': pct_ly,
            'odchylka_ly_pct': delta_ly,
            'odchylka_ly_kc': _round_kc(sk - ly) if ly else None,
            'pct_vs_plan': pct_plan,
            'odchylka_plan_pct': delta_plan,
            'odchylka_plan_kc': _round_kc(sk - plan) if s_planem else None,
        }

    return {
        'celkem_predikce_rok': celkem_pred_rok,
        'celkem_obrat_ly_rok': celkem_ly_rok,
        'za_ukoncene_obdobi': za_obdobi,
        'reference_date': ref.isoformat(),
    }


def _serie_skutecnost_rok(ctx, rok, reference=None):
    ref = reference or date.today()
    mesice = []
    for m in range(1, 13):
        o = float(ctx.obrat(rok, m) or 0)
        mesice.append({
            'mesic': m,
            'obrat': _round_kc(o),
            'stav': stav_mesice(rok, m, ref),
        })
    return {
        'rok': rok,
        'typ': 'skutecnost',
        'mesice': mesice,
        'celkem_obrat': _round_kc(sum(x['obrat'] for x in mesice)),
    }


def predikce_mesic_nahled(ctx, mesic, rust_procent=None, mesice_historie=36):
    """
    Lehká predikce jednoho měsíce pro výhled – bez rozpadů prodejen/kategorií.
    Pouze čtení z přednačtené mapy obratů.
    """
    cilovy_rok = ctx.cilovy_rok
    seasonal, hist_n = ctx.seasonal_obrat(mesic)
    trend = ctx.yoy_trend_pct(mesice_historie)
    mesice_dopredu = _mesice_do_cile(cilovy_rok, mesic)

    if rust_procent is not None:
        rust = float(rust_procent) / 100
    else:
        rust = trend * (1 + mesice_dopredu * 0.1)
        rust = max(TREND_MIN, min(TREND_MAX, rust))

    obrat_pred = (seasonal * (1 + Decimal(str(rust)))).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP,
    ) if seasonal > 0 else Decimal('0')

    ly = ctx.obrat(cilovy_rok - 1, mesic)
    obrat_ly = float(ly) if ly else 0

    pm_out = {
        'rok': cilovy_rok,
        'mesic': mesic,
        'obrat_pred': _round_kc(obrat_pred),
        'obrat_ly': _round_kc(obrat_ly),
        'delta_pct_ly': _round_pct((float(obrat_pred) / obrat_ly - 1) * 100) if obrat_ly else None,
        'rust_pouzity_pct': _round_pct(rust * 100),
        'confidence': _confidence(hist_n),
        'history_months_same': hist_n,
    }
    return pm_out


def predikce_rok(
    cilovy_rok,
    rust_procent=None,
    mesice_historie=36,
    reference=None,
    ctx=None,
    include_chybejici_pobocky=False,
):
    ref = reference or date.today()
    if ctx is None:
        ctx = ForecastContext(cilovy_rok, mesice_historie=mesice_historie, reference=ref)
    mesice = []
    warnings = []
    confidences = []
    for m in range(1, 13):
        pm = predikce_mesic_nahled(
            ctx, m, rust_procent=rust_procent, mesice_historie=mesice_historie,
        )
        dopln_plneni_k_mesici(pm, reference=ref, ctx=ctx)
        if include_chybejici_pobocky and not ctx.prodejna_ids:
            chybi = pobocky_bez_dat_v_mesici(cilovy_rok, m)
            if chybi:
                pm['chybejici_pobocky'] = chybi
        mesice.append(pm)
        confidences.append(pm['confidence'])
        if pm['confidence'] == 'low':
            warnings.append(
                f'{m:02d}/{cilovy_rok}: málo historických dat pro stejný měsíc '
                f'({pm["history_months_same"]} roky).'
            )

    if all(c == 'low' for c in confidences):
        meta_conf = 'low'
    elif any(c == 'low' for c in confidences):
        meta_conf = 'medium'
    else:
        meta_conf = 'high'

    celkem = sum(x['obrat_pred'] for x in mesice)
    return {
        'rok': cilovy_rok,
        'mesice': mesice,
        'celkem_obrat_pred': _round_kc(celkem),
        'plneni_souhrn': _souhrn_plneni_roku(mesice),
        'souhrn_roku': _souhrn_roku_kompletni(mesice, reference=ref),
        'meta': {
            'mesice_historie': mesice_historie,
            'confidence': meta_conf,
            'min_historie': min(x['history_months_same'] for x in mesice),
            'reference_date': ref.isoformat(),
        },
        'warnings': warnings,
    }


def vyhled_forecast(
    hlavni_rok,
    compare_roky=None,
    rust_procent=None,
    mesice_historie=36,
    reference=None,
    prodejna_id=None,
    prodejna_ids=None,
):
    """
    Hlavní predikční rok + volitelné roky do grafu (skutečnost nebo predikce).
    """
    from stores.models import Prodejna

    ref = reference or date.today()
    pids = None
    if prodejna_ids:
        pids = sorted({int(x) for x in prodejna_ids if x is not None})
    elif prodejna_id:
        pids = [int(prodejna_id)]
    compare = sorted({int(r) for r in (compare_roky or []) if r is not None}, reverse=True)
    roky_graf = sorted({hlavni_rok} | set(compare), reverse=True)

    ctx = ForecastContext(
        hlavni_rok,
        mesice_historie=mesice_historie,
        reference=ref,
        compare_roky=compare,
        prodejna_ids=pids,
    )
    predikce = predikce_rok(
        hlavni_rok,
        rust_procent=rust_procent,
        mesice_historie=mesice_historie,
        reference=ref,
        ctx=ctx,
        include_chybejici_pobocky=True,
    )

    porovnani = []
    for rok in roky_graf:
        if rok == hlavni_rok:
            continue
        if rok >= ref.year:
            sub = ctx.for_rok(rok)
            data = predikce_rok(
                rok,
                rust_procent=rust_procent,
                mesice_historie=mesice_historie,
                reference=ref,
                ctx=sub,
            )
            typ = 'predikce' if any(m.get('stav') == 'budouci' for m in data['mesice']) else 'mix'
            serie = {
                'rok': rok,
                'typ': typ,
                'mesice': [
                    {
                        'mesic': m['mesic'],
                        'obrat': m.get('plneni', {}) and m['plneni'].get('obrat')
                        or m['obrat_pred'],
                        'obrat_pred': m['obrat_pred'],
                        'obrat_skutecny': (m.get('plneni') or {}).get('obrat'),
                        'stav': m.get('stav'),
                    }
                    for m in data['mesice']
                ],
                'celkem_obrat': data['celkem_obrat_pred'],
            }
        else:
            serie = _serie_skutecnost_rok(ctx, rok, ref)
        porovnani.append(serie)

    from .plan_service import mesice_bez_aktualniho_planu

    roky_meta = dostupne_roky_z_prodeje()
    mesice_bez_planu = mesice_bez_aktualniho_planu(hlavni_rok)
    prodejny_meta = [
        {'id': p.id, 'nazev': p.nazev}
        for p in Prodejna.get_aktivni_prodejny()
    ]
    prodejna_nazev = None
    if pids:
        nazvy = list(
            Prodejna.objects.filter(pk__in=pids).order_by('poradi', 'nazev').values_list('nazev', flat=True),
        )
        prodejna_nazev = ', '.join(nazvy) if nazvy else None
    filtr = 'firma'
    if pids:
        filtr = 'prodejna' if len(pids) == 1 else 'prodejny'

    return {
        'hlavni_rok': hlavni_rok,
        'predikce': predikce,
        'porovnani_roky': porovnani,
        'roky_graf': roky_graf,
        'meta': {
            'dostupne_roky': roky_meta['roky'],
            'rok_od': roky_meta['rok_od'],
            'rok_do': roky_meta['rok_do'],
            'prodejny': prodejny_meta,
            'prodejna_id': pids[0] if pids and len(pids) == 1 else None,
            'prodejna_ids': pids or [],
            'prodejna_nazev': prodejna_nazev,
            'filtr': filtr,
            'mesice_bez_planu': mesice_bez_planu,
            'pocet_mesicu_bez_planu': len(mesice_bez_planu),
        },
    }
