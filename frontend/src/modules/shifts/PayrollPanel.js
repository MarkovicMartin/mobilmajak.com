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
import SymplioDocLink from '../../components/SymplioDocLink';
import './PayrollPanel.css';

const CACHE_PREFIX = 'payroll-overview-v3';
const CURRENT_MONTH_STALE_MS = 5 * 60 * 1000;
const RETURNS_CACHE_PREFIX = 'payroll-returns-v1';
const RETURNS_STALE_MS = 10 * 60 * 1000;
const EMPTY_PENALIZACE_POLOZKA = { typ: 'procenta', hodnota: '10', duvod: '' };
const memoryCache = new Map();
const returnsMemoryCache = new Map();

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

async function fetchManualRevision(month) {
    const res = await fetch(`/api/shifts/payroll/manual-revision/?mesic=${month}`, { credentials: 'include' });
    if (!res.ok) return null;
    const data = await res.json();
    return data.manual_revision ?? null;
}

async function mergeManualRows(month, baseRows) {
    const res = await fetch('/api/shifts/payroll/merge-manual/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ mesic: month, rows: baseRows }),
    });
    if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || 'Chyba při načítání manuálních úprav');
    }
    return res.json();
}

function buildPayrollCacheData(baseData, mergedData) {
    return {
        mesic: baseData.mesic,
        fondu_h: baseData.fondu_h,
        celkem_bodu: mergedData.celkem_bodu,
        celkem_vyplata: mergedData.celkem_bodu,
        manual_revision: mergedData.manual_revision,
        baseRows: baseData.rows,
        rows: mergedData.rows,
    };
}

function returnsCacheKey(month, part) {
    return `${RETURNS_CACHE_PREFIX}:${month}:${part}`;
}

function readReturnsCache(month, part) {
    const memKey = `${month}:${part}`;
    if (returnsMemoryCache.has(memKey)) return returnsMemoryCache.get(memKey);
    try {
        const raw = sessionStorage.getItem(returnsCacheKey(month, part));
        if (!raw) return null;
        const parsed = JSON.parse(raw);
        returnsMemoryCache.set(memKey, parsed);
        return parsed;
    } catch {
        return null;
    }
}

function writeReturnsCache(month, part, data) {
    const entry = { data, fetchedAt: Date.now() };
    returnsMemoryCache.set(`${month}:${part}`, entry);
    try {
        sessionStorage.setItem(returnsCacheKey(month, part), JSON.stringify(entry));
    } catch {
        // sessionStorage plné – modulová cache stačí
    }
}

