import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { castkaBezDphZCelkem } from '../../utils/dph';
import './PlansModule.css';
import ProdejnaKarta from './ProdejnaKarta';
import DraftNumberInput from './DraftNumberInput';

const NAZVY_MESICU = [
  'Leden','Únor','Březen','Duben','Květen','Červen',
  'Červenec','Srpen','Září','Říjen','Listopad','Prosinec'
];

const ONBOARDING_KEY = 'plans_onboarding_dismissed_v1';

const formatCastka = (v) =>
  Number(v).toLocaleString('cs-CZ', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) + ' Kč';

/** Závorka s částkou bez DPH (plán je zadáván s 21 % DPH) */
const formatBezDphParen = (sDph) => {
  const bez = castkaBezDphZCelkem(sDph);
  if (!bez) return null;
  return (
    <span className="plans-castka-bezdph"> ({formatCastka(bez)} bez DPH)</span>
  );
};

const trendTrida = (pct) => {
  if (pct == null) return '';
  if (pct >= 100) return 'plneni-trend-ok';
  if (pct >= 80) return 'plneni-trend-var';
  return 'plneni-trend-chyba';
};

const plneniBarWidthPct = (pct) => Math.min(100, Math.max(0, Number(pct) || 0));

const plneniFillClass = (pct) =>
  `plneni-progress-fill${(Number(pct) || 0) >= 100 ? ' plneni-over' : ''}`;

const dnesniMesic = () => {
  const d = new Date();
  return { rok: d.getFullYear(), mesic: d.getMonth() + 1 };
};

const generateMesiceOptions = () => {
  const options = [];
  const dnes = new Date();
  for (let i = -6; i <= 3; i++) {
    const d = new Date(dnes.getFullYear(), dnes.getMonth() + i, 1);
    options.push({ rok: d.getFullYear(), mesic: d.getMonth() + 1 });
  }
  return options;
};

/** Normalizuje lock_mode z backendu (fallback z legacy zamknuto). */
const normalizeLockMode = (lm, zamknuto) => {
  if (lm === 'pct' || lm === 'kc' || lm === 'none') return lm;
  if (zamknuto === true) return 'pct';
  return 'none';
};

