import React, { useState, useEffect } from 'react';
import './ShiftOverview.css';
import { shiftRoleLabel } from './shiftRoleLabels';

function ShiftOverview({ user, month }) {
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

    const formatTime = (value) => (value ? String(value).substring(0, 5) : '');

    const formatAttendance = (smena) => {
        if (smena.typ_smeny !== 'prace') {
            return '—';
        }
        if (!smena.dochazka_od && smena.stav_dochazky === 'bez_zaznamu') {
            return 'bez záznamu';
        }
        const od = smena.dochazka_od || '—';
        const doValue = smena.dochazka_do || '—';
        return `${od} – ${doValue}`;
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
            <div className="overview-user-bar">
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
                        <div className="stat-value">{(overview.mesicni_fond ?? overview.standardni_hodiny)}h</div>
                        <div className="stat-label">Měsíční fond</div>
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

            {overview.dovolena_stav && (
                <div className="vacation-fund-section">
                    <h4>🏖️ Roční fond dovolené ({overview.dovolena_stav.rok})</h4>
                    <div className="vacation-fund-grid">
                        <span>Fond: <strong>{overview.dovolena_stav.fond_h} h</strong></span>
                        <span>Čerpáno: <strong>{overview.dovolena_stav.cerpano_h} h</strong></span>
                        <span>Zbývá: <strong>{overview.dovolena_stav.zbyva_h} h</strong></span>
                        {overview.dovolena_stav.cerpano_smeny_h > 0 && (
                            <span>Směny dovolené: <strong>{overview.dovolena_stav.cerpano_smeny_h} h</strong></span>
                        )}
                        {overview.dovolena_stav.odeceno_deficit_h > 0 && (
                            <span>Deficit fondu: <strong>{overview.dovolena_stav.odeceno_deficit_h} h</strong></span>
                        )}
                        {overview.dovolena_stav.prevod_h > 0 && (
                            <span>Převod: <strong>{overview.dovolena_stav.prevod_h} h</strong></span>
                        )}
                    </div>
                    {overview.deficit_mesic_h > 0 && (
                        <p className="vacation-deficit-hint">
                            Tento měsíc: deficit fondu <strong>{overview.deficit_mesic_h} h</strong>
                            {' '}(odečte se z dovolené po skončení měsíce)
                        </p>
                    )}
                </div>
            )}

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
                            <div>Plán</div>
                            <div>Docházka</div>
                            <div>Hodiny</div>
                            <div>Typ</div>
                        </div>
                        
                        {overview.smeny_detail.map((smena, index) => (
                            <div key={index} className={`table-row ${smena.typ_smeny}`}>
                                <div className="date-cell">
                                    {new Date(smena.datum).toLocaleDateString('cs-CZ')}
                                </div>
                                <div className="store-cell">
                                    {smena.typ_smeny === 'prace' ? smena.prodejna : '—'}
                                    {smena.typ_smeny === 'prace' && !smena.je_domaci_prodejna && (
                                        <span className="foreign-badge">📍</span>
                                    )}
                                </div>
                                <div className="time-cell plan-cell">
                                    {formatTime(smena.cas_od)} – {formatTime(smena.cas_do)}
                                </div>
                                <div className={`time-cell attendance-cell ${smena.stav_dochazky === 'bez_zaznamu' ? 'missing' : ''} ${smena.stav_dochazky === 'otevreno' ? 'open' : ''}`}>
                                    {formatAttendance(smena)}
                                </div>
                                <div className="hours-cell">
                                    {smena.hodiny}h
                                    {smena.hodiny_z_dochozky != null && smena.hodiny_z_dochozky !== smena.hodiny && (
                                        <span className="actual-hours"> / {smena.hodiny_z_dochozky}h</span>
                                    )}
                                </div>
                                <div className="type-cell">
                                    <span className={`type-badge ${smena.typ_smeny}`}>
                                        {smena.typ_smeny === 'prace' && '💼'}
                                        {smena.typ_smeny === 'dovolena' && '🏖️'}
                                        {smena.typ_smeny === 'nemoc' && '🏥'}
                                        {shiftRoleLabel(smena)}
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