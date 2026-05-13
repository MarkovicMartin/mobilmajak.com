import React, { useState, useEffect } from 'react';
import './ShiftOverview.css';

function ShiftOverview({ user, month, onMonthChange }) {
    const [overview, setOverview] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        if (user && month) {
            fetchOverview();
        }
    }, [user, month]);

    const fetchOverview = async () => {
        try {
            setLoading(true);
            setError('');
            
            const response = await fetch(
                `/api/shifts/overview/?mesic=${month}`,
                {
                    credentials: 'include'
                }
            );

            if (response.ok) {
                const data = await response.json();
                setOverview(data);
            } else {
                setError('Chyba při načítání přehledu');
            }
        } catch (error) {
            console.error('Chyba při načítání přehledu:', error);
            setError('Chyba při načítání přehledu');
        } finally {
            setLoading(false);
        }
    };

    const formatMonthName = (monthStr) => {
        const [year, month] = monthStr.split('-').map(Number);
        const date = new Date(year, month - 1);
        return date.toLocaleDateString('cs-CZ', { month: 'long', year: 'numeric' });
    };

    const handleMonthChange = (direction) => {
        const [year, monthNum] = month.split('-').map(Number);
        const date = new Date(year, monthNum - 1);
        
        if (direction === 'prev') {
            date.setMonth(date.getMonth() - 1);
        } else {
            date.setMonth(date.getMonth() + 1);
        }
        
        const newMonth = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
        onMonthChange(newMonth);
    };

    if (loading) {
        return (
            <div className="shift-overview">
                <div className="loading">Načítání přehledu...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="shift-overview">
                <div className="error">{error}</div>
                <button onClick={fetchOverview} className="retry-btn">
                    🔄 Zkusit znovu
                </button>
            </div>
        );
    }

    if (!overview) {
        return null;
    }

    const progressPercentage = Math.min(overview.procento_naplneni, 100);
    const isOvertime = overview.procento_naplneni > 100;

    return (
        <div className="shift-overview">
            {/* Header s navigací měsíců */}
            <div className="overview-header">
                <div className="month-navigation">
                    <button onClick={() => handleMonthChange('prev')}>
                        ◀ Předchozí
                    </button>
                    <h3>{formatMonthName(month)}</h3>
                    <button onClick={() => handleMonthChange('next')}>
                        Následující ▶
                    </button>
                </div>
                <div className="user-info">
                    👤 {overview.user_jmeno}
                </div>
            </div>

            {/* Statistické karty */}
            <div className="stats-grid">
                <div className="stat-card primary">
                    <div className="stat-icon">⏰</div>
                    <div className="stat-content">
                        <div className="stat-value">{overview.celkem_hodin_naplanovanych}h</div>
                        <div className="stat-label">Naplánováno hodin</div>
                    </div>
                </div>

                <div className="stat-card success">
                    <div className="stat-icon">📊</div>
                    <div className="stat-content">
                        <div className="stat-value">{overview.standardni_hodiny}h</div>
                        <div className="stat-label">Standardní měsíc</div>
                    </div>
                </div>

                <div className="stat-card warning">
                    <div className="stat-icon">🏖️</div>
                    <div className="stat-content">
                        <div className="stat-value">{overview.hodin_dovolene}h</div>
                        <div className="stat-label">Dovolená</div>
                    </div>
                </div>

                <div className="stat-card info">
                    <div className="stat-icon">📋</div>
                    <div className="stat-content">
                        <div className="stat-value">{overview.pocet_smeny}</div>
                        <div className="stat-label">Počet směn</div>
                    </div>
                </div>
            </div>

            {/* Progress bar s procentem naplnění */}
            <div className="progress-section">
                <div className="progress-header">
                    <h4>📈 Plnění standardu</h4>
                    <span className={`progress-percentage ${isOvertime ? 'overtime' : ''}`}>
                        {overview.procento_naplneni}%
                    </span>
                </div>
                
                <div className="progress-container">
                    <div className="progress-bar">
                        <div 
                            className={`progress-fill ${isOvertime ? 'overtime' : ''}`}
                            style={{ width: `${Math.min(progressPercentage, 100)}%` }}
                        ></div>
                    </div>
                    <div className="progress-labels">
                        <span>0h</span>
                        <span>{overview.standardni_hodiny}h</span>
                    </div>
                </div>

                {isOvertime && (
                    <div className="overtime-info">
                        🚀 Přesčas: {(overview.celkem_hodin_naplanovanych - overview.standardni_hodiny).toFixed(1)}h
                    </div>
                )}
            </div>

            {/* Detailní rozpis směn */}
            <div className="shifts-detail">
                <h4>📅 Detailní rozpis směn</h4>
                
                {overview.smeny_detail.length > 0 ? (
                    <div className="shifts-table">
                        <div className="table-header">
                            <div>Datum</div>
                            <div>Prodejna</div>
                            <div>Čas</div>
                            <div>Hodiny</div>
                            <div>Typ</div>
                        </div>
                        
                        {overview.smeny_detail.map((smena, index) => (
                            <div key={index} className={`table-row ${smena.typ_smeny}`}>
                                <div className="date-cell">
                                    {new Date(smena.datum).toLocaleDateString('cs-CZ')}
                                </div>
                                <div className="store-cell">
                                    {smena.prodejna}
                                    {!smena.je_domaci_prodejna && <span className="foreign-badge">📍</span>}
                                </div>
                                <div className="time-cell">
                                    {smena.cas_od.substring(0, 5)} - {smena.cas_do.substring(0, 5)}
                                </div>
                                <div className="hours-cell">
                                    {smena.hodiny}h
                                </div>
                                <div className="type-cell">
                                    <span className={`type-badge ${smena.typ_smeny}`}>
                                        {smena.typ_smeny === 'prace' && '💼'}
                                        {smena.typ_smeny === 'dovolena' && '🏖️'}
                                        {smena.typ_smeny === 'nemoc' && '🏥'}
                                        {smena.typ_smeny === 'prace' ? 'Práce' : 
                                         smena.typ_smeny === 'dovolena' ? 'Dovolená' : 'Nemoc'}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="no-shifts">
                        📋 Žádné směny nenalezeny pro tento měsíc
                    </div>
                )}
            </div>
        </div>
    );
}

export default ShiftOverview; 