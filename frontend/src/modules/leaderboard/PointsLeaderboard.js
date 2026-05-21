import React from 'react';
import './PointsLeaderboard.css';

const PointsLeaderboard = ({ data, loading, currentUser, period = 'month' }) => {
    const isDay = period === 'day';
    const periodLabel = isDay ? 'dnešek' : 'aktuální měsíc';
    const compareLabel = isDay ? 'Body včera' : 'Skóre minulý měsíc';
    const getComparePoints = (seller) =>
        isDay ? (seller.yesterday_points || 0) : (seller.last_month_points || 0);
    if (loading) {
        return (
            <div className="loading-container">
                <div className="loading-spinner"></div>
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

    const topThree = data.slice(0, 3);
    const restOfList = data;

    /** Nejvyšší body v porovnávacím období (včera / minulý měsíc), ne lídr dnešního žebříčku. */
    const topByCompare = data.reduce(
        (best, seller) => (getComparePoints(seller) > getComparePoints(best) ? seller : best),
        data[0],
    );

    const getCurrentUserPosition = () => {
        if (!currentUser) return null;
        const userIndex = data.findIndex(seller => seller.id === currentUser.id);
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

    return (
        <div className="points-leaderboard">
            {/* Hlavní statistiky */}
            <div className="leaderboard-stats">
                <div className="stat-card">
                    <h4>🏆 Celkové body</h4>
                    <div className="stat-value">
                        {data.reduce((sum, seller) => sum + seller.total_points, 0).toLocaleString()}
                    </div>
                    <div className="stat-change">Všichni prodejci</div>
                </div>
                <div className="stat-card">
                    <h4>👥 Aktivní prodejci</h4>
                    <div className="stat-value">{data.length}</div>
                    <div className="stat-change">Za {periodLabel}</div>
                </div>
                <div className="stat-card">
                    <h4>📊 Průměr bodů</h4>
                    <div className="stat-value">
                        {Math.round(data.reduce((sum, seller) => sum + seller.total_points, 0) / data.length)}
                    </div>
                    <div className="stat-change">Na prodejce</div>
                </div>
                <div className="stat-card">
                    <h4>🎯 {compareLabel}</h4>
                    <div className="stat-value">{getComparePoints(topByCompare).toLocaleString()}</div>
                    <div className="stat-change">
                        {topByCompare?.prodejce || 'N/A'}
                        <span className="stat-change-hint">
                            {isDay ? ' · nejlepší včera' : ' · nejlepší minulý měsíc'}
                        </span>
                    </div>
                </div>
            </div>

            {/* TOP 3 prodejci - karty */}
            {topThree.length > 0 && (
                <div className="top-three-section">
                    <h3>🏆 Žebříček prodejců</h3>
                    <p>Nejlepší prodejci podle bodového hodnocení za {periodLabel}</p>
                    
                    <div className="top-three-cards">
                        {topThree.map((seller, index) => (
                            <div 
                                key={seller.id} 
                                className={`top-seller-card ${getPositionClass(seller.position)} ${currentUser?.id === seller.id ? 'current-user' : ''}`}
                            >
                                <div className="medal-position">
                                    <span className="medal">{getMedalIcon(seller.position)}</span>
                                    <span className="position-number">{seller.position}</span>
                                </div>
                                
                                <div className="seller-info">
                                    <h4>{seller.prodejce}</h4>
                                    <p className="store-name">{seller.prodejna}</p>
                                </div>
                                
                                <div className="score-section">
                                    <div className="total-score">
                                        {seller.total_points.toLocaleString()}
                                    </div>
                                    <div className="score-label">BODŮ</div>
                                </div>
                                
                                <div className="additional-stats">
                                    <div className="stat-item">
                                        <span className="stat-label">Položky</span>
                                        <span className="stat-value">{(seller.polozky_nad_100 || 0) + (seller.sluzby_celkem || 0)}</span>
                                    </div>
                                    <div className="stat-item">
                                        <span className="stat-label">Průměr pol./účt.</span>
                                        <span className="stat-value">{seller.prumer_polozek_uctu.toFixed(2)}</span>
                                    </div>
                                    <div className="stat-item stat-item-servis">
                                        <span className="stat-label">Servis</span>
                                        <span className="stat-value">{seller.servis_provize ?? 0}</span>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Tabulka s ostatními prodejci */}
            {restOfList.length > 0 && (
                <div className="leaderboard-table-section">
                    <h4>🏅 Kompletní žebříček</h4>
                    <div className="table-wrapper">
                        <table className="leaderboard-table">
                            <thead>
                                <tr>
                                    <th>Pozice</th>
                                    <th>Prodejce</th>
                                    <th>Prodejna</th>
                                    <th>Celkové body</th>
                                    <th>Průměr pol./účt.</th>
                                    <th>{compareLabel}</th>
                                </tr>
                            </thead>
                            <tbody>
                                {restOfList.map((seller) => (
                                    <tr 
                                        key={seller.id}
                                        className={currentUser?.id === seller.id ? 'current-user-row' : ''}
                                    >
                                        <td>
                                            <span className="position-badge">
                                                {seller.position}.
                                            </span>
                                        </td>
                                        <td>
                                            <div className="seller-cell">
                                                <strong>{seller.prodejce}</strong>
                                                {currentUser?.id === seller.id && (
                                                    <span className="you-badge">Vy</span>
                                                )}
                                            </div>
                                        </td>
                                        <td>{seller.prodejna}</td>
                                        <td>
                                            <span className="points-value">
                                                {seller.total_points.toLocaleString()}
                                            </span>
                                        </td>
                                        <td>{seller.prumer_polozek_uctu.toFixed(2)}</td>
                                        <td>
                                            <span className="score-highlight">
                                                {getComparePoints(seller).toLocaleString()}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Vaše pozice */}
            {currentUserPosition && (
                <div className="user-position-card">
                    <h4>📍 Vaše pozice</h4>
                    <div className="position-info">
                        <span className="position">{currentUserPosition}. místo</span>
                        <span className="points">{data.find(s => s.id === currentUser.id)?.total_points?.toLocaleString()} bodů</span>
                        <span className="store">{currentUser.prodejna}</span>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PointsLeaderboard; 