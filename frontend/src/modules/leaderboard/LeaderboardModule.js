import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { getApiEndpoints } from '../../config/apiConfig';
import PointsLeaderboard from './PointsLeaderboard';
import AverageItemsLeaderboard from './AverageItemsLeaderboard';
import './LeaderboardModule.css';

const LeaderboardModule = () => {
    const { user } = useAuth();
    const [activeTab, setActiveTab] = useState('points');
    const [pointsData, setPointsData] = useState([]);
    const [averageItemsData, setAverageItemsData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (activeTab === 'points') {
            fetchPointsLeaderboard();
        } else {
            fetchAverageItemsLeaderboard();
        }
    }, [activeTab]);

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

    const fetchAverageItemsLeaderboard = async () => {
        setLoading(true);
        setError(null);
        try {
            const endpoints = getApiEndpoints();
            const response = await fetch(endpoints.leaderboardAverageItems, {
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error('Chyba při načítání žebříčku průměru položek');
            }

            const data = await response.json();
            if (data.success) {
                setAverageItemsData(data.data || []);
            } else {
                throw new Error(data.error || 'Neznámá chyba');
            }
        } catch (err) {
            setError(err.message);
            console.error('Chyba při načítání žebříčku průměru položek:', err);
        } finally {
            setLoading(false);
        }
    };

    const refreshData = () => {
        if (activeTab === 'points') {
            fetchPointsLeaderboard();
        } else {
            fetchAverageItemsLeaderboard();
        }
    };

    return (
        <div className="leaderboard-module">
            <div className="leaderboard-header">
                <h1>🏆 Žebříček prodejců</h1>
                <p>Nejlepší prodejci podle bodového hodnocení za aktuální měsíc</p>
            </div>

            {error && (
                <div className="error-message">
                    <span>⚠️ {error}</span>
                    <button onClick={() => setError(null)} className="close-btn">✕</button>
                </div>
            )}

            <div className="leaderboard-tabs">
                <button 
                    className={`tab-button ${activeTab === 'points' ? 'active' : ''}`}
                    onClick={() => setActiveTab('points')}
                >
                    <i className="fas fa-star"></i>
                    Žebříček bodů
                </button>
                <button 
                    className={`tab-button ${activeTab === 'average' ? 'active' : ''}`}
                    onClick={() => setActiveTab('average')}
                >
                    <i className="fas fa-chart-line"></i>
                    Průměr položek/účtenka
                </button>
                <button 
                    className="refresh-button"
                    onClick={refreshData}
                    disabled={loading}
                >
                    <i className={`fas fa-sync-alt ${loading ? 'fa-spin' : ''}`}></i>
                    Obnovit
                </button>
            </div>

            <div className="leaderboard-content">
                {activeTab === 'points' && (
                    <PointsLeaderboard 
                        data={pointsData} 
                        loading={loading}
                        currentUser={user}
                    />
                )}
                {activeTab === 'average' && (
                    <AverageItemsLeaderboard 
                        data={averageItemsData} 
                        loading={loading}
                        currentUser={user}
                    />
                )}
            </div>
        </div>
    );
};

export default LeaderboardModule; 