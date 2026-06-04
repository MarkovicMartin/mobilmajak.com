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
import { formatMonthKeyLabel } from '../sections/celkovaPeriodUtils';

const COMPARE_LINE_LABELS = {
    prev_month: 'Předchozí měsíc',
    prev_quarter: 'Předchozí kvartál',
    prev_year: 'Předchozí rok',
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

const fetchTimeline = async (userId, metric, chartRange, filters, comparePeriod) => {
    const p = new URLSearchParams();
    p.set('user_id', String(userId));
    p.set('metric', metric);
    p.set('period', 'custom');
    p.set('start_date', chartRange.start_date);
    p.set('end_date', chartRange.end_date);
    if (comparePeriod) p.set('compare_period', comparePeriod);
    if (filters?.kanal) p.set('kanal', filters.kanal);
    if (filters?.prodejna_id) p.set('prodejna_id', filters.prodejna_id);
    if (filters?.segment) p.set('segment', filters.segment);
    const json = await analyticsGet('web-prodeje/polozky/timeline/', p);
    if (!json.success) throw new Error(json.error || 'Chyba');
    return json.points || [];
};

const mergeTwoSellers = (pointsA, pointsB) => {
    const byMonth = new Map();
    (pointsA || []).forEach((pt) => {
        byMonth.set(pt.month, {
            month: pt.month,
            label: formatMonthKeyLabel(pt.month),
            primary: Number(pt.value) || 0,
            secondary: null,
        });
    });
    (pointsB || []).forEach((pt) => {
        const row = byMonth.get(pt.month) || {
            month: pt.month,
            label: formatMonthKeyLabel(pt.month),
            primary: 0,
            secondary: null,
        };
        row.secondary = Number(pt.value) || 0;
        byMonth.set(pt.month, row);
    });
    return [...byMonth.values()].sort((a, b) => a.month.localeCompare(b.month));
};

const mergeTimeCompare = (points) => (points || []).map((pt) => ({
    month: pt.month,
    label: formatMonthKeyLabel(pt.month),
    primary: Number(pt.value) || 0,
    secondary: pt.compare_value != null ? Number(pt.compare_value) : null,
    compare_month: pt.compare_month,
}));

const ChartTooltip = ({ active, payload, label, metric, secondaryLabel }) => {
    if (!active || !payload?.length) return null;
    const row = payload[0]?.payload;
    return (
        <div className="polozky-chart-tooltip">
            <div className="polozky-chart-tooltip__title">{label}</div>
            {payload.map((entry) => (
                <div key={entry.dataKey} style={{ color: entry.color }}>
                    {entry.name}: {formatValue(metric, entry.value)}
                </div>
            ))}
            {row?.compare_month && secondaryLabel && (
                <div className="polozky-chart-tooltip__sub">
                    Srovnání: {formatMonthKeyLabel(row.compare_month)}
                </div>
            )}
        </div>
    );
};

/**
 * @param primaryUserId – hlavní prodejce
 * @param secondaryUserId – volitelný druhý prodejce (srovnání lidí)
 * @param comparePeriod – prev_month|prev_quarter|prev_year (jen bez secondaryUserId)
 */
const PolozkySellerTimelineChart = ({
    primaryUserId,
    primaryName,
    secondaryUserId = null,
    secondaryName = '',
    metric,
    chartRange,
    filters,
    comparePeriod = null,
    compact = false,
}) => {
    const [points, setPoints] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!primaryUserId || !metric) {
            setPoints([]);
            return;
        }
        const load = async () => {
            setLoading(true);
            setError(null);
            try {
                if (secondaryUserId) {
                    const [a, b] = await Promise.all([
                        fetchTimeline(primaryUserId, metric, chartRange, filters, null),
                        fetchTimeline(secondaryUserId, metric, chartRange, filters, null),
                    ]);
                    setPoints(mergeTwoSellers(a, b));
                } else {
                    const raw = await fetchTimeline(
                        primaryUserId,
                        metric,
                        chartRange,
                        filters,
                        comparePeriod,
                    );
                    setPoints(mergeTimeCompare(raw));
                }
            } catch (e) {
                setError(e.message);
                setPoints([]);
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [
        primaryUserId,
        secondaryUserId,
        metric,
        chartRange.start_date,
        chartRange.end_date,
        comparePeriod,
        filters?.kanal,
        filters?.prodejna_id,
        filters?.segment,
    ]);

    const hasData = points.some(
        (pt) => pt.primary > 0 || (pt.secondary != null && pt.secondary > 0),
    );

    const yMax = useMemo(() => {
        let max = 0;
        points.forEach((pt) => {
            max = Math.max(max, pt.primary, pt.secondary ?? 0);
        });
        return max > 0 ? Math.ceil(max * 1.1) : 10;
    }, [points]);

    const primaryLabel = primaryName || `Prodejce ${primaryUserId}`;
    const secondaryLabel = secondaryUserId
        ? (secondaryName || `Prodejce ${secondaryUserId}`)
        : (comparePeriod ? (COMPARE_LINE_LABELS[comparePeriod] || 'Srovnání') : null);

    if (loading) {
        return (
            <div className={`polozky-seller-chart__plot${compact ? ' polozky-seller-chart__plot--compact' : ''} polozky-seller-chart__plot--loading`}>
                <div className="loading-spinner" />
                <p>Načítám graf…</p>
            </div>
        );
    }
    if (error) return <p className="celkova-cisla-error">{error}</p>;
    if (!hasData) return <p className="polozky-chart-hint">Pro zvolené období nejsou žádná data.</p>;

    return (
        <div className={`polozky-seller-chart__plot${compact ? ' polozky-seller-chart__plot--compact' : ''}`}>
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={points} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
                    <XAxis dataKey="label" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                    <YAxis
                        tick={{ fontSize: 11 }}
                        domain={[0, yMax]}
                        allowDecimals={metric === 'celkovy_obrat'}
                    />
                    <Tooltip
                        content={(
                            <ChartTooltip
                                metric={metric}
                                secondaryLabel={secondaryLabel}
                            />
                        )}
                    />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Line
                        type="monotone"
                        dataKey="primary"
                        name={primaryLabel}
                        stroke="var(--brand-navy)"
                        strokeWidth={2}
                        dot={{ r: 3 }}
                        connectNulls
                    />
                    {secondaryLabel && (
                        <Line
                            type="monotone"
                            dataKey="secondary"
                            name={secondaryLabel}
                            stroke="var(--chart-3)"
                            strokeWidth={2}
                            strokeDasharray={secondaryUserId ? undefined : '6 4'}
                            dot={{ r: 2 }}
                            connectNulls
                        />
                    )}
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
};

export default PolozkySellerTimelineChart;
