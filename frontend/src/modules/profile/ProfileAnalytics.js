import React, { useState, useEffect, useCallback } from 'react';
import { getApiEndpoints } from '../../config/apiConfig';
import { AnalyticsDateInput } from '../../components/AnalyticsDateRange';
import {
    PRODUCT_COMMISSIONS,
    CT300_INFO_KEY,
    CT300_INFO_LABEL,
} from '../../constants/productCommissions';
import './ProfileAnalytics.css';

const SERVIS_RATE = 0.1;

const buildBreakdownFromData = (data) => {
    if (!data) return null;
    const breakdown = {};
    const ct300Count = data[CT300_INFO_KEY] || 0;
    breakdown[CT300_INFO_KEY] = { count: ct300Count, points: 0, informational: true };
    PRODUCT_COMMISSIONS.forEach(({ key, rate }) => {
        const count = data[key] || 0;
        breakdown[key] = { count, points: count * rate };
    });
    const marze = data.servisni_prace?.marze ?? 0;
    const servisPoints = data.servisni_prace?.odmena != null
        ? Math.round(data.servisni_prace.odmena)
        : Math.round(marze * SERVIS_RATE);
    breakdown.servis_marze = {
        marze,
        points: servisPoints,
        odmena_sazba: data.servisni_prace?.odmena_sazba ?? 10,
    };
    return breakdown;
};

const sumProductPoints = (breakdown) => {
    if (!breakdown) return 0;
    let total = 0;
    PRODUCT_COMMISSIONS.forEach(({ key }) => {
        if (breakdown[key]?.informational) return;
        total += breakdown[key]?.points || 0;
    });
    total += breakdown.servis_marze?.points || 0;
    return total;
};

const formatMonthLabel = (isoDate) => {
    const [y, m] = isoDate.split('-');
    return `${m}/${y}`;
};

