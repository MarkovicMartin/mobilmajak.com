import React, { useEffect, useMemo, useState } from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from 'recharts';
import { analyticsGet } from '../../../utils/analyticsRequest';
import {
    formatChartRangeLabel,
    formatMonthKeyLabel,
} from '../sections/celkovaPeriodUtils';
import {
    buildPolozkyChartRange,
    CHART_PRESETS,
    COMPARE_OPTIONS,
    defaultCompareForPreset,
} from '../sections/polozkyChartPresets';
import { POLOZKY_METRIC_GROUPS } from './PolozkyMetricPicker';

const COMPARE_LINE_LABELS = {
    prev_month: 'Předchozí měsíc',
    prev_quarter: 'Předchozí kvartál',
    prev_year: 'Předchozí rok',
};

const metricLabel = (key) => {
    for (const g of POLOZKY_METRIC_GROUPS) {
        const m = g.metrics.find((x) => x.key === key);
        if (m) return m.label;
    }
    return key;
};

const formatValue = (metric, v) => {
    const n = Number(v) || 0;
    if (metric === 'celkovy_obrat') {
        return new Intl.NumberFormat('cs-CZ', {
            style: 'currency',
            currency: 'CZK',
            maximumFractionDigits: 0,
        }).format(n);
    }
    return Number.isInteger(n) ? String(n) : n.toFixed(2);
};

const ChartTooltip = ({ active, payload, label, metric, compareMode }) => {
    if (!active || !payload?.length) return null;
    const row = payload[0]?.payload;
    return (
        <div className="polozky-chart-tooltip">
            <div className="polozky-chart-tooltip__title">{formatMonthKeyLabel(label)}</div>
            {payload.map((entry) => (
                <div key={entry.dataKey} style={{ color: entry.color }}>
                    {entry.name}: {formatValue(metric, entry.value)}
                </div>
            ))}
            {row?.compare_month && compareMode && (
                <div className="polozky-chart-tooltip__sub">
                    Srovnání: {formatMonthKeyLabel(row.compare_month)}
                </div>
            )}
        </div>
    );
};

const PolozkySellerChart = ({
    userId,
    sellerName,
    metric,
    filters,
    onClose,
}) => {
    const [chartPreset, setChartPreset] = useState('year');
    const [compareMode, setCompareMode] = useState('prev_year');
    const [points, setPoints] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const chartRange = useMemo(
        () => buildPolozkyChartRange(chartPreset),
        [chartPreset],
    );

    useEffect(() => {
        setCompareMode(defaultCompareForPreset(chartPreset));
    }, [chartPreset]);

    useEffect(() => {
        if (!userId) {
            setPoints([]);
            return;
        }
        const load = async () => {
            setLoading(true);
            setError(null);
            try {
                const p = new URLSearchParams();
                p.set('user_id', String(userId));
                p.set('metric', metric || 'polozky_nad_100');
                p.set('period', 'custom');
                p.set('start_date', chartRange.start_date);
                p.set('end_date', chartRange.end_date);
                if (compareMode) p.set('compare_period', compareMode);
                if (filters?.kanal) p.set('kanal', filters.kanal);
                if (filters?.prodejna_id) p.set('prodejna_id', filters.prodejna_id);
                if (filters?.segment) p.set('segment', filters.segment);
                const json = await analyticsGet('web-prodeje/polozky/timeline/', p);
                if (!json.success) throw new Error(json.error || 'Chyba');
                setPoints((json.points || []).map((pt) => ({
                    month: pt.month,
                    label: formatMonthKeyLabel(pt.month),
                    value: Number(pt.value) || 0,
                    compare_value: pt.compare_value != null ? Number(pt.compare_value) : null,
                    compare_month: pt.compare_month,
                })));
            } catch (e) {
                setError(e.message);
                setPoints([]);
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [userId, metric, chartRange.start_date, chartRange.end_date, compareMode, filters?.kanal, filters?.prodejna_id, filters?.segment]);

    const hasData = points.some(
        (pt) => pt.value > 0 || (pt.compare_value != null && pt.compare_value > 0),
    );
    const yMax = useMemo(() => {
        let max = 0;
        points.forEach((pt) => {
            max = Math.max(max, pt.value, pt.compare_value ?? 0);
        });
        return max > 0 ? Math.ceil(max * 1.1) : 10;
    }, [points]);

    if (!userId) {
        return <p className="polozky-chart-hint">Vyberte prodejce v přehledu (tlačítko Graf).</p>;
    }

    const compareLabel = COMPARE_LINE_LABELS[compareMode] || 'Srovnání';
    const currentLabel = 'Aktuální období';

    return (
        <div className="polozky-seller-chart">
            <div className="polozky-seller-chart__head">
                <div>
                    <h5>{sellerName || `Prodejce ${userId}`}</h5>
                    <span className="polozky-seller-chart__meta">
                        {metricLabel(metric)} · {formatChartRangeLabel(chartRange)}
                    </span>
                </div>
                {onClose && (
                    <button type="button" className="refresh-btn polozky-seller-chart__close" onClick={onClose}>
                        Zavřít
                    </button>
                )}
            </div>

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
                    <span className="polozky-seller-chart__control-label">Srovnání</span>
                    <div className="polozky-seller-chart__btn-row">
                        {COMPARE_OPTIONS.map((opt) => (
                            <button
                                key={opt.id}
                                type="button"
                                className={`refresh-btn polozky-seller-chart__preset${compareMode === opt.id ? ' polozky-seller-chart__preset--on' : ''}`}
                                onClick={() => setCompareMode(opt.id)}
                            >
                                {opt.label}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {loading && (
                <div className="polozky-seller-chart__plot polozky-seller-chart__plot--loading">
                    <div className="loading-spinner" />
                    <p>Načítám graf…</p>
                </div>
            )}
            {!loading && error && (
                <p className="celkova-cisla-error">{error}</p>
            )}
            {!loading && !error && !hasData && (
                <p className="polozky-chart-hint">Pro zvolené období nejsou žádná data.</p>
            )}
            {!loading && !error && hasData && (
                <div className="polozky-seller-chart__plot">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={points} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
                            <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
                            <XAxis
                                dataKey="label"
                                tick={{ fontSize: 11 }}
                                interval="preserveStartEnd"
                            />
                            <YAxis
                                tick={{ fontSize: 11 }}
                                domain={[0, yMax]}
                                allowDecimals={metric === 'celkovy_obrat'}
                            />
                            <Tooltip content={<ChartTooltip metric={metric} compareMode={compareMode} />} />
                            <Legend wrapperStyle={{ fontSize: 12 }} />
                            <Line
                                type="monotone"
                                dataKey="value"
                                name={currentLabel}
                                stroke="var(--brand-navy)"
                                strokeWidth={2}
                                dot={{ r: 3 }}
                                activeDot={{ r: 5 }}
                                connectNulls
                            />
                            {compareMode && (
                                <Line
                                    type="monotone"
                                    dataKey="compare_value"
                                    name={compareLabel}
                                    stroke="var(--chart-3)"
                                    strokeWidth={2}
                                    strokeDasharray="6 4"
                                    dot={{ r: 2 }}
                                    connectNulls
                                />
                            )}
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            )}
        </div>
    );
};

export default PolozkySellerChart;
