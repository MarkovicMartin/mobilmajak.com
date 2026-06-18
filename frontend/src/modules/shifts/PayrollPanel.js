import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import Modal from '../../components/Modal';
import {
    PRODUCT_COMMISSIONS,
    SERVIS_BREAKDOWN_KEY,
    BREAKDOWN_LINE_LABELS,
    INFO_ONLY_COMMISSIONS,
} from '../../constants/productCommissions';
import { formatPoints, formatNumber } from '../../utils/formatBody';
import { manualNumberInputClass, preventNumberInputWheel } from '../../utils/manualNumberInput';
import './PayrollPanel.css';

const CACHE_PREFIX = 'payroll-overview-v1';
const CURRENT_MONTH_STALE_MS = 5 * 60 * 1000;
const memoryCache = new Map();

function cacheKey(month) {
    return `${CACHE_PREFIX}:${month}`;
}

function readCache(month) {
    const mem = memoryCache.get(month);
    if (mem) return mem;
    try {
        const raw = sessionStorage.getItem(cacheKey(month));
        if (!raw) return null;
        const parsed = JSON.parse(raw);
        memoryCache.set(month, parsed);
        return parsed;
    } catch {
        return null;
    }
}

function writeCache(month, payload) {
    const entry = { ...payload, fetchedAt: Date.now() };
    memoryCache.set(month, entry);
    try {
        sessionStorage.setItem(cacheKey(month), JSON.stringify(entry));
    } catch {
        // sessionStorage plné – modulová cache stačí
    }
}

function invalidateCache(month) {
    memoryCache.delete(month);
    try {
        sessionStorage.removeItem(cacheKey(month));
    } catch {
        // ignore
    }
}

function needsBackgroundRefresh(month, cached, now = new Date()) {
    if (!cached) return true;
    const current = currentMonthStr();
    if (month < current) return false;
    if (month > current) return true;
    return Date.now() - (cached.fetchedAt || 0) > CURRENT_MONTH_STALE_MS;
}

function applyPayrollPayload(data, setRows, setFonduH) {
    setRows(data.rows || []);
    const fond = data.fondu_h ?? data.rows?.[0]?.fondu_h ?? null;
    setFonduH(fond);
}

const MONTH_NAMES = [
    'Leden', 'Únor', 'Březen', 'Duben', 'Květen', 'Červen',
    'Červenec', 'Srpen', 'Září', 'Říjen', 'Listopad', 'Prosinec',
];

function formatMonthName(monthStr) {
    const [year, month] = monthStr.split('-').map(Number);
    return `${MONTH_NAMES[month - 1]} ${year}`;
}

function currentMonthStr() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

