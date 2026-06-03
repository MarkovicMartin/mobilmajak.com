import React, { useEffect, useMemo, useState } from 'react';
import {
    VICEPRACE_LABEL,
    VICEPRACE_TOP_CARD_TITLE,
    formatVicepraceObrat,
} from '../../constants/viceprace';
import {
    METRIC_KEYS,
    METRICS,
    STAT_CARD_META,
    formatMetricValue,
    formatPrumerHodnotaUctenky,
    getOppositeMetric,
    getTopByMetric,
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
    hideLastPeriodColumn = false,
    tableTitle = '🏅 Kompletní žebříček',
    sellerColumnLabel = 'Prodejce',
    hideStoreColumn = false,
    emptyTitle = '📊 Žádná data k zobrazení',
    emptyMessage = null,
}) => {
    const [rankMetric, setRankMetric] = useState(METRIC_KEYS.TOTAL_POINTS);
    const [expandedMetric, setExpandedMetric] = useState(null);

    useEffect(() => {
        setRankMetric(METRIC_KEYS.TOTAL_POINTS);
        setExpandedMetric(null);
    }, [period]);

    const isDay = period === 'day';
    const periodLabel = isDay ? 'dnešek' : 'aktuální měsíc';
    const defaultEmptyMessage = `Pro ${periodLabel} nejsou k dispozici žádná data o bodovém hodnocení.`;
    const tableShiftLabel = isDay ? 'Body minulou směnu' : 'Skóre minulý měsíc';
    const metricConfig = METRICS[rankMetric] || METRICS[METRIC_KEYS.TOTAL_POINTS];

    const getLastShiftPoints = (seller) =>
        isDay ? (seller.last_shift_points || 0) : (seller.last_month_points || 0);
    const getMonthComparePoints = (seller) => seller.last_month_points || 0;

    /** Měsíční: bez prodeje v aktuálním měsíci skrytí, dokud neřadíte podle minulého měsíce. */
    const tableData = useMemo(() => {
        if (!data?.length) return [];
        if (isDay || rankMetric === METRIC_KEYS.LAST_PERIOD) return data;
        return data.filter((s) => (s.total_points || 0) > 0);
    }, [data, isDay, rankMetric]);

    const sortedData = useMemo(
        () => (tableData.length ? sortByMetric(tableData, rankMetric, isDay) : []),
        [tableData, rankMetric, isDay],
    );

    const topByMonthCompare = useMemo(() => {
        if (!data?.length || isDay) return null;
        return data.reduce(
            (best, seller) => (
                getMonthComparePoints(seller) > getMonthComparePoints(best) ? seller : best
            ),
            data[0],
        );
    }, [data, isDay]);

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
                <h3>{emptyTitle}</h3>
                <p>{emptyMessage || defaultEmptyMessage}</p>
            </div>
        );
    }

    const topThree = sortedData.slice(0, 3);

    const statTopPoints = isDay
        ? (yesterdayBest?.points ?? 0)
        : (topByMonthCompare ? getMonthComparePoints(topByMonthCompare) : 0);
    const statTopName = isDay
        ? (yesterdayBest?.prodejce || '—')
        : (topByMonthCompare?.prodejce || '—');

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

    const showVykupy = !hideStoreColumn;
    const statCardKeys = (hideLastPeriodColumn
        ? [
            METRIC_KEYS.TOTAL_POINTS,
            METRIC_KEYS.SERVIS,
            ...(showVykupy ? [METRIC_KEYS.VYKUPY] : []),
            METRIC_KEYS.VICEPRACE,
            METRIC_KEYS.PRUMER_POLOZEK,
            METRIC_KEYS.PRUMER_HODNOTA,
        ]
        : [
            METRIC_KEYS.TOTAL_POINTS,
            METRIC_KEYS.SERVIS,
            ...(showVykupy ? [METRIC_KEYS.VYKUPY] : []),
            METRIC_KEYS.VICEPRACE,
            METRIC_KEYS.PRUMER_POLOZEK,
            METRIC_KEYS.PRUMER_HODNOTA,
            METRIC_KEYS.LAST_PERIOD,
        ]);

    const renderStatCardValue = (metricKey) => {
        if (metricKey === METRIC_KEYS.TOTAL_POINTS) {
            return data.reduce((sum, row) => sum + row.total_points, 0).toLocaleString('cs-CZ');
        }
        if (metricKey === METRIC_KEYS.VICEPRACE) {
            return formatVicepraceObrat(vicepraceTopObrat);
        }
        if (metricKey === METRIC_KEYS.LAST_PERIOD) {
            return statTopPoints.toLocaleString('cs-CZ');
        }
        const top = getTopByMetric(data, metricKey, isDay);
        if (!top.row || top.value <= 0) {
            return metricKey === METRIC_KEYS.PRUMER_HODNOTA ? '—' : '0';
        }
        return formatMetricValue(top.row, metricKey, isDay);
    };

    const renderStatCardFoot = (metricKey) => {
        if (metricKey === METRIC_KEYS.TOTAL_POINTS || STAT_CARD_META[metricKey]?.showSum) {
            return null;
        }
        if (metricKey === METRIC_KEYS.VICEPRACE) {
            return vicepraceTopObrat > 0 ? vicepraceTopName : null;
        }
        if (metricKey === METRIC_KEYS.LAST_PERIOD) {
            return statTopName !== '—' ? statTopName : null;
        }
        const top = getTopByMetric(data, metricKey, isDay);
        return top.value > 0 ? top.name : null;
    };

    const getStatCardTitle = (metricKey) => {
        const meta = STAT_CARD_META[metricKey];
        if (metricKey === METRIC_KEYS.VICEPRACE) {
            return `${meta?.icon || '🎁'} ${VICEPRACE_TOP_CARD_TITLE}`;
        }
        if (metricKey === METRIC_KEYS.LAST_PERIOD) {
            const title = isDay ? meta?.titleDay : meta?.titleMonth;
            return `${meta?.icon || '🎯'} ${title || METRICS[metricKey].label}`;
        }
        const title = meta?.title || METRICS[metricKey]?.label || '';
        return `${meta?.icon || ''} ${title}`.trim();
    };

    const statsGridClass = hideLastPeriodColumn
        ? 'leaderboard-stats leaderboard-stats--stores'
        : 'leaderboard-stats leaderboard-stats--full';

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
                    {showVykupy && (
                        <div className="breakdown-cell breakdown-vykupy">
                            <span className="breakdown-label">Výkupy</span>
                            <span className="breakdown-value">{seller.vykupy ?? 0}</span>
                        </div>
                    )}
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
            <div className={statsGridClass}>
                {statCardKeys.map((metricKey) => {
                    const foot = renderStatCardFoot(metricKey);
                    return (
                        <button
                            key={metricKey}
                            type="button"
                            className={statCardClass(metricKey)}
                            onClick={() => handleMetricSelect(metricKey)}
                            title={metricKey === METRIC_KEYS.VICEPRACE
                                ? 'Součet obratu víceprací P63615 (s DPH), nepočítá se do bodů'
                                : undefined}
                        >
                            <h4 className="stat-card-title">{getStatCardTitle(metricKey)}</h4>
                            <div className="stat-value">{renderStatCardValue(metricKey)}</div>
                            {foot && (
                                <p className="stat-card-foot stat-card-name" title={foot}>{foot}</p>
                            )}
                        </button>
                    );
                })}
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
                                </div>

                                <div className="seller-info">
                                    <h4 title={seller.prodejce}>{seller.prodejce}</h4>
                                    {!hideStoreColumn && (
                                        <p className="store-name" title={seller.prodejna}>{seller.prodejna}</p>
                                    )}
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

            {!isDay && sortedData.length === 0 && data.length > 0 && rankMetric !== METRIC_KEYS.LAST_PERIOD && (
                <p className="leaderboard-filter-hint">
                    V aktuálním měsíci zatím není evidovaný prodej. Pro srovnání podle minulého měsíce
                    (včetně všech prodejců) klikněte na kartu „Nejlepší skóre minulý měsíc“.
                </p>
            )}

            {sortedData.length > 0 && (
                <div className="leaderboard-table-section">
                    <h4>{tableTitle}</h4>
                    <div className="table-wrapper">
                        <table className="leaderboard-table">
                            <thead>
                                <tr>
                                    <th className="col-position">Poz.</th>
                                    <th className="col-seller">{sellerColumnLabel}</th>
                                    {!hideStoreColumn && <th className="col-store">Prodejna</th>}
                                    {renderSortableHeader(METRIC_KEYS.TOTAL_POINTS, 'Body')}
                                    {renderSortableHeader(METRIC_KEYS.SERVIS, 'Servis')}
                                    {showVykupy && renderSortableHeader(METRIC_KEYS.VYKUPY, 'Výkupy')}
                                    {renderSortableHeader(METRIC_KEYS.VICEPRACE, VICEPRACE_LABEL)}
                                    {renderSortableHeader(METRIC_KEYS.PRUMER_POLOZEK, 'Pol./účt.')}
                                    {renderSortableHeader(METRIC_KEYS.PRUMER_HODNOTA, 'Hodn. účt.')}
                                    {!hideLastPeriodColumn && renderSortableHeader(
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
                                            <span className="position-rank">{seller.position}.</span>
                                        </td>
                                        <td className="col-seller">
                                            <div className="seller-cell" title={seller.prodejce}>
                                                <strong>{seller.prodejce}</strong>
                                                {currentUser?.id === seller.id && (
                                                    <span className="you-badge">Vy</span>
                                                )}
                                            </div>
                                        </td>
                                        {!hideStoreColumn && (
                                            <td className="col-store" title={seller.prodejna}>{seller.prodejna}</td>
                                        )}
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
                                        {showVykupy && (
                                            <td className={`col-num ${rankMetric === METRIC_KEYS.VYKUPY ? 'cell-active' : ''}`}>
                                                {seller.vykupy ?? 0}
                                            </td>
                                        )}
                                        <td className={`col-num ${rankMetric === METRIC_KEYS.VICEPRACE ? 'cell-active' : ''}`}>
                                            {formatVicepraceObrat(seller.viceprace_obrat)}
                                        </td>
                                        <td className={`col-num ${rankMetric === METRIC_KEYS.PRUMER_POLOZEK ? 'cell-active' : ''}`}>
                                            {(seller.prumer_polozek_uctu ?? 0).toFixed(2)}
                                        </td>
                                        <td className={`col-num ${rankMetric === METRIC_KEYS.PRUMER_HODNOTA ? 'cell-active' : ''}`}>
                                            {formatPrumerHodnotaUctenky(seller.prumer_hodnota_uctenky)}
                                        </td>
                                        {!hideLastPeriodColumn && (
                                            <td className={`col-num ${rankMetric === METRIC_KEYS.LAST_PERIOD ? 'cell-active' : ''}`}>
                                                <span className="score-highlight">
                                                    {getLastShiftPoints(seller).toLocaleString('cs-CZ')}
                                                </span>
                                            </td>
                                        )}
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
                            {rankMetric === METRIC_KEYS.VYKUPY ? ' ks' : ''}
                        </span>
                        <span className="store">{currentUser.prodejna}</span>
                    </div>
                </div>
            )}

        </div>
    );
};

export default PointsLeaderboard;
