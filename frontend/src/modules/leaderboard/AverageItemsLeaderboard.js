import React from 'react';
import './AverageItemsLeaderboard.css';

const AverageItemsLeaderboard = ({ data, loading, currentUser }) => {
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
                <p>Pro aktuální měsíc nejsou k dispozici žádná data o průměru položek na účtenku.</p>
            </div>
        );
    }

    const topThree = data.slice(0, 3);
    const restOfList = data;

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
    const overallAverage = data.reduce((sum, seller) => sum + seller.prumer_polozek_uctu, 0) / data.length;

    return (
        <div className="average-items-leaderboard">
            {/* Hlavní statistiky */}
            <div className="leaderboard-stats">
                <div className="stat-card">
                    <h4>📋 Celkem položek</h4>
                    <div className="stat-value">
                        {data.reduce((sum, seller) => sum + seller.polozky_nad_100, 0).toLocaleString()}
                    </div>
                    <div className="stat-change">Všichni prodejci</div>
                </div>
                <div className="stat-card">
                    <h4>📊 Celkový průměr</h4>
                    <div className="stat-value">{overallAverage.toFixed(2)}</div>
                    <div className="stat-change">Položek na účtenku</div>
                </div>
                <div className="stat-card">
                    <h4>🎯 Nejvyšší průměr</h4>
                    <div className="stat-value">{data[0]?.prumer_polozek_uctu?.toFixed(2) || '0.00'}</div>
                    <div className="stat-change positive">{data[0]?.prodejce || 'N/A'}</div>
                </div>
                <div className="stat-card">
                    <h4>👥 Aktivní prodejci</h4>
                    <div className="stat-value">{data.length}</div>
                    <div className="stat-change">Za aktuální měsíc</div>
                </div>
            </div>

            {/* TOP 3 prodejci - karty */}
            {topThree.length > 0 && (
                <div className="top-three-section">
                    <h3>📊 Žebříček průměru položek/účtenka</h3>
                    <p>Nejlepší prodejci podle průměru položek na účtenku za aktuální měsíc</p>
                    
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
                                        {seller.prumer_polozek_uctu.toFixed(2)}
                                    </div>
                                    <div className="score-label">PRŮMĚR</div>
                                </div>
                                
                                <div className="additional-stats">
                                    <div className="stat-item">
                                        <span className="stat-label">Položky 100+</span>
                                        <span className="stat-value">{seller.polozky_nad_100}</span>
                                    </div>
                                    <div className="stat-item">
                                        <span className="stat-label">Celkové body</span>
                                        <span className="stat-value">{seller.total_points}</span>
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
                    <h4>📋 Kompletní žebříček</h4>
                    <div className="table-wrapper">
                        <table className="leaderboard-table">
                            <thead>
                                <tr>
                                    <th>Pozice</th>
                                    <th>Prodejce</th>
                                    <th>Prodejna</th>
                                    <th>Průměr pol./účt.</th>
                                    <th>Položky 100+</th>
                                    <th>Celkové body</th>
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
                                            <span className="average-value">
                                                {seller.prumer_polozek_uctu.toFixed(2)}
                                            </span>
                                        </td>
                                        <td>{seller.polozky_nad_100}</td>
                                        <td>
                                            <span className="points-highlight">
                                                {seller.total_points.toLocaleString()}
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
                        <span className="average">{data.find(s => s.id === currentUser.id)?.prumer_polozek_uctu?.toFixed(2)} průměr</span>
                        <span className="store">{currentUser.prodejna}</span>
                    </div>
                </div>
            )}

            {/* Informace o průměru */}
            <div className="average-info-section">
                <h4>ℹ️ Informace o průměru</h4>
                <div className="info-cards">
                    <div className="info-card">
                        <h5>Co je průměr položek/účtenka?</h5>
                        <p>Průměrný počet položek na jeden prodejní doklad (účtenku). Vyšší hodnota znamená více položek na jednu transakci.</p>
                    </div>
                    <div className="info-card">
                        <h5>Jak se počítá?</h5>
                        <p>Celkový počet prodaných položek / počet účtenek. Data se aktualizují denně podle prodejních dat.</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AverageItemsLeaderboard; 