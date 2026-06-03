import React, { useState, useEffect, useCallback } from 'react';
import { getApiEndpoints } from '../../config/apiConfig';
import { AnalyticsDateInput } from '../../components/AnalyticsDateRange';
import { useSalespersonMetrics } from '../../hooks/useSalespersonMetrics';
import {
    PRODUCT_COMMISSIONS,
    CT300_INFO_KEY,
    CT300_INFO_LABEL,
} from '../../constants/productCommissions';
import { VICEPRACE_LABEL, formatVicepraceObrat } from '../../constants/viceprace';
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
    total += breakdown.vykupy?.points || 0;
    total += breakdown.servis_marze?.points || 0;
    return total;
};

const formatMonthLabel = (isoDate) => {
    const [y, m] = isoDate.split('-');
    return `${m}/${y}`;
};

const ProfileAnalytics = ({ userId }) => {
    const [selectedDate, setSelectedDate] = useState('');
    const [highlightDates, setHighlightDates] = useState([]);
    const {
        today: todayData,
        month: monthlyData,
        todayPoints,
        monthPoints: monthlyPoints,
        loading,
        error,
    } = useSalespersonMetrics(userId, { date: selectedDate, enabled: !!userId });

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

        const ct300Count = breakdown?.[CT300_INFO_KEY]?.count ?? data[CT300_INFO_KEY] ?? 0;

        const renderCommissionLine = ({ key, label, rate }) => {
            const item = breakdown?.[key];
            if (item?.informational) return null;
            const count = item?.count ?? data[key] ?? 0;
            const points = item?.points ?? count * rate;
            return (
                <div
                    key={key}
                    className={`product-item${count ? '' : ' product-item--zero'}`}
                >
                    <span>{label}</span>
                    <span className="product-calc">{formatCalculation(count, rate, points)}</span>
                </div>
            );
        };

        const polozkyCommission = PRODUCT_COMMISSIONS.find((p) => p.key === 'polozky_nad_100');
        const sunshineCommission = PRODUCT_COMMISSIONS.find((p) => p.key === 'sunshine');
        const vykupyCommission = PRODUCT_COMMISSIONS.find((p) => p.key === 'vykupy');
        const gridCommissions = PRODUCT_COMMISSIONS.filter(
            (p) => !['polozky_nad_100', 'sunshine', 'vykupy'].includes(p.key),
        );
        const sunshineRow = sunshineCommission ? renderCommissionLine(sunshineCommission) : null;
        const vykupyRow = vykupyCommission ? renderCommissionLine(vykupyCommission) : null;

        return (
            <div className="data-card data-card--compact">
                <div className="card-header card-header--compact">
                    <h3>{title}</h3>
                    <div className="metric-item-body metric-item-body--chip">
                        <span className="metric-value">{formatNumber(totalPoints)}</span>
                        <span className="metric-label">bodů</span>
                    </div>
                </div>

                <div className="card-content card-content--compact">
                    <div className="metrics-mini-grid">
                        <div className="metric-item metric-item--mini">
                            <span className="metric-value">{data.polozky_nad_100 || 0}</span>
                            <span className="metric-label">Nad 100 Kč</span>
                        </div>
                        <div className="metric-item metric-item--mini">
                            <span className="metric-value">{data.sluzby_celkem || 0}</span>
                            <span className="metric-label">Služby</span>
                        </div>
                        <div className="metric-item metric-item--mini">
                            <span className="metric-value">{formatVicepraceObrat(data.viceprace_obrat)}</span>
                            <span className="metric-label">{VICEPRACE_LABEL}</span>
                        </div>
                        <div className="metric-item metric-item--mini">
                            <span className="metric-value">{(data.prumer_polozek_uctu ?? data.pol_dok ?? 0).toFixed(2)}</span>
                            <span className="metric-label">Ø pol./účet</span>
                        </div>
                        <div className="metric-item metric-item--mini">
                            <span className="metric-value">{data.vykupy ?? 0}</span>
                            <span className="metric-label">Výkupy</span>
                        </div>
                    </div>

                    <div className="products-list products-list--compact products-list--aligned">
                        <div className="products-list__grid">
                            {polozkyCommission && renderCommissionLine(polozkyCommission)}
                            <div className={`product-item product-item-info${ct300Count ? '' : ' product-item--zero'}`}>
                                <span>{CT300_INFO_LABEL}</span>
                                <span className="product-calc">
                                    {formatCalculation(ct300Count, 0, 0)}
                                </span>
                            </div>
                            {gridCommissions.map((c) => renderCommissionLine(c)).filter(Boolean)}
                            {vykupyRow}
                        </div>
                        <div className="products-list-pre-servis">
                            {sunshineRow}
                            <div className={`product-item product-item-info${(data.viceprace_obrat || 0) > 0 ? '' : ' product-item--zero'}`}>
                                <span>{VICEPRACE_LABEL}</span>
                                <span className="product-calc">
                                    {(data.viceprace_obrat || 0) > 0
                                        ? `${formatVicepraceObrat(data.viceprace_obrat)} (0 b.)`
                                        : '0 (0 b.)'}
                                </span>
                            </div>
                        </div>
                        <div className="product-item product-item-servis">
                            <span>Servis</span>
                            <span className="product-calc product-calc-servis">
                                {formatServisCalculation(breakdown?.servis_marze)}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        );
    };

    const dataSource = todayData?.source || monthlyData?.source;

    return (
        <div className="profile-analytics profile-analytics--fit">
            {error && (
                <div className="error-message">
                    {error}
                </div>
            )}

            <div className="analytics-controls analytics-controls--compact">
                <AnalyticsDateInput
                    id="date-select"
                    label="Datum:"
                    value={selectedDate}
                    onApply={setSelectedDate}
                    wrapperClassName="date-picker date-picker--compact"
                    showError={false}
                    highlightDates={highlightDates}
                    onMonthChange={loadActiveDates}
                />
                {selectedDate && (
                    <span className="date-picker-hint">
                        Den {formatDate(selectedDate)} · měsíc {formatMonthLabel(selectedDate)}
                    </span>
                )}
                {loading && <span className="analytics-loading-inline">Načítám…</span>}
            </div>

            <div className="analytics-grid analytics-grid--fit">
                {renderDataCard(dailyTitle, todayData, todayPoints)}
                {renderDataCard(monthlyTitle, monthlyData, monthlyPoints)}
            </div>

            {dataSource && dataSource !== 'none' && (
                <p className="profile-analytics-source">
                    Zdroj: {dataSource === 'database' ? 'databáze' : 'Google Sheets'}
                </p>
            )}
        </div>
    );
};

export default ProfileAnalytics;
