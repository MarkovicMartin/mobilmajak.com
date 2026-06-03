import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';
import { getApiEndpoints } from '../../config/apiConfig';
import { leaderboardAPI } from '../../services/api';
import PointsLeaderboard from './PointsLeaderboard';
import StoresLeaderboard from './StoresLeaderboard';
import './LeaderboardModule.css';

/** Denní žebříček – častější obnova během směny */
const POLL_MS_TODAY = 60 * 1000;
/** Měsíční / prodejny – stejný interval jako objednávky */
const POLL_MS_MONTH_STORES = 120 * 1000;

const TAB_CONFIG = {
    month: {
        urlKey: 'leaderboardPoints',
        params: {},
        errorMsg: 'Chyba při načítání žebříčku bodů',
    },
    today: {
        urlKey: 'leaderboardPoints',
        params: { period: 'today' },
        errorMsg: 'Chyba při načítání denního žebříčku bodů',
    },
    stores: {
        urlKey: 'leaderboardStores',
        params: {},
        errorMsg: 'Chyba při načítání žebříčku prodejen',
    },
};

const LeaderboardModule = () => {
    const { user } = useAuth();
    const [pointsSubTab, setPointsSubTab] = useState('month');
    const [pointsData, setPointsData] = useState([]);
    const [pointsTodayData, setPointsTodayData] = useState([]);
    const [pointsTodayMeta, setPointsTodayMeta] = useState(null);
    const [pointsMonthMeta, setPointsMonthMeta] = useState(null);
    const [storesData, setStoresData] = useState([]);
    const [storesMeta, setStoresMeta] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [lastUpdated, setLastUpdated] = useState(null);

    const applyTabResult = useCallback((tab, rows, meta) => {
        if (tab === 'today') {
            setPointsTodayData(rows);
            setPointsTodayMeta(meta);
        } else if (tab === 'stores') {
            setStoresData(rows);
            setStoresMeta(meta);
        } else {
            setPointsData(rows);
            setPointsMonthMeta(meta);
        }
    }, []);

    const fetchTab = useCallback(async (tab, { silent = false } = {}) => {
        const config = TAB_CONFIG[tab];
        if (!config) return;

        if (!silent) setLoading(true);
        setError(null);

        try {
            const endpoints = getApiEndpoints();
            const url = endpoints[config.urlKey];
            if (!url) throw new Error('Endpoint pro žebříček není k dispozici');

            const data = await leaderboardAPI.fetch(url, config.params);
            if (!data.success) throw new Error(data.error || 'Neznámá chyba');

            applyTabResult(tab, data.data || [], data.meta || null);
            setLastUpdated(new Date());
        } catch (err) {
            if (!silent) setError(err.message || config.errorMsg);
            console.error(config.errorMsg, err);
        } finally {
            if (!silent) setLoading(false);
        }
    }, [applyTabResult]);

    const refreshActiveTab = useCallback(
        (opts = {}) => fetchTab(pointsSubTab, opts),
        [pointsSubTab, fetchTab],
    );

    useEffect(() => {
        refreshActiveTab();
    }, [refreshActiveTab]);

    useEffect(() => {
        const pollMs = pointsSubTab === 'today' ? POLL_MS_TODAY : POLL_MS_MONTH_STORES;
        const id = window.setInterval(() => refreshActiveTab({ silent: true }), pollMs);
        const onFocus = () => refreshActiveTab({ silent: true });
        const onVis = () => {
            if (document.visibilityState === 'visible') refreshActiveTab({ silent: true });
        };
        window.addEventListener('focus', onFocus);
        document.addEventListener('visibilitychange', onVis);
        return () => {
            clearInterval(id);
            window.removeEventListener('focus', onFocus);
            document.removeEventListener('visibilitychange', onVis);
        };
    }, [pointsSubTab, refreshActiveTab]);

    const lastUpdatedLabel = lastUpdated
        ? lastUpdated.toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' })
        : null;

    return (
        <div className="leaderboard-module">
            {error && (
                <div className="error-message">
                    <span>⚠️ {error}</span>
                    <button type="button" onClick={() => setError(null)} className="close-btn">✕</button>
                </div>
            )}

            <div className="leaderboard-period-bar" role="tablist" aria-label="Období žebříčku">
                <button
                    type="button"
                    role="tab"
                    aria-selected={pointsSubTab === 'month'}
                    className={`period-tab ${pointsSubTab === 'month' ? 'period-tab--expanded' : ''}`}
                    onClick={() => setPointsSubTab('month')}
                >
                    {pointsSubTab === 'month' ? (
                        <>
                            <span className="period-tab-icon" aria-hidden="true">
                                <i className="fas fa-calendar-alt" />
                            </span>
                            <span className="period-tab-title">Měsíční</span>
                        </>
                    ) : (
                        <span className="period-tab-label">Měsíční</span>
                    )}
                </button>
                <button
                    type="button"
                    role="tab"
                    aria-selected={pointsSubTab === 'today'}
                    className={`period-tab ${pointsSubTab === 'today' ? 'period-tab--expanded' : ''}`}
                    onClick={() => setPointsSubTab('today')}
                >
                    {pointsSubTab === 'today' ? (
                        <>
                            <span className="period-tab-icon" aria-hidden="true">
                                <i className="fas fa-sun" />
                            </span>
                            <span className="period-tab-title">Dnešní žebříček</span>
                        </>
                    ) : (
                        <span className="period-tab-label">Dnešní žebříček</span>
                    )}
                </button>
                <button
                    type="button"
                    role="tab"
                    aria-selected={pointsSubTab === 'stores'}
                    className={`period-tab ${pointsSubTab === 'stores' ? 'period-tab--expanded' : ''}`}
                    onClick={() => setPointsSubTab('stores')}
                >
                    {pointsSubTab === 'stores' ? (
                        <>
                            <span className="period-tab-icon" aria-hidden="true">
                                <i className="fas fa-store" />
                            </span>
                            <span className="period-tab-title">Prodejny</span>
                        </>
                    ) : (
                        <span className="period-tab-label">Prodejny</span>
                    )}
                </button>
            </div>

            {lastUpdatedLabel && (
                <p className="leaderboard-updated" aria-live="polite">
                    Aktualizováno v {lastUpdatedLabel}
                    <button
                        type="button"
                        className="leaderboard-updated-refresh"
                        onClick={() => refreshActiveTab()}
                        disabled={loading}
                        title="Obnovit žebříček"
                    >
                        ↻
                    </button>
                </p>
            )}

            <div className="leaderboard-content">
                {pointsSubTab === 'month' && (
                    <PointsLeaderboard
                        data={pointsData}
                        loading={loading}
                        currentUser={user}
                        period="month"
                        vicepraceLeader={pointsMonthMeta?.viceprace_leader}
                    />
                )}
                {pointsSubTab === 'today' && (
                    <PointsLeaderboard
                        data={pointsTodayData}
                        loading={loading}
                        currentUser={user}
                        period="day"
                        yesterdayBest={pointsTodayMeta?.yesterday_best}
                        vicepraceLeader={pointsTodayMeta?.viceprace_leader}
                    />
                )}
                {pointsSubTab === 'stores' && (
                    <StoresLeaderboard
                        data={storesData}
                        loading={loading}
                        vicepraceLeader={storesMeta?.viceprace_leader}
                    />
                )}
            </div>
        </div>
    );
};

export default LeaderboardModule;
