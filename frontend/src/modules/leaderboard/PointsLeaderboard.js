import React, { useEffect, useMemo, useState } from 'react';
import {
    VICEPRACE_LABEL,
    VICEPRACE_TOP_CARD_TITLE,
    formatVicepraceObrat,
} from '../../constants/viceprace';
import {
    METRIC_KEYS,
    METRICS,
    formatMetricValue,
    formatPrumerHodnotaUctenky,
    getOppositeMetric,
    isExpandableMetric,
    sortByMetric,
} from './leaderboardMetrics';
import './PointsLeaderboard.css';

const PointsLeaderboard = ({
    data,
    loading,
    currentUser,
    period = 'month',
    yesterdayBest = null,
    vicepraceLeader = null,
}) => {
    const [rankMetric, setRankMetric] = useState(METRIC_KEYS.TOTAL_POINTS);
    const [expandedMetric, setExpandedMetric] = useState(null);

    useEffect(() => {
        setRankMetric(METRIC_KEYS.TOTAL_POINTS);
        setExpandedMetric(null);
    }, [period]);

    const isDay = period === 'day';
    const periodLabel = isDay ? 'dnešek' : 'aktuální měsíc';
    const statCardLabel = isDay ? 'Body včera' : 'Skóre minulý měsíc';
    const tableShiftLabel = isDay ? 'Body minulou směnu' : 'Skóre minulý měsíc';
    const metricConfig = METRICS[rankMetric] || METRICS[METRIC_KEYS.TOTAL_POINTS];

    const getLastShiftPoints = (seller) =>
        isDay ? (seller.last_shift_points || 0) : (seller.last_month_points || 0);
    const getMonthComparePoints = (seller) => seller.last_month_points || 0;

    const sortedData = useMemo(
        () => (data?.length ? sortByMetric(data, rankMetric, isDay) : []),
        [data, rankMetric, isDay],
    );

    const handleMetricSelect = (metricKey) => {
        if (rankMetric === metricKey) {
            if (isExpandableMetric(metricKey)) {
                setExpandedMetric((prev) => (prev === metricKey ? null : metricKey));
            }
        } else {
            setRankMetric(metricKey);
            setExpandedMetric(null);
        }
    };

    if (loading) {
        return (
            <div className="loading-container">
                <div className="loading-spinner" />
                <p>Načítám žebříček...</p>
            </div>
        );
    }

    if (!data || data.length === 0) {
        return (
            <div className="no-data">
                <h3>📊 Žádná data k zobrazení</h3>
                <p>Pro {periodLabel} nejsou k dispozici žádná data o bodovém hodnocení.</p>
            </div>
        );
    }

    const topThree = sortedData.slice(0, 3);

    const topByMonthCompare = data.reduce(
        (best, seller) => (getMonthComparePoints(seller) > getMonthComparePoints(best) ? seller : best),
        data[0],
    );
    const statTopPoints = isDay
        ? (yesterdayBest?.points > 0 ? yesterdayBest.points : 0)
        : getMonthComparePoints(topByMonthCompare);
    const statTopName = isDay
        ? (yesterdayBest?.points > 0 ? yesterdayBest.prodejce : '—')
        : (statTopPoints > 0 ? topByMonthCompare?.prodejce : '—');

    const getCurrentUserPosition = () => {
        if (!currentUser) return null;
        const userIndex = sortedData.findIndex((seller) => seller.id === currentUser.id);
        return userIndex !== -1 ? userIndex + 1 : null;
    };

    const getMedalIcon = (position) => {
        switch (position) {
            case 1: return '🥇';
            case 2: return '🥈';
            case 3: return '🥉';
            default: return '🏅';
        }
    };

    const getPositionClass = (position) => {
        switch (position) {
            case 1: return 'winner';
            case 2: return 'second';
            case 3: return 'third';
            default: return '';
        }
    };

    const currentUserPosition = getCurrentUserPosition();
    const currentUserRow = sortedData.find((s) => s.id === currentUser?.id);

    const topVicepraceFromData = data.reduce(
        (best, seller) => ((seller.viceprace_obrat || 0) > (best?.viceprace_obrat || 0) ? seller : best),
        data[0],
    );
    const vicepraceTopObrat = (vicepraceLeader?.obrat ?? 0) > 0
        ? vicepraceLeader.obrat
        : (topVicepraceFromData?.viceprace_obrat || 0);
    const vicepraceTopName = (vicepraceLeader?.obrat ?? 0) > 0
        ? (vicepraceLeader.prodejce || '—')
        : (vicepraceTopObrat > 0 ? topVicepraceFromData?.prodejce : '—');

    const showBreakdown = expandedMetric === rankMetric && isExpandableMetric(rankMetric);
    const oppositeMetric = getOppositeMetric(rankMetric);

    const renderTopThreeBreakdown = (seller) => {
        if (!showBreakdown) return null;

        if (rankMetric === METRIC_KEYS.TOTAL_POINTS) {
            return (
                <div className="metric-breakdown">
                    <div className="breakdown-cell breakdown-servis">
                        <span className="breakdown-label">Servis</span>
                        <span className="breakdown-value">{(seller.servis_provize ?? 0).toLocaleString('cs-CZ')}</span>
                    </div>
                    <div className="breakdown-cell breakdown-viceprace">
                        <span className="breakdown-label">{VICEPRACE_LABEL}</span>
                        <span className="breakdown-value">{formatVicepraceObrat(seller.viceprace_obrat)}</span>
                    </div>
                </div>
            );
        }

        if (oppositeMetric) {
            return (
                <div className="breakdown-secondary">
                    <span className="breakdown-label">{METRICS[oppositeMetric].label}</span>
                    <span className="breakdown-value">{formatMetricValue(seller, oppositeMetric, isDay)}</span>
                </div>
            );
        }

        return null;
    };

    const renderSortableHeader = (metricKey, label) => (
        <th
            key={metricKey}
            className={`col-num sortable ${rankMetric === metricKey ? 'sort-active' : ''}`}
            onClick={() => handleMetricSelect(metricKey)}
            title={label}
        >
            {label}
            {rankMetric === metricKey && expandedMetric === metricKey && (
                <span className="sort-expand-hint"> ▾</span>
            )}
        </th>
    );

    const statCardClass = (metricKey) => {
        const classes = ['stat-card'];
        if (metricKey) {
            classes.push('clickable');
            if (rankMetric === metricKey) classes.push('active');
            if (expandedMetric === metricKey) classes.push('expanded');
        }
        return classes.join(' ');
    };

    return (
        <div className="points-leaderboard">
            <div className="leaderboard-stats">
                <button
                    type="button"
                    className={statCardClass(METRIC_KEYS.TOTAL_POINTS)}
                    onClick={() => handleMetricSelect(METRIC_KEYS.TOTAL_POINTS)}
                >
                    <h4 className="stat-card-title">🏆 Celkové body</h4>
                    <div className="stat-value">
                        {data.reduce((sum, seller) => sum + seller.total_points, 0).toLocaleString('cs-CZ')}
                    </div>
                </button>
                <button
                    type="button"
                    className={statCardClass(METRIC_KEYS.VICEPRACE)}
                    onClick={() => handleMetricSelect(METRIC_KEYS.VICEPRACE)}
                    title="Součet obratu víceprací P63615 (s DPH), nepočítá se do bodů"
                >
                    <h4 className="stat-card-title">🎁 {VICEPRACE_TOP_CARD_TITLE}</h4>
                    <div className="stat-value">{formatVicepraceObrat(vicepraceTopObrat)}</div>
                    <p className="stat-card-foot" title={vicepraceTopName}>{vicepraceTopName}</p>
                </button>
                <button
                    type="button"
                    className={statCardClass(METRIC_KEYS.LAST_PERIOD)}
                    onClick={() => handleMetricSelect(METRIC_KEYS.LAST_PERIOD)}
                >
                    <h4 className="stat-card-title">🎯 {statCardLabel}</h4>
                    <div className="stat-value">{statTopPoints.toLocaleString('cs-CZ')}</div>
                    <p className="stat-card-foot" title={statTopName}>{statTopName}</p>
                    {statTopPoints > 0 && (
                        <p className="stat-card-foot stat-card-foot-hint">
                            {isDay ? 'Nejlepší včera' : 'Nejlepší minulý měsíc'}
                        </p>
                    )}
                </button>
            </div>

            {topThree.length > 0 && (
                <div className="top-three-section">
                    <div className="top-three-cards">
                        {topThree.map((seller) => (
                            <div
                                key={seller.id}
                                className={`top-seller-card ${getPositionClass(seller.position)} ${currentUser?.id === seller.id ? 'current-user' : ''}`}
                            >
                                <div className="medal-position">
                                    <span className="medal">{getMedalIcon(seller.position)}</span>
                                    <span className="position-number">{seller.position}</span>
                                </div>

                                <div className="seller-info">
                                    <h4 title={seller.prodejce}>{seller.prodejce}</h4>
                                    <p className="store-name" title={seller.prodejna}>{seller.prodejna}</p>
                                </div>

                                <div className="score-section">
                                    <div className="total-score">
                                        {formatMetricValue(seller, rankMetric, isDay)}
                                    </div>
                                    <div className="score-label">{metricConfig.scoreLabel}</div>
                                </div>

                                {renderTopThreeBreakdown(seller)}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {sortedData.length > 0 && (
                <div className="leaderboard-table-section">
                    <h4>🏅 Kompletní žebříček</h4>
                    <div className="table-wrapper">
                        <table className="leaderboard-table">
                            <thead>
                                <tr>
                                    <th className="col-position">Poz.</th>
                                    <th className="col-seller">Prodejce</th>
                                    <th className="col-store">Prodejna</th>
                                    {renderSortableHeader(METRIC_KEYS.TOTAL_POINTS, 'Body')}
                                    {renderSortableHeader(METRIC_KEYS.SERVIS, 'Servis')}
                                    {renderSortableHeader(METRIC_KEYS.VICEPRACE, VICEPRACE_LABEL)}
                                    {renderSortableHeader(METRIC_KEYS.PRUMER_POLOZEK, 'Pol./účt.')}
                                    {renderSortableHeader(METRIC_KEYS.PRUMER_HODNOTA, 'Hodn. účt.')}
                                    {renderSortableHeader(
                                        METRIC_KEYS.LAST_PERIOD,
                                        isDay ? 'Min. směna' : 'Min. měsíc',
                                    )}
                                </tr>
                            </thead>
                            <tbody>
                                {sortedData.map((seller) => (
                                    <tr
                                        key={seller.id}
                                        className={currentUser?.id === seller.id ? 'current-user-row' : ''}
                                    >
                                        <td className="col-position">
                                            <span className="position-badge">
                                                {seller.position}.
                                            </span>
                                        </td>
                                        <td className="col-seller">
                                            <div className="seller-cell" title={seller.prodejce}>
                                                <strong>{seller.prodejce}</strong>
                                                {currentUser?.id === seller.id && (
                                                    <span className="you-badge">Vy</span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="col-store" title={seller.prodejna}>{seller.prodejna}</td>
                                        <td className={`col-num ${rankMetric === METRIC_KEYS.TOTAL_POINTS ? 'cell-active' : ''}`}>
                                            <span className="points-value">
                                                {seller.total_points.toLocaleString('cs-CZ')}
                                            </span>
                                        </td>
                                        <td className={`col-num ${rankMetric === METRIC_KEYS.SERVIS ? 'cell-active' : ''}`}>
                                            <span className="servis-value">
                                                {(seller.servis_provize ?? 0).toLocaleString('cs-CZ')}
                                            </span>
                                        </td>
                                        <td className={`col-num ${rankMetric === METRIC_KEYS.VICEPRACE ? 'cell-active' : ''}`}>
                                            {formatVicepraceObrat(seller.viceprace_obrat)}
                                        </td>
                                        <td className={`col-num ${rankMetric === METRIC_KEYS.PRUMER_POLOZEK ? 'cell-active' : ''}`}>
                                            {(seller.prumer_polozek_uctu ?? 0).toFixed(2)}
                                        </td>
                                        <td className={`col-num ${rankMetric === METRIC_KEYS.PRUMER_HODNOTA ? 'cell-active' : ''}`}>
                                            {formatPrumerHodnotaUctenky(seller.prumer_hodnota_uctenky)}
                                        </td>
                                        <td className={`col-num ${rankMetric === METRIC_KEYS.LAST_PERIOD ? 'cell-active' : ''}`}>
                                            <span className="score-highlight">
                                                {getLastShiftPoints(seller).toLocaleString('cs-CZ')}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {currentUserPosition && currentUserRow && (
                <div className="user-position-card">
                    <h4>📍 Vaše pozice</h4>
                    <div className="position-info">
                        <span className="position">{currentUserPosition}. místo</span>
                        <span className="points">
                            {formatMetricValue(currentUserRow, rankMetric, isDay)}
                            {(rankMetric === METRIC_KEYS.TOTAL_POINTS
                                || rankMetric === METRIC_KEYS.SERVIS
                                || rankMetric === METRIC_KEYS.LAST_PERIOD) ? ' bodů' : ''}
                        </span>
                        <span className="store">{currentUser.prodejna}</span>
                    </div>
                </div>
            )}

        </div>
    );
};

export default PointsLeaderboard;
