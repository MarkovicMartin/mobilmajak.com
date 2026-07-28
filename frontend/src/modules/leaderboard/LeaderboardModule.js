import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';
import { getApiEndpoints } from '../../config/apiConfig';
import { leaderboardAPI } from '../../services/api';
import { withGatewayRetry } from '../../utils/apiErrorMessage';
import { PageHeader, SegmentControl } from '../../components/ui';
import PointsLeaderboard from './PointsLeaderboard';
import StoresLeaderboard from './StoresLeaderboard';
import './LeaderboardModule.css';

const LEADERBOARD_PERIOD_OPTIONS = [
    { id: 'month', label: 'Měsíční', icon: <i className="fas fa-calendar-alt" /> },
    { id: 'today', label: 'Dnešní žebříček', icon: <i className="fas fa-sun" /> },
    { id: 'stores', label: 'Prodejny', icon: <i className="fas fa-store" /> },
];

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

            const data = await withGatewayRetry(
                () => leaderboardAPI.fetch(url, config.params),
                { retries: 1, delayMs: 800 },
            );
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
            <PageHeader title="Žebříček" />

            {error && (
                <div className="error-message">
                    <span>⚠️ {error}</span>
                    <button type="button" onClick={() => setError(null)} className="close-btn">✕</button>
                </div>
            )}

            <SegmentControl
                className="leaderboard-period-bar"
                options={LEADERBOARD_PERIOD_OPTIONS}
                value={pointsSubTab}
                onChange={setPointsSubTab}
                ariaLabel="Období žebříčku"
            />

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
