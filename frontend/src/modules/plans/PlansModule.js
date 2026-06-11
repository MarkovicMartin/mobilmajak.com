import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { plansAPI } from '../../services/api';
import { castkaBezDphZCelkem } from '../../utils/dph';
import { PageHeader } from '../../components/ui';
import './PlansModule.css';
import ProdejnaKarta from './ProdejnaKarta';
import DraftNumberInput from './DraftNumberInput';
import PlneniStrom, { PlneniHistorieMini } from './PlneniStrom';
import AuditZbytekPanel from './AuditZbytekPanel';
import VyhledFilterMenu from './VyhledFilterMenu';
import PlansNav from './PlansNav';
import {
  plansIdFromPath,
  plansIdFromHash,
  plansPathForId,
} from './plansSections';

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

const jeMesicAktualniNeboBudouci = (rok, mesic) => {
  const d = dnesniMesic();
  return rok > d.rok || (rok === d.rok && mesic >= d.mesic);
};

const GRAF_ROKY_BARVY = ['#1d4ed8', '#16a34a', '#d97706', '#7c3aed', '#db2777', '#475569'];

const formatKc = (v) =>
  Math.round(Number(v) || 0).toLocaleString('cs-CZ', { maximumFractionDigits: 0 }) + ' Kč';

/** Částka bez měny (tabulka výhledu – sloupec je v Kč). */
const formatNum = (v) => {
  const n = Math.round(Number(v) || 0);
  if (!n) return '—';
  return n.toLocaleString('cs-CZ', { maximumFractionDigits: 0 });
};

const formatKcShort = (v) => {
  const n = Math.round(Number(v) || 0);
  if (n >= 1_000_000) {
    return `${(n / 1_000_000).toLocaleString('cs-CZ', { maximumFractionDigits: 1 })} mil Kč`;
  }
  return formatKc(n);
};

const formatKcDeltaShort = (kc, { withKc = true } = {}) => {
  const v = Math.round(Number(kc) || 0);
  if (v === 0) return 'stejně';
  const abs = Math.abs(v);
  const word = v > 0 ? 'více' : 'méně';
  const suf = withKc ? ' Kč' : '';
  if (abs >= 1_000_000) {
    const mil = (abs / 1_000_000).toLocaleString('cs-CZ', { maximumFractionDigits: 1 });
    return `o ${mil} mil${suf} ${word}`;
  }
  if (abs >= 1000) {
    const tis = Math.round(abs / 1000).toLocaleString('cs-CZ');
    return `o ${tis} tis.${suf} ${word}`;
  }
  return `o ${abs.toLocaleString('cs-CZ')}${suf} ${word}`;
};

/** Plnění % + rozdíl pro shrnutí nahoře (slovně). */
const formatPorovnani = (pct, kc, { table = false } = {}) => {
  const parts = [];
  if (pct != null) parts.push(`${Math.round(pct)} %`);
  if (kc != null && kc !== 0) parts.push(formatKcDeltaShort(kc, { withKc: !table }));
  return parts.length ? parts.join(' · ') : '—';
};

/** Kompaktní rozdíl: -190tis, +324mil */
const formatDeltaTis = (kc) => {
  const v = Math.round(Number(kc) || 0);
  if (v === 0) return '';
  const sign = v > 0 ? '+' : '-';
  const abs = Math.abs(v);
  if (abs >= 1_000_000) {
    return `${sign}${(abs / 1_000_000).toLocaleString('cs-CZ', { maximumFractionDigits: 1 })}mil`;
  }
  if (abs >= 1000) {
    return `${sign}${Math.round(abs / 1000)}tis`;
  }
  return `${sign}${abs.toLocaleString('cs-CZ')}`;
};

/** Barva buňky vs …: down = červená, neutral = černá, up = zelená */
const vyhledPorovnaniTone = (pct, kc) => {
  const p = pct != null ? Math.round(Number(pct)) : null;
  const k = Math.round(Number(kc) || 0);
  if (p == null && k === 0) return 'neutral';
  if (p != null && p >= 98 && p <= 102 && Math.abs(k) < 50_000) return 'neutral';
  if (k > 0 || (p != null && p >= 103)) return 'up';
  if (k < 0 || (p != null && p <= 97)) return 'down';
  return 'neutral';
};

const formatPorovnaniCompact = (pct, kc) => {
  const p = pct != null ? Math.round(Number(pct)) : null;
  const delta = formatDeltaTis(kc);
  if (p == null && !delta) return null;
  const text = delta
    ? `${p != null ? `${p}%` : ''} ${delta}`.trim()
    : `${p}%`;
  return { text, tone: vyhledPorovnaniTone(pct, kc) };
};

const VyhledPorovnaniCell = ({ pct, kc }) => {
  const out = formatPorovnaniCompact(pct, kc);
  if (!out) return '—';
  return (
    <span className={`plans-vyhled-pct plans-vyhled-pct-${out.tone}`}>
      {out.text}
    </span>
  );
};

/** Řádky tooltipu měsíce – vše co je v grafu (hlavní rok + porovnání). */
const grafMesicTooltipRadky = (mesic, forecastPred, forecastData, hlavniRok) => {
  const radky = [];
  const hm = forecastPred?.mesice?.find(x => x.mesic === mesic);
  if (hm) {
    radky.push({
      key: `${hlavniRok}-pred`,
      dot: 'pred',
      label: `${hlavniRok} predikce`,
      hodnota: formatKc(hm.obrat_pred),
    });
    if (hm.plneni?.obrat != null) {
      radky.push({
        key: `${hlavniRok}-pln`,
        dot: 'pln',
        label: `${hlavniRok} plnění`,
        hodnota: formatKc(hm.plneni.obrat),
      });
    }
  }
  (forecastData?.porovnani_roky || []).forEach((serie, si) => {
    const row = serie.mesice?.find(x => x.mesic === mesic);
    if (!row) return;
    const val = row.obrat_skutecny ?? row.obrat ?? row.obrat_pred ?? 0;
    const jeSkutecnost = serie.typ === 'skutecnost';
    radky.push({
      key: `serie-${serie.rok}`,
      barva: GRAF_ROKY_BARVY[(si + 1) % GRAF_ROKY_BARVY.length],
      label: `${serie.rok} ${jeSkutecnost ? 'obrat' : 'predikce'}`,
      hodnota: formatKc(val),
    });
  });
  return radky;
};

const MESIC_ZKRATKA = ['Led', 'Úno', 'Bře', 'Dub', 'Kvě', 'Čvn', 'Čvc', 'Srp', 'Zář', 'Říj', 'Lis', 'Pro'];

const formatChybejiciPobocky = (list) => {
  if (!list?.length) return '';
  const labels = { bez_obratu: 'bez obratu', bez_smen: 'bez směn', bez_obratu_i_smen: 'bez obratu i směn' };
  return list.map(p => `${p.nazev} (${labels[p.duvod] || p.duvod})`).join(', ');
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
  const viewMode = plansIdFromPath(location.pathname);
  const [vybraneMesic, setVybraneMesic] = useState(dnesniMesic());
  const [planData, setPlanData] = useState(null); // eslint-disable-line no-unused-vars
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
  const [prepocet, setPrepocet] = useState(null);
  const [onboardingDismissed, setOnboardingDismissed] = useState(() => {
    if (typeof window === 'undefined') return false;
    try { return window.localStorage.getItem(ONBOARDING_KEY) === '1'; } catch (_) { return false; }
  });

  const [plneniData, setPlneniData] = useState(null);
  const [plneniProdejciData, setPlneniProdejciData] = useState(null);
  const [plneniLoading, setPlneniLoading] = useState(false);
  const [nahled3m, setNahled3m] = useState(null);
  const [nahled3mLoading, setNahled3mLoading] = useState(false);
  const [autoGenerating, setAutoGenerating] = useState(false);
  const [pokrocileOpen, setPokrocileOpen] = useState(false);
  const autoGenerateAttempted = useRef(null);

  const [forecastRok, setForecastRok] = useState(() => new Date().getFullYear());
  const [forecastCompareRoky, setForecastCompareRoky] = useState(() => {
    const y = new Date().getFullYear();
    return [y - 1, y - 2];
  });
  const [vyhledFirma, setVyhledFirma] = useState(true);
  const [vyhledProdejny, setVyhledProdejny] = useState([]);
  const [dostupneRoky, setDostupneRoky] = useState([]);
  const [forecastData, setForecastData] = useState(null);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [forecastCreating, setForecastCreating] = useState(false);
  const [prodejnyMenuOpen, setProdejnyMenuOpen] = useState(false);
  const [rokyMenuOpen, setRokyMenuOpen] = useState(false);
  const [draftVyhledFirma, setDraftVyhledFirma] = useState(true);
  const [draftVyhledProdejny, setDraftVyhledProdejny] = useState([]);
  const [draftForecastRok, setDraftForecastRok] = useState(() => new Date().getFullYear());
  const [draftCompareRoky, setDraftCompareRoky] = useState([]);

  const mesiceOptions = generateMesiceOptions();

  const loadPlneni = useCallback(async (rok, mesic) => {
    setPlneniLoading(true);
    try {
      const res = await plansAPI.getPlneni(rok, mesic);
      setPlneniData(res.plneni);
    } catch {
      setPlneniData(null);
    } finally {
      setPlneniLoading(false);
    }
  }, []);

  const loadPlneniProdejci = useCallback(async (rok, mesic) => {
    setPlneniLoading(true);
    try {
      const res = await plansAPI.getPlneniProdejci(rok, mesic);
      setPlneniProdejciData(res.prodejci || []);
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
    const base = location.pathname.replace(/\/$/, '');
    if (base === '/plans') {
      navigate('/plans/vyhled', { replace: true });
    }
  }, [location.pathname, navigate]);

  useEffect(() => {
    if (!location.hash) return;
    const target = plansPathForId(plansIdFromHash(location.hash));
    navigate(target, { replace: true });
  }, [location.hash, navigate]);

  useEffect(() => {
    if (viewMode !== 'prodejny' || !plneniData) return;
    const id = window.requestAnimationFrame(() => {
      document.getElementById('plans-anc-prodejny')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    return () => window.cancelAnimationFrame(id);
  }, [viewMode, plneniData]);

  useEffect(() => {
    if (viewMode !== 'prodejci' || plneniProdejciData == null) return;
    const id = window.requestAnimationFrame(() => {
      document.getElementById('plans-anc-prodejci')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    return () => window.cancelAnimationFrame(id);
  }, [viewMode, plneniProdejciData]);

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

  const vytvorPlanAuto = useCallback(async (rok, mesic) => {
    const rust = Number(String(rustProcent).replace(',', '.'));
    const rustVal = Number.isNaN(rust) || rust < -100 ? 10 : rust;
    setAutoGenerating(true);
    setChyba(null);
    setWarnings([]);
    try {
      const res = await plansAPI.createPlan(rok, mesic, {
        create_auto: true,
        rust_procent: rustVal,
        auto_prodejci: true,
      });
      setAktivniPlan(res);
      nactiVerziDoPlaneru(res);
      const aw = res.auto_prodejci_warnings || [];
      if (aw.length) setWarnings(aw);
      setUspech('Plán byl automaticky vytvořen z historie (YoY + 6m prodejny + 3m kategorie).');
      await plansAPI.getPlan(rok, mesic);
    } catch (e) {
      setChyba(e.response?.data?.error || 'Automatické vytvoření plánu se nezdařilo.');
    } finally {
      setAutoGenerating(false);
    }
  }, [nactiVerziDoPlaneru, rustProcent]);

  const loadPlan = useCallback(async (rok, mesic) => {
    setLoading(true);
    setChyba(null);
    setWarnings([]);
    try {
      const res = await plansAPI.getPlan(rok, mesic);
      const aktualni = res.aktualni;
      if (aktualni) {
        setAktivniPlan(aktualni);
        nactiVerziDoPlaneru(aktualni);
      } else {
        setAktivniPlan(null);
        setProdejny([]);
        setCastkaFirma('');
        const key = `${rok}-${mesic}`;
        if (
          jeMesicAktualniNeboBudouci(rok, mesic)
          && autoGenerateAttempted.current !== key
        ) {
          autoGenerateAttempted.current = key;
          setLoading(false);
          await vytvorPlanAuto(rok, mesic);
          return;
        }
      }
    } catch (e) {
      setChyba('Nepodařilo se načíst plán.');
    } finally {
      setLoading(false);
    }
  }, [nactiVerziDoPlaneru, vytvorPlanAuto]);

  useEffect(() => {
    autoGenerateAttempted.current = null;
    loadPlan(vybraneMesic.rok, vybraneMesic.mesic);
  }, [vybraneMesic, loadPlan]);

  const loadForecast = useCallback(async () => {
    const rust = Number(String(rustProcent).replace(',', '.'));
    if (Number.isNaN(rust) || rust < -100) {
      setChyba('Zadejte platné procento růstu.');
      return;
    }
    setForecastLoading(true);
    setChyba(null);
    try {
      const roky = [...new Set([...forecastCompareRoky, forecastRok])].filter(
        r => r !== forecastRok,
      );
      const pids = vyhledFirma || !vyhledProdejny.length ? [] : vyhledProdejny;
      const res = await plansAPI.getForecast(forecastRok, rust, roky, pids.length ? pids : null);
      setForecastData(res);
      if (res.meta?.dostupne_roky?.length) {
        setDostupneRoky(res.meta.dostupne_roky);
      }
    } catch (e) {
      setForecastData(null);
      setChyba(e.response?.data?.error || 'Nepodařilo se načíst výhled.');
    } finally {
      setForecastLoading(false);
    }
  }, [forecastRok, forecastCompareRoky, vyhledFirma, vyhledProdejny, rustProcent]);

  useEffect(() => {
    if (viewMode === 'vyhled') loadForecast();
  }, [viewMode, forecastRok, forecastCompareRoky, vyhledFirma, vyhledProdejny, loadForecast]);

  const forecastPred = forecastData?.predikce || forecastData;
  const vyhledMeta = forecastData?.meta;

  const rokyVolba = useMemo(() => {
    const todayY = new Date().getFullYear();
    const set = new Set(dostupneRoky.length ? dostupneRoky : [todayY]);
    for (let y = todayY; y <= todayY + 2; y += 1) set.add(y);
    set.add(forecastRok);
    forecastCompareRoky.forEach((r) => set.add(r));
    return [...set].sort((a, b) => b - a);
  }, [dostupneRoky, forecastRok, forecastCompareRoky]);

  const prodejnyTriggerLabel = useMemo(() => {
    if (vyhledFirma && !vyhledProdejny.length) return 'Celá firma';
    const list = vyhledMeta?.prodejny || [];
    if (vyhledProdejny.length === 1) {
      const p = list.find(x => x.id === vyhledProdejny[0]);
      return p?.nazev || '1 pobočka';
    }
    return `${vyhledProdejny.length} pobočky`;
  }, [vyhledFirma, vyhledProdejny, vyhledMeta]);

  const rokyTriggerLabel = useMemo(() => {
    const cmp = forecastCompareRoky.length
      ? ` · ${forecastCompareRoky.join(', ')}`
      : '';
    return `${forecastRok} ★${cmp}`;
  }, [forecastRok, forecastCompareRoky]);

  const grafLegendaPolozky = useMemo(() => {
    const polozky = [
      { key: 'pred', typ: 'pred', label: `${forecastRok} predikce` },
      { key: 'pln', typ: 'pln', label: `${forecastRok} plnění` },
    ];
    (forecastData?.porovnani_roky || []).forEach((serie, si) => {
      polozky.push({
        key: `rok-${serie.rok}`,
        barva: GRAF_ROKY_BARVY[(si + 1) % GRAF_ROKY_BARVY.length],
        label: String(serie.rok),
      });
    });
    return polozky;
  }, [forecastRok, forecastData?.porovnani_roky]);

  const toggleProdejnyMenu = () => {
    if (prodejnyMenuOpen) {
      setProdejnyMenuOpen(false);
      return;
    }
    setDraftVyhledFirma(vyhledFirma);
    setDraftVyhledProdejny([...vyhledProdejny]);
    setProdejnyMenuOpen(true);
    setRokyMenuOpen(false);
  };

  const closeProdejnyMenu = (apply) => {
    setProdejnyMenuOpen(false);
    if (apply) {
      setVyhledFirma(draftVyhledFirma);
      setVyhledProdejny([...draftVyhledProdejny]);
    }
  };

  const toggleDraftProdejna = (id) => {
    setDraftVyhledFirma(false);
    setDraftVyhledProdejny((prev) => {
      const next = prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id];
      if (!next.length) {
        setDraftVyhledFirma(true);
        return [];
      }
      return next;
    });
  };

  const toggleRokyMenu = () => {
    if (rokyMenuOpen) {
      setRokyMenuOpen(false);
      return;
    }
    setDraftForecastRok(forecastRok);
    setDraftCompareRoky([...forecastCompareRoky]);
    setRokyMenuOpen(true);
    setProdejnyMenuOpen(false);
  };

  const closeRokyMenu = (apply) => {
    setRokyMenuOpen(false);
    if (apply) {
      setForecastRok(draftForecastRok);
      setForecastCompareRoky([...draftCompareRoky].sort((a, b) => b - a));
      if (draftForecastRok !== vybraneMesic.rok) {
        setVybraneMesic({ rok: draftForecastRok, mesic: 1 });
      }
    }
  };

  const setDraftHlavniRok = (rok) => {
    setDraftForecastRok(rok);
    setDraftCompareRoky((prev) => prev.filter(r => r !== rok));
  };

  const toggleDraftCompareRok = (rok) => {
    if (rok === draftForecastRok) return;
    setDraftCompareRoky((prev) => (
      prev.includes(rok) ? prev.filter(r => r !== rok) : [...prev, rok].sort((a, b) => b - a)
    ));
  };

  const mesiceBezPlanu = vyhledMeta?.mesice_bez_planu || [];
  const pocetMesicuBezPlanu = vyhledMeta?.pocet_mesicu_bez_planu ?? mesiceBezPlanu.length;

  const zalozitPlanyNaRok = async () => {
    const rust = Number(String(rustProcent).replace(',', '.'));
    if (Number.isNaN(rust) || rust < -100) {
      setChyba('Zadejte platné procento růstu.');
      return;
    }
    if (pocetMesicuBezPlanu === 0) {
      setUspech(`Rok ${forecastRok}: všechny měsíce už mají aktivní plán.`);
      return;
    }
    const mesiceText = mesiceBezPlanu.map(m => NAZVY_MESICU[m - 1]).join(', ');
    const conf = forecastPred?.meta?.confidence || 'medium';
    const warnCount = (forecastPred?.warnings || []).length;
    const msg = `Založit ${pocetMesicuBezPlanu} plánů pro rok ${forecastRok} (${mesiceText})`
      + ' a rozdělit cíle na prodejce podle hodin na směnách?'
      + (warnCount ? ` (${warnCount} upozornění v náhledu)` : '')
      + `\nSpolehlivost odhadu: ${conf}.`
      + '\nMěsíce, které už plán mají, se přeskočí.';
    if (!window.confirm(msg)) return;
    setForecastCreating(true);
    setChyba(null);
    try {
      const res = await plansAPI.createForecastYear(forecastRok, rust, true);
      setWarnings(res.warnings || []);
      const prep = res.pocet_prepocet_prodejci ?? 0;
      const vytvoreneMesice = (res.vytvoreno || [])
        .map(x => NAZVY_MESICU[x.mesic - 1])
        .join(', ');
      const jizMesice = (res.jiz_existovalo || [])
        .map(x => NAZVY_MESICU[x.mesic - 1])
        .join(', ');
      const chybyData = (res.preskoceno || []).filter(p => p.reason === 'missing_data');
      if (res.pocet_vytvoreno > 0) {
        let txt = `Vytvořeno ${res.pocet_vytvoreno} plánů: ${vytvoreneMesice}.`;
        if (res.pocet_jiz_existovalo > 0) {
          txt += ` Již existovalo: ${jizMesice}.`;
        }
        if (prep > 0) {
          txt += ` Prodejci přepočítáni u ${prep} měsíců.`;
        }
        setUspech(txt);
        setVybraneMesic({ rok: forecastRok, mesic: res.vytvoreno[0]?.mesic || 1 });
        navigate('/plans/plan');
        loadForecast();
      } else if (res.info || res.pocet_jiz_existovalo === 12) {
        setUspech(res.info || `Rok ${forecastRok}: všechny měsíce už mají plán.`);
      } else if (chybyData.length) {
        setChyba(
          `Plány se nevytvořily (chybí historie): ${chybyData.map(c => NAZVY_MESICU[c.mesic - 1]).join(', ')}.`,
        );
      } else {
        setChyba('Žádný plán nebyl vytvořen. Zkontrolujte náhled výhledu nebo log.');
      }
    } catch (e) {
      setChyba(e.response?.data?.error || 'Hromadné založení plánů selhalo.');
    } finally {
      setForecastCreating(false);
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
      const res = await plansAPI.createPlan(vybraneMesic.rok, vybraneMesic.mesic, {
        castka_celkem: castka,
        copy_from_previous: copyFromPrevious,
      });
      setAktivniPlan(res);
      nactiVerziDoPlaneru(res);
      await loadPlan(vybraneMesic.rok, vybraneMesic.mesic);
      setUspech('Plán byl vytvořen.');
    } catch (e) {
      setChyba(e.response?.data?.error || 'Nepodařilo se vytvořit plán.');
    } finally {
      setLoading(false);
    }
  };

  const nactiNahled3m = async () => {
    const rust = Number(String(rustProcent).replace(',', '.'));
    if (Number.isNaN(rust) || rust < -100) {
      setChyba('Zadejte platné procento růstu.');
      return;
    }
    setNahled3mLoading(true);
    setChyba(null);
    try {
      const res = await plansAPI.getHistorie3mNahled(vybraneMesic.rok, vybraneMesic.mesic, rust);
      setNahled3m(res);
    } catch (e) {
      setNahled3m(null);
      setChyba(e.response?.data?.error || 'Nepodařilo se načíst náhled.');
    } finally {
      setNahled3mLoading(false);
    }
  };

  const vytvorPlanZ3Mesicu = async () => {
    const rust = Number(String(rustProcent).replace(',', '.'));
    if (Number.isNaN(rust) || rust < -100) {
      setChyba('Zadejte platné procento růstu (např. 10 pro +10 %).');
      return;
    }
    setLoading(true);
    setChyba(null);
    try {
      const res = await plansAPI.createPlan(vybraneMesic.rok, vybraneMesic.mesic, {
        create_from_3m: true,
        rust_procent: rust,
        auto_prodejci: true,
      });
      setAktivniPlan(res);
      nactiVerziDoPlaneru(res);
      await loadPlan(vybraneMesic.rok, vybraneMesic.mesic);
      const aw = res.auto_prodejci_warnings || [];
      if (aw.length) setWarnings(aw);
      setUspech('Plán byl vytvořen z průměru 3 měsíců; prodejci přiřazeni podle směn.');
      setNahled3m(null);
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
      const res = await plansAPI.createPlan(vybraneMesic.rok, vybraneMesic.mesic, {
        create_from_history: true,
        rust_procent: rust,
      });
      setAktivniPlan(res);
      nactiVerziDoPlaneru(res);
      await loadPlan(vybraneMesic.rok, vybraneMesic.mesic);
      setUspech('Plán byl vytvořen z minulého roku a růstu.');
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
        const res = await plansAPI.prepocet(vybraneMesic.rok, vybraneMesic.mesic, payload);
        setPrepocet(res);
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
        nova_verze: false,
        prodejny: buildPayloadProdejny(),
      };
      const res = await plansAPI.ulozit(vybraneMesic.rok, vybraneMesic.mesic, payload);
      setAktivniPlan(res);
      nactiVerziDoPlaneru(res);
      await loadPlan(vybraneMesic.rok, vybraneMesic.mesic);
      setUspech('Plán byl uložen.');
      setWarnings(res?.warnings || []);
    } catch (e) {
      setChyba(e.response?.data?.error || 'Nepodařilo se uložit plán.');
    } finally {
      setSaving(false);
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

  const onMonthSelect = useCallback((value) => {
    const [r, m] = value.split('-').map(Number);
    setVybraneMesic({ rok: r, mesic: m });
  }, []);

  return (
    <div className="plans-module">
      <PageHeader title="Plány" />
      <PlansNav
        showMonth={viewMode !== 'vyhled'}
        monthValue={`${vybraneMesic.rok}-${vybraneMesic.mesic}`}
        monthOptions={mesiceOptions}
        monthLabels={NAZVY_MESICU}
        onMonthChange={onMonthSelect}
        showPlanRezim={viewMode === 'plan' && Boolean(aktivniPlan)}
        planovaciRezim={planovaciRezim}
        onPlanovaciRezimChange={setPlanovaciRezim}
      />

      <div className="plans-content">
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

      {(loading || autoGenerating) && viewMode !== 'vyhled' && (
        <div className="plans-loading">
          {autoGenerating ? 'Generuji plán z historie…' : 'Načítám...'}
        </div>
      )}

      {!loading && !autoGenerating && !aktivniPlan && viewMode !== 'vyhled' && (
        <div className="plans-empty">
          <h3>Pro {NAZVY_MESICU[vybraneMesic.mesic - 1]} {vybraneMesic.rok} zatím neexistuje plán.</h3>
          {jeMesicAktualniNeboBudouci(vybraneMesic.rok, vybraneMesic.mesic) ? (
            <p className="plans-empty-hint">
              U aktuálního a budoucích měsíců se plán obvykle vytvoří automaticky při otevření.
            </p>
          ) : (
            <p className="plans-empty-hint">U minulých měsíců použijte ruční akce níže.</p>
          )}
          <button
            type="button"
            className="plans-btn plans-btn-secondary"
            onClick={() => vytvorPlanAuto(vybraneMesic.rok, vybraneMesic.mesic)}
            disabled={loading || autoGenerating}
          >
            Zkusit znovu (hybridní auto)
          </button>
          <details
            className="plans-pokrocile"
            open={pokrocileOpen}
            onToggle={e => setPokrocileOpen(e.target.open)}
          >
            <summary>Pokročilé – ruční vytvoření</summary>
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
                <label>Růst (%)</label>
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
                  type="button"
                  className="plans-btn plans-btn-secondary"
                  onClick={nactiNahled3m}
                  disabled={loading || nahled3mLoading}
                >
                  {nahled3mLoading ? 'Načítám…' : 'Náhled z 3 měsíců'}
                </button>
                <button
                  className="plans-btn plans-btn-secondary"
                  onClick={vytvorPlanZ3Mesicu}
                  disabled={loading}
                >
                  Z 3 měsíců + růst
                </button>
                <button
                  type="button"
                  className="plans-btn plans-btn-ghost"
                  onClick={vytvorPlanZHistorie}
                  disabled={loading}
                  title="Stejný měsíc minulý rok"
                >
                  YoY minulý rok
                </button>
              </div>
              {nahled3m && (
                <div className="plans-nahled-3m">
                  <p>
                    Průměr 3 měsíců: <strong>{Number(nahled3m.obrat_prumer_3m).toLocaleString('cs-CZ')} Kč</strong>
                    {' → '}návrh: <strong>{Number(nahled3m.navrh_obrat).toLocaleString('cs-CZ')} Kč</strong>
                  </p>
                </div>
              )}
            </div>
          </details>
        </div>
      )}

      {viewMode === 'vyhled' && (
        <div className="plans-vyhled">
          {forecastLoading && <div className="plans-loading">Načítám výhled…</div>}
          {!forecastLoading && forecastPred && (
            <>
              <div className="plans-vyhled-toolbar">
                <div className="ui-filter-bar plans-vyhled-toolbar-filters">
                  <VyhledFilterMenu
                    open={prodejnyMenuOpen}
                    onClose={closeProdejnyMenu}
                    triggerLabel={prodejnyTriggerLabel}
                    onTriggerClick={toggleProdejnyMenu}
                    title="Výběr poboček"
                    className="plans-vyhled-dropdown-prodejny"
                  >
                    <p className="plans-vyhled-dropdown-section">Pohled na obrat</p>
                    <label className="plans-vyhled-dropdown-row">
                      <input
                        type="checkbox"
                        checked={draftVyhledFirma && !draftVyhledProdejny.length}
                        onChange={() => {
                          setDraftVyhledFirma(true);
                          setDraftVyhledProdejny([]);
                        }}
                      />
                      <span>Celá firma</span>
                    </label>
                    {(vyhledMeta?.prodejny || []).map(p => (
                      <label key={p.id} className="plans-vyhled-dropdown-row" title={p.nazev}>
                        <input
                          type="checkbox"
                          checked={draftVyhledProdejny.includes(p.id)}
                          onChange={() => toggleDraftProdejna(p.id)}
                        />
                        <span>{p.nazev}</span>
                      </label>
                    ))}
                  </VyhledFilterMenu>
                  <VyhledFilterMenu
                    open={rokyMenuOpen}
                    onClose={closeRokyMenu}
                    triggerLabel={rokyTriggerLabel}
                    onTriggerClick={toggleRokyMenu}
                    title="Rok plánování a porovnání v grafu"
                    className="plans-vyhled-dropdown-roky"
                  >
                    <p className="plans-vyhled-dropdown-section">Plánovaný rok (tabulka, predikce, založení plánů)</p>
                    <div className="plans-vyhled-dropdown-roky-hlavni">
                      {rokyVolba.map((rok, i) => (
                        <button
                          key={`h-${rok}`}
                          type="button"
                          className={`plans-vyhled-dropdown-rok-btn${rok === draftForecastRok ? ' is-hlavni' : ''}`}
                          onClick={() => setDraftHlavniRok(rok)}
                        >
                          <span
                            className="plans-vyhled-chip-dot"
                            style={{ background: GRAF_ROKY_BARVY[i % GRAF_ROKY_BARVY.length] }}
                          />
                          {rok}{rok === draftForecastRok ? ' ★' : ''}
                          {rok > new Date().getFullYear() && (
                            <span className="plans-vyhled-rok-budouci"> plán</span>
                          )}
                        </button>
                      ))}
                    </div>
                    <p className="plans-vyhled-dropdown-section">Roky v grafu (porovnání)</p>
                    {rokyVolba.map((rok, i) => (
                      <label
                        key={`c-${rok}`}
                        className={`plans-vyhled-dropdown-row${rok === draftForecastRok ? ' is-disabled' : ''}`}
                      >
                        <input
                          type="checkbox"
                          checked={rok === draftForecastRok || draftCompareRoky.includes(rok)}
                          disabled={rok === draftForecastRok}
                          onChange={() => toggleDraftCompareRok(rok)}
                        />
                        <span
                          className="plans-vyhled-chip-dot"
                          style={{ background: GRAF_ROKY_BARVY[i % GRAF_ROKY_BARVY.length] }}
                        />
                        <span>{rok}{rok === draftForecastRok ? ' (hlavní)' : ''}</span>
                      </label>
                    ))}
                  </VyhledFilterMenu>
                </div>
                <div className="plans-vyhled-toolbar-summary">
                  <span className="plans-vyhled-summary-pred">
                    Predikce <strong>{forecastRok}</strong>
                    {vyhledMeta?.prodejna_nazev ? ` · ${vyhledMeta.prodejna_nazev}` : ''}
                    {' '}{formatKcShort(forecastPred.celkem_obrat_pred)}
                  </span>
                  <span className={`plans-confidence plans-confidence-${forecastPred.meta?.confidence || 'medium'}`}>
                    {forecastPred.meta?.confidence || '—'}
                  </span>
                </div>
              </div>
              <div
                className="plans-vyhled-legenda"
                title="Tabulka: částky v Kč. Sloupce vs: zelená nad referencí, červená pod, černá ≈ shoda. Modrý řádek = probíhající měsíc. ⚠ = chybějící pobočky."
              >
                <span className="plans-vyhled-legenda-skupina">
                  <span className="plans-vyhled-legenda-nadpis">Graf</span>
                  {grafLegendaPolozky.map(p => (
                    <span key={p.key} className="plans-vyhled-legenda-polozka">
                      <span
                        className={
                          p.typ
                            ? `plans-vyhled-legenda-swatch plans-vyhled-legenda-swatch-${p.typ}`
                            : 'plans-vyhled-legenda-swatch'
                        }
                        style={p.barva ? { background: p.barva } : undefined}
                      />
                      {p.label}
                    </span>
                  ))}
                </span>
                <span className="plans-vyhled-legenda-skupina plans-vyhled-legenda-tab" aria-hidden="true">
                  ·
                </span>
                <span className="plans-vyhled-legenda-skupina plans-vyhled-legenda-tab">
                  Tabulka Kč · najetí měsíc · <span className="plans-vyhled-legenda-warn">⚠</span>
                  {' · '}
                  <span className="plans-vyhled-pct-up">▲</span>
                  <span className="plans-vyhled-pct-down">▼</span> vs
                </span>
              </div>
              <div className="plans-vyhled-chart plans-vyhled-chart-multi plans-vyhled-chart-compact">
                {Array.from({ length: 12 }, (_, i) => i + 1).map((mesic) => {
                  const allVals = [];
                  if (forecastPred.mesice) {
                    const hm = forecastPred.mesice.find(x => x.mesic === mesic);
                    if (hm) {
                      allVals.push(hm.obrat_pred || 0, hm.plneni?.obrat || 0);
                    }
                  }
                  (forecastData?.porovnani_roky || []).forEach((serie) => {
                    const row = serie.mesice?.find(x => x.mesic === mesic);
                    if (row) {
                      allVals.push(row.obrat_skutecny ?? row.obrat ?? row.obrat_pred ?? 0);
                    }
                  });
                  const max = Math.max(...allVals, 1);
                  const tooltipRadky = grafMesicTooltipRadky(
                    mesic, forecastPred, forecastData, forecastRok,
                  );
                  return (
                    <div
                      key={mesic}
                      className="plans-vyhled-bar-wrap"
                      tabIndex={0}
                      aria-label={`${NAZVY_MESICU[mesic - 1]} – ${tooltipRadky.length} hodnot v grafu`}
                    >
                      {tooltipRadky.length > 0 && (
                        <div className="plans-vyhled-chart-tooltip" role="tooltip">
                          <div className="plans-vyhled-chart-tooltip-title">
                            {NAZVY_MESICU[mesic - 1]}
                          </div>
                          <ul className="plans-vyhled-chart-tooltip-list">
                            {tooltipRadky.map(r => (
                              <li key={r.key}>
                                <span
                                  className={`plans-vyhled-chart-tooltip-dot${r.dot ? ` plans-vyhled-chart-tooltip-dot-${r.dot}` : ''}`}
                                  style={r.barva ? { background: r.barva } : undefined}
                                />
                                <span className="plans-vyhled-chart-tooltip-label">{r.label}</span>
                                <span className="plans-vyhled-chart-tooltip-value">{r.hodnota}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      <div className="plans-vyhled-bars plans-vyhled-bars-multi">
                        {(() => {
                          const hm = forecastPred.mesice?.find(x => x.mesic === mesic);
                          if (!hm) return null;
                          const hPred = Math.round((hm.obrat_pred / max) * 100);
                          const sk = hm.plneni?.obrat;
                          const hPln = sk != null ? Math.round((sk / max) * 100) : 0;
                          return (
                            <>
                              <div
                                className="plans-vyhled-bar plans-vyhled-bar-pred"
                                style={{ height: `${hPred}%` }}
                              />
                              {sk != null && (
                                <div
                                  className="plans-vyhled-bar plans-vyhled-bar-pln"
                                  style={{ height: `${hPln}%` }}
                                />
                              )}
                            </>
                          );
                        })()}
                        {(forecastData?.porovnani_roky || []).map((serie, si) => {
                          const row = serie.mesice?.find(x => x.mesic === mesic);
                          const val = row?.obrat_skutecny ?? row?.obrat ?? row?.obrat_pred ?? 0;
                          const h = Math.round((val / max) * 100);
                          const barva = GRAF_ROKY_BARVY[(si + 1) % GRAF_ROKY_BARVY.length];
                          return (
                            <div
                              key={serie.rok}
                              className="plans-vyhled-bar"
                              style={{ height: `${h}%`, background: barva }}
                            />
                          );
                        })}
                      </div>
                      <span className="plans-vyhled-bar-label">{MESIC_ZKRATKA[mesic - 1]}</span>
                    </div>
                  );
                })}
              </div>
              <div className="plans-vyhled-table-wrap">
                <table className="plans-vyhled-table plans-vyhled-table-compact">
                  <thead className="plans-vyhled-thead-sticky">
                    <tr>
                      <th className="plans-vyhled-col-mesic" />
                      <th>LY</th>
                      <th>Pred.</th>
                      <th>Plán</th>
                      <th>Plnění</th>
                      <th>vs LY</th>
                      <th>vs pred.</th>
                      <th>vs plán</th>
                    </tr>
                  </thead>
                  <tbody>
                    {forecastPred.mesice?.map(m => {
                      const pl = m.plneni;
                      const chybiHint = formatChybejiciPobocky(m.chybejici_pobocky);
                      const rowTitle = [
                        chybiHint,
                        m.stav === 'probiha' && pl?.den_v_mesici
                          ? `Probíhá – ${pl.den_v_mesici}. den v měsíci`
                          : null,
                        m.stav === 'probiha' && pl?.trend_k_mesici != null
                          ? `Trend do konce: ${formatNum(pl.trend_k_mesici)}`
                          : null,
                      ].filter(Boolean).join(' · ') || undefined;
                      const rowClass = [
                        m.stav ? `plans-vyhled-row-${m.stav}` : '',
                        m.stav === 'probiha' ? 'plans-vyhled-row-aktualni' : '',
                      ].filter(Boolean).join(' ');
                      return (
                        <tr key={m.mesic} className={rowClass} title={rowTitle}>
                          <td className="plans-vyhled-col-mesic">
                            <span className="plans-vyhled-mesic-label">{MESIC_ZKRATKA[m.mesic - 1]}</span>
                            {chybiHint && (
                              <span className="plans-vyhled-chybi" title={chybiHint}>⚠</span>
                            )}
                          </td>
                          <td className="plans-vyhled-num">{m.obrat_ly > 0 ? formatNum(m.obrat_ly) : '—'}</td>
                          <td className="plans-vyhled-num">{formatNum(m.obrat_pred)}</td>
                          <td className="plans-vyhled-num">{pl?.ma_plan ? formatNum(pl.plan_obrat) : '—'}</td>
                          <td className="plans-vyhled-num">
                            {pl ? formatNum(pl.obrat) : '—'}
                          </td>
                          <td className="plans-vyhled-pct">
                            {pl && m.obrat_ly > 0
                              ? <VyhledPorovnaniCell pct={pl.pct_vs_ly} kc={pl.odchylka_ly_kc} />
                              : '—'}
                          </td>
                          <td className="plans-vyhled-pct">
                            {pl ? <VyhledPorovnaniCell pct={pl.pct_predikce} kc={pl.odchylka_pred_kc} /> : '—'}
                          </td>
                          <td className="plans-vyhled-pct">
                            {pl?.plan_obrat
                              ? <VyhledPorovnaniCell pct={pl.pct_plan} kc={pl.odchylka_plan_kc} />
                              : '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                  <tfoot>
                    <tr className="plans-vyhled-foot">
                      <td><strong>Celkem</strong></td>
                      <td className="plans-vyhled-num">{formatNum(forecastPred.souhrn_roku?.celkem_obrat_ly_rok)}</td>
                      <td className="plans-vyhled-num"><strong>{formatNum(forecastPred.celkem_obrat_pred)}</strong></td>
                      <td colSpan={2} />
                      <td colSpan={3} />
                    </tr>
                    {forecastPred.souhrn_roku?.za_ukoncene_obdobi && (
                      <tr className="plans-vyhled-foot plans-vyhled-foot-obdobi">
                        <td
                          title={
                            forecastPred.souhrn_roku.za_ukoncene_obdobi.prorated
                              ? 'YTD: ukončené měsíce celé; u běžícího měsíce LY/pred/plán jen za stejný počet dní jako skutečnost.'
                              : undefined
                          }
                        >
                          <strong>
                            YTD ({forecastPred.souhrn_roku.za_ukoncene_obdobi.popis_obdobi
                              || `${forecastPred.souhrn_roku.za_ukoncene_obdobi.mesicu} m.`})
                          </strong>
                        </td>
                        <td className="plans-vyhled-num">{formatNum(forecastPred.souhrn_roku.za_ukoncene_obdobi.obrat_ly)}</td>
                        <td className="plans-vyhled-num">{formatNum(forecastPred.souhrn_roku.za_ukoncene_obdobi.obrat_predikce)}</td>
                        <td className="plans-vyhled-num">
                          {forecastPred.souhrn_roku.za_ukoncene_obdobi.obrat_plan != null
                            ? formatNum(forecastPred.souhrn_roku.za_ukoncene_obdobi.obrat_plan)
                            : '—'}
                        </td>
                        <td className="plans-vyhled-num">
                          <strong>{formatNum(forecastPred.souhrn_roku.za_ukoncene_obdobi.obrat_skutecny)}</strong>
                        </td>
                        <td className="plans-vyhled-pct">
                          <strong>
                            <VyhledPorovnaniCell
                              pct={forecastPred.souhrn_roku.za_ukoncene_obdobi.pct_vs_ly}
                              kc={forecastPred.souhrn_roku.za_ukoncene_obdobi.odchylka_ly_kc}
                            />
                          </strong>
                        </td>
                        <td className="plans-vyhled-pct">
                          <strong>
                            <VyhledPorovnaniCell
                              pct={forecastPred.souhrn_roku.za_ukoncene_obdobi.pct_vs_predikce}
                              kc={forecastPred.souhrn_roku.za_ukoncene_obdobi.odchylka_pred_kc}
                            />
                          </strong>
                        </td>
                        <td className="plans-vyhled-pct">
                          <strong>
                            <VyhledPorovnaniCell
                              pct={forecastPred.souhrn_roku.za_ukoncene_obdobi.pct_vs_plan}
                              kc={forecastPred.souhrn_roku.za_ukoncene_obdobi.odchylka_plan_kc}
                            />
                          </strong>
                        </td>
                      </tr>
                    )}
                  </tfoot>
                </table>
              </div>
              {(forecastPred.warnings || []).length > 0 && (
                <ul className="plans-souhrn-warnings">
                  {forecastPred.warnings.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              )}
              <button
                type="button"
                className="plans-btn plans-btn-primary"
                onClick={zalozitPlanyNaRok}
                disabled={forecastCreating || pocetMesicuBezPlanu === 0}
                title={
                  pocetMesicuBezPlanu === 0
                    ? 'Všechny měsíce tohoto roku už mají plán'
                    : undefined
                }
              >
                {forecastCreating
                  ? 'Zakládám plány…'
                  : pocetMesicuBezPlanu === 0
                    ? `Rok ${forecastRok} – všechny plány hotové`
                    : `Založit ${pocetMesicuBezPlanu} chybějících plánů (${forecastRok})`}
              </button>
            </>
          )}
        </div>
      )}

      {/* ==== Plnění Prodejny ==== */}
      {!loading && viewMode === 'prodejny' && aktivniPlan && (
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

              <AuditZbytekPanel rok={vybraneMesic.rok} mesic={vybraneMesic.mesic} />

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
                <PlneniStrom
                  rok={vybraneMesic.rok}
                  mesic={vybraneMesic.mesic}
                  showCelkemBar={false}
                  kategorie={agrFirmaKategorie.map(kat => {
                    const pd = plneniData.kategorie?.[kat.kategorie_kod] || {};
                    return {
                      kategorie_kod: kat.kategorie_kod,
                      kategorie_nazev: kat.kategorie_nazev,
                      plan_kusy: kat.kusy,
                      skutecne_kusy: pd.skutecne_kusy,
                      plneni_procent: pd.plneni_procent,
                      trend_kusy: pd.trend_kusy,
                      trend_procent: pd.trend_procent,
                    };
                  })}
                  plneniFillClass={plneniFillClass}
                  plneniBarWidthPct={plneniBarWidthPct}
                  trendTrida={trendTrida}
                />
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
                      <PlneniStrom
                        rok={vybraneMesic.rok}
                        mesic={vybraneMesic.mesic}
                        nadpis={p.prodejna_nazev}
                        celkemPct={pctProd}
                        prodejnaId={p.prodejna_id}
                        celkemMeta={(
                          <span className="plneni-bar-meta">
                            {formatCastka(pdProd.skutecny_obrat || 0)}
                            {formatBezDphParen(pdProd.skutecny_obrat || 0)}
                            {' / '}
                            {formatCastka(p.castka_prodejna)}
                            {formatBezDphParen(p.castka_prodejna)}
                            {pdProd.trend_obrat != null && (
                              <span className={`plneni-trend-badge ${trendTrida(pdProd.trend_procent)}`}>
                                → ~{formatCastka(pdProd.trend_obrat)}
                              </span>
                            )}
                          </span>
                        )}
                        kategorie={(p.kategorie || []).map(k => {
                          const pdKat = pdProd.kategorie?.[k.kategorie_kod] || {};
                          return {
                            kategorie_kod: k.kategorie_kod,
                            kategorie_nazev: k.kategorie_nazev,
                            plan_kusy: k.pocet_kusu,
                            skutecne_kusy: pdKat.skutecne_kusy,
                            plneni_procent: pdKat.plneni_procent,
                            trend_kusy: pdKat.trend_kusy,
                            trend_procent: pdKat.trend_procent,
                          };
                        })}
                        plneniFillClass={plneniFillClass}
                        plneniBarWidthPct={plneniBarWidthPct}
                        trendTrida={trendTrida}
                      />
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
      {!loading && viewMode === 'prodejci' && aktivniPlan && (
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
                  const pctProd = prod.plneni_procent_kusy ?? prod.plneni_procent_hlavni ?? 0;
                  return (
                    <div key={prod.prodejce_id} className="plneni-prodejna plneni-prodejce-karta">
                      <div className="plneni-prodejce-karta-top">
                        <PlneniHistorieMini historie={prod.historie_3m} />
                      </div>
                      <PlneniStrom
                        rok={vybraneMesic.rok}
                        mesic={vybraneMesic.mesic}
                        nadpis={`${prod.jmeno} ${prod.prijmeni}`}
                        celkemPct={pctProd}
                        prodejceId={prod.prodejce_id}
                        metaExtra={prod.prodejna_nazev ? (
                          <span className="plneni-prodejna-meta"> ({prod.prodejna_nazev})</span>
                        ) : null}
                        celkemMeta={(
                          <span className="plneni-bar-meta">
                            {prod.skutecne_kusy ?? 0} / {prod.plan_kusy ?? 0} ks
                            {prod.trend_kusy != null && (
                              <span className={`plneni-trend-badge ${trendTrida(prod.trend_procent_kusy)}`}>
                                → ~{prod.trend_kusy} ks
                              </span>
                            )}
                            {prod.historie_3m?.prumer_plneni_3m != null && (
                              <span className="plneni-trend-badge" title="Průměr 3 měsíců">
                                ø {prod.historie_3m.prumer_plneni_3m} %
                              </span>
                            )}
                          </span>
                        )}
                        kategorie={prod.kategorie || []}
                        plneniFillClass={plneniFillClass}
                        plneniBarWidthPct={plneniBarWidthPct}
                        trendTrida={trendTrida}
                      />
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
                onClick={vytvorPlanZ3Mesicu}
                disabled={loading}
              >
                Vytvořit z 3 měsíců + růst
              </button>
              <button
                className="plans-btn plans-btn-ghost"
                onClick={vytvorPlanZHistorie}
                disabled={loading}
              >
                YoY minulý rok
              </button>
            </span>
          </div>
        </>
      )}
      </div>
    </div>
  );
}
