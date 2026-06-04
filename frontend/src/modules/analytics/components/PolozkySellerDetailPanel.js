import React, { useEffect, useMemo, useState } from 'react';
import { POLOZKY_METRIC_GROUPS } from './PolozkyMetricPicker';
import PolozkySellerTimelineChart from './PolozkySellerTimelineChart';
import { formatChartRangeLabel } from '../sections/celkovaPeriodUtils';
import {
    buildPolozkyChartRange,
    CHART_PRESETS,
    COMPARE_OPTIONS,
    defaultCompareForPreset,
    TIMELINE_METRIC_KEYS,
} from '../sections/polozkyChartPresets';

const OVERVIEW_METRICS = [
    { key: 'polozky_nad_100', label: 'Položky nad 100 Kč' },
    { key: 'sluzby_celkem', label: 'Služby celkem' },
    { key: 'celkovy_obrat', label: 'Obrat s DPH' },
    { key: 'unikatni_doklady', label: 'Unikátní doklady' },
];

const metricLabel = (key) => {
    for (const g of POLOZKY_METRIC_GROUPS) {
        const m = g.metrics.find((x) => x.key === key);
        if (m) return m.label;
    }
    return key;
};

const buildMetricOptions = (visibleMetrics) => {
    const out = [];
    POLOZKY_METRIC_GROUPS.forEach((group) => {
        group.metrics.forEach((m) => {
            if (!TIMELINE_METRIC_KEYS.has(m.key)) return;
            if (visibleMetrics?.size && !visibleMetrics.has(m.key)) return;
            out.push(m);
        });
    });
    return out;
};

