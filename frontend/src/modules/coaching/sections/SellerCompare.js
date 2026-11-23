import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DateRangePicker, Select } from '../../../components/ui';
import { coachingAPI } from '../../../services/api';
import CoachingTimelineChart from '../components/CoachingTimelineChart';
import CompareRateToggle from '../components/CompareRateToggle';
import CompareMetricsTable from '../components/CompareMetricsTable';

const ALL_METRICS = [
    { value: 'polozky_nad_100', label: 'Položky nad 100 Kč' },
    { value: 'sluzby_celkem', label: 'Služby' },
    { value: 'celkovy_obrat', label: 'Obrat' },
    { value: 'unikatni_doklady', label: 'Účtenky' },
    { value: 'odpracovane_hodiny', label: 'Odpracované hodiny' },
];

const USER_SAFE_METRIC_KEYS = new Set([
    'polozky_nad_100',
    'sluzby_celkem',
    'unikatni_doklady',
    'odpracovane_hodiny',
]);
const USER_SAFE_METRICS = ALL_METRICS.filter((m) => USER_SAFE_METRIC_KEYS.has(m.value));

const COMPARE_OPTS = [
    { value: '', label: 'Bez srovnání období' },
    { value: 'this_month', label: 'vs tento měsíc' },
    { value: 'prev_month', label: 'vs minulý měsíc' },
    { value: 'prev_quarter', label: 'vs minulý kvartál' },
    { value: 'prev_year', label: 'vs minulý rok' },
    { value: 'store_avg', label: 'vs průměr prodejny' },
    { value: 'store_top', label: 'vs top prodejce' },
];

const monthRange = (mesic) => {
    const [year, month] = String(mesic || '').split('-').map(Number);
    if (!year || !month) return { start_date: '', end_date: '' };
    const start = `${year}-${String(month).padStart(2, '0')}-01`;
    const last = new Date(year, month, 0).getDate();
    const end = `${year}-${String(month).padStart(2, '0')}-${String(last).padStart(2, '0')}`;
    return { start_date: start, end_date: end };
};

const formatCzDate = (iso) => {
    if (!iso) return '';
    const [year, month, day] = iso.split('-');
    if (!day) return iso;
    return `${Number(day)}. ${Number(month)}. ${year}`;
};

const sellerName = (u) => (u ? `${u.jmeno || ''} ${u.prijmeni || ''}`.trim() : '');

const optionLabel = (u) => {
    const name = sellerName(u);
    return u?.prodejna ? `${name} (${u.prodejna})` : name;
};

