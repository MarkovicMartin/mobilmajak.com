import { analyticsGet } from '../../../utils/analyticsRequest';
import React, { useState, useEffect, useMemo } from 'react';
import AnalyticsPeriodFilterPanel from '../../../components/analytics/AnalyticsPeriodFilterPanel';
import { computeQuickRange, detectQuickRangePreset } from '../../../utils/analyticsQuickRange';
import { PolozkyDeltaBadge } from '../components/PolozkyComparisonDelta';
import PolozkySellerDetailChips from '../components/PolozkySellerDetailChips';
import { formatFiltersPeriodLabel } from './celkovaPeriodUtils';
import { buildInitialPolozkyFilters, mergePolozkyScope } from './polozkyFilters';
import './SectionStyles.css';
import './Polozky.css';

const formatCurrency = (value) => {
    const n = Number(value) || 0;
    return new Intl.NumberFormat('cs-CZ', {
        style: 'currency',
        currency: 'CZK',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(Math.round(n));
};

const losPctProlepenost = (los, skla, sunshine) => {
    const l = Number(los) || 0;
    const zaklad = (Number(skla) || 0) + (Number(sunshine) || 0);
    if (zaklad <= 0) return null;
    return Math.round((100 * l) / zaklad);
};

const buildApiParams = (filters, visibleMetrics) => {
    const params = new URLSearchParams();
    Object.keys(filters).forEach((key) => {
        if (filters[key] != null && filters[key] !== '') params.append(key, filters[key]);
    });
    const hourly = ['odpracovane_hodiny', 'polozky_nad_100_za_hodinu', 'celkovy_obrat_za_hodinu'];
    if ([...visibleMetrics].some((m) => hourly.includes(m))) {
        params.set('include_hours', '1');
    }
    return params;
};

const findCompareRow = (compareData, id) =>
    (compareData || []).find((r) => r.id_prodejce === id);

const ProdejnyPolozkyView = ({
    isComparison = false,
    paneRole = 'single',
    filtersFromParent,
    scopeFilters,
    onFiltersChange,
    compareData = null,
    onSellerClick,
    visibleMetrics,
    compactDetail = false,
}) => {
    const [filters, setFilters] = useState(() => mergePolozkyScope(
        filtersFromParent || buildInitialPolozkyFilters(),
        scopeFilters,
    ));
    const [salesData, setSalesData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [lastUpdate, setLastUpdate] = useState(null);
    const [dateError, setDateError] = useState('');
    const [quickKey, setQuickKey] = useState(() =>
        detectQuickRangePreset(
            (filtersFromParent || buildInitialPolozkyFilters()).start_date,
            (filtersFromParent || buildInitialPolozkyFilters()).end_date,
        ),
    );

    const effectiveFilters = useMemo(
        () => mergePolozkyScope(filters, scopeFilters),
        [filters, scopeFilters],
    );

    useEffect(() => {
        if (filtersFromParent) {
            setFilters(mergePolozkyScope(filtersFromParent, scopeFilters));
        }
    }, [filtersFromParent, scopeFilters]);

    useEffect(() => {
        setFilters((prev) => mergePolozkyScope(prev, scopeFilters));
    }, [scopeFilters]);

    const updateFilters = (next) => {
        const merged = mergePolozkyScope(next, scopeFilters);
        setFilters(merged);
        onFiltersChange?.(merged);
    };

    const applyDateRange = ({ start_date, end_date, preset }) => {
        setDateError('');
        updateFilters({ ...filters, period: 'custom', start_date, end_date });
        setQuickKey(preset || detectQuickRangePreset(start_date, end_date));
    };

    const handlePeriodChange = ({ type, month }) => {
        if (type === 'custom') {
            handleFilterChange('period', 'custom');
            setQuickKey('custom');
            setDateError('');
        } else if (type === 'month') {
            updateFilters({
                ...filters,
                period: 'monthly_select',
                selected_month: month,
                start_date: '',
                end_date: '',
            });
            setDateError('');
        }
    };

    const handleQuickPreset = (id) => {
        const range = computeQuickRange(id);
        if (!range) return;
        applyDateRange({ ...range, preset: id });
    };

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const params = buildApiParams(effectiveFilters, visibleMetrics);
            const result = await analyticsGet('web-prodeje/polozky/', params);
            if (result.success && Array.isArray(result.data)) {
                setSalesData(result.data);
                setLastUpdate(result.lastUpdate || result.generated_at || new Date().toISOString());
            } else {
                throw new Error(result.error || 'Chyba při načítání dat');
            }
        } catch (err) {
            setError(err.message);
            setSalesData([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [effectiveFilters, visibleMetrics]);

    const handleFilterChange = (filterName, value) => {
        updateFilters({ ...filters, [filterName]: value });
    };

    const totalPolozky = salesData.reduce((sum, item) => sum + (item.polozky_nad_100 || 0), 0);
    const totalSluzby = salesData.reduce((sum, item) => sum + (item.sluzby_celkem || 0), 0);
    const totalObrat = salesData.reduce((sum, item) => sum + (item.celkovy_obrat || 0), 0);
    const totalAktivniDoklady = salesData.reduce((sum, item) => sum + (item.unikatni_doklady || 0), 0);
    const avgHodnotaUctenky = totalAktivniDoklady > 0
        ? formatCurrency(totalObrat / totalAktivniDoklady)
        : formatCurrency(0);
    const avgPolDok = salesData.length > 0
        ? (salesData.reduce((sum, item) => sum + (item.pol_dok || 0), 0) / salesData.length).toFixed(2)
        : 0;
    const aktivnichProdejcu = salesData.filter((item) => item.polozky_nad_100 > 0).length;
    const nejlepsiProdejce = salesData.reduce(
        (best, current) => ((current.polozky_nad_100 > (best.polozky_nad_100 || 0)) ? current : best),
        {},
    );
    const compareTotals = compareData ? {
        polozky_nad_100: compareData.reduce((s, i) => s + (i.polozky_nad_100 || 0), 0),
        sluzby_celkem: compareData.reduce((s, i) => s + (i.sluzby_celkem || 0), 0),
    } : null;

    const showMetric = (key) => visibleMetrics.has(key);

    return (
        <div className={`celkova-cisla-view polozky-view ${isComparison ? 'is-comparison' : ''} celkova-cisla-view--${paneRole}`}>
            {isComparison && (
                <div className="celkova-pane-title">
                    {paneRole === 'right' ? 'Srovnávací období' : 'Vybrané období'}
                    <span className="celkova-pane-title__range">
                        {formatFiltersPeriodLabel(effectiveFilters)}
                    </span>
                </div>
            )}

            <AnalyticsPeriodFilterPanel
                filters={filters}
                quickKey={quickKey}
                onPeriodChange={handlePeriodChange}
                onDateApply={(range) => applyDateRange({ ...range, preset: 'custom' })}
                onQuickPreset={handleQuickPreset}
                onRefresh={fetchData}
                onDateErrorChange={setDateError}
                loading={loading}
                dateError={dateError}
            />

            {loading && (
                <div className="celkova-cisla-loading">
                    <div className="loading-spinner" />
                    <p>Načítám data…</p>
                </div>
            )}
            {error && (
                <div className="celkova-cisla-error">
                    <h3>❌ Chyba při načítání dat</h3>
                    <p>{error}</p>
                    <button type="button" onClick={fetchData}>Zkusit znovu</button>
                </div>
            )}
            {lastUpdate && !loading && !error && (
                <div className="last-update">
                    <small>Poslední aktualizace: {new Date(lastUpdate).toLocaleString('cs-CZ')}</small>
                </div>
            )}

            <div className="section-content">
                {!isComparison && (
                <div className="stats-cards">
                    {showMetric('polozky_nad_100') && (
                        <div className="stat-card">
                            <h4>Celkem položek nad 100 Kč</h4>
                            <div className="stat-value">
                                {totalPolozky}
                                {compareTotals && (
                                    <PolozkyDeltaBadge
                                        left={compareTotals.polozky_nad_100}
                                        right={totalPolozky}
                                    />
                                )}
                            </div>
                            <div className="stat-change">Z {aktivnichProdejcu} aktivních prodejců</div>
                        </div>
                    )}
                    {showMetric('sluzby_celkem') && (
                        <div className="stat-card">
                            <h4>Z toho Služby</h4>
                            <div className="stat-value">
                                {totalSluzby}
                                {compareTotals && (
                                    <PolozkyDeltaBadge left={compareTotals.sluzby_celkem} right={totalSluzby} />
                                )}
                            </div>
                        </div>
                    )}
                    {showMetric('celkovy_obrat') && (
                        <div className="stat-card">
                            <h4>Průměrná hodnota účtenky</h4>
                            <div className="stat-value">{avgHodnotaUctenky}</div>
                            <div className="stat-change" title="Unikátní doklady = proxy obsluhy, ne počet zákazníků v provozu">
                                Obrat / aktivní účtenky
                            </div>
                        </div>
                    )}
                    {showMetric('pol_dok') && (
                        <div className="stat-card">
                            <h4>Průměr položek/účtenka</h4>
                            <div className="stat-value">{avgPolDok}</div>
                        </div>
                    )}
                    <div className="stat-card">
                        <h4>Nejlepší prodejce</h4>
                        <div className="stat-value">{nejlepsiProdejce.prodejce || 'N/A'}</div>
                        <div className="stat-change positive">{nejlepsiProdejce.polozky_nad_100 || 0} položek</div>
                    </div>
                </div>
                )}

                {isComparison && (
                    <div className="polozky-comparison-summary">
                        {showMetric('polozky_nad_100') && (
                            <div className="polozky-comparison-kpi">
                                <span className="polozky-comparison-kpi__label">Položky nad 100</span>
                                <span className="polozky-comparison-kpi__value">{totalPolozky}</span>
                                {compareTotals && (
                                    <PolozkyDeltaBadge
                                        left={compareTotals.polozky_nad_100}
                                        right={totalPolozky}
                                    />
                                )}
                            </div>
                        )}
                        {showMetric('sluzby_celkem') && (
                            <div className="polozky-comparison-kpi">
                                <span className="polozky-comparison-kpi__label">Služby</span>
                                <span className="polozky-comparison-kpi__value">{totalSluzby}</span>
                                {compareTotals && (
                                    <PolozkyDeltaBadge
                                        left={compareTotals.sluzby_celkem}
                                        right={totalSluzby}
                                    />
                                )}
                            </div>
                        )}
                        {showMetric('unikatni_doklady') && (
                            <div className="polozky-comparison-kpi">
                                <span className="polozky-comparison-kpi__label">Účtenky</span>
                                <span className="polozky-comparison-kpi__value">{totalAktivniDoklady}</span>
                            </div>
                        )}
                    </div>
                )}

                <div className="sellers-panel" aria-busy={loading}>
                    {salesData.length > 0 ? (
                        <div className={`sellers-cards${isComparison ? ' sellers-cards--comparison' : ''}`}>
                            {salesData.map((item, index) => {
                                const cmp = findCompareRow(compareData, item.id_prodejce);
                                return (
                                    <div
                                        key={item.id_prodejce || index}
                                        role="button"
                                        tabIndex={0}
                                        className="seller-card seller-card--clickable"
                                        onClick={() => onSellerClick?.(item)}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter' || e.key === ' ') {
                                                e.preventDefault();
                                                onSellerClick?.(item);
                                            }
                                        }}
                                    >
                                        <div className="seller-header">
                                            <div className="seller-info">
                                                <h5 className="seller-name">
                                                    {item.prodejce}
                                                    <span className="seller-card__open-hint">Výkony ›</span>
                                                </h5>
                                                <span className="seller-store">{item.prodejna}</span>
                                            </div>
                                            <span className="rank-number">#{index + 1}</span>
                                        </div>
                                        <div className="seller-main-metrics">
                                            {showMetric('polozky_nad_100') && (
                                                <div className="metric-item primary">
                                                    <span className="metric-label">Položky nad 100 Kč</span>
                                                    <span className="metric-value highlight-blue">
                                                        {item.polozky_nad_100 || 0}
                                                        {cmp && (
                                                            <PolozkyDeltaBadge
                                                                left={cmp.polozky_nad_100}
                                                                right={item.polozky_nad_100}
                                                            />
                                                        )}
                                                    </span>
                                                </div>
                                            )}
                                            {showMetric('sluzby_celkem') && (
                                                <div className="metric-item primary">
                                                    <span className="metric-label">Služby</span>
                                                    <span className="metric-value highlight-green">{item.sluzby_celkem || 0}</span>
                                                </div>
                                            )}
                                            {showMetric('unikatni_doklady') && (
                                                <div className="metric-item" title="Proxy obsluhy – ne počet zákazníků v provozu">
                                                    <span className="metric-label">Unikátní doklady</span>
                                                    <span className="metric-value">{item.unikatni_doklady || 0}</span>
                                                </div>
                                            )}
                                            {showMetric('odpracovane_hodiny') && (
                                                <div className="metric-item">
                                                    <span className="metric-label">Hodiny</span>
                                                    <span className="metric-value">
                                                        {item.odpracovane_hodiny ?? '—'}
                                                    </span>
                                                </div>
                                            )}
                                            {showMetric('polozky_nad_100_za_hodinu') && (
                                                <div className="metric-item">
                                                    <span className="metric-label">Položky/h</span>
                                                    <span className="metric-value">
                                                        {item.polozky_nad_100_za_hodinu ?? '—'}
                                                    </span>
                                                </div>
                                            )}
                                        </div>
                                        <PolozkySellerDetailChips
                                            item={item}
                                            losPctFn={losPctProlepenost}
                                            dense={compactDetail}
                                        />
                                    </div>
                                );
                            })}
                        </div>
                    ) : (
                        <div className="no-data">{loading ? 'Načítám data…' : 'Žádná data'}</div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ProdejnyPolozkyView;