function returnsNeedsRefresh(month, cached) {
    if (!cached) return true;
    const current = currentMonthStr();
    if (month < current) return false;
    if (month > current) return true;
    return Date.now() - (cached.fetchedAt || 0) > RETURNS_STALE_MS;
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

function monthShortLabel(month, year) {
    return `${MONTH_NAMES[month - 1]} ${year}`;
}

function formatDovolenaSazbaLabel(row) {
    const sazba = row.prumer_dovolena_h ?? row.prumer_fixni_h;
    const detail = row.prumer_dovolena_detail;
    if (!detail || sazba == null) return null;
    if (detail.zdroj === 'fallback_zaklad_fond' && detail.fallback_zaklad_body && detail.fallback_fond_h) {
        return `${formatPoints(detail.fallback_zaklad_body)} / ${formatNumber(detail.fallback_fond_h)} h = ${formatPoints(sazba)}/h (fallback – bez historie)`;
    }
    if (detail.celkem_h > 0 && detail.celkem_mzda > 0) {
        const mesice = (detail.mesice || [])
            .map((pm) => monthShortLabel(pm.mesic, pm.rok))
            .join(', ');
        const importNote = detail.zdroj === 'override_excel' ? ', hodiny z importu' : '';
        return `${formatPoints(detail.celkem_mzda)} / ${formatNumber(detail.celkem_h)} h = ${formatPoints(sazba)}/h (${mesice}${importNote})`;
    }
    return `${formatPoints(sazba)}/h`;
}

function returnsPersonKey(id, name) {
    if (id != null && id !== '') return `id:${id}`;
    return `name:${String(name || '—').trim().toLowerCase()}`;
}

function currentMonthStr() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

function formatPenalizaceLabel(p) {
    const duvod = (p.duvod || '').trim();
    const autor = (p.vytvoril_jmeno || '').trim();
    const suffix = autor ? ` (${autor})` : '';
    if (p.typ === 'fixni') {
        return `−${formatPoints(p.hodnota)}: ${duvod}${suffix}`;
    }
    return `−${formatNumber(p.hodnota)} %: ${duvod}${suffix}`;
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
    const [penalizaceForm, setPenalizaceForm] = useState({
        user_id: '',
        polozky: [{ ...EMPTY_PENALIZACE_POLOZKA }],
    });
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
    const [dobropisyPairingTotals, setDobropisyPairingTotals] = useState({
        zrcadlo: 0, par: 0, bez_paru: 0,
    });
    const dobropisyRowsLoadedRef = useRef(false);
    const [vydejkySummary, setVydejkySummary] = useState([]);
    const [vydejkyRows, setVydejkyRows] = useState([]);
    const [vydejkyTotals, setVydejkyTotals] = useState({ polozky: 0, doklady: 0, castka: 0 });
    const [vydejkyDuvodTotals, setVydejkyDuvodTotals] = useState({ rucni: 0, spotreba: 0, reklamace: 0 });
    const [vydejkyLoading, setVydejkyLoading] = useState(false);
    const [vydejkyError, setVydejkyError] = useState('');
    const [vydejkyExpanded, setVydejkyExpanded] = useState({});
    const [returnsExpandedPerson, setReturnsExpandedPerson] = useState({});
    const vydejkyRowsLoadedRef = useRef(false);
    const odmenaFormRef = useRef(null);
    const penalizaceFormRef = useRef(null);
    const fetchSeq = useRef(0);

    const closeOdmenaModal = useCallback(() => {
        setShowOdmenaModal(false);
        setOdmenaForm({ user_id: '', castka: '', poznamka: '' });
    }, []);

    const closePenalizaceModal = useCallback(() => {
        setShowPenalizaceModal(false);
        setPenalizaceForm({ user_id: '', polozky: [{ ...EMPTY_PENALIZACE_POLOZKA }] });
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

        const syncManualFromCache = async () => {
            const baseRows = cached?.data?.baseRows;
            if (!baseRows?.length) return false;
            const remoteRevision = await fetchManualRevision(month);
            if (seq !== fetchSeq.current) return true;
            const localRevision = cached?.manual_revision ?? cached?.data?.manual_revision ?? null;
            if (remoteRevision === localRevision) return false;
            const merged = await mergeManualRows(month, baseRows);
            if (seq !== fetchSeq.current) return true;
            const data = buildPayrollCacheData(
                { mesic: month, fondu_h: cached.data.fondu_h, rows: baseRows },
                merged,
            );
            writeCache(month, { data, manual_revision: merged.manual_revision });
            applyPayrollPayload(data, setRows, setFonduH);
            return true;
        };

        try {
            const manualChanged = await syncManualFromCache();
            if (seq !== fetchSeq.current) return;

            if (!force && !needsBackgroundRefresh(month, cached) && !manualChanged) {
                if (cached?.data?.baseRows?.length) {
                    return;
                }
            }

            const res = await fetch(`/api/shifts/payroll/?mesic=${month}&base_only=1`, { credentials: 'include' });
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.error || 'Chyba při načítání výplaty');
            }
            const baseData = await res.json();
            if (seq !== fetchSeq.current) return;

            const merged = await mergeManualRows(month, baseData.rows || []);
            if (seq !== fetchSeq.current) return;

            const data = buildPayrollCacheData(baseData, merged);
            writeCache(month, { data, manual_revision: merged.manual_revision });
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
        setDiscountedOpen(false);
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
        setDobropisyOpen(false);
        setReturnsExpandedPerson({});

        const cachedSummary = readReturnsCache(month, 'dobropisy-summary');
        if (cachedSummary?.data) {
            setDobropisySummary(cachedSummary.data.summary || []);
            setDobropisyTotals(cachedSummary.data.totals || { polozky: 0, doklady: 0, castka: 0 });
        } else {
            setDobropisySummary([]);
            setDobropisyTotals({ polozky: 0, doklady: 0, castka: 0 });
        }

        const cachedRows = readReturnsCache(month, 'dobropisy-rows');
        if (cachedRows?.data) {
            setDobropisyRows(cachedRows.data.rows || []);
            setDobropisyPairingTotals(cachedRows.data.pairing_totals || { zrcadlo: 0, par: 0, bez_paru: 0 });
            dobropisyRowsLoadedRef.current = true;
        } else {
            dobropisyRowsLoadedRef.current = false;
            setDobropisyRows([]);
            setDobropisyPairingTotals({ zrcadlo: 0, par: 0, bez_paru: 0 });
        }

        if (!returnsNeedsRefresh(month, cachedSummary)) {
            return;
        }

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
            writeReturnsCache(month, 'dobropisy-summary', data);
            setDobropisySummary(data.summary || []);
            setDobropisyTotals(data.totals || { polozky: 0, doklady: 0, castka: 0 });
        } catch (e) {
            setDobropisyError(e.message);
            if (!cachedSummary?.data) {
                setDobropisySummary([]);
                setDobropisyTotals({ polozky: 0, doklady: 0, castka: 0 });
            }
        }
    }, [month]);

    const loadDobropisyRows = useCallback(async (opts = {}) => {
        const { background = false, force = false } = opts;
        if (!month) return;

        const cached = readReturnsCache(month, 'dobropisy-rows');
        if (!force && cached?.data) {
            setDobropisyRows(cached.data.rows || []);
            setDobropisyPairingTotals(cached.data.pairing_totals || { zrcadlo: 0, par: 0, bez_paru: 0 });
            dobropisyRowsLoadedRef.current = true;
            if (!returnsNeedsRefresh(month, cached)) {
                return;
            }
        } else if (!force && dobropisyRowsLoadedRef.current) {
            return;
        }

        if (!background) {
            setDobropisyLoading(true);
        }
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
            writeReturnsCache(month, 'dobropisy-rows', data);
            setDobropisyRows(data.rows || []);
            setDobropisyPairingTotals(data.pairing_totals || { zrcadlo: 0, par: 0, bez_paru: 0 });
            dobropisyRowsLoadedRef.current = true;
        } catch (e) {
            setDobropisyError(e.message);
            if (!cached?.data) {
                setDobropisyRows([]);
            }
        } finally {
            if (!background) {
                setDobropisyLoading(false);
            }
        }
    }, [month]);

    const toggleDobropisy = useCallback(() => {
        setDobropisyOpen((wasOpen) => !wasOpen);
    }, []);

    const loadVydejkySummary = useCallback(async () => {
        if (!month) return;
        setVydejkyError('');
        setVydejkyExpanded({});
        setReturnsExpandedPerson({});

        const cachedSummary = readReturnsCache(month, 'vydejky-summary');
        if (cachedSummary?.data) {
            setVydejkySummary(cachedSummary.data.summary || []);
            setVydejkyTotals(cachedSummary.data.totals || { polozky: 0, doklady: 0, castka: 0 });
        } else {
            setVydejkySummary([]);
            setVydejkyTotals({ polozky: 0, doklady: 0, castka: 0 });
        }

        const cachedRows = readReturnsCache(month, 'vydejky-rows');
        if (cachedRows?.data) {
            setVydejkyRows(cachedRows.data.rows || []);
            setVydejkyDuvodTotals(cachedRows.data.duvod_totals || { rucni: 0, spotreba: 0, reklamace: 0 });
            vydejkyRowsLoadedRef.current = true;
        } else {
            vydejkyRowsLoadedRef.current = false;
            setVydejkyRows([]);
            setVydejkyDuvodTotals({ rucni: 0, spotreba: 0, reklamace: 0 });
        }

        if (!returnsNeedsRefresh(month, cachedSummary)) {
            return;
        }

        try {
            const res = await fetch(
                `/api/shifts/payroll/vydejky/?mesic=${month}`,
                { credentials: 'include' },
            );
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.error || 'Chyba při načítání skladových výdejek');
            }
            const data = await res.json();
            writeReturnsCache(month, 'vydejky-summary', data);
            setVydejkySummary(data.summary || []);
            setVydejkyTotals(data.totals || { polozky: 0, doklady: 0, castka: 0 });
        } catch (e) {
            setVydejkyError(e.message);
            if (!cachedSummary?.data) {
                setVydejkySummary([]);
                setVydejkyTotals({ polozky: 0, doklady: 0, castka: 0 });
            }
        }
    }, [month]);

    const loadVydejkyRows = useCallback(async (opts = {}) => {
        const { background = false, force = false } = opts;
        if (!month) return;

        const cached = readReturnsCache(month, 'vydejky-rows');
        if (!force && cached?.data) {
            setVydejkyRows(cached.data.rows || []);
            setVydejkyDuvodTotals(cached.data.duvod_totals || { rucni: 0, spotreba: 0, reklamace: 0 });
            vydejkyRowsLoadedRef.current = true;
            if (!returnsNeedsRefresh(month, cached)) {
                return;
            }
        } else if (!force && vydejkyRowsLoadedRef.current) {
            return;
        }

        if (!background) {
            setVydejkyLoading(true);
        }
        setVydejkyError('');
        try {
            const res = await fetch(
                `/api/shifts/payroll/vydejky/?mesic=${month}&rows_only=1`,
                { credentials: 'include' },
            );
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.error || 'Chyba při načítání položek výdejek');
            }
            const data = await res.json();
            writeReturnsCache(month, 'vydejky-rows', data);
            setVydejkyRows(data.rows || []);
            setVydejkyDuvodTotals(data.duvod_totals || { rucni: 0, spotreba: 0, reklamace: 0 });
            vydejkyRowsLoadedRef.current = true;
        } catch (e) {
            setVydejkyError(e.message);
            if (!cached?.data) {
                setVydejkyRows([]);
            }
        } finally {
            if (!background) {
                setVydejkyLoading(false);
            }
        }
    }, [month]);

    const toggleReturnsPerson = useCallback((personKey) => {
        setReturnsExpandedPerson((prev) => ({ ...prev, [personKey]: !prev[personKey] }));
    }, []);

    const toggleVydejkaExpanded = useCallback((doklad) => {
        setVydejkyExpanded((prev) => ({ ...prev, [doklad]: !prev[doklad] }));
    }, []);

    const returnsPersonGroups = useMemo(() => {
        const map = new Map();

        const ensure = (key, name) => {
            if (!map.has(key)) {
                map.set(key, {
                    key,
                    name,
                    dobropisy: [],
                    vydejky: { rucni: [], spotreba: [], reklamace: [] },
                    counts: { dobropisy: 0, rucni: 0, spotreba: 0, reklamace: 0 },
                    castky: { dobropisy: 0, rucni: 0, spotreba: 0, reklamace: 0, celkem: 0 },
                });
            }
            const group = map.get(key);
            if (name && name !== '—' && group.name === '—') {
                group.name = name;
            }
            return group;
        };

        for (const row of dobropisyRows) {
            const key = returnsPersonKey(row.id_prodejce, row.prodejce);
            const group = ensure(key, row.prodejce || '—');
            group.dobropisy.push(row);
            group.counts.dobropisy += 1;
            group.castky.dobropisy += Number(row.castka) || 0;
        }

        for (const row of vydejkyRows) {
            const key = returnsPersonKey(row.id_spravce, row.spravce);
            const group = ensure(key, row.spravce || '—');
            const cat = row.duvod_kategorie;
            if (cat === 'rucni' || cat === 'spotreba' || cat === 'reklamace') {
                group.vydejky[cat].push(row);
                group.counts[cat] += 1;
                group.castky[cat] += Number(row.castka_s_dph) || 0;
            }
        }

        for (const group of map.values()) {
            group.castky.celkem = group.castky.dobropisy
                + group.castky.rucni
                + group.castky.spotreba
                + group.castky.reklamace;
            group.vydejkyAll = [
                ...group.vydejky.rucni,
                ...group.vydejky.spotreba,
                ...group.vydejky.reklamace,
            ].sort((a, b) => (b.datum || '').localeCompare(a.datum || '') || (a.doklad || '').localeCompare(b.doklad || ''));
        }

        return Array.from(map.values()).sort(
            (a, b) => Math.abs(b.castky.celkem) - Math.abs(a.castky.celkem)
                || a.name.localeCompare(b.name, 'cs'),
        );
    }, [dobropisyRows, vydejkyRows]);

    const returnsGrandTotals = useMemo(() => ({
        dobropisy: dobropisyTotals.polozky || 0,
        rucni: vydejkyDuvodTotals.rucni || 0,
        spotreba: vydejkyDuvodTotals.spotreba || 0,
        reklamace: vydejkyDuvodTotals.reklamace || 0,
        castka: (Number(dobropisyTotals.castka) || 0) + (Number(vydejkyTotals.castka) || 0),
    }), [dobropisyTotals, vydejkyTotals, vydejkyDuvodTotals]);

    const returnsHasData = returnsGrandTotals.dobropisy > 0
        || returnsGrandTotals.rucni > 0
        || returnsGrandTotals.spotreba > 0
        || returnsGrandTotals.reklamace > 0;

    const returnsLoading = (dobropisyLoading || vydejkyLoading)
        && returnsPersonGroups.length === 0
        && returnsHasData;

    useEffect(() => {
        loadPayroll();
        loadDiscountedSummary();
        loadDobropisySummary();
        loadVydejkySummary();
    }, [loadPayroll, loadDiscountedSummary, loadDobropisySummary, loadVydejkySummary]);

    useEffect(() => {
        if (!month) return;
        if (dobropisyTotals.polozky > 0) {
            loadDobropisyRows({ background: true });
        }
    }, [month, dobropisyTotals.polozky, loadDobropisyRows]);

    useEffect(() => {
        if (!month) return;
        if (vydejkyTotals.doklady > 0) {
            loadVydejkyRows({ background: true });
        }
    }, [month, vydejkyTotals.doklady, loadVydejkyRows]);

    useEffect(() => {
        if (discountedOpen && discountedCount > 0 && !discountedRowsLoadedRef.current) {
            loadDiscountedRows();
        }
    }, [discountedOpen, discountedCount, loadDiscountedRows]);

    useEffect(() => {
        if (!dobropisyOpen) return;
        if (dobropisyTotals.polozky > 0 && !dobropisyRowsLoadedRef.current) {
            loadDobropisyRows();
        }
        if (vydejkyTotals.doklady > 0 && !vydejkyRowsLoadedRef.current) {
            loadVydejkyRows();
        }
    }, [
        dobropisyOpen,
        dobropisyTotals.polozky,
        vydejkyTotals.doklady,
        loadDobropisyRows,
        loadVydejkyRows,
    ]);

    const employeeOptions = useMemo(
        () => rows.map((r) => ({ id: r.user_id, jmeno: r.jmeno })),
        [rows],
    );

    const existingPenalizaceForForm = useMemo(() => {
        if (!penalizaceForm.user_id) return [];
        const row = rows.find((r) => String(r.user_id) === String(penalizaceForm.user_id));
        return row?.penalizace || [];
    }, [penalizaceForm.user_id, rows]);

    const existingPenalizaceRow = useMemo(() => {
        if (!penalizaceForm.user_id) return null;
        return rows.find((r) => String(r.user_id) === String(penalizaceForm.user_id)) || null;
    }, [penalizaceForm.user_id, rows]);

    const savePenalizace = async (e) => {
        e.preventDefault();
        if (!penalizaceForm.user_id) {
            alert('Vyberte zaměstnance.');
            return;
        }
        const polozky = penalizaceForm.polozky
            .map((p) => ({
                typ: p.typ,
                hodnota: parseFloat(String(p.hodnota).replace(',', '.')),
                duvod: (p.duvod || '').trim(),
            }))
            .filter((p) => p.duvod);
        if (!polozky.length) {
            alert('Přidejte alespoň jednu penalizaci s důvodem.');
            return;
        }
        if (polozky.some((p) => !Number.isFinite(p.hodnota) || p.hodnota <= 0)) {
            alert('Zadejte kladnou hodnotu u každé penalizace.');
            return;
        }
        if (polozky.some((p) => p.typ === 'procenta' && p.hodnota > 100)) {
            alert('Procenta max. 100.');
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
                    polozky,
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
        const profilZaklad = zaklad + doplnky.reduce((s, d) => s + (Number(d.castka) || 0), 0);
        const hDoFondu = Math.min(Number(row.odpracovano_h) || 0, Number(fond) || 0);
        lines.push(
            <div key="zaklad-profil" className="breakdown-line breakdown-line-muted">
                <span className="breakdown-label">Základ z profilu (měsíčně)</span>
                <span className="breakdown-value">{formatPoints(profilZaklad)}</span>
            </div>
        );
        lines.push(
            <div key="zaklad-pomer" className="breakdown-line">
                <span className="breakdown-label">
                    Základ poměrný ({formatNumber(hDoFondu)} h / fond {formatNumber(fond)} h)
                </span>
                <span className="breakdown-value">{formatPoints(fixni)}</span>
            </div>
        );
        doplnky.forEach((d, i) => {
            lines.push(
                <div key={`d-${i}`} className="breakdown-line breakdown-line-muted">
                    <span className="breakdown-label">↳ v profilu: {d.nazev}</span>
                    <span className="breakdown-value">{formatPoints(d.castka)}</span>
                </div>
            );
        });
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
                        <span className="breakdown-label">− Penalizace {formatPenalizaceLabel(p)}</span>
                        <span className="breakdown-value">—</span>
                    </div>
                );
            });
            const pctLabel = Number(row.penalizace_procent) > 0
                ? `${formatNumber(row.penalizace_procent)} %`
                : null;
            const fixLabel = Number(row.penalizace_fixni_body) > 0
                ? `${formatPoints(row.penalizace_fixni_body)} b`
                : null;
            const srazkaParts = [pctLabel, fixLabel].filter(Boolean);
            lines.push(
                <div key="provize-srazka" className="breakdown-line breakdown-line-deduction">
                    <span className="breakdown-label">
                        − Srážka z provize
                        {srazkaParts.length ? ` (${srazkaParts.join(' + ')})` : ''}
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
            const sazbaDovolenaLabel = formatDovolenaSazbaLabel(row);
            lines.push(
                <div key="dovolena" className="breakdown-line">
                    <span className="breakdown-label">
                        + Dovolená ({formatNumber(row.dovolena_h)} h
                        {sazbaDovolenaLabel ? `, ${sazbaDovolenaLabel}` : ` × ${formatPoints(row.prumer_fixni_h)}/h`})
                    </span>
                    <span className="breakdown-value">{formatPoints(dovolena)}</span>
                </div>
            );
            const prumerDetail = row.prumer_dovolena_detail;
            if (prumerDetail?.mesice?.length > 0) {
                lines.push(
                    <div key="dovolena-prumer" className="payroll-prumer-dovolena-wrap">
                        <table className="payroll-prumer-dovolena-table">
                            <thead>
                                <tr>
                                    <th>Měsíc (průměr)</th>
                                    <th>Odpracováno</th>
                                    <th>Základ</th>
                                    <th>Provize</th>
                                    <th>Položky</th>
                                    <th>Odměna</th>
                                    <th>Srážky</th>
                                    <th>Sazba</th>
                                </tr>
                            </thead>
                            <tbody>
                                {prumerDetail.mesice.map((pm) => (
                                    <tr key={`${pm.rok}-${pm.mesic}`}>
                                        <td>{monthShortLabel(pm.mesic, pm.rok)}</td>
                                        <td>
                                            {formatNumber(pm.odpracovano_h)} h
                                            {pm.odpracovano_h_smeny != null && pm.hodiny_rozdil_h
                                                ? ` (směny ${formatNumber(pm.odpracovano_h_smeny)})`
                                                : ''}
                                        </td>
                                        <td>{formatPoints(pm.zaklad_body ?? pm.fixni_body)}</td>
                                        <td>{formatPoints(pm.provize_body || 0)}</td>
                                        <td>{formatPoints(pm.pol_dok_odmena_body || 0)}</td>
                                        <td>{formatPoints(pm.odmena_mesic_body || 0)}</td>
                                        <td>
                                            {pm.penalizace_srazka_body > 0
                                                ? `−${formatPoints(pm.penalizace_srazka_body)}`
                                                : '—'}
                                        </td>
                                        <td>{formatPoints(pm.sazba_h)}/h</td>
                                    </tr>
                                ))}
                            </tbody>
                            <tfoot>
                                <tr>
                                    <td>Celkem / průměr</td>
                                    <td>{formatNumber(prumerDetail.celkem_h)} h</td>
                                    <td>{formatPoints(prumerDetail.celkem_fixni)}</td>
                                    <td>{formatPoints(prumerDetail.celkem_provize || 0)}</td>
                                    <td>{formatPoints(prumerDetail.celkem_pol_dok || 0)}</td>
                                    <td>{formatPoints(prumerDetail.celkem_odmena || 0)}</td>
                                    <td>
                                        {prumerDetail.celkem_penalizace > 0
                                            ? `−${formatPoints(prumerDetail.celkem_penalizace)}`
                                            : '—'}
                                    </td>
                                    <td>
                                        <strong>{formatPoints(prumerDetail.prumer_h ?? row.prumer_dovolena_h)}/h</strong>
                                    </td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                );
            }
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
                        + Penalizace
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
                Základ = (základ + doplňky z profilu) × odpracované hodiny do fondu / fond.
                Přesčas = stejná sazba × hodiny nad fondem. Dýška = obrat P63615 (1 bod = 1 Kč).
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
                    Dobropisy a skladové výdejky
                    {(dobropisyTotals.polozky > 0 || vydejkyTotals.doklady > 0) && (
                        <span className="dobropisy-badge">
                            {dobropisyTotals.polozky > 0 && (
                                <span>{dobropisyTotals.polozky} dobropisů</span>
                            )}
                            {dobropisyTotals.polozky > 0 && vydejkyTotals.doklady > 0 && ' · '}
                            {vydejkyTotals.doklady > 0 && (
                                <span>{vydejkyTotals.doklady} výdejek</span>
                            )}
                        </span>
                    )}
                </button>
                {dobropisyOpen && (
                    <div className="payroll-dobropisy-body">
                        <p className="payroll-dobropisy-hint">
                            Přehled dobropisů a skladových výdejek podle osoby. Rozkliknutím uvidíte jednotlivé doklady.
                            {' '}Dobropisy = vratky z pokladny. Výdejky = ruční / spotřeba / reklamace ze skladu.
                            {' '}Pouze informativní – bez dopadu na body výplaty.
                        </p>
                        {(dobropisyPairingTotals.zrcadlo + dobropisyPairingTotals.par + dobropisyPairingTotals.bez_paru > 0
                            || returnsGrandTotals.rucni + returnsGrandTotals.spotreba + returnsGrandTotals.reklamace > 0) && (
                            <div className="payroll-dobropisy-chips">
                                {dobropisyPairingTotals.zrcadlo + dobropisyPairingTotals.par + dobropisyPairingTotals.bez_paru > 0 && (
                                    <>
                                        <span className="pairing-chip pairing-chip--mirror">
                                            Zrcadlo: {dobropisyPairingTotals.zrcadlo}
                                        </span>
                                        <span className="pairing-chip pairing-chip--par">
                                            Jiný prodej: {dobropisyPairingTotals.par}
                                        </span>
                                        <span className="pairing-chip pairing-chip--none">
                                            Bez páru: {dobropisyPairingTotals.bez_paru}
                                        </span>
                                    </>
                                )}
                                {returnsGrandTotals.rucni > 0 && (
                                    <span className="pairing-chip">Ruční: {returnsGrandTotals.rucni}</span>
                                )}
                                {returnsGrandTotals.spotreba > 0 && (
                                    <span className="pairing-chip">Spotřeba: {returnsGrandTotals.spotreba}</span>
                                )}
                                {returnsGrandTotals.reklamace > 0 && (
                                    <span className="pairing-chip">Reklamace: {returnsGrandTotals.reklamace}</span>
                                )}
                            </div>
                        )}
                        {returnsLoading && (
                            <p className="payroll-loading-inline">Načítám přehled…</p>
                        )}
                        {(dobropisyError || vydejkyError) && (
                            <div className="error-message">{dobropisyError || vydejkyError}</div>
                        )}
                        {!returnsLoading && !dobropisyError && !vydejkyError && !returnsHasData && (
                            <p className="payroll-dobropisy-empty">V tomto měsíci žádné.</p>
                        )}
                        {!returnsLoading && returnsHasData && returnsPersonGroups.length > 0 && (
                            <div className="payroll-dobropisy-summary-wrap">
                                <table className="payroll-dobropisy-table payroll-dobropisy-summary payroll-returns-person-table">
                                    <thead>
                                        <tr>
                                            <th aria-label="Rozbalit" />
                                            <th>Osoba</th>
                                            <th>Dobropisy</th>
                                            <th>Ruční</th>
                                            <th>Spotřeba</th>
                                            <th>Reklamace</th>
                                            <th>Hodnota celkem</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {returnsPersonGroups.map((group) => (
                                            <React.Fragment key={group.key}>
                                                <tr
                                                    className={`returns-person-row${returnsExpandedPerson[group.key] ? ' returns-person-row--open' : ''}`}
                                                >
                                                    <td>
                                                        <button
                                                            type="button"
                                                            className="vydejka-expand-btn"
                                                            onClick={() => toggleReturnsPerson(group.key)}
                                                            aria-expanded={Boolean(returnsExpandedPerson[group.key])}
                                                            aria-label={`Rozbalit ${group.name}`}
                                                        >
                                                            {returnsExpandedPerson[group.key] ? '▼' : '▶'}
                                                        </button>
                                                    </td>
                                                    <td>
                                                        <button
                                                            type="button"
                                                            className="returns-person-name"
                                                            onClick={() => toggleReturnsPerson(group.key)}
                                                        >
                                                            {group.name}
                                                        </button>
                                                    </td>
                                                    <td>{group.counts.dobropisy || '—'}</td>
                                                    <td>{group.counts.rucni || '—'}</td>
                                                    <td>{group.counts.spotreba || '—'}</td>
                                                    <td>{group.counts.reklamace || '—'}</td>
                                                    <td className="col-negative">
                                                        {group.castky.celkem
                                                            ? `${formatNumber(group.castky.celkem)} Kč`
                                                            : '—'}
                                                    </td>
                                                </tr>
                                                {returnsExpandedPerson[group.key] && (
                                                    <tr className="returns-person-detail-row">
                                                        <td colSpan={7}>
                                                            <div className="returns-person-detail">
                                                                {group.dobropisy.length > 0 && (
                                                                    <div className="returns-person-detail-section">
                                                                        <h4 className="returns-person-detail-title">
                                                                            Dobropisy ({group.dobropisy.length})
                                                                        </h4>
                                                                        <div className="payroll-dobropisy-table-wrap">
                                                                            <table className="payroll-dobropisy-table">
                                                                                <thead>
                                                                                    <tr>
                                                                                        <th>Typ</th>
                                                                                        <th>Datum</th>
                                                                                        <th>Doklad</th>
                                                                                        <th>Kód</th>
                                                                                        <th>Název</th>
                                                                                        <th>Původní doklad</th>
                                                                                        <th>Po prodeji</th>
                                                                                        <th>Částka</th>
                                                                                    </tr>
                                                                                </thead>
                                                                                <tbody>
                                                                                    {group.dobropisy.map((row, idx) => (
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
                                                                                            <td>
                                                                                                <SymplioDocLink
                                                                                                    doklad={row.doklad}
                                                                                                    url={row.symplio_doklad_url}
                                                                                                />
                                                                                            </td>
                                                                                            <td><code>{row.kod}</code></td>
                                                                                            <td className="col-nazev" title={row.nazev}>{row.nazev || '—'}</td>
                                                                                            <td>
                                                                                                <SymplioDocLink
                                                                                                    doklad={row.puvodni_doklad}
                                                                                                    url={row.symplio_puvodni_doklad_url}
                                                                                                />
                                                                                            </td>
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
                                                                    </div>
                                                                )}
                                                                {group.vydejkyAll.length > 0 && (
                                                                    <div className="returns-person-detail-section">
                                                                        <h4 className="returns-person-detail-title">
                                                                            Skladové výdejky ({group.vydejkyAll.length})
                                                                        </h4>
                                                                        <div className="vydejka-spravce-detail">
                                                                            {group.vydejkyAll.map((doc) => (
                                                                                <div key={doc.doklad} className="vydejka-doklad-block">
                                                                                    <button
                                                                                        type="button"
                                                                                        className="vydejka-doklad-header"
                                                                                        onClick={() => toggleVydejkaExpanded(doc.doklad)}
                                                                                        aria-expanded={Boolean(vydejkyExpanded[doc.doklad])}
                                                                                    >
                                                                                        <span className="vydejka-doklad-header__toggle">
                                                                                            {vydejkyExpanded[doc.doklad] ? '▼' : '▶'}
                                                                                        </span>
                                                                                        <span className="vydejka-doklad-header__meta">
                                                                                            <SymplioDocLink
                                                                                                doklad={doc.doklad}
                                                                                                url={doc.symplio_doklad_url}
                                                                                                className="symplio-doc-link symplio-doc-link--code"
                                                                                                label={<code>{doc.doklad}</code>}
                                                                                            />
                                                                                            <span>{doc.datum}</span>
                                                                                            <span className="vydejka-duvod-label">{doc.duvod_kategorie_label}</span>
                                                                                            {doc.vazba && (
                                                                                                <span className="vydejka-vazba-hint">
                                                                                                    vazba{' '}
                                                                                                    <SymplioDocLink
                                                                                                        doklad={doc.vazba}
                                                                                                        url={doc.symplio_vazba_url}
                                                                                                    />
                                                                                                </span>
                                                                                            )}
                                                                                        </span>
                                                                                        <span className="vydejka-doklad-header__castka col-negative">
                                                                                            {formatNumber(doc.castka_s_dph)} Kč
                                                                                        </span>
                                                                                        <span className="vydejka-doklad-header__count">
                                                                                            {(doc.polozky || []).length} pol.
                                                                                        </span>
                                                                                    </button>
                                                                                    {vydejkyExpanded[doc.doklad] && (
                                                                                        <div className="payroll-dobropisy-table-wrap vydejka-polozky-wrap">
                                                                                            {(doc.polozky || []).length > 0 ? (
                                                                                                <table className="payroll-dobropisy-table payroll-vydejky-polozky-flat">
                                                                                                    <thead>
                                                                                                        <tr>
                                                                                                            <th>Kód</th>
                                                                                                            <th>Název</th>
                                                                                                            <th>Kusy</th>
                                                                                                            <th>Cena/ks</th>
                                                                                                            <th>Částka</th>
                                                                                                        </tr>
                                                                                                    </thead>
                                                                                                    <tbody>
                                                                                                        {doc.polozky.map((p, idx) => (
                                                                                                            <tr key={`${doc.doklad}-${p.kod}-${idx}`}>
                                                                                                                <td><code>{p.kod}</code></td>
                                                                                                                <td className="col-nazev" title={p.nazev}>{p.nazev || '—'}</td>
                                                                                                                <td>{p.kusy}</td>
                                                                                                                <td>
                                                                                                                    {p.cena_ks_bez_dph != null
                                                                                                                        ? `${formatNumber(p.cena_ks_bez_dph)} Kč`
                                                                                                                        : '—'}
                                                                                                                </td>
                                                                                                                <td className="col-negative">
                                                                                                                    {p.castka != null
                                                                                                                        ? `${formatNumber(p.castka)} Kč`
                                                                                                                        : '—'}
                                                                                                                </td>
                                                                                                            </tr>
                                                                                                        ))}
                                                                                                    </tbody>
                                                                                                </table>
                                                                                            ) : (
                                                                                                <p className="vydejka-polozky-empty">
                                                                                                    Žádné položky v importu
                                                                                                    <span className="vydejka-duvod-detail" title={doc.duvod_vyskladneni}>
                                                                                                        {' '}({doc.duvod_vyskladneni})
                                                                                                    </span>
                                                                                                </p>
                                                                                            )}
                                                                                        </div>
                                                                                    )}
                                                                                </div>
                                                                            ))}
                                                                        </div>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        </td>
                                                    </tr>
                                                )}
                                            </React.Fragment>
                                        ))}
                                    </tbody>
                                    <tfoot>
                                        <tr>
                                            <td />
                                            <td className="tfoot-label">Celkem</td>
                                            <td>{returnsGrandTotals.dobropisy || '—'}</td>
                                            <td>{returnsGrandTotals.rucni || '—'}</td>
                                            <td>{returnsGrandTotals.spotreba || '—'}</td>
                                            <td>{returnsGrandTotals.reklamace || '—'}</td>
                                            <td className="col-negative">
                                                <strong>{formatNumber(returnsGrandTotals.castka)} Kč</strong>
                                            </td>
                                        </tr>
                                    </tfoot>
                                </table>
                            </div>
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
                                        <td>
                                            {formatPoints(row.provize_body)}
                                            {Number(row.penalizace_srazka_body) > 0 && (
                                                <span
                                                    className="payroll-srazka-hint"
                                                    title={row.penalizace_popis || 'Srážka z provize'}
                                                >
                                                    {' '}
                                                    (−{formatPoints(row.penalizace_srazka_body)})
                                                </span>
                                            )}
                                        </td>
                                        <td className="col-celkem"><strong>{formatPoints(row.celkem_body)}</strong></td>
                                    </tr>
                                    {isOpen && (
                                        <tr className="detail-row">
                                            <td colSpan={6}>
                                                <div className="payroll-detail-full">
                                    {renderBrigadnikSouhrn(row)}
                                    {renderMzdaSouhrn(row)}
                                    {row.dovolena_smeny_h > 0 && row.dovolena_smeny_h !== row.dovolena_h && (
                                        <p className="payroll-detail-hint">
                                            Směny dovolené ve výpisu: {formatNumber(row.dovolena_smeny_h)} h
                                            {' '}(proplácen deficit fondu {formatNumber(row.dovolena_h)} h
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
                    title="Penalizace z provize"
                    onClose={closePenalizaceModal}
                    size="md"
                    onSubmit={savePenalizace}
                    formRef={penalizaceFormRef}
                    footer={(
                        <>
                            <button type="button" className="btn-cancel" onClick={closePenalizaceModal}>
                                Zrušit
                            </button>
                            <button type="submit" className="btn-submit" disabled={savingPenalizace}>
                                {savingPenalizace ? 'Ukládám…' : 'Uložit penalizace'}
                            </button>
                        </>
                    )}
                >
                        <p className="modal-hint">
                            Procenta se sčítají z hrubé provize (max. 100 %). Fixní body se odečtou
                            po procentech. Základ, cestovné a bonusy se nemění. Měsíc: {formatMonthName(month)}.
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
                            {existingPenalizaceForForm.length > 0 && (
                                <div className="payroll-penalizace-existing">
                                    <strong>Už zadané srážky za {formatMonthName(month)}</strong>
                                    <ul>
                                        {existingPenalizaceForForm.map((p) => (
                                            <li key={p.id}>
                                                {formatPenalizaceLabel(p)}
                                                {p.vytvoreno ? (
                                                    <span className="payroll-penalizace-meta">
                                                        {' '}· {new Date(p.vytvoreno).toLocaleString('cs-CZ')}
                                                    </span>
                                                ) : null}
                                            </li>
                                        ))}
                                    </ul>
                                    {existingPenalizaceRow && Number(existingPenalizaceRow.penalizace_srazka_body) > 0 && (
                                        <p className="payroll-penalizace-sum">
                                            Celkem srážka: −{formatPoints(existingPenalizaceRow.penalizace_srazka_body)}
                                            {Number(existingPenalizaceRow.provize_body_brutto) > 0
                                                ? ` z ${formatPoints(existingPenalizaceRow.provize_body_brutto)} hrubé provize`
                                                : ''}
                                        </p>
                                    )}
                                </div>
                            )}
                            <div className="payroll-penalizace-polozky">
                                {penalizaceForm.polozky.map((polozka, index) => (
                                    <div key={index} className="payroll-penalizace-polozka">
                                        <div className="payroll-penalizace-polozka-head">
                                            <strong>Penalizace {index + 1}</strong>
                                            {penalizaceForm.polozky.length > 1 && (
                                                <button
                                                    type="button"
                                                    className="payroll-penalizace-remove"
                                                    onClick={() => setPenalizaceForm((f) => ({
                                                        ...f,
                                                        polozky: f.polozky.filter((_, i) => i !== index),
                                                    }))}
                                                >
                                                    Odebrat
                                                </button>
                                            )}
                                        </div>
                                        <label>
                                            Typ srážky
                                            <select
                                                value={polozka.typ}
                                                onChange={(e) => {
                                                    const typ = e.target.value;
                                                    setPenalizaceForm((f) => ({
                                                        ...f,
                                                        polozky: f.polozky.map((p, i) => (
                                                            i === index
                                                                ? {
                                                                    ...p,
                                                                    typ,
                                                                    hodnota: typ === 'procenta' ? '10' : p.hodnota,
                                                                }
                                                                : p
                                                        )),
                                                    }));
                                                }}
                                            >
                                                <option value="procenta">Procenta z provize</option>
                                                <option value="fixni">Fixní body</option>
                                            </select>
                                        </label>
                                        <label>
                                            {polozka.typ === 'fixni' ? 'Body' : 'Procenta'}
                                            <input
                                                type="number"
                                                className={manualNumberInputClass()}
                                                min="0.01"
                                                max={polozka.typ === 'procenta' ? '100' : undefined}
                                                step={polozka.typ === 'procenta' ? '1' : '1'}
                                                value={polozka.hodnota}
                                                onChange={(e) => setPenalizaceForm((f) => ({
                                                    ...f,
                                                    polozky: f.polozky.map((p, i) => (
                                                        i === index ? { ...p, hodnota: e.target.value } : p
                                                    )),
                                                }))}
                                                onWheel={preventNumberInputWheel}
                                                required
                                            />
                                        </label>
                                        <label>
                                            Důvod
                                            <input
                                                type="text"
                                                value={polozka.duvod}
                                                onChange={(e) => setPenalizaceForm((f) => ({
                                                    ...f,
                                                    polozky: f.polozky.map((p, i) => (
                                                        i === index ? { ...p, duvod: e.target.value } : p
                                                    )),
                                                }))}
                                                required
                                            />
                                        </label>
                                    </div>
                                ))}
                            </div>
                            <button
                                type="button"
                                className="payroll-penalizace-add"
                                onClick={() => setPenalizaceForm((f) => ({
                                    ...f,
                                    polozky: [...f.polozky, { ...EMPTY_PENALIZACE_POLOZKA }],
                                }))}
                            >
                                + Další penalizace
                            </button>
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