export default function PlansModule() {
  const location = useLocation();
  const navigate = useNavigate();
  const [vybraneMesic, setVybraneMesic] = useState(dnesniMesic());
  const [planData, setPlanData] = useState(null); // eslint-disable-line no-unused-vars
  const [verze, setVerze] = useState([]);
  const [vybrana_verze_id, setVybranaVezeId] = useState(null);
  const [aktivniPlan, setAktivniPlan] = useState(null);

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [chyba, setChyba] = useState(null);
  const [uspech, setUspech] = useState(null);
  const [warnings, setWarnings] = useState([]);

  const [castkaFirma, setCastkaFirma] = useState('');
  const [totalLock, setTotalLock] = useState(false);
  const [planovaciRezim, setPlanovaciRezim] = useState('top_down'); // 'top_down' | 'bottom_up'
  const [rustProcent, setRustProcent] = useState('10');
  const [prodejny, setProdejny] = useState([]);
  const [novaVerze, setNovaVerze] = useState(false);
  const [prepocet, setPrepocet] = useState(null);
  const [onboardingDismissed, setOnboardingDismissed] = useState(() => {
    if (typeof window === 'undefined') return false;
    try { return window.localStorage.getItem(ONBOARDING_KEY) === '1'; } catch (_) { return false; }
  });

  const [viewMode, setViewMode] = useState(() => {
    if (typeof window === 'undefined') return 'plan';
    const h = window.location.hash;
    if (h === '#plneni-prodejny') return 'prodejny';
    if (h === '#plneni-prodejci') return 'prodejci';
    return 'plan';
  });
  const [plneniData, setPlneniData] = useState(null);
  const [plneniProdejciData, setPlneniProdejciData] = useState(null);
  const [plneniLoading, setPlneniLoading] = useState(false);

  const mesiceOptions = generateMesiceOptions();

  const loadPlneni = useCallback(async (rok, mesic) => {
    setPlneniLoading(true);
    try {
      const res = await axios.get(`/api/plans/${rok}/${mesic}/plneni/`);
      setPlneniData(res.data.plneni);
    } catch {
      setPlneniData(null);
    } finally {
      setPlneniLoading(false);
    }
  }, []);

  const loadPlneniProdejci = useCallback(async (rok, mesic) => {
    setPlneniLoading(true);
    try {
      const res = await axios.get(`/api/plans/${rok}/${mesic}/plneni-prodejci/`);
      setPlneniProdejciData(res.data.prodejci || []);
    } catch {
      setPlneniProdejciData([]);
    } finally {
      setPlneniLoading(false);
    }
  }, []);

  useEffect(() => {
    if (viewMode === 'prodejny' && aktivniPlan) {
      loadPlneni(vybraneMesic.rok, vybraneMesic.mesic);
    } else {
      setPlneniData(null);
    }
  }, [viewMode, aktivniPlan, vybraneMesic, loadPlneni]);

  useEffect(() => {
    if (viewMode === 'prodejci' && aktivniPlan) {
      loadPlneniProdejci(vybraneMesic.rok, vybraneMesic.mesic);
    } else {
      setPlneniProdejciData(null);
    }
  }, [viewMode, aktivniPlan, vybraneMesic, loadPlneniProdejci]);

  useEffect(() => {
    const h = location.hash || '';
    if (h === '#plneni-prodejny') setViewMode('prodejny');
    else if (h === '#plneni-prodejci') setViewMode('prodejci');
  }, [location.hash]);

  useEffect(() => {
    if (location.state?.fromDashboardPlans) {
      setViewMode('plan');
      navigate(`${location.pathname}${location.search}`, { replace: true, state: null });
    }
  }, [location.state, location.pathname, location.search, navigate]);

  useEffect(() => {
    if (location.hash !== '#plneni-prodejny' || viewMode !== 'prodejny' || !plneniData) return;
    const id = window.requestAnimationFrame(() => {
      document.getElementById('plans-anc-prodejny')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    return () => window.cancelAnimationFrame(id);
  }, [location.hash, viewMode, plneniData]);

  useEffect(() => {
    if (location.hash !== '#plneni-prodejci' || viewMode !== 'prodejci' || plneniProdejciData == null) return;
    const id = window.requestAnimationFrame(() => {
      document.getElementById('plans-anc-prodejci')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    return () => window.cancelAnimationFrame(id);
  }, [location.hash, viewMode, plneniProdejciData]);

  const nactiVerziDoPlaneru = useCallback((plan) => {
    setCastkaFirma(String(Math.round(Number(plan.castka_celkem))));
    setTotalLock(Boolean(plan.total_lock));
    setProdejny(plan.prodejny.map(p => ({
      ...p,
      podil_procenta: Number(p.podil_procenta),
      castka_prodejna: Number(p.castka_prodejna),
      castka_prodej: Number(p.castka_prodej),
      castka_servis: Number(p.castka_servis),
      lock_mode: normalizeLockMode(p.lock_mode, p.zamknuto),
      servis_lock_mode: normalizeLockMode(p.servis_lock_mode, false),
      kategorie: (p.kategorie || []).map(k => ({
        ...k,
        podil_procenta: Number(k.podil_procenta),
        castka_kategorie: Number(k.castka_kategorie),
        prumerna_cena_za_kus: k.prumerna_cena_za_kus != null ? Number(k.prumerna_cena_za_kus) : null,
        lock_mode: normalizeLockMode(k.lock_mode, false),
      })),
    })));
    setPrepocet(null);
  }, []);

  const loadPlan = useCallback(async (rok, mesic) => {
    setLoading(true);
    setChyba(null);
    setWarnings([]);
    try {
      const res = await axios.get(`/api/plans/${rok}/${mesic}/`);
      setVerze(res.data.verze || []);
      const aktualni = res.data.aktualni;
      if (aktualni) {
        setAktivniPlan(aktualni);
        nactiVerziDoPlaneru(aktualni);
        setVybranaVezeId(aktualni.id);
      } else {
        setAktivniPlan(null);
        setProdejny([]);
        setCastkaFirma('');
        setVybranaVezeId(null);
      }
    } catch (e) {
      setChyba('Nepodařilo se načíst plán.');
    } finally {
      setLoading(false);
    }
  }, [nactiVerziDoPlaneru]);

  useEffect(() => {
    loadPlan(vybraneMesic.rok, vybraneMesic.mesic);
  }, [vybraneMesic, loadPlan]);

  const loadVerzi = async (verzeId) => {
    setLoading(true);
    try {
      const res = await axios.get(`/api/plans/verze/${verzeId}/`);
      nactiVerziDoPlaneru(res.data);
      setVybranaVezeId(verzeId);
    } catch {
      setChyba('Nepodařilo se načíst verzi.');
    } finally {
      setLoading(false);
    }
  };

  const vytvorNovyPlan = async (copyFromPrevious = false) => {
    const castka = Number(String(castkaFirma).replace(/\s/g, ''));
    if (!castka || castka < 500000) {
      setChyba('Zadejte celkovou částku (min. 500 000 Kč).');
      return;
    }
    setLoading(true);
    setChyba(null);
    try {
      const res = await axios.post(`/api/plans/${vybraneMesic.rok}/${vybraneMesic.mesic}/`, {
        castka_celkem: castka,
        copy_from_previous: copyFromPrevious,
      });
      setAktivniPlan(res.data);
      nactiVerziDoPlaneru(res.data);
      await loadPlan(vybraneMesic.rok, vybraneMesic.mesic);
      setUspech('Plán byl vytvořen.');
    } catch (e) {
      setChyba(e.response?.data?.error || 'Nepodařilo se vytvořit plán.');
    } finally {
      setLoading(false);
    }
  };

  const vytvorPlanZHistorie = async () => {
    const rust = Number(String(rustProcent).replace(',', '.'));
    if (Number.isNaN(rust) || rust < -100) {
      setChyba('Zadejte platné procento růstu (např. 10 pro +10 %).');
      return;
    }
    setLoading(true);
    setChyba(null);
    try {
      const res = await axios.post(`/api/plans/${vybraneMesic.rok}/${vybraneMesic.mesic}/`, {
        create_from_history: true,
        rust_procent: rust,
      });
      setAktivniPlan(res.data);
      nactiVerziDoPlaneru(res.data);
      await loadPlan(vybraneMesic.rok, vybraneMesic.mesic);
      setUspech('Plán byl vytvořen z historie a růstu.');
    } catch (e) {
      setChyba(e.response?.data?.error || 'Nepodařilo se vytvořit plán z historie.');
    } finally {
      setLoading(false);
    }
  };

  // ---------- Payload builder (sdílený pro prepocet i ulozit) ----------
  const buildPayloadProdejny = useCallback(() => {
    return prodejny.map(p => ({
      prodejna_id: p.prodejna_id,
      prodejna_nazev: p.prodejna_nazev,
      podil_procenta: Number(p.podil_procenta).toFixed(3),
      castka_prodejna: Number(p.castka_prodejna).toFixed(2),
      castka_prodej: Number(p.castka_prodej).toFixed(2),
      castka_servis: Number(p.castka_servis).toFixed(2),
      lock_mode: p.lock_mode || 'none',
      servis_lock_mode: p.servis_lock_mode || 'none',
      zamknuto: (p.lock_mode === 'pct'),
      kategorie: (p.kategorie || []).map(k => ({
        kategorie_kod: k.kategorie_kod,
        podil_procenta: Number(k.podil_procenta).toFixed(3),
        castka_kategorie: Number(k.castka_kategorie).toFixed(2),
        lock_mode: k.lock_mode || 'none',
        ...(k.prumerna_cena_za_kus != null && { prumerna_cena_za_kus: Number(k.prumerna_cena_za_kus).toFixed(2) }),
      })),
    }));
  }, [prodejny]);

  // ---------- Debounced dry-run /prepocet/ ----------
  const prepocetTimer = useRef(null);
  const prepocetInFlight = useRef(false);

  useEffect(() => {
    if (!aktivniPlan || viewMode !== 'plan') return;
    if (prodejny.length === 0) return;
    const castka = Number(String(castkaFirma).replace(/\s/g, ''));
    if (!castka || castka < 500000) return;

    const schedule = (delay) => {
      if (prepocetTimer.current) clearTimeout(prepocetTimer.current);
      prepocetTimer.current = setTimeout(run, delay);
    };

    const run = async () => {
      // Focus guard – pokud je v .plans-module focusovaný input, posuneme o 400 ms
      if (typeof document !== 'undefined') {
        const ae = document.activeElement;
        if (ae && ae.tagName === 'INPUT' && ae.closest && ae.closest('.plans-module')) {
          schedule(400);
          return;
        }
      }
      if (prepocetInFlight.current) {
        schedule(400);
        return;
      }
      prepocetInFlight.current = true;
      try {
        const payload = {
          castka_celkem: castka,
          total_lock: totalLock,
          prodejny: buildPayloadProdejny(),
        };
        const res = await axios.post(`/api/plans/${vybraneMesic.rok}/${vybraneMesic.mesic}/prepocet/`, payload);
        setPrepocet(res.data);
      } catch (_e) {
        setPrepocet(null);
      } finally {
        prepocetInFlight.current = false;
      }
    };

    schedule(500);
    return () => {
      if (prepocetTimer.current) clearTimeout(prepocetTimer.current);
    };
  }, [aktivniPlan, viewMode, prodejny, castkaFirma, totalLock, vybraneMesic, buildPayloadProdejny]);

  // Promítnutí dopočtu do prodejen jako *_dopocet pole (shadow, nepřepisuje vstup)
  const prodejnyWithDopocet = useMemo(() => {
    if (!prepocet || !prepocet.prodejny) return prodejny;
    const mapa = Object.fromEntries(prepocet.prodejny.map(p => [p.prodejna_id, p]));
    return prodejny.map(p => {
      const pd = mapa[p.prodejna_id];
      if (!pd) return p;
      const katMapa = Object.fromEntries((pd.kategorie || []).map(k => [k.kategorie_kod, k]));
      return {
        ...p,
        podil_procenta_dopocet: pd.podil_procenta != null ? Number(pd.podil_procenta) : null,
        castka_prodejna_dopocet: pd.castka_prodejna != null ? Number(pd.castka_prodejna) : null,
        castka_prodej_dopocet: pd.castka_prodej != null ? Number(pd.castka_prodej) : null,
        castka_servis_dopocet: pd.castka_servis != null ? Number(pd.castka_servis) : null,
        kategorie: (p.kategorie || []).map(k => {
          const kd = katMapa[k.kategorie_kod];
          if (!kd) return k;
          return {
            ...k,
            podil_procenta_dopocet: kd.podil_procenta != null ? Number(kd.podil_procenta) : null,
            castka_kategorie_dopocet: kd.castka_kategorie != null ? Number(kd.castka_kategorie) : null,
          };
        }),
      };
    });
  }, [prodejny, prepocet]);

  const ulozitPlan = async () => {
    // V bottom-up režimu posíláme prepocet.castka_celkem (součet Kč)
    let castka = Number(String(castkaFirma).replace(/\s/g, ''));
    if (planovaciRezim === 'bottom_up' && prepocet?.soucet_castek) {
      castka = Number(prepocet.soucet_castek);
    }
    if (!castka) {
      setChyba('Zadejte celkovou částku firmy.');
      return;
    }
    setSaving(true);
    setChyba(null);
    setUspech(null);
    setWarnings([]);
    try {
      const payload = {
        castka_celkem: castka,
        total_lock: totalLock,
        nova_verze: novaVerze,
        prodejny: buildPayloadProdejny(),
      };
      const res = await axios.put(`/api/plans/${vybraneMesic.rok}/${vybraneMesic.mesic}/ulozit/`, payload);
      setAktivniPlan(res.data);
      nactiVerziDoPlaneru(res.data);
      await loadPlan(vybraneMesic.rok, vybraneMesic.mesic);
      setUspech('Plán byl uložen.');
      setWarnings(res.data?.warnings || []);
      setNovaVerze(false);
    } catch (e) {
      setChyba(e.response?.data?.error || 'Nepodařilo se uložit plán.');
    } finally {
      setSaving(false);
    }
  };

  const setAktualniVerzi = async (verzeId) => {
    try {
      await axios.post(`/api/plans/verze/${verzeId}/set-aktualni/`);
      await loadPlan(vybraneMesic.rok, vybraneMesic.mesic);
      setUspech('Verze nastavena jako aktuální.');
    } catch {
      setChyba('Nepodařilo se nastavit verzi.');
    }
  };

  const onProdejnaChange = (prodejnaId, zmeny) => {
    setProdejny(prev => prev.map(p => p.prodejna_id === prodejnaId ? { ...p, ...zmeny } : p));
    // Invalidace stínového dopočtu – jinak by zastaralé *_dopocet hodnoty
    // přebíjely aktuální vstup (slider/číselník by vizuálně skákal zpět),
    // než dorazí nový /prepocet/ po debounce.
    setPrepocet(null);
  };

  const dismissOnboarding = () => {
    setOnboardingDismissed(true);
    try { window.localStorage.setItem(ONBOARDING_KEY, '1'); } catch (_) { /* noop */ }
  };

  // ---------- Souhrn / banner ----------
  const castkaFirmaNum = Number(String(castkaFirma).replace(/\s/g, ''));
  const soucetPodilu = prepocet?.soucet_podilu != null
    ? Number(prepocet.soucet_podilu)
    : prodejny.reduce((s, p) => s + Number(p.podil_procenta), 0);
  const soucetCastek = prepocet?.soucet_castek != null
    ? Number(prepocet.soucet_castek)
    : prodejny.reduce((s, p) => s + Number(p.castka_prodejna), 0);
  const soucetZamkPct = prepocet?.soucet_zamk_pct != null ? Number(prepocet.soucet_zamk_pct) : 0;
  const soucetZamkKc = prepocet?.soucet_zamk_kc != null ? Number(prepocet.soucet_zamk_kc) : 0;
  const soucetAutoPct = prepocet?.soucet_auto_pct != null ? Number(prepocet.soucet_auto_pct) : 0;
  const prepocetCelek = prepocet?.castka_celkem != null ? Number(prepocet.castka_celkem) : castkaFirmaNum;

  const diffCastek = Math.abs(soucetCastek - castkaFirmaNum);
  const hasWarnings = (prepocet?.warnings?.length || 0) > 0;
  let souhrnStav = 'ok';
  if (totalLock && diffCastek > 1) souhrnStav = 'error';
  else if (hasWarnings || Math.abs(soucetPodilu - 100) > 0.5) souhrnStav = 'warn';

  const agrFirmaKategorie = useMemo(() => {
    const agg = {};
    prodejny.forEach(p => {
      (p.kategorie || []).forEach(k => {
        const kod = k.kategorie_kod;
        if (!agg[kod]) {
          agg[kod] = { kategorie_kod: kod, kategorie_nazev: k.kategorie_nazev, castka: 0, kusy: 0 };
        }
        agg[kod].castka += Number(k.castka_kategorie) || 0;
        const ks = k.pocet_kusu;
        agg[kod].kusy += (ks != null && !Number.isNaN(ks)) ? ks : 0;
      });
    });
    return Object.values(agg).sort((a, b) => (a.kategorie_nazev || '').localeCompare(b.kategorie_nazev || ''));
  }, [prodejny]);

  const dorovnatCelek = () => {
    setCastkaFirma(String(Math.round(prepocetCelek)));
    setTotalLock(false);
  };

  const firmaInputReadOnly = planovaciRezim === 'bottom_up';
  const firmaInputValue = firmaInputReadOnly
    ? String(Math.round(soucetCastek))
    : castkaFirma;

  return (
    <div className="plans-module">
      <div className="plans-header">
        <h2 className="plans-title">Firemní plány</h2>

        <div className="plans-controls">
          {aktivniPlan && viewMode === 'plan' && (
            <div className="plans-control-group">
              <label>Režim plánování</label>
              <div className="plans-toggle-row">
                <button
                  type="button"
                  className={`plans-toggle-btn ${planovaciRezim === 'top_down' ? 'plans-toggle-btn-active' : ''}`}
                  onClick={() => setPlanovaciRezim('top_down')}
                  title="Zadáte celkovou částku a rozpočtete ji na prodejny"
                >
                  Top-down
                </button>
                <button
                  type="button"
                  className={`plans-toggle-btn ${planovaciRezim === 'bottom_up' ? 'plans-toggle-btn-active' : ''}`}
                  onClick={() => setPlanovaciRezim('bottom_up')}
                  title="Zadáte Kč cíle prodejen a celkem se sčítá"
                >
                  Bottom-up
                </button>
              </div>
            </div>
          )}

          {aktivniPlan && (
            <div className="plans-control-group">
              <label>Zobrazení</label>
              <div className="plans-toggle-row">
                <button
                  type="button"
                  className={`plans-toggle-btn ${viewMode === 'plan' ? 'plans-toggle-btn-active' : ''}`}
                  onClick={() => setViewMode('plan')}
                >
                  Plán
                </button>
                <button
                  type="button"
                  className={`plans-toggle-btn ${viewMode === 'prodejny' ? 'plans-toggle-btn-active' : ''}`}
                  onClick={() => setViewMode('prodejny')}
                >
                  Plnění Prodejny
                </button>
                <button
                  type="button"
                  className={`plans-toggle-btn ${viewMode === 'prodejci' ? 'plans-toggle-btn-active' : ''}`}
                  onClick={() => setViewMode('prodejci')}
                >
                  Plnění Prodejci
                </button>
              </div>
            </div>
          )}
          <div className="plans-control-group">
            <label>Měsíc</label>
            <select
              value={`${vybraneMesic.rok}-${vybraneMesic.mesic}`}
              onChange={e => {
                const [r, m] = e.target.value.split('-').map(Number);
                setVybraneMesic({ rok: r, mesic: m });
              }}
              className="plans-select"
            >
              {mesiceOptions.map(o => (
                <option key={`${o.rok}-${o.mesic}`} value={`${o.rok}-${o.mesic}`}>
                  {NAZVY_MESICU[o.mesic - 1]} {o.rok}
                </option>
              ))}
            </select>
          </div>

          {verze.length > 1 && (
            <div className="plans-control-group">
              <label>Verze</label>
              <select
                value={vybrana_verze_id || ''}
                onChange={e => loadVerzi(Number(e.target.value))}
                className="plans-select"
              >
                {verze.map(v => (
                  <option key={v.id} value={v.id}>
                    v{v.cislo_verze} – {formatCastka(v.castka_celkem)}
                    {v.je_aktualni ? ' ★' : ''}
                  </option>
                ))}
              </select>
              {vybrana_verze_id && !verze.find(v => v.id === vybrana_verze_id)?.je_aktualni && (
                <button className="plans-btn plans-btn-sm" onClick={() => setAktualniVerzi(vybrana_verze_id)}>
                  Nastavit jako aktuální
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Onboarding info-box */}
      {!onboardingDismissed && viewMode === 'plan' && aktivniPlan && (
        <div className="plans-onboarding">
          <span className="plans-onboarding-icon" aria-hidden="true">💡</span>
          <div className="plans-onboarding-text">
            <strong>Nové zámky a režimy plánování.</strong>{' '}
            U každé prodejny/kategorie si zvolíte zámek:
            {' '}<span className="plans-tag plans-tag-auto">🔓 Auto</span> – dopočítá se,
            {' '}<span className="plans-tag plans-tag-pct">🔒 %</span> – zamčené procento,
            {' '}<span className="plans-tag plans-tag-kc">💰 Kč</span> – zamčená absolutní částka.
            {' '}V režimu <span className="plans-kbd">Top-down</span> zadáváte celek a systém rozpočítá, v režimu
            {' '}<span className="plans-kbd">Bottom-up</span> zadáváte Kč cíle prodejen a celek se sečte.
          </div>
          <button className="plans-onboarding-close" onClick={dismissOnboarding} title="Zavřít" aria-label="Zavřít">×</button>
        </div>
      )}

      {chyba && <div className="plans-alert plans-alert-error">{chyba} <button onClick={() => setChyba(null)}>×</button></div>}
      {uspech && <div className="plans-alert plans-alert-success">{uspech} <button onClick={() => setUspech(null)}>×</button></div>}
      {warnings && warnings.length > 0 && (
        <div className="plans-alert plans-alert-warn">
          <strong>Upozornění:</strong>
          <ul className="plans-souhrn-warnings">
            {warnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
          <button onClick={() => setWarnings([])}>×</button>
        </div>
      )}

      {loading && <div className="plans-loading">Načítám...</div>}

      {!loading && !aktivniPlan && (
        <div className="plans-empty">
          <h3>Pro {NAZVY_MESICU[vybraneMesic.mesic - 1]} {vybraneMesic.rok} zatím neexistuje plán.</h3>
          <div className="plans-empty-form">
            <label>Celková částka firmy (Kč)</label>
            <input
              type="number"
              value={castkaFirma}
              onChange={e => setCastkaFirma(e.target.value)}
              placeholder="např. 3000000"
              className="plans-input"
              min="500000"
              max="90000000"
            />
            <div className="plans-empty-actions">
              <button className="plans-btn plans-btn-primary" onClick={() => vytvorNovyPlan(false)} disabled={loading}>
                Vytvořit prázdný plán
              </button>
              <button className="plans-btn plans-btn-secondary" onClick={() => vytvorNovyPlan(true)} disabled={loading}>
                Zkopírovat z předchozího měsíce
              </button>
            </div>
            <div className="plans-empty-form plans-empty-form-historie">
              <label>Růst oproti minulému roku (%)</label>
              <input
                type="number"
                value={rustProcent}
                onChange={e => setRustProcent(e.target.value)}
                placeholder="10"
                className="plans-input plans-input-sm"
                min="-100"
                max="500"
                step="0.5"
              />
              <button
                className="plans-btn plans-btn-primary"
                onClick={vytvorPlanZHistorie}
                disabled={loading}
              >
                Vyplnit z historie + růst
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ==== Plnění Prodejny ==== */}
      {!loading && aktivniPlan && viewMode === 'prodejny' && (
        <div className="plans-plneni">
          {plneniLoading && <div className="plneni-loading">Načítám plnění...</div>}
          {!plneniLoading && plneniData && (
            <>
              <div className="plneni-preview">
                <div className="plneni-preview-item">
                  <span className="plneni-preview-label">Plán</span>
                  <span className="plneni-preview-value">
                    {formatCastka(castkaFirmaNum)}
                    {formatBezDphParen(castkaFirmaNum)}
                  </span>
                </div>
                <div className="plneni-preview-item">
                  <span className="plneni-preview-label">Plníme</span>
                  <span className="plneni-preview-value plneni-pct">
                    {plneniData.firma?.plneni_procent ?? 0} %
                  </span>
                </div>
                {plneniData.firma?.trend_procent != null && (
                  <div className={`plneni-preview-item plneni-trend ${trendTrida(plneniData.firma.trend_procent)}`}>
                    <span className="plneni-preview-label">Trend</span>
                    <span className="plneni-preview-value">
                      ~{plneniData.firma.trend_procent} % na konci měsíce
                    </span>
                  </div>
                )}
              </div>

              <div className="plneni-sekce">
                <h3 className="plneni-nadpis">Plnění plánu firmy</h3>
                <div className="plneni-bar-wrap">
                  <div className="plneni-bar-label">
                    <span>Celkem</span>
                    <span className="plneni-bar-meta">
                      {formatCastka(plneniData.firma?.skutecny_obrat || 0)}
                      {formatBezDphParen(plneniData.firma?.skutecny_obrat || 0)}
                      {' / '}
                      {formatCastka(castkaFirmaNum)}
                      {formatBezDphParen(castkaFirmaNum)}
                      <span className="plneni-pct-badge">{plneniData.firma?.plneni_procent ?? 0} %</span>
                      {plneniData.firma?.trend_obrat != null && (
                        <span className={`plneni-trend-badge ${trendTrida(plneniData.firma.trend_procent)}`}>
                          → ~{formatCastka(plneniData.firma.trend_obrat)}
                          {formatBezDphParen(plneniData.firma.trend_obrat)}
                        </span>
                      )}
                    </span>
                  </div>
                  <div className="plneni-progress-track">
                    <div
                      className={plneniFillClass(plneniData.firma?.plneni_procent)}
                      style={{ width: `${plneniBarWidthPct(plneniData.firma?.plneni_procent)}%` }}
                    />
                  </div>
                </div>
              </div>

              <div className="plneni-sekce">
                <h3 className="plneni-nadpis">Kategorie (firma)</h3>
                <div className="plneni-kategorie-list">
                  {agrFirmaKategorie.map(kat => {
                    const pd = plneniData.kategorie?.[kat.kategorie_kod] || {};
                    const pct = pd.plneni_procent ?? 0;
                    return (
                      <div key={kat.kategorie_kod} className="plneni-kat-item">
                        <div className="plneni-bar-label">
                          <span>{kat.kategorie_nazev || kat.kategorie_kod}</span>
                          <span className="plneni-bar-meta">
                            {pd.skutecne_kusy ?? 0} / {kat.kusy} ks
                            <span className="plneni-pct-badge">{pct} %</span>
                            {pd.trend_kusy != null && (
                              <span className={`plneni-trend-badge ${trendTrida(pd.trend_procent)}`}>
                                → ~{pd.trend_kusy} ks
                              </span>
                            )}
                          </span>
                        </div>
                        <div className="plneni-progress-track">
                          <div
                            className={plneniFillClass(pct)}
                            style={{ width: `${plneniBarWidthPct(pct)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="plneni-sekce">
                <h3 className="plneni-nadpis" id="plans-anc-prodejny">
                  Prodejny
                </h3>
                {prodejny.map(p => {
                  const pdProd = plneniData.prodejny?.[p.prodejna_id] || {};
                  const pctProd = pdProd.plneni_procent ?? 0;
                  return (
                    <div key={p.prodejna_id} className="plneni-prodejna">
                      <div className="plneni-prodejna-header">
                        <span className="plneni-prodejna-nazev">{p.prodejna_nazev}</span>
                        <span className="plneni-bar-meta">
                          {formatCastka(pdProd.skutecny_obrat || 0)}
                          {formatBezDphParen(pdProd.skutecny_obrat || 0)}
                          {' / '}
                          {formatCastka(p.castka_prodejna)}
                          {formatBezDphParen(p.castka_prodejna)}
                          <span className="plneni-pct-badge">{pctProd} %</span>
                          {pdProd.skutecne_kusy != null && ` · ${pdProd.skutecne_kusy} ks`}
                          {pdProd.trend_obrat != null && (
                            <span className={`plneni-trend-badge ${trendTrida(pdProd.trend_procent)}`}>
                              → ~{formatCastka(pdProd.trend_obrat)}
                              {formatBezDphParen(pdProd.trend_obrat)}
                            </span>
                          )}
                        </span>
                      </div>
                      <div className="plneni-bar-wrap plneni-bar-prodejna">
                        <div className="plneni-progress-track">
                          <div
                            className={plneniFillClass(pctProd)}
                            style={{ width: `${plneniBarWidthPct(pctProd)}%` }}
                          />
                        </div>
                      </div>
                      <div className="plneni-prodejna-kat">
                        {(p.kategorie || []).map(k => {
                          const pdKat = pdProd.kategorie?.[k.kategorie_kod] || {};
                          const pctKat = pdKat.plneni_procent ?? 0;
                          return (
                            <div key={k.id || k.kategorie_kod} className="plneni-kat-item plneni-kat-sub">
                              <div className="plneni-bar-label">
                                <span>{k.kategorie_nazev || k.kategorie_kod}</span>
                                <span className="plneni-bar-meta">
                                  {pdKat.skutecne_kusy ?? 0} / {k.pocet_kusu != null ? k.pocet_kusu : '—'} ks
                                  <span className="plneni-pct-badge">{pdKat.plneni_procent ?? 0} %</span>
                                  {pdKat.trend_kusy != null && (
                                    <span className={`plneni-trend-badge ${trendTrida(pdKat.trend_procent)}`}>
                                      → ~{pdKat.trend_kusy} ks
                                    </span>
                                  )}
                                </span>
                              </div>
                              <div className="plneni-progress-track">
                                <div
                                  className={plneniFillClass(pctKat)}
                                  style={{ width: `${plneniBarWidthPct(pctKat)}%` }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}
          {!plneniLoading && !plneniData && (
            <div className="plneni-empty">Plnění není k dispozici.</div>
          )}
        </div>
      )}

      {/* ==== Plnění Prodejci ==== */}
      {!loading && aktivniPlan && viewMode === 'prodejci' && (
        <div className="plans-plneni">
          {plneniLoading && <div className="plneni-loading">Načítám plnění prodejců...</div>}
          {!plneniLoading && plneniProdejciData && (
            <div className="plneni-sekce">
              <h3 className="plneni-nadpis" id="plans-anc-prodejci">
                Plnění prodejců
              </h3>
              {plneniProdejciData.length === 0 ? (
                <div className="plneni-empty">Žádní prodejci nemají nastavený plán pro tento měsíc.</div>
              ) : (
                plneniProdejciData.map(prod => {
                  const pctProd = prod.plneni_procent_kusy ?? 0;
                  return (
                    <div key={prod.prodejce_id} className="plneni-prodejna">
                      <div className="plneni-prodejna-header">
                        <span className="plneni-prodejna-nazev">
                          {prod.jmeno} {prod.prijmeni}
                          {prod.prodejna_nazev && (
                            <span className="plneni-prodejna-meta"> ({prod.prodejna_nazev})</span>
                          )}
                        </span>
                        <span className="plneni-bar-meta">
                          {prod.skutecne_kusy ?? 0} / {prod.plan_kusy ?? 0} ks
                          <span className="plneni-pct-badge">{pctProd} %</span>
                          {prod.trend_kusy != null && (
                            <span className={`plneni-trend-badge ${trendTrida(prod.trend_procent_kusy)}`}>
                              → ~{prod.trend_kusy} ks
                            </span>
                          )}
                        </span>
                      </div>
                      <div className="plneni-bar-wrap plneni-bar-prodejna">
                        <div className="plneni-progress-track">
                          <div
                            className={plneniFillClass(pctProd)}
                            style={{ width: `${plneniBarWidthPct(pctProd)}%` }}
                          />
                        </div>
                      </div>
                      <div className="plneni-prodejna-kat">
                        {(prod.kategorie || []).map(k => {
                          const pctKat = k.plneni_procent ?? 0;
                          const odchylka = (k.skutecne_kusy ?? 0) - (k.plan_kusy ?? 0);
                          const odchylkaClass = odchylka >= 0 ? 'plneni-trend-ok' : 'plneni-trend-chyba';
                          return (
                            <div key={k.kategorie_kod} className="plneni-kat-item plneni-kat-sub">
                              <div className="plneni-bar-label">
                                <span>{k.kategorie_nazev || k.kategorie_kod}</span>
                                <span className="plneni-bar-meta">
                                  {k.skutecne_kusy ?? 0} / {k.plan_kusy ?? 0} ks
                                  <span className="plneni-pct-badge">{pctKat} %</span>
                                  {k.plan_kusy != null && (
                                    <span className={`plneni-trend-badge ${odchylkaClass}`}>
                                      → {odchylka >= 0 ? '+' : ''}{odchylka} ks
                                    </span>
                                  )}
                                  {k.trend_kusy != null && (
                                    <span className={`plneni-trend-badge ${trendTrida(k.trend_procent)}`}>
                                      trend ~{k.trend_kusy} ks
                                    </span>
                                  )}
                                </span>
                              </div>
                              <div className="plneni-progress-track">
                                <div
                                  className={plneniFillClass(pctKat)}
                                  style={{ width: `${plneniBarWidthPct(pctKat)}%` }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>
      )}

      {/* ==== Editor plánu ==== */}
      {!loading && aktivniPlan && viewMode === 'plan' && (
        <>
          {/* Celková částka firmy */}
          <div className="plans-firma-castka">
            <div className="plans-firma-castka-inner">
              <label>Celková částka firmy {planovaciRezim === 'bottom_up' && <span className="plans-firma-hint">(součet prodejen, read-only)</span>}</label>
              <div className="plans-firma-input-row">
                <DraftNumberInput
                  value={firmaInputValue}
                  onChange={v => !firmaInputReadOnly && setCastkaFirma(String(v))}
                  decimals={0}
                  min={500000}
                  max={90000000}
                  disabled={firmaInputReadOnly}
                  className={`plans-input plans-input-lg ${totalLock ? 'plans-input-locked-kc' : ''}`}
                />
                {!firmaInputReadOnly && (
                  <button
                    type="button"
                    onClick={() => setTotalLock(v => !v)}
                    className={`plans-total-lock-btn ${totalLock ? 'plans-total-lock-btn-on' : ''}`}
                    title={totalLock ? 'Celek je pevně zamčený – zamčené hodnoty ho nepřepíšou.' : 'Auto-dopočet – zamčené hodnoty mohou celek zvýšit.'}
                  >
                    {totalLock ? '🔒 Pevná' : '🔓 Auto-dopočet'}
                  </button>
                )}
                <span className="plans-firma-formatted">
                  {castkaFirmaNum > 0 ? (
                    <>
                      {formatCastka(castkaFirmaNum)}
                      {formatBezDphParen(castkaFirmaNum)}
                    </>
                  ) : (
                    '—'
                  )}
                </span>
              </div>
              {castkaFirmaNum > 0 && castkaFirmaNum < 500000 && (
                <span className="plans-validace-chyba">Minimum je 500 000 Kč</span>
              )}
              {castkaFirmaNum > 90000000 && (
                <span className="plans-validace-chyba">Maximum je 90 000 000 Kč</span>
              )}
            </div>
          </div>

          {/* Souhrnný banner */}
          <div className={`plans-souhrn plans-souhrn-${souhrnStav}`}>
            <div className="plans-souhrn-radek">
              <span className="plans-souhrn-label">Součet podílů</span>
              <span className="plans-souhrn-hodnota">{soucetPodilu.toFixed(1)} %</span>
              <span className="plans-souhrn-label">Součet Kč</span>
              <span className="plans-souhrn-hodnota">{formatCastka(soucetCastek)}</span>
            </div>
            <div className="plans-souhrn-rozpad">
              <span className="plans-tag plans-tag-pct" title="Zamčené procento">🔒 {soucetZamkPct.toFixed(1)} %</span>
              <span className="plans-tag plans-tag-kc" title="Zamčená absolutní Kč">💰 {formatCastka(soucetZamkKc)}</span>
              <span className="plans-tag plans-tag-auto" title="Auto-dopočet (podíl %)">🔓 Auto {soucetAutoPct.toFixed(1)} %</span>
            </div>
            {totalLock && diffCastek > 1 && (
              <div className="plans-souhrn-dorovnani">
                <span className="plans-souhrn-poznamka">
                  Součet prodejen ({formatCastka(soucetCastek)}) nesedí s pevným celkem ({formatCastka(castkaFirmaNum)}).
                  Rozpočet navrhuje celek {formatCastka(prepocetCelek)}.
                </span>
                <button className="plans-btn plans-btn-primary plans-souhrn-cta" onClick={dorovnatCelek}>
                  Dorovnat celkovou částku na {formatCastka(prepocetCelek)}
                </button>
              </div>
            )}
            {prepocet?.warnings?.length > 0 && (
              <ul className="plans-souhrn-warnings">
                {prepocet.warnings.map((w, i) => <li key={i}>⚠ {w}</li>)}
              </ul>
            )}
          </div>

          {/* Prodejny */}
          <div className="plans-prodejny">
            {prodejnyWithDopocet.map(p => (
              <ProdejnaKarta
                key={p.prodejna_id}
                prodejna={p}
                castkaFirma={castkaFirmaNum}
                ostatniProdejny={prodejny.filter(o => o.prodejna_id !== p.prodejna_id)}
                onZmena={zmeny => onProdejnaChange(p.prodejna_id, zmeny)}
              />
            ))}
          </div>

          {/* Akce */}
          <div className="plans-actions">
            <label className="plans-checkbox-label">
              <input
                type="checkbox"
                checked={novaVerze}
                onChange={e => setNovaVerze(e.target.checked)}
              />
              Uložit jako novou verzi
            </label>
            <button
              className="plans-btn plans-btn-primary plans-btn-lg"
              onClick={ulozitPlan}
              disabled={saving || castkaFirmaNum < 500000 || castkaFirmaNum > 90000000}
            >
              {saving ? 'Ukládám...' : 'Uložit plán'}
            </button>
            <button
              className="plans-btn plans-btn-secondary"
              onClick={() => vytvorNovyPlan(true)}
              disabled={loading}
            >
              Zkopírovat z předchozího měsíce
            </button>
            <span className="plans-actions-historie">
              <input
                type="number"
                value={rustProcent}
                onChange={e => setRustProcent(e.target.value)}
                placeholder="10"
                className="plans-input plans-input-sm plans-input-inline"
                min="-100"
                max="500"
                step="0.5"
                title="Růst oproti minulému roku (%)"
              />
              <span className="plans-input-suffix">%</span>
              <button
                className="plans-btn plans-btn-secondary"
                onClick={vytvorPlanZHistorie}
                disabled={loading}
              >
                Vytvořit z minulého roku + růst
              </button>
            </span>
          </div>
        </>
      )}
    </div>
  );
}
