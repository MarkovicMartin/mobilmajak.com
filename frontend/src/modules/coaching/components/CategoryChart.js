import React, { useEffect, useState } from 'react';
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from 'recharts';
import { coachingAPI } from '../../../services/api';
import { formatMonthKeyLabel } from '../../analytics/sections/celkovaPeriodUtils';

const CategoryChart = ({ userId, kategorieKod, nazev, mesic, kanal = 'all' }) => {
    const [points, setPoints] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!userId || !kategorieKod) return;
        let cancelled = false;
        const load = async () => {
            setLoading(true);
            try {
                const [rok, m] = mesic.split('-').map(Number);
                const res = await coachingAPI.getSellerTimeline(userId, {
                    mesic,
                    rok,
                    mesic_cislo: m,
                    metrics: kategorieKod,
                    kanal,
                });
                if (!cancelled) setPoints(res.metrics?.[kategorieKod] || []);
            } catch {
                if (!cancelled) setPoints([]);
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        load();
        return () => { cancelled = true; };
    }, [userId, kategorieKod, mesic, kanal]);

    if (!kategorieKod) return null;
    const data = points.map((pt) => ({
        label: formatMonthKeyLabel(pt.month),
        value: Number(pt.value) || 0,
    }));

    return (
        <div className="coaching-category-chart">
            <h4>{nazev} – 12 měsíců</h4>
            {loading ? <p className="coaching-muted">Načítám…</p> : (
                <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="label" fontSize={11} />
                        <YAxis fontSize={11} />
                        <Tooltip />
                        <Bar dataKey="value" fill="var(--accent, #2563eb)" radius={[4, 4, 0, 0]} />
                    </BarChart>
                </ResponsiveContainer>
            )}
        </div>
    );
};

export default CategoryChart;
