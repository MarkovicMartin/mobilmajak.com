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
import { coachingAPI } from '../../../services/api';
import { formatMonthKeyLabel } from '../../analytics/sections/celkovaPeriodUtils';

const COMPARE_LABELS = {
    prev_month: 'Předchozí měsíc',
    prev_quarter: 'Předchozí kvartál',
    prev_year: 'Předchozí rok',
    store_avg: 'Průměr prodejny',
    store_top: 'Top prodejce',
};

const METRIC_PARAMS = (mesic) => {
    const [rok, m] = mesic.split('-').map(Number);
    return { mesic, rok, mesic_cislo: m };
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
    return Number.isInteger(n) ? String(n) : n.toFixed(1);
};

const fetchTimeline = async (userId, metric, mesic, compare, kanal) => {
    const res = await coachingAPI.getSellerTimeline(userId, {
        ...METRIC_PARAMS(mesic),
        metrics: metric,
        compare: compare || undefined,
        kanal,
    });
    return res.metrics?.[metric] || [];
};

const mergeChartRows = (primaryPts, peerPts, primaryLabel, peerLabel, compareLabel) => {
    const byMonth = new Map();
    (primaryPts || []).forEach((pt) => {
        byMonth.set(pt.month, {
            month: pt.month,
            label: formatMonthKeyLabel(pt.month),
            primary: Number(pt.value) || 0,
            benchmark: pt.compare_value != null ? Number(pt.compare_value) : null,
            peer: null,
        });
    });
    (peerPts || []).forEach((pt) => {
        const row = byMonth.get(pt.month) || {
            month: pt.month,
            label: formatMonthKeyLabel(pt.month),
            primary: null,
            benchmark: null,
            peer: null,
        };
        row.peer = Number(pt.value) || 0;
        byMonth.set(pt.month, row);
    });
    return {
        data: [...byMonth.values()].sort((a, b) => a.month.localeCompare(b.month)),
        primaryLabel,
        peerLabel,
        compareLabel,
    };
};

const CoachingTimelineChart = ({
    userId,
    metric,
    mesic,
    compare,
    kanal = 'all',
    primaryLabel = 'Prodejce',
    peerUserId,
    peerLabel,
}) => {
    const [primaryPts, setPrimaryPts] = useState([]);
    const [peerPts, setPeerPts] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!userId || !metric) return;
        let cancelled = false;
        const load = async () => {
            setLoading(true);
            try {
                const [main, peer] = await Promise.all([
                    fetchTimeline(userId, metric, mesic, compare, kanal),
                    peerUserId
                        ? fetchTimeline(peerUserId, metric, mesic, null, kanal)
                        : Promise.resolve([]),
                ]);
                if (!cancelled) {
                    setPrimaryPts(main);
                    setPeerPts(peer);
                }
            } catch {
                if (!cancelled) {
                    setPrimaryPts([]);
                    setPeerPts([]);
                }
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        load();
        return () => { cancelled = true; };
    }, [userId, peerUserId, metric, mesic, compare, kanal]);

    const chart = useMemo(
        () => mergeChartRows(
            primaryPts,
            peerPts,
            primaryLabel,
            peerLabel,
            compare ? COMPARE_LABELS[compare] : null,
        ),
        [primaryPts, peerPts, primaryLabel, peerLabel, compare],
    );

    if (loading) return <p className="coaching-muted">Načítám graf…</p>;
    if (!chart.data.length) return <p className="coaching-muted">Žádná data pro graf</p>;

    return (
        <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chart.data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" fontSize={11} />
                <YAxis fontSize={11} />
                <Tooltip formatter={(v) => formatValue(metric, v)} />
                <Legend />
                <Line
                    type="monotone"
                    dataKey="primary"
                    name={chart.primaryLabel}
                    stroke="var(--accent, #2563eb)"
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                />
                {compare && (
                    <Line
                        type="monotone"
                        dataKey="benchmark"
                        name={chart.compareLabel}
                        stroke="#94a3b8"
                        strokeWidth={2}
                        strokeDasharray="4 4"
                        dot={false}
                        connectNulls
                    />
                )}
                {peerUserId && (
                    <Line
                        type="monotone"
                        dataKey="peer"
                        name={chart.peerLabel || 'Druhý prodejce'}
                        stroke="#ea580c"
                        strokeWidth={2}
                        dot={false}
                        connectNulls
                    />
                )}
            </LineChart>
        </ResponsiveContainer>
    );
};

export default CoachingTimelineChart;