const PolozkySellerDetailPanel = ({
    seller,
    filters,
    visibleMetrics,
    staffUsers = [],
    onClose,
}) => {
    const [chartPreset, setChartPreset] = useState('year');
    const [comparePeriod, setComparePeriod] = useState('prev_year');
    const [overviewMetric, setOverviewMetric] = useState('polozky_nad_100');
    const [detailMetric, setDetailMetric] = useState(null);
    const [compareSellerId, setCompareSellerId] = useState('');

    const chartRange = useMemo(() => buildPolozkyChartRange(chartPreset), [chartPreset]);
    const metricOptions = useMemo(
        () => buildMetricOptions(visibleMetrics),
        [visibleMetrics],
    );

    const compareSeller = staffUsers.find((u) => String(u.id) === compareSellerId);
    const compareName = compareSeller
        ? `${compareSeller.jmeno || ''} ${compareSeller.prijmeni || ''}`.trim()
        : '';

    useEffect(() => {
        setComparePeriod(defaultCompareForPreset(chartPreset));
    }, [chartPreset]);

    useEffect(() => {
        if (!seller?.id_prodejce) return;
        setDetailMetric(null);
        setCompareSellerId('');
    }, [seller?.id_prodejce]);

    if (!seller?.id_prodejce) return null;

    const sellerCompareMode = Boolean(compareSellerId);

    return (
        <div className="polozky-seller-detail inline-detail-panel">
            <div className="inline-detail-header polozky-seller-detail__header">
                <div>
                    <h4>{seller.prodejce || `Prodejce ${seller.id_prodejce}`}</h4>
                    <span className="polozky-seller-detail__sub">
                        {seller.prodejna ? `${seller.prodejna} · ` : ''}
                        {formatChartRangeLabel(chartRange)}
                    </span>
                </div>
                <button type="button" className="refresh-btn polozky-seller-chart__close" onClick={onClose}>
                    Zavřít
                </button>
            </div>

            <div className="inline-detail-body polozky-seller-detail__body">
                <div className="polozky-seller-chart__controls">
                    <div className="polozky-seller-chart__control-group">
                        <span className="polozky-seller-chart__control-label">Období grafu</span>
                        <div className="polozky-seller-chart__btn-row">
                            {CHART_PRESETS.map((preset) => (
                                <button
                                    key={preset.id}
                                    type="button"
                                    className={`refresh-btn polozky-seller-chart__preset${chartPreset === preset.id ? ' polozky-seller-chart__preset--on' : ''}`}
                                    onClick={() => setChartPreset(preset.id)}
                                >
                                    {preset.label}
                                </button>
                            ))}
                        </div>
                    </div>
                    <div className="polozky-seller-chart__control-group">
                        <span className="polozky-seller-chart__control-label">Srovnat s prodejcem</span>
                        <select
                            className="polozky-seller-detail__compare-select"
                            value={compareSellerId}
                            onChange={(e) => setCompareSellerId(e.target.value)}
                        >
                            <option value="">— žádný —</option>
                            {staffUsers
                                .filter((u) => String(u.id) !== String(seller.id_prodejce))
                                .map((u) => (
                                    <option key={u.id} value={u.id}>
                                        {`${u.jmeno || ''} ${u.prijmeni || ''}`.trim() || `ID ${u.id}`}
                                    </option>
                                ))}
                        </select>
                    </div>
                    {!sellerCompareMode && (
                        <div className="polozky-seller-chart__control-group">
                            <span className="polozky-seller-chart__control-label">Srovnání v čase</span>
                            <div className="polozky-seller-chart__btn-row">
                                {COMPARE_OPTIONS.map((opt) => (
                                    <button
                                        key={opt.id}
                                        type="button"
                                        className={`refresh-btn polozky-seller-chart__preset${comparePeriod === opt.id ? ' polozky-seller-chart__preset--on' : ''}`}
                                        onClick={() => setComparePeriod(opt.id)}
                                    >
                                        {opt.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                <section className="polozky-seller-detail__section">
                    <h5 className="polozky-seller-detail__section-title">Celkový vývoj</h5>
                    <div className="polozky-seller-detail__overview-metrics">
                        {OVERVIEW_METRICS.map((m) => (
                            <button
                                key={m.key}
                                type="button"
                                className={`polozky-seller-detail__metric-btn${overviewMetric === m.key ? ' polozky-seller-detail__metric-btn--on' : ''}`}
                                onClick={() => setOverviewMetric(m.key)}
                            >
                                {m.label}
                            </button>
                        ))}
                    </div>
                    <PolozkySellerTimelineChart
                        primaryUserId={seller.id_prodejce}
                        primaryName={seller.prodejce}
                        secondaryUserId={sellerCompareMode ? compareSellerId : null}
                        secondaryName={compareName}
                        metric={overviewMetric}
                        chartRange={chartRange}
                        filters={filters}
                        comparePeriod={sellerCompareMode ? null : comparePeriod}
                    />
                </section>

                <section className="polozky-seller-detail__section">
                    <h5 className="polozky-seller-detail__section-title">Rozpad na metriky</h5>
                    <p className="polozky-chart-hint">
                        Klikněte na metriku ze sledovaných – zobrazí se její vývoj v čase.
                    </p>
                    <div className="polozky-seller-detail__metric-grid">
                        {metricOptions.map((m) => (
                            <button
                                key={m.key}
                                type="button"
                                className={`polozky-seller-detail__metric-chip${detailMetric === m.key ? ' polozky-seller-detail__metric-chip--on' : ''}`}
                                onClick={() => setDetailMetric(detailMetric === m.key ? null : m.key)}
                            >
                                {m.label}
                            </button>
                        ))}
                    </div>
                    {detailMetric && (
                        <div className="polozky-seller-detail__detail-chart">
                            <h6>{metricLabel(detailMetric)}</h6>
                            <PolozkySellerTimelineChart
                                primaryUserId={seller.id_prodejce}
                                primaryName={seller.prodejce}
                                secondaryUserId={sellerCompareMode ? compareSellerId : null}
                                secondaryName={compareName}
                                metric={detailMetric}
                                chartRange={chartRange}
                                filters={filters}
                                comparePeriod={sellerCompareMode ? null : comparePeriod}
                                compact
                            />
                        </div>
                    )}
                </section>
            </div>
        </div>
    );
};

export default PolozkySellerDetailPanel;
