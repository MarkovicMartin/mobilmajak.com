import React, { useState, useEffect } from 'react';
import './AttendancePanel.css';

function AttendancePanel({ user }) {
    const [todayShift, setTodayShift] = useState(null);
    const [attendanceHistory, setAttendanceHistory] = useState([]);
    const [currentStatus, setCurrentStatus] = useState('offline'); // offline, working, on_break
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState(false);
    const [error, setError] = useState('');
    const [warnings, setWarnings] = useState([]);

    useEffect(() => {
        fetchTodayData();
        fetchWarnings();
        const interval = setInterval(() => {
            fetchTodayData();
            fetchWarnings();
        }, 60000);
        return () => clearInterval(interval);
    }, []);

    const fetchWarnings = async () => {
        try {
            const res = await fetch('/api/shifts/attendance/my-status/', { credentials: 'include' });
            if (res.ok) {
                const data = await res.json();
                setWarnings(data.warnings || []);
            }
        } catch (err) {
            console.error('Chyba při načítání upozornění docházky:', err);
        }
    };

    const fetchTodayData = async () => {
        try {
            setLoading(true);
            const today = new Date().toISOString().split('T')[0];
            
            // Načtení dnešních směn
            const shiftsResponse = await fetch(
                `/api/shifts/?mesic=${today.substring(0, 7)}`,
                {
                    credentials: 'include'
                }
            );

            if (shiftsResponse.ok) {
                const shifts = await shiftsResponse.json();
                const todayShifts = shifts.filter(shift => shift.datum === today);
                
                if (todayShifts.length > 0) {
                    const shift = todayShifts[0];
                    setTodayShift(shift);
                    setAttendanceHistory(shift.dochazka || []);
                    calculateCurrentStatus(shift.dochazka || []);
                } else {
                    setTodayShift(null);
                    setAttendanceHistory([]);
                    setCurrentStatus('no_shift');
                }
            }
        } catch (error) {
            console.error('Chyba při načítání dat:', error);
            setError('Chyba při načítání dat');
        } finally {
            setLoading(false);
        }
    };

    const calculateCurrentStatus = (history) => {
        if (history.length === 0) {
            setCurrentStatus('offline');
            return;
        }

        // Seřazení podle času
        const sortedHistory = [...history].sort((a, b) => new Date(a.cas) - new Date(b.cas));
        const lastAction = sortedHistory[sortedHistory.length - 1];

        switch (lastAction.typ_akce) {
            case 'prichod':
                setCurrentStatus('working');
                break;
            case 'pauza_start':
                setCurrentStatus('on_break');
                break;
            case 'pauza_konec':
                setCurrentStatus('working');
                break;
            case 'odchod':
                setCurrentStatus('offline');
                break;
            default:
                setCurrentStatus('offline');
        }
    };

    const handleAttendanceAction = async (actionType) => {
        if (!todayShift) {
            setError('Nemáte naplánovanou směnu na dnešní den');
            return;
        }

        try {
            setActionLoading(true);
            setError('');

            const response = await fetch('/api/shifts/attendance/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    smena_id: todayShift.id,
                    typ_akce: actionType,
                    poznamka: ''
                })
            });

            if (response.ok) {
                // Refresh data
                await fetchTodayData();
            } else {
                const data = await response.json();
                setError(data.error || 'Chyba při zaznamenávání akce');
            }
        } catch (error) {
            setError('Chyba při zaznamenávání akce');
        } finally {
            setActionLoading(false);
        }
    };

    const formatTime = (dateTimeStr) => {
        return new Date(dateTimeStr).toLocaleTimeString('cs-CZ', {
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const getStatusDisplay = () => {
        switch (currentStatus) {
            case 'working':
                return { icon: '🟢', text: 'V práci', class: 'working' };
            case 'on_break':
                return { icon: '🟡', text: 'Na pauze', class: 'break' };
            case 'offline':
                return { icon: '🔴', text: 'Mimo práci', class: 'offline' };
            case 'no_shift':
                return { icon: '⚫', text: 'Bez směny', class: 'no-shift' };
            default:
                return { icon: '⚫', text: 'Neznámý stav', class: 'unknown' };
        }
    };

    const calculateWorkTime = () => {
        if (attendanceHistory.length === 0) return '0:00';
        
        let totalMinutes = 0;
        let currentPeriodStart = null;
        
        const sortedHistory = [...attendanceHistory].sort((a, b) => new Date(a.cas) - new Date(b.cas));
        
        for (const action of sortedHistory) {
            const actionTime = new Date(action.cas);
            
            if (action.typ_akce === 'prichod' || action.typ_akce === 'pauza_konec') {
                currentPeriodStart = actionTime;
            } else if (action.typ_akce === 'pauza_start' || action.typ_akce === 'odchod') {
                if (currentPeriodStart) {
                    totalMinutes += (actionTime - currentPeriodStart) / (1000 * 60);
                    currentPeriodStart = null;
                }
            }
        }
        
        // Pokud je stále v práci, počítáme do teď
        if (currentPeriodStart && currentStatus === 'working') {
            totalMinutes += (new Date() - currentPeriodStart) / (1000 * 60);
        }
        
        const hours = Math.floor(totalMinutes / 60);
        const minutes = Math.floor(totalMinutes % 60);
        return `${hours}:${minutes.toString().padStart(2, '0')}`;
    };

    if (loading) {
        return (
            <div className="attendance-panel">
                <div className="loading">Načítání docházky...</div>
            </div>
        );
    }

    const statusDisplay = getStatusDisplay();

    return (
        <div className="attendance-panel">
            <div className="attendance-header">
                <h3>⏰ Docházka - {new Date().toLocaleDateString('cs-CZ')}</h3>
                <div className={`status-indicator ${statusDisplay.class}`}>
                    {statusDisplay.icon} {statusDisplay.text}
                </div>
            </div>

            {todayShift ? (
                <div className="shift-info-card">
                    <h4>📋 Dnešní směna</h4>
                    <div className="shift-details">
                        <div><strong>Prodejna:</strong> {todayShift.prodejna}</div>
                        <div><strong>Plánovaný čas:</strong> {todayShift.cas_od.substring(0, 5)} - {todayShift.cas_do.substring(0, 5)}</div>
                        <div><strong>Odpracováno:</strong> {calculateWorkTime()}</div>
                    </div>
                </div>
            ) : (
                <div className="no-shift-info">
                    📅 Dnes nemáte naplánovanou žádnou směnu
                </div>
            )}

            {warnings.length > 0 && (
                <div className="attendance-warning-banner" role="alert">
                    {warnings.map((w, i) => (
                        <p key={i}>⚠️ {w.zprava}</p>
                    ))}
                </div>
            )}

            {todayShift && currentStatus === 'working' && todayShift.cas_do && (() => {
                const now = new Date();
                const [h, m] = todayShift.cas_do.substring(0, 5).split(':').map(Number);
                const end = new Date();
                end.setHours(h, m, 0, 0);
                if (now > end) {
                    return (
                        <div className="attendance-warning-banner" role="alert">
                            <p>⚠️ Směna už skončila ({todayShift.cas_do.substring(0, 5)}) – nezapomeňte odkliknout odchod.</p>
                        </div>
                    );
                }
                return null;
            })()}

            {error && <div className="error-message">{error}</div>}

            {todayShift && (
                <div className="attendance-controls">
                    <div className="control-buttons">
                        <button 
                            className={`attendance-btn arrival ${currentStatus === 'offline' || currentStatus === 'no_shift' ? 'active' : 'disabled'}`}
                            onClick={() => handleAttendanceAction('prichod')}
                            disabled={actionLoading || (currentStatus !== 'offline' && currentStatus !== 'no_shift')}
                        >
                            🔵 Příchod
                        </button>
                        
                        <button 
                            className={`attendance-btn break ${currentStatus === 'working' ? 'active' : 'disabled'}`}
                            onClick={() => handleAttendanceAction('pauza_start')}
                            disabled={actionLoading || currentStatus !== 'working'}
                        >
                            ⏸️ Pauza
                        </button>
                        
                        <button 
                            className={`attendance-btn continue ${currentStatus === 'on_break' ? 'active' : 'disabled'}`}
                            onClick={() => handleAttendanceAction('pauza_konec')}
                            disabled={actionLoading || currentStatus !== 'on_break'}
                        >
                            ▶️ Pokračovat
                        </button>
                        
                        <button 
                            className={`attendance-btn departure ${currentStatus === 'working' || currentStatus === 'on_break' ? 'active' : 'disabled'}`}
                            onClick={() => handleAttendanceAction('odchod')}
                            disabled={actionLoading || (currentStatus !== 'working' && currentStatus !== 'on_break')}
                        >
                            🔴 Odchod
                        </button>
                    </div>
                </div>
            )}

            {attendanceHistory.length > 0 && (
                <div className="attendance-history">
                    <h4>📜 Historie akcí dnes</h4>
                    <div className="history-list">
                        {attendanceHistory
                            .sort((a, b) => new Date(b.cas) - new Date(a.cas))
                            .map((action, index) => (
                            <div key={index} className={`history-item ${action.typ_akce}`}>
                                <div className="action-icon">
                                    {action.typ_akce === 'prichod' && '🔵'}
                                    {action.typ_akce === 'pauza_start' && '⏸️'}
                                    {action.typ_akce === 'pauza_konec' && '▶️'}
                                    {action.typ_akce === 'odchod' && '🔴'}
                                </div>
                                <div className="action-details">
                                    <div className="action-type">
                                        {action.typ_akce === 'prichod' && 'Příchod'}
                                        {action.typ_akce === 'pauza_start' && 'Začátek pauzy'}
                                        {action.typ_akce === 'pauza_konec' && 'Konec pauzy'}
                                        {action.typ_akce === 'odchod' && 'Odchod'}
                                    </div>
                                    <div className="action-time">{formatTime(action.cas)}</div>
                                </div>
                                {action.poznamka && (
                                    <div className="action-note">{action.poznamka}</div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

export default AttendancePanel; 