function PayrollPanel({ month, onExport }) {
    const [rows, setRows] = useState([]);
    const [fonduH, setFonduH] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [expandedId, setExpandedId] = useState(null);
    const [showOdmenaModal, setShowOdmenaModal] = useState(false);
    const [showPenalizaceModal, setShowPenalizaceModal] = useState(false);
    const [savingOdmena, setSavingOdmena] = useState(false);
    const [savingPenalizace, setSavingPenalizace] = useState(false);
    const [odmenaForm, setOdmenaForm] = useState({ user_id: '', castka: '', poznamka: '' });
    const [penalizaceForm, setPenalizaceForm] = useState({ user_id: '', duvod: '' });
    const [discountedRows, setDiscountedRows] = useState([]);
    const [discountedCount, setDiscountedCount] = useState(0);
    const [discountedExcluded, setDiscountedExcluded] = useState(0);
    const [discountedLoading, setDiscountedLoading] = useState(false);
    const [discountedError, setDiscountedError] = useState('');
    const [discountedOpen, setDiscountedOpen] = useState(false);
    const discountedRowsLoadedRef = useRef(false);
    const [dobropisySummary, setDobropisySummary] = useState([]);
    const [dobropisyRows, setDobropisyRows] = useState([]);
    const [dobropisyTotals, setDobropisyTotals] = useState({ polozky: 0, doklady: 0, castka: 0 });
    const [dobropisyLoading, setDobropisyLoading] = useState(false);
    const [dobropisyError, setDobropisyError] = useState('');
    const [dobropisyOpen, setDobropisyOpen] = useState(false);
    const [dobropisyFilterUser, setDobropisyFilterUser] = useState('');
    const [dobropisyFilterPairing, setDobropisyFilterPairing] = useState('');
    const [dobropisyPairingTotals, setDobropisyPairingTotals] = useState({
        zrcadlo: 0, par: 0, bez_paru: 0,
    });
    const dobropisyRowsLoadedRef = useRef(false);
    const odmenaFormRef = useRef(null);
    const penalizaceFormRef = useRef(null);
    const fetchSeq = useRef(0);

    const closeOdmenaModal = useCallback(() => {
        setShowOdmenaModal(false);
        setOdmenaForm({ user_id: '', castka: '', poznamka: '' });
    }, []);

    const closePenalizaceModal = useCallback(() => {
        setShowPenalizaceModal(false);
        setPenalizaceForm({ user_id: '', duvod: '' });
    }, []);

    const soucetBodu = useMemo(
        () => rows.reduce((s, r) => s + (Number(r.celkem_body) || 0), 0),
        [rows],
    );

    const loadPayroll = useCallback(async (options = {}) => {
        const { force = false } = options;
        if (!month) return;
        const seq = ++fetchSeq.current;
        const cached = force ? null : readCache(month);
        const hasCachedRows = Boolean(cached?.data?.rows?.length);

        if (cached?.data) {
            applyPayrollPayload(cached.data, setRows, setFonduH);
            setLoading(false);
        } else {
            setLoading(true);
        }
        setError('');

        if (!force && !needsBackgroundRefresh(month, cached)) {
            return;
        }

        try {
            const res = await fetch(`/api/shifts/payroll/?mesic=${month}`, { credentials: 'include' });
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.error || 'Chyba při načítání výplaty');
            }
            const data = await res.json();
            if (seq !== fetchSeq.current) return;

            writeCache(month, { data });
            applyPayrollPayload(data, setRows, setFonduH);
        } catch (e) {
            if (seq !== fetchSeq.current) return;
            if (!hasCachedRows) {
                setError(e.message);
                setRows([]);
                setFonduH(null);
            }
        } finally {
            if (seq === fetchSeq.current) {
                setLoading(false);
            }
        }
    }, [month]);

    const loadDiscountedSummary = useCallback(async () => {
        if (!month) return;
        setDiscountedError('');
        discountedRowsLoadedRef.current = false;
        setDiscountedRows([]);
        try {
            const res = await fetch(
                `/api/shifts/payroll/discounted-services/?mesic=${month}`,
                { credentials: 'include' },
            );
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.error || 'Chyba při načítání slev');
            }
            const data = await res.json();
            setDiscountedCount(Number(data.count) || 0);
            setDiscountedExcluded(Number(data.vyloucene_body_celkem) || 0);
            if ((data.count || 0) > 0) {
                setDiscountedOpen(true);
            }
        } catch (e) {
            setDiscountedError(e.message);
            setDiscountedCount(0);
            setDiscountedExcluded(0);
        }
    }, [month]);

    const loadDiscountedRows = useCallback(async () => {
        if (!month || discountedRowsLoadedRef.current) return;
        setDiscountedLoading(true);
        setDiscountedError('');
        try {
            const res = await fetch(
                `/api/shifts/payroll/discounted-services/?mesic=${month}&rows_only=1`,
                { credentials: 'include' },
            );
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.error || 'Chyba při načítání položek se slevou');
            }
            const data = await res.json();
            setDiscountedRows(data.rows || []);
            setDiscountedCount(Number(data.count) || (data.rows || []).length);
            setDiscountedExcluded(Number(data.vyloucene_body_celkem) || 0);
            discountedRowsLoadedRef.current = true;
        } catch (e) {
            setDiscountedError(e.message);
            setDiscountedRows([]);
        } finally {
            setDiscountedLoading(false);
        }
    }, [month]);

    const toggleDiscounted = useCallback(() => {
        setDiscountedOpen((wasOpen) => {
            const next = !wasOpen;
            if (next && !discountedRowsLoadedRef.current && discountedCount > 0) {
                loadDiscountedRows();
            }
            return next;
        });
    }, [discountedCount, loadDiscountedRows]);

    const loadDobropisySummary = useCallback(async () => {
        if (!month) return;
        setDobropisyError('');
        dobropisyRowsLoadedRef.current = false;
        setDobropisyRows([]);
        setDobropisyPairingTotals({ zrcadlo: 0, par: 0, bez_paru: 0 });
        try {
            const res = await fetch(
                `/api/shifts/payroll/dobropisy/?mesic=${month}`,
                { credentials: 'include' },
            );
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.error || 'Chyba při načítání dobropisů');
            }
            const data = await res.json();
            setDobropisySummary(data.summary || []);
            setDobropisyTotals(data.totals || { polozky: 0, doklady: 0, castka: 0 });
            setDobropisyFilterUser('');
            if ((data.totals?.polozky || 0) > 0) {
                setDobropisyOpen(true);
            }
        } catch (e) {
            setDobropisyError(e.message);
            setDobropisySummary([]);
            setDobropisyTotals({ polozky: 0, doklady: 0, castka: 0 });
        }
    }, [month]);

    const loadDobropisyRows = useCallback(async () => {
        if (!month || dobropisyRowsLoadedRef.current) return;
        setDobropisyLoading(true);
        setDobropisyError('');
        try {
            const res = await fetch(
                `/api/shifts/payroll/dobropisy/?mesic=${month}&rows_only=1`,
                { credentials: 'include' },
            );
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.error || 'Chyba při načítání položek dobropisů');
            }
            const data = await res.json();
            setDobropisyRows(data.rows || []);
            setDobropisyPairingTotals(data.pairing_totals || { zrcadlo: 0, par: 0, bez_paru: 0 });
            setDobropisyFilterPairing('');
            dobropisyRowsLoadedRef.current = true;
        } catch (e) {
            setDobropisyError(e.message);
            setDobropisyRows([]);
        } finally {
            setDobropisyLoading(false);
        }
    }, [month]);

    const toggleDobropisy = useCallback(() => {
        setDobropisyOpen((wasOpen) => {
            const next = !wasOpen;
            if (next && !dobropisyRowsLoadedRef.current) {
                loadDobropisyRows();
            }
            return next;
        });
    }, [loadDobropisyRows]);

    const filteredDobropisyRows = useMemo(() => {
        let out = dobropisyRows;
        if (dobropisyFilterUser) {
            const uid = Number(dobropisyFilterUser);
            out = out.filter((r) => Number(r.id_prodejce) === uid);
        }
        if (dobropisyFilterPairing) {
            out = out.filter((r) => r.pairing === dobropisyFilterPairing);
        }
        return out;
    }, [dobropisyRows, dobropisyFilterUser, dobropisyFilterPairing]);

    useEffect(() => {
        loadPayroll();
        loadDiscountedSummary();
        loadDobropisySummary();
    }, [loadPayroll, loadDiscountedSummary, loadDobropisySummary]);

    useEffect(() => {
        if (discountedOpen && discountedCount > 0 && !discountedRowsLoadedRef.current) {
            loadDiscountedRows();
        }
    }, [discountedOpen, discountedCount, loadDiscountedRows]);

    useEffect(() => {
        if (dobropisyOpen && dobropisyTotals.polozky > 0 && !dobropisyRowsLoadedRef.current) {
            loadDobropisyRows();
        }
    }, [dobropisyOpen, dobropisyTotals.polozky, loadDobropisyRows]);

    const employeeOptions = useMemo(
        () => rows.map((r) => ({ id: r.user_id, jmeno: r.jmeno })),
        [rows],
    );

    const savePenalizace = async (e) => {
        e.preventDefault();
        const duvod = (penalizaceForm.duvod || '').trim();
        if (!penalizaceForm.user_id || !duvod) {
            alert('Vyberte zaměstnance a zadejte důvod srážky.');
            return;
        }
        setSavingPenalizace(true);
        try {
            const res = await fetch('/api/shifts/payroll/penalizace/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    user_id: parseInt(penalizaceForm.user_id, 10),
                    mesic: month,
                    duvod,
                }),
            });
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.error || 'Uložení selhalo');
            }
            closePenalizaceModal();
            invalidateCache(month);
            await loadPayroll({ force: true });
        } catch (err) {
            alert(err.message);
        } finally {
            setSavingPenalizace(false);
        }
    };

    const saveOdmena = async (e) => {
        e.preventDefault();
        const castka = parseFloat(odmenaForm.castka);
        if (!odmenaForm.user_id || Number.isNaN(castka) || castka <= 0) {
            alert('Vyberte zaměstnance a zadejte kladný počet bodů.');
            return;
        }
        setSavingOdmena(true);
        try {
            const res = await fetch('/api/shifts/payroll/odmena/', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    user_id: parseInt(odmenaForm.user_id, 10),
                    mesic: month,
                    castka,
                    poznamka: odmenaForm.poznamka || '',
                    add: true,
                }),
            });
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.error || 'Uložení selhalo');
            }
            closeOdmenaModal();
            invalidateCache(month);
            await loadPayroll({ force: true });
        } catch (err) {
            alert(err.message);
        } finally {
            setSavingOdmena(false);
        }
    };

    const renderProvizeBreakdown = (breakdown) => {
        if (!breakdown) return null;
        const lines = [];
        PRODUCT_COMMISSIONS.forEach(({ key }) => {
            const item = breakdown[key];
            if (item && (item.count > 0 || item.points > 0)) {
                lines.push(
                    <div key={key} className="breakdown-line">
                        <span className="breakdown-label">{BREAKDOWN_LINE_LABELS[key]}</span>
                        <span className="breakdown-value">{item.count}× → {formatPoints(item.points)}</span>
                    </div>
                );
            }
        });
        const servis = breakdown[SERVIS_BREAKDOWN_KEY];
        if (servis && servis.points > 0) {
            lines.push(
                <div key="servis" className="breakdown-line">
                    <span className="breakdown-label">{BREAKDOWN_LINE_LABELS[SERVIS_BREAKDOWN_KEY]}</span>
                    <span className="breakdown-value">{formatPoints(servis.points)}</span>
                </div>
            );
        }
        INFO_ONLY_COMMISSIONS.forEach(({ key, label }) => {
            const item = breakdown[key];
            if (item && item.count > 0) {
                lines.push(
                    <div key={key} className="breakdown-line breakdown-line-info">
                        <span className="breakdown-label">{label}</span>
                        <span className="breakdown-value">{item.count} ks (jen výpis)</span>
                    </div>
                );
            }
        });
        return lines.length ? (
            <div className="payroll-detail-section">
                <h4>Provize z prodeje</h4>
                <div className="payroll-breakdown payroll-breakdown-grid">{lines}</div>
            </div>
        ) : null;
    };

    const renderPolDokLine = (row) => {
        const bonus = Number(row.pol_dok_odmena_body) || 0;
        if (!bonus) return null;
        const avg = Number(row.pol_dok) || 0;
        const label = bonus > 0
            ? `+ Prům. pol./účt. ${avg.toFixed(2)} (nad 2)`
            : `− Prům. pol./účt. ${avg.toFixed(2)} (pod 2)`;
        return (
            <div
                key="pol-dok"
                className={`breakdown-line${bonus < 0 ? ' breakdown-line-deduction' : ''}`}
            >
                <span className="breakdown-label">{label}</span>
                <span className="breakdown-value">
                    {bonus > 0 ? '+' : ''}{formatPoints(bonus)}
                </span>
            </div>
        );
    };

    const renderBrigadnikSouhrn = (row) => {
        if (!row.is_brigadnik) return null;
        const vypomocH = Number(row.vypomoc_h) || 0;
        const prodejceH = Number(row.prodejce_h) || 0;
        const sazbaProdejce = row.body_za_hodinu ?? 0;
        const sazbaVypomoc = row.body_vypomoc_za_hodinu ?? 150;
        const zaklad = Number(row.zaklad_body) || 0;
        const provize = Number(row.provize_body) || 0;
        const celkem = Number(row.celkem_body) || 0;
        return (
            <div className="payroll-detail-section">
                <h4>Výpočet brigádníka</h4>
                <div className="payroll-breakdown payroll-breakdown-grid">
                    {vypomocH > 0 && (
                        <div className="breakdown-line">
                            <span className="breakdown-label">Výpomoc</span>
                            <span className="breakdown-value">
                                {formatNumber(vypomocH)} h × {sazbaVypomoc} = {formatPoints(vypomocH * sazbaVypomoc)}
                            </span>
                        </div>
                    )}
                    {prodejceH > 0 && (
                        <div className="breakdown-line">
                            <span className="breakdown-label">Jako prodejce</span>
                            <span className="breakdown-value">
                                {formatNumber(prodejceH)} h × {sazbaProdejce} = {formatPoints(prodejceH * sazbaProdejce)}
                            </span>
                        </div>
                    )}
                    <div className="breakdown-line">
                        <span className="breakdown-label">Hodiny celkem (základ)</span>
                        <span className="breakdown-value">{formatPoints(zaklad)}</span>
                    </div>
                    <div className="breakdown-line">
                        <span className="breakdown-label">+ Provize (body z prodeje)</span>
                        <span className="breakdown-value">{formatPoints(provize)}</span>
                    </div>
                    {(row.dyska_body || 0) > 0 && (
                        <div className="breakdown-line">
                            <span className="breakdown-label">
                                + Dýška / vícepráce P63615
                                {(row.dyska_kusy || 0) > 0 ? ` (${row.dyska_kusy} ks)` : ''}
                            </span>
                            <span className="breakdown-value">{formatPoints(row.dyska_body)}</span>
                        </div>
                    )}
                    {renderPolDokLine(row)}
                    {(row.doplnky_body > 0 || row.odmena_mesic_body > 0) && (
                        <div className="breakdown-line">
                            <span className="breakdown-label">+ Doplňky / měsíční bonus</span>
                            <span className="breakdown-value">
                                {formatPoints((row.doplnky_body || 0) + (row.odmena_mesic_body || 0))}
                            </span>
                        </div>
                    )}
                    <div className="breakdown-line breakdown-line-total">
                        <span className="breakdown-label">Celkem</span>
                        <span className="breakdown-value"><strong>{formatPoints(celkem)}</strong></span>
                    </div>
                </div>
            </div>
        );
    };

    const renderMzdaSouhrn = (row) => {
        if (row.is_brigadnik) return null;
        const zaklad = Number(row.zaklad_body) || 0;
        const doplnky = row.doplnky || [];
        const cestovne = Number(row.cestovne_body) || 0;
        const prescas = Number(row.prescas_body) || 0;
        const prescasH = Number(row.prescas_h) || 0;
        const sazbaPrescas = row.prescas_sazba_h ?? row.viceprace_sazba_h;
        const dyska = Number(row.dyska_body) || 0;
        const dyskaKusy = Number(row.dyska_kusy) || 0;
        const zakladVp = row.zaklad_pro_vicepraci_body;
        const dovolena = Number(row.dovolena_body) || 0;
        const manual = Number(row.odmena_mesic_body) || 0;
        const provize = Number(row.provize_body) || 0;
        const fixni = Number(row.mzda_fixni_body) || 0;
        const celkem = Number(row.celkem_body) || 0;
        const fond = row.fondu_h;

        const lines = [];
        lines.push(
            <div key="zaklad" className="breakdown-line">
                <span className="breakdown-label">Základ (fixní body)</span>
                <span className="breakdown-value">{formatPoints(zaklad)}</span>
            </div>
        );
        doplnky.forEach((d, i) => {
            lines.push(
                <div key={`d-${i}`} className="breakdown-line">
                    <span className="breakdown-label">+ {d.nazev}</span>
                    <span className="breakdown-value">{formatPoints(d.castka)}</span>
                </div>
            );
        });
        if (doplnky.length > 0) {
            lines.push(
                <div key="fixni" className="breakdown-line">
                    <span className="breakdown-label">= Fixní celkem</span>
                    <span className="breakdown-value">{formatPoints(fixni)}</span>
                </div>
            );
        }
        if (cestovne > 0) {
            lines.push(
                <div key="cestovne" className="breakdown-line">
                    <span className="breakdown-label">+ Cestovné (profil, měsíčně)</span>
                    <span className="breakdown-value">{formatPoints(cestovne)}</span>
                </div>
            );
        }
        const provizeBrutto = Number(row.provize_body_brutto ?? row.provize_body) || 0;
        const srazka = Number(row.penalizace_srazka_body) || 0;
        if (srazka > 0 && provizeBrutto > provize) {
            lines.push(
                <div key="provize-brutto" className="breakdown-line">
                    <span className="breakdown-label">+ Provize z prodeje (hrubá)</span>
                    <span className="breakdown-value">{formatPoints(provizeBrutto)}</span>
                </div>
            );
            (row.penalizace || []).forEach((p, i) => {
                lines.push(
                    <div key={`pen-${i}`} className="breakdown-line breakdown-line-deduction">
                        <span className="breakdown-label">− Penalizace −10 %: {p.duvod}</span>
                        <span className="breakdown-value">—</span>
                    </div>
                );
            });
            lines.push(
                <div key="provize-srazka" className="breakdown-line breakdown-line-deduction">
                    <span className="breakdown-label">
                        − Srážka z provize ({row.penalizace_procent || 0} %)
                    </span>
                    <span className="breakdown-value">−{formatPoints(srazka)}</span>
                </div>
            );
        }
        lines.push(
            <div key="provize" className="breakdown-line">
                <span className="breakdown-label">+ Provize z prodeje{ srazka > 0 ? ' (po srážkách)' : ''}</span>
                <span className="breakdown-value">{formatPoints(provize)}</span>
            </div>
        );
        if (dovolena > 0) {
            lines.push(
                <div key="dovolena" className="breakdown-line">
                    <span className="breakdown-label">
                        + Dovolená ({formatNumber(row.dovolena_h)} h × {formatPoints(row.prumer_fixni_h)}/h)
                    </span>
                    <span className="breakdown-value">{formatPoints(dovolena)}</span>
                </div>
            );
        }
        if (dyska > 0) {
            lines.push(
                <div key="dyska" className="breakdown-line">
                    <span className="breakdown-label">
                        + Dýška / vícepráce P63615
                        {dyskaKusy > 0 ? ` (${dyskaKusy} ks)` : ''}
                    </span>
                    <span className="breakdown-value">{formatPoints(dyska)}</span>
                </div>
            );
        }
        const polDokLine = renderPolDokLine(row);
        if (polDokLine) lines.push(polDokLine);
        if (prescas > 0) {
            const sazbaLabel = sazbaPrescas != null && zakladVp != null && fond
                ? `${formatPoints(zakladVp)} / ${formatNumber(fond)} h = ${formatPoints(sazbaPrescas)}/h`
                : null;
            lines.push(
                <div key="prescas" className="breakdown-line">
                    <span className="breakdown-label">
                        + Přesčas ({formatNumber(prescasH)} h
                        {sazbaLabel ? `, ${sazbaLabel}` : ''})
                    </span>
                    <span className="breakdown-value">{formatPoints(prescas)}</span>
                </div>
            );
        }
        if (manual > 0) {
            lines.push(
                <div key="manual" className="breakdown-line">
                    <span className="breakdown-label">
                        + Manuální příplatek
                        {row.odmena_mesic_poznamka ? ` (${row.odmena_mesic_poznamka})` : ''}
                    </span>
                    <span className="breakdown-value">{formatPoints(manual)}</span>
                </div>
            );
        }
        lines.push(
            <div key="celkem" className="breakdown-line breakdown-line-total">
                <span className="breakdown-label">Celkem</span>
                <span className="breakdown-value"><strong>{formatPoints(celkem)}</strong></span>
            </div>
        );

        return (
            <div className="payroll-detail-section">
                <h4>Výpočet výplaty</h4>
                <div className="payroll-breakdown payroll-breakdown-grid">{lines}</div>
            </div>
        );
    };

    if (loading && rows.length === 0) {
        return <div className="payroll-panel loading">Načítání výplaty…</div>;
    }

    return (
        <div className="payroll-panel">
            <div className="payroll-toolbar">
                <div className="payroll-stats stats-grid">
                    <div className="stat-card primary">
                        <div className="stat-content">
                            <div className="stat-value">{formatPoints(soucetBodu)}</div>
                            <div className="stat-label">Součet bodů za měsíc</div>
                        </div>
                    </div>
                    <div className="stat-card success">
                        <div className="stat-content">
                            <div className="stat-value">
                                {fonduH != null ? `${formatNumber(fonduH)} h` : '—'}
                            </div>
                            <div className="stat-label">Měsíční fond</div>
                        </div>
                    </div>
                </div>

                <div className="payroll-actions action-buttons">
                    <button
                        type="button"
                        className="btn-primary"
                        onClick={() => setShowOdmenaModal(true)}
                    >
                        + Přidej odměnu
                    </button>
                    <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => setShowPenalizaceModal(true)}
                    >
                        + Penalizace −10 %
                    </button>
                    {onExport && (
                        <button type="button" className="btn-export" onClick={onExport}>
                            📊 Export
                        </button>
                    )}
                </div>
            </div>

            {loading && <p className="payroll-loading-inline">Aktualizuji data…</p>}

            <p className="payroll-hint">
                Rozklikněte řádek pro detail (vedoucí, cestovné, přesčas, provize).
                Přesčas = (základ + variabilní z profilu) / fond × hodiny nad fondem. Dýška = obrat P63615 (1 bod = 1 Kč).
                Cestovné a manuální bonus se do sazby přesčasu nepřičítají.
            </p>

            {error && <div className="error-message">{error}</div>}

            <section className="payroll-discounted-section">
                <button
                    type="button"
                    className="payroll-discounted-toggle"
                    onClick={toggleDiscounted}
                    aria-expanded={discountedOpen}
                >
                    <span className="toggle-icon">{discountedOpen ? '▼' : '▶'}</span>
                    Služby se slevou ≥ 20 % (bez příplatku)
                    {discountedCount > 0 && (
                        <span className="discounted-badge">
                            {discountedCount} řádků · −{formatPoints(discountedExcluded)} b.
                        </span>
                    )}
                </button>
                {discountedOpen && (
                    <div className="payroll-discounted-body">
                        <p className="payroll-discounted-hint">
                            Ceny typu 599 / 499 / 249 (x99) a sleva do 10 % zůstávají v odměňování.
                            Od 20 % slevy se příplatek za službu nepočítá.
                        </p>
                        {discountedLoading && (
                            <p className="payroll-loading-inline">Načítám výjimky…</p>
                        )}
                        {discountedError && (
                            <div className="error-message">{discountedError}</div>
                        )}
                        {!discountedLoading && !discountedError && discountedCount === 0 && (
                            <p className="payroll-discounted-empty">V tomto měsíci žádné.</p>
                        )}
                        {discountedRows.length > 0 && (
                            <div className="payroll-discounted-table-wrap">
                                <table className="payroll-discounted-table">
                                    <thead>
                                        <tr>
                                            <th>Datum</th>
                                            <th>Doklad</th>
                                            <th>Kód</th>
                                            <th>Prodejce</th>
                                            <th>Cena/ks</th>
                                            <th>Katalog</th>
                                            <th>Sleva</th>
                                            <th>Ks</th>
                                            <th>Bez bodů</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {discountedRows.map((row, idx) => (
                                            <tr key={`${row.doklad}-${row.kod}-${idx}`}>
                                                <td>{row.datum || '—'}</td>
                                                <td>{row.doklad || '—'}</td>
                                                <td><code>{row.kod}</code></td>
                                                <td>{row.prodejce || '—'}</td>
                                                <td>{formatNumber(row.cena_ks_vcl_dph)} Kč</td>
                                                <td>
                                                    {row.katalog_cena != null
                                                        ? `${formatNumber(row.katalog_cena)} Kč`
                                                        : '—'}
                                                </td>
                                                <td>
                                                    {row.sleva_procent != null
                                                        ? `${formatNumber(row.sleva_procent)} %`
                                                        : '—'}
                                                </td>
                                                <td>{row.kusy}</td>
                                                <td className="col-excluded">−{formatPoints(row.vyloucene_body)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                    <tfoot>
                                        <tr>
                                            <td colSpan={8} className="tfoot-label">Celkem vyloučené body</td>
                                            <td className="col-excluded">
                                                <strong>−{formatPoints(discountedExcluded)}</strong>
                                            </td>
                                        </tr>
                                    </tfoot>
                                </table>
                            </div>
                        )}
                    </div>
                )}
            </section>

            <section className="payroll-dobropisy-section">
                <button
                    type="button"
                    className="payroll-dobropisy-toggle"
                    onClick={toggleDobropisy}
                    aria-expanded={dobropisyOpen}
                >
                    <span className="toggle-icon">{dobropisyOpen ? '▼' : '▶'}</span>
                    Dobropisy (vratky)
                    {dobropisyTotals.polozky > 0 && (
                        <span className="dobropisy-badge">
                            {dobropisyTotals.polozky} položek · {dobropisyTotals.doklady} dokladů
                        </span>
                    )}
                </button>
                {dobropisyOpen && (
                    <div className="payroll-dobropisy-body">
                        <p className="payroll-dobropisy-hint">
                            Skutečné vratky produktů (záporná cena). Nezapočítáváme slevy BODY/SLEVA ani zaokrouhlení.
                            {' '}<strong>Zrcadlo</strong> = stejný den, stejná cena/ks, do 3 h po prodeji.
                            {' '}<strong>Jiný prodej</strong> = starší prodej stejné položky u stejného prodejce.
                        </p>
                        {dobropisyPairingTotals.zrcadlo + dobropisyPairingTotals.par + dobropisyPairingTotals.bez_paru > 0 && (
                            <div className="payroll-dobropisy-chips">
                                <span className="pairing-chip pairing-chip--mirror">
                                    Zrcadlo: {dobropisyPairingTotals.zrcadlo}
                                </span>
                                <span className="pairing-chip pairing-chip--par">
                                    Jiný prodej: {dobropisyPairingTotals.par}
                                </span>
                                <span className="pairing-chip pairing-chip--none">
                                    Bez páru: {dobropisyPairingTotals.bez_paru}
                                </span>
                            </div>
                        )}
                        {dobropisyLoading && (
                            <p className="payroll-loading-inline">Načítám dobropisy…</p>
                        )}
                        {dobropisyError && (
                            <div className="error-message">{dobropisyError}</div>
                        )}
                        {!dobropisyLoading && !dobropisyError && dobropisyTotals.polozky === 0 && (
                            <p className="payroll-dobropisy-empty">V tomto měsíci žádné.</p>
                        )}
                        {!dobropisyLoading && !dobropisyError && dobropisyTotals.polozky > 0 && (
                            <>
                                <div className="payroll-dobropisy-summary-wrap">
                                    <table className="payroll-dobropisy-table payroll-dobropisy-summary">
                                        <thead>
                                            <tr>
                                                <th>Prodejce</th>
                                                <th>Položky</th>
                                                <th>Doklady</th>
                                                <th>Částka</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {dobropisySummary.map((row) => (
                                                <tr key={row.id_prodejce}>
                                                    <td>{row.prodejce}</td>
                                                    <td>{row.polozky}</td>
                                                    <td>{row.doklady}</td>
                                                    <td className="col-negative">{formatNumber(row.castka)} Kč</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                        <tfoot>
                                            <tr>
                                                <td className="tfoot-label">Celkem</td>
                                                <td>{dobropisyTotals.polozky}</td>
                                                <td>{dobropisyTotals.doklady}</td>
                                                <td className="col-negative">
                                                    <strong>{formatNumber(dobropisyTotals.castka)} Kč</strong>
                                                </td>
                                            </tr>
                                        </tfoot>
                                    </table>
                                </div>

                                <div className="payroll-dobropisy-filter">
                                    <label>
                                        Prodejce
                                        <select
                                            value={dobropisyFilterUser}
                                            onChange={(e) => setDobropisyFilterUser(e.target.value)}
                                        >
                                            <option value="">Všichni prodejci</option>
                                            {dobropisySummary.map((row) => (
                                                <option key={row.id_prodejce} value={row.id_prodejce}>
                                                    {row.prodejce} ({row.polozky})
                                                </option>
                                            ))}
                                        </select>
                                    </label>
                                    <label>
                                        Typ páru
                                        <select
                                            value={dobropisyFilterPairing}
                                            onChange={(e) => setDobropisyFilterPairing(e.target.value)}
                                        >
                                            <option value="">Vše</option>
                                            <option value="zrcadlo">Zrcadlo ({dobropisyPairingTotals.zrcadlo})</option>
                                            <option value="par">Jiný prodej ({dobropisyPairingTotals.par})</option>
                                            <option value="bez_paru">Bez páru ({dobropisyPairingTotals.bez_paru})</option>
                                        </select>
                                    </label>
                                </div>

                                <div className="payroll-dobropisy-table-wrap">
                                    <table className="payroll-dobropisy-table">
                                        <thead>
                                            <tr>
                                                <th>Typ</th>
                                                <th>Datum</th>
                                                <th>Doklad</th>
                                                <th>Kód</th>
                                                <th>Název</th>
                                                <th>Prodejce</th>
                                                <th>Původní doklad</th>
                                                <th>Původní den</th>
                                                <th>Po prodeji</th>
                                                <th>Částka</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {filteredDobropisyRows.map((row, idx) => (
                                                <tr
                                                    key={`${row.doklad}-${row.kod}-${idx}`}
                                                    className={`pairing-row pairing-row--${row.pairing || 'bez_paru'}`}
                                                >
                                                    <td>
                                                        <span className={`pairing-badge pairing-badge--${row.pairing}`}>
                                                            {row.pairing_label || '—'}
                                                        </span>
                                                    </td>
                                                    <td>{row.datum || '—'}</td>
                                                    <td>{row.doklad || '—'}</td>
                                                    <td><code>{row.kod}</code></td>
                                                    <td className="col-nazev" title={row.nazev}>{row.nazev || '—'}</td>
                                                    <td>{row.prodejce || '—'}</td>
                                                    <td>{row.puvodni_doklad || '—'}</td>
                                                    <td>{row.puvodni_datum || '—'}</td>
                                                    <td>
                                                        {row.minut_po_prodeji != null
                                                            ? `${formatNumber(row.minut_po_prodeji)} min`
                                                            : '—'}
                                                    </td>
                                                    <td className="col-negative">{formatNumber(row.castka)} Kč</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </>
                        )}
                    </div>
                )}
            </section>

            <div className="payroll-table-wrap">
                <table className="payroll-table">
                    <thead>
                        <tr>
                            <th className="col-expand" />
                            <th>Jméno</th>
                            <th>Odprac. h</th>
                            <th>Fixní</th>
                            <th>Provize</th>
                            <th>Celkem</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((row) => {
                            const isOpen = expandedId === row.user_id;
                            return (
                                <React.Fragment key={row.user_id}>
                                    <tr className={isOpen ? 'row-expanded' : ''}>
                                        <td className="col-expand">
                                            <button
                                                type="button"
                                                className="expand-btn"
                                                onClick={() => setExpandedId(isOpen ? null : row.user_id)}
                                                aria-expanded={isOpen}
                                            >
                                                {isOpen ? '▼' : '▶'}
                                            </button>
                                        </td>
                                        <td className="col-name">{row.jmeno}</td>
                                        <td>{formatNumber(row.odpracovano_h)}</td>
                                        <td
                                            title={
                                                row.is_brigadnik
                                                    ? `${row.body_za_hodinu} bodů/h × ${row.odpracovano_h} h`
                                                    : (row.doplnky_body > 0
                                                        ? `Základ ${row.zaklad_body} + doplňky ${row.doplnky_body}`
                                                        : undefined)
                                            }
                                        >
                                            {formatPoints(row.mzda_fixni_body)}
                                            {row.is_brigadnik && row.body_za_hodinu != null && (
                                                <span className="payroll-sazba-hint"> ({row.body_za_hodinu}/h)</span>
                                            )}
                                        </td>
                                        <td>{formatPoints(row.provize_body)}</td>
                                        <td className="col-celkem"><strong>{formatPoints(row.celkem_body)}</strong></td>
                                    </tr>
                                    {isOpen && (
                                        <tr className="detail-row">
                                            <td colSpan={6}>
                                                <div className="payroll-detail-full">
                                    {renderBrigadnikSouhrn(row)}
                                    {renderMzdaSouhrn(row)}
                                    {row.deficit_h > 0 && (
                                        <p className="payroll-detail-hint">
                                            Deficit fondu v měsíci: {formatNumber(row.deficit_h)} h
                                            {' '}(odečteno z roční dovolené
                                            {row.prumer_fixni_h > 0
                                                ? `, průměr ${formatPoints(row.prumer_fixni_h)} bodů/h`
                                                : ''}
                                            ).
                                        </p>
                                    )}
                                    {renderProvizeBreakdown(row.provize_breakdown)}
                                                </div>
                                            </td>
                                        </tr>
                                    )}
                                </React.Fragment>
                            );
                        })}
                    </tbody>
                    {rows.length > 0 && (
                        <tfoot>
                            <tr className="payroll-tfoot">
                                <td colSpan={5} className="tfoot-label">Součet bodů</td>
                                <td className="col-celkem"><strong>{formatPoints(soucetBodu)}</strong></td>
                            </tr>
                        </tfoot>
                    )}
                </table>
            </div>

            {showPenalizaceModal && (
                <Modal
                    title="Penalizace −10 % z provize"
                    onClose={closePenalizaceModal}
                    size="sm"
                    onSubmit={savePenalizace}
                    formRef={penalizaceFormRef}
                    footer={(
                        <>
                            <button type="button" className="btn-cancel" onClick={closePenalizaceModal}>
                                Zrušit
                            </button>
                            <button type="submit" className="btn-submit" disabled={savingPenalizace}>
                                {savingPenalizace ? 'Ukládám…' : 'Přidat penalizaci'}
                            </button>
                        </>
                    )}
                >
                        <p className="modal-hint">
                            Každá penalizace sníží provizi o dalších 10 % (3× = −30 %). Základ, cestovné
                            a bonusy se nemění. Měsíc: {formatMonthName(month)}.
                        </p>
                            <label>
                                Zaměstnanec
                                <select
                                    value={penalizaceForm.user_id}
                                    onChange={(e) => setPenalizaceForm((f) => ({ ...f, user_id: e.target.value }))}
                                    required
                                >
                                    <option value="">— vyberte —</option>
                                    {employeeOptions.map((u) => (
                                        <option key={u.id} value={u.id}>{u.jmeno}</option>
                                    ))}
                                </select>
                            </label>
                            <label>
                                Důvod srážky
                                <input
                                    type="text"
                                    value={penalizaceForm.duvod}
                                    onChange={(e) => setPenalizaceForm((f) => ({ ...f, duvod: e.target.value }))}
                                    required
                                />
                            </label>
                </Modal>
            )}

            {showOdmenaModal && (
                <Modal
                    title="Přidej odměnu"
                    onClose={closeOdmenaModal}
                    size="sm"
                    onSubmit={saveOdmena}
                    formRef={odmenaFormRef}
                    footer={(
                        <>
                            <button type="button" className="btn-cancel" onClick={closeOdmenaModal}>
                                Zrušit
                            </button>
                            <button type="submit" className="btn-submit" disabled={savingOdmena}>
                                {savingOdmena ? 'Ukládám…' : 'Přidat'}
                            </button>
                        </>
                    )}
                >
                        <p className="modal-hint">
                            Body se přičtou k měsíční odměně za {formatMonthName(month)}.
                        </p>
                            <label>
                                Zaměstnanec
                                <select
                                    value={odmenaForm.user_id}
                                    onChange={(e) => setOdmenaForm((f) => ({ ...f, user_id: e.target.value }))}
                                    required
                                >
                                    <option value="">— vyberte —</option>
                                    {employeeOptions.map((u) => (
                                        <option key={u.id} value={u.id}>{u.jmeno}</option>
                                    ))}
                                </select>
                            </label>
                            <label>
                                Body
                                <input
                                    type="number"
                                    className={manualNumberInputClass()}
                                    min="1"
                                    step="1"
                                    value={odmenaForm.castka}
                                    onChange={(e) => setOdmenaForm((f) => ({ ...f, castka: e.target.value }))}
                                    onWheel={preventNumberInputWheel}
                                    required
                                />
                            </label>
                            <label>
                                Poznámka (volitelné)
                                <input
                                    type="text"
                                    value={odmenaForm.poznamka}
                                    onChange={(e) => setOdmenaForm((f) => ({ ...f, poznamka: e.target.value }))}
                                />
                            </label>
                </Modal>
            )}
        </div>
    );
}

export default PayrollPanel;