const ProfileAnalytics = ({ userId }) => {
    const [selectedDate, setSelectedDate] = useState('');
    const [todayData, setTodayData] = useState(null);
    const [monthlyData, setMonthlyData] = useState(null);
    const [todayPoints, setTodayPoints] = useState(null);
    const [monthlyPoints, setMonthlyPoints] = useState(null);
    const [highlightDates, setHighlightDates] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const dateQuery = selectedDate ? `&date=${selectedDate}` : '';

    const loadPeriodData = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const endpoints = getApiEndpoints();
            const base = `user_id=${userId}${dateQuery}`;
            const [dailyRes, monthlyRes, dailyPtsRes, monthlyPtsRes] = await Promise.all([
                fetch(`${endpoints.salespersonToday}?${base}`, { credentials: 'include' }),
                fetch(`${endpoints.salespersonMonthly}?${base}`, { credentials: 'include' }),
                fetch(`${endpoints.salespersonPointsToday}?${base}`, { credentials: 'include' }),
                fetch(`${endpoints.salespersonPointsMonthly}?${base}`, { credentials: 'include' }),
            ]);

            if (dailyRes.ok) setTodayData(await dailyRes.json());
            else setError('Chyba při načítání denních dat');

            if (monthlyRes.ok) setMonthlyData(await monthlyRes.json());
            else setError('Chyba při načítání měsíčních dat');

            if (dailyPtsRes.ok) setTodayPoints(await dailyPtsRes.json());
            if (monthlyPtsRes.ok) setMonthlyPoints(await monthlyPtsRes.json());
        } catch {
            setError('Chyba při komunikaci se serverem');
        } finally {
            setLoading(false);
        }
    }, [userId, dateQuery]);

    const loadActiveDates = useCallback(async (yearMonth) => {
        const endpoints = getApiEndpoints();
        if (!endpoints.salespersonActiveDates) return;
        const month = yearMonth || new Date().toISOString().slice(0, 7);
        try {
            const res = await fetch(
                `${endpoints.salespersonActiveDates}?user_id=${userId}&month=${month}`,
                { credentials: 'include' },
            );
            if (res.ok) {
                const data = await res.json();
                setHighlightDates(data.dates || []);
            }
        } catch {
            /* podbarvení je doplňkové */
        }
    }, [userId]);

    useEffect(() => {
        loadPeriodData();
    }, [loadPeriodData]);

    useEffect(() => {
        loadActiveDates();
    }, [loadActiveDates]);

    const formatDate = (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('cs-CZ');
    };

    const formatNumber = (num) => {
        if (num === null || num === undefined) return '0';
        return new Intl.NumberFormat('cs-CZ', { maximumFractionDigits: 0 }).format(Math.round(num));
    };

    const formatCalculation = (count, rate, points) => {
        const c = count || 0;
        const p = points ?? c * rate;
        return `${c}×${rate} = ${formatNumber(p)}`;
    };

    const formatServisCalculation = (breakdown) => {
        const marze = breakdown?.marze ?? 0;
        const points = breakdown?.points ?? Math.round(marze * SERVIS_RATE);
        return `${formatNumber(marze)} × 0,1 = ${formatNumber(points)}`;
    };

    const resolvePointsContext = (data, pointsPayload) => {
        const pointsOk = pointsPayload && pointsPayload.source !== 'error' && !pointsPayload.error;
        const breakdown = (pointsOk && pointsPayload.breakdown)
            ? pointsPayload.breakdown
            : buildBreakdownFromData(data);
        const totalPoints = pointsOk && pointsPayload.total_points != null
            ? pointsPayload.total_points
            : sumProductPoints(breakdown);
        return { breakdown, totalPoints };
    };

    const dailyTitle = selectedDate
        ? `Denní výsledky – ${formatDate(selectedDate)}`
        : 'Dnešní výsledky';
    const monthlyTitle = selectedDate
        ? `Měsíční výsledky – ${formatMonthLabel(selectedDate)}`
        : 'Měsíční výsledky';

    const renderDataCard = (title, data, pointsPayload = null) => {
        if (!data || data.source === 'none') {
            return (
                <div className="data-card no-data">
                    <h3>{title}</h3>
                    <p>Pro toto období nejsou k dispozici žádná data</p>
                </div>
            );
        }

        const { breakdown, totalPoints } = resolvePointsContext(data, pointsPayload);

        return (
            <div className="data-card">
                <div className="card-header">
                    <h3>{title}</h3>
                    <div className="card-date">
                        {formatDate(data.date || data.timestamp || new Date())}
                    </div>
                </div>

                <div className="card-content">
                    <div className="metrics-summary metrics-summary-body">
                        <div className="metric-item metric-item-body">
                            <div className="metric-value">{formatNumber(totalPoints)}</div>
                            <div className="metric-label">Body</div>
                        </div>
                    </div>

                    <div className="metrics-summary metrics-summary-classic">
                        <div className="metric-item">
                            <div className="metric-value">{data.polozky_nad_100 || 0}</div>
                            <div className="metric-label">Položky nad 100 Kč</div>
                        </div>
                        <div className="metric-item">
                            <div className="metric-value">{data.sluzby_celkem || 0}</div>
                            <div className="metric-label">Služby celkem</div>
                        </div>
                        <div className="metric-item">
                            <div className="metric-value">{(data.prumer_polozek_uctu ?? data.pol_dok ?? 0).toFixed(2)}</div>
                            <div className="metric-label">Průměr pol./účtu</div>
                        </div>
                    </div>

                    <div className="products-grid">
                        <div className="products-list products-list-calculations">
                            {(() => {
                                const ct300Item = breakdown?.[CT300_INFO_KEY];
                                const ct300Count = ct300Item?.count ?? data[CT300_INFO_KEY] ?? 0;
                                if (ct300Count > 0) {
                                    return (
                                        <div key={CT300_INFO_KEY} className="product-item product-item-info">
                                            <span>{CT300_INFO_LABEL}:</span>
                                            <span className="product-calc">{ct300Count} ks (bez bodů)</span>
                                        </div>
                                    );
                                }
                                return null;
                            })()}
                            {PRODUCT_COMMISSIONS.map(({ key, label, rate }) => {
                                const item = breakdown?.[key];
                                if (item?.informational) return null;
                                const count = item?.count ?? data[key] ?? 0;
                                const points = item?.points ?? count * rate;
                                return (
                                    <div key={key} className="product-item">
                                        <span>{label}:</span>
                                        <span className="product-calc">
                                            {formatCalculation(count, rate, points)}
                                        </span>
                                    </div>
                                );
                            })}
                            <div className="product-item product-item-servis">
                                <span>Servis:</span>
                                <span className="product-calc product-calc-servis">
                                    {formatServisCalculation(breakdown?.servis_marze)}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="data-source">
                    <small>Zdroj: {data.source === 'database' ? 'Databáze' : 'Google Sheets'}</small>
                </div>
            </div>
        );
    };

    return (
        <div className="profile-analytics">
            <div className="analytics-header">
                <h2>Moje výsledky</h2>
                <p>Přehled vašich prodejních výsledků a bodového hodnocení</p>
            </div>

            {error && (
                <div className="error-message">
                    {error}
                </div>
            )}

            <div className="analytics-controls">
                <AnalyticsDateInput
                    id="date-select"
                    label="Vyberte datum:"
                    value={selectedDate}
                    onApply={setSelectedDate}
                    wrapperClassName="date-picker"
                    showError={false}
                    highlightDates={highlightDates}
                    onMonthChange={loadActiveDates}
                />
                {selectedDate && (
                    <p className="date-picker-hint">
                        Zobrazen den {formatDate(selectedDate)} a měsíc {formatMonthLabel(selectedDate)}
                    </p>
                )}
            </div>

            {loading && <div className="loading analytics-loading">Načítání výsledků…</div>}

            <div className="analytics-grid">
                {renderDataCard(dailyTitle, todayData, todayPoints)}
                {renderDataCard(monthlyTitle, monthlyData, monthlyPoints)}
            </div>
        </div>
    );
};

export default ProfileAnalytics;
