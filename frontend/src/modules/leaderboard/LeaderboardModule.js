import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { getApiEndpoints } from '../../config/apiConfig';
import PointsLeaderboard from './PointsLeaderboard';
import StoresLeaderboard from './StoresLeaderboard';
import './LeaderboardModule.css';

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

    useEffect(() => {
        if (pointsSubTab === 'today') {
            fetchPointsTodayLeaderboard();
        } else if (pointsSubTab === 'stores') {
            fetchStoresLeaderboard();
        } else {
            fetchPointsLeaderboard();
        }
    }, [pointsSubTab]);

    const fetchPointsLeaderboard = async () => {
        setLoading(true);
        setError(null);
        try {
            const endpoints = getApiEndpoints();
            const response = await fetch(endpoints.leaderboardPoints, {
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error('Chyba při načítání žebříčku bodů');
            }

            const data = await response.json();
            if (data.success) {
                setPointsData(data.data || []);
                setPointsMonthMeta(data.meta || null);
            } else {
                throw new Error(data.error || 'Neznámá chyba');
            }
        } catch (err) {
            setError(err.message);
            console.error('Chyba při načítání žebříčku bodů:', err);
        } finally {
            setLoading(false);
        }
    };

    const fetchPointsTodayLeaderboard = async () => {
        setLoading(true);
        setError(null);
        try {
            const endpoints = getApiEndpoints();
            if (!endpoints.leaderboardPoints) {
                throw new Error('Endpoint pro denní žebříček není k dispozici');
            }
            const url = `${endpoints.leaderboardPoints}?period=today`;
            const response = await fetch(url, {
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error('Chyba při načítání denního žebříčku bodů');
            }

            const data = await response.json();
            if (data.success) {
                setPointsTodayData(data.data || []);
                setPointsTodayMeta(data.meta || null);
            } else {
                throw new Error(data.error || 'Neznámá chyba');
            }
        } catch (err) {
            setError(err.message);
            console.error('Chyba při načítání denního žebříčku bodů:', err);
        } finally {
            setLoading(false);
        }
    };

    const fetchStoresLeaderboard = async () => {
        setLoading(true);
        setError(null);
        try {
            const endpoints = getApiEndpoints();
            const url = endpoints.leaderboardStores;
            if (!url) {
                throw new Error('Endpoint pro žebříček prodejen není k dispozici');
            }
            const response = await fetch(url, {
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error('Chyba při načítání žebříčku prodejen');
            }

            const data = await response.json();
            if (data.success) {
                setStoresData(data.data || []);
                setStoresMeta(data.meta || null);
            } else {
                throw new Error(data.error || 'Neznámá chyba');
            }
        } catch (err) {
            setError(err.message);
            console.error('Chyba při načítání žebříčku prodejen:', err);
        } finally {
            setLoading(false);
        }
    };

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