const SellerCompare = ({
    staffUsers = [],
    mesic,
    monthOptions = [],
    onMesicChange,
    lockedPrimaryId = '',
    lockedPrimaryName = '',
    userSafe = false,
}) => {
    const navigate = useNavigate();
    const metrics = userSafe ? USER_SAFE_METRICS : ALL_METRICS;
    const [primaryId, setPrimaryId] = useState(lockedPrimaryId ? String(lockedPrimaryId) : '');
    const [peerId, setPeerId] = useState('');
    const [metric, setMetric] = useState('polozky_nad_100');
    const [compare, setCompare] = useState('prev_year');
    const [range, setRange] = useState(() => monthRange(mesic));
    const [rateMode, setRateMode] = useState('total');
    const [compareData, setCompareData] = useState(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (lockedPrimaryId) setPrimaryId(String(lockedPrimaryId));
    }, [lockedPrimaryId]);

    useEffect(() => {
        setRange(monthRange(mesic));
    }, [mesic]);

    const primary = useMemo(
        () => staffUsers.find((u) => String(u.id) === String(primaryId)),
        [staffUsers, primaryId],
    );
    const peer = useMemo(
        () => staffUsers.find((u) => String(u.id) === String(peerId)),
        [staffUsers, peerId],
    );
    const primaryName = sellerName(primary) || lockedPrimaryName;
    const peerName = sellerName(peer);
    const chartPerHour = !userSafe && rateMode === 'per_hour' && metric !== 'odpracovane_hodiny';
    const tableRateMode = userSafe ? 'total' : rateMode;
    const showMonth = typeof onMesicChange === 'function' && monthOptions.length > 0;

    useEffect(() => {
        if (!primaryId || !peerId || peerId === primaryId) {
            setCompareData(null);
            return;
        }
        let cancelled = false;
        const load = async () => {
            setLoading(true);
            try {
                const [rok, m] = mesic.split('-').map(Number);
                const cmpRes = await coachingAPI.compareSellers({
                    user_a: primaryId,
                    user_b: peerId,
                    mesic,
                    rok,
                    mesic_cislo: m,
                    start_date: range.start_date || undefined,
                    end_date: range.end_date || undefined,
                });
                if (!cancelled) setCompareData(cmpRes);
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        load();
        return () => { cancelled = true; };
    }, [primaryId, peerId, mesic, range.start_date, range.end_date]);

    const primarySelectOptions = useMemo(
        () => [
            { value: '', label: 'Vyberte prodejce…' },
            ...staffUsers.map((u) => ({ value: String(u.id), label: optionLabel(u) })),
        ],
        [staffUsers],
    );
    const peerSelectOptions = useMemo(
        () => [
            { value: '', label: 'Jen jeden prodejce' },
            ...staffUsers
                .filter((u) => String(u.id) !== String(primaryId))
                .map((u) => ({ value: String(u.id), label: optionLabel(u) })),
        ],
        [staffUsers, primaryId],
    );
    const visibleMetriky = userSafe
        ? (compareData?.metriky || []).filter((row) => USER_SAFE_METRIC_KEYS.has(row.metric))
        : compareData?.metriky;
    const hoursRow = (compareData?.metriky || []).find((row) => row.metric === 'odpracovane_hodiny');
    const periodLabel = compareData?.obdobi?.od && compareData?.obdobi?.do
        ? `${formatCzDate(compareData.obdobi.od)} – ${formatCzDate(compareData.obdobi.do)}`
        : (range.start_date && range.end_date
            ? `${formatCzDate(range.start_date)} – ${formatCzDate(range.end_date)}`
            : mesic);
    const fmtHours = (value) => {
        if (value == null || value === '') return '—';
        const n = Number(value);
        if (Number.isNaN(n)) return '—';
        return n.toLocaleString('cs-CZ', { maximumFractionDigits: 1 });
    };

    return (
        <section className="coaching-panel coaching-analysis">
            {!userSafe && (
                <p className="coaching-analysis-hint">
                    Vyberte prodejce pro vývoj v čase. Druhého prodejce můžete přidat pro srovnání v grafu i tabulce.
                </p>
            )}

            <div className="coaching-chart-controls">
                {showMonth && (
                    <label className="coaching-nav-filter">
                        <span className="coaching-nav-filter-label">Měsíc</span>
                        <Select
                            options={monthOptions}
                            value={mesic}
                            onChange={onMesicChange}
                            aria-label="Měsíc"
                        />
                    </label>
                )}
                {!lockedPrimaryId && (
                    <label className="coaching-nav-filter">
                        <span className="coaching-nav-filter-label">Prodejce</span>
                        <Select
                            options={primarySelectOptions}
                            value={primaryId}
                            onChange={setPrimaryId}
                            aria-label="Prodejce"
                        />
                    </label>
                )}
                <label className="coaching-nav-filter">
                    <span className="coaching-nav-filter-label">Porovnat s</span>
                    <Select
                        options={peerSelectOptions}
                        value={peerId}
                        onChange={setPeerId}
                        aria-label="Porovnat s prodejcem"
                        className="coaching-compare-peer-select"
                    />
                </label>
                <label className="coaching-nav-filter">
                    <span className="coaching-nav-filter-label">Metrika</span>
                    <Select
                        options={metrics}
                        value={metric}
                        onChange={setMetric}
                        aria-label="Metrika grafu"
                    />
                </label>
                <label className="coaching-nav-filter">
                    <span className="coaching-nav-filter-label">Období</span>
                    <Select
                        options={COMPARE_OPTS}
                        value={compare}
                        onChange={setCompare}
                        aria-label="Srovnání období"
                    />
                </label>
                {!userSafe && (
                    <CompareRateToggle value={rateMode} onChange={setRateMode} />
                )}
                <label className="coaching-nav-filter">
                    <span className="coaching-nav-filter-label">Hodiny za období</span>
                    <DateRangePicker
                        startDate={range.start_date}
                        endDate={range.end_date}
                        onApply={setRange}
                    />
                </label>
            </div>

            {!primaryId && (
                <p className="coaching-muted">Začněte výběrem prodejce – zobrazí se graf vývoje za posledních 12 měsíců.</p>
            )}

            {primaryId && (
                <>
                    <div className="coaching-analysis-header">
                        <div>
                            <h3>{primaryName}</h3>
                            {peerId && peerName && (
                                <p className="coaching-muted">Srovnání s {peerName}</p>
                            )}
                        </div>
                        {!userSafe && (
                            <button
                                type="button"
                                className="coaching-link-btn"
                                onClick={() => navigate(`/coaching/seller/${primaryId}?mesic=${mesic}`)}
                            >
                                Otevřít detail →
                            </button>
                        )}
                    </div>

                    <CoachingTimelineChart
                        userId={primaryId}
                        peerUserId={userSafe ? undefined : (peerId || undefined)}
                        primaryLabel={primaryName}
                        peerLabel={peerName}
                        metric={metric}
                        mesic={mesic}
                        compare={compare || undefined}
                        perHour={chartPerHour}
                    />

                    {loading && peerId && <p className="coaching-muted">Načítám srovnání…</p>}

                    {hoursRow && peerId && (
                        <p className="coaching-hours-line">
                            Odpracované hodiny ({periodLabel}): {primaryName} {fmtHours(hoursRow.a)} h
                            {' · '}
                            {peerName} {fmtHours(hoursRow.b)} h
                        </p>
                    )}

                    {compareData && peerId && (
                        <CompareMetricsTable
                            metriky={visibleMetriky}
                            kategorie={compareData.kategorie}
                            nameA={primaryName}
                            nameB={peerName}
                            mesicLabel={periodLabel}
                            rateMode={tableRateMode}
                        />
                    )}
                </>
            )}
        </section>
    );
};

export default SellerCompare;
