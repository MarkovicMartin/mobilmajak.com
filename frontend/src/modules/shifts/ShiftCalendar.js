import React, { useState, useEffect } from 'react';
import './ShiftCalendar.css';
import UnifiedCalendar from './UnifiedCalendar';
import { format } from 'date-fns';

function ShiftCalendar({ prodejna, month, user, refreshTrigger, onRefresh }) {
    const [kalendarData, setKalendarData] = useState({});
    const [svatky, setSvatky] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [showConfirm, setShowConfirm] = useState(false);
    const [shiftToDelete, setShiftToDelete] = useState(null);

    useEffect(() => {
        if (prodejna && month) {
            fetchKalendarData();
        }
    }, [prodejna, month]);

    // Efekt pro refresh trigger
    useEffect(() => {
        if (refreshTrigger > 0 && prodejna && month) {
            fetchKalendarData();
        }
    }, [refreshTrigger]);

    const fetchKalendarData = async () => {
        try {
            setLoading(true);
            setError('');
            
            const url = `/api/shifts/calendar/?mesic=${month}&prodejna=${prodejna}`;
            console.log('Volám kalendář API:', url);
            console.log('Parametry:', { month, prodejna });
            
            const response = await fetch(url, {
                    credentials: 'include'
            });

            console.log('Odpověď kalendáře:', response.status, response.statusText);

            if (response.ok) {
                const data = await response.json();
                console.log('Kalendář data:', data);
                setKalendarData(data.kalendar_data);
                setSvatky(data.svatky || {});
            } else {
                const errorData = await response.json().catch(() => ({}));
                console.error('Chyba kalendáře:', errorData);
                setError(`Chyba při načítání kalendářních dat: ${errorData.error || response.statusText}`);
            }
        } catch (error) {
            console.error('Chyba při načítání kalendáře:', error);
            setError('Chyba při načítání kalendáře');
        } finally {
            setLoading(false);
        }
    };

    const generateCalendar = () => {
        const [year, monthNum] = month.split('-').map(Number);
        
        const firstDay = new Date(year, monthNum - 1, 1);
        const daysInMonth = new Date(year, monthNum, 0).getDate();
        const startDay = firstDay.getDay();
        
        // Převod neděle (0) na 7 pro pondělí jako první den
        const mondayStartDay = startDay === 0 ? 6 : startDay - 1;
        
        const calendar = [];
        
        // Dny z předchozího měsíce
        const prevMonth = new Date(year, monthNum - 1, 0);
        for (let i = mondayStartDay; i > 0; i--) {
            const day = prevMonth.getDate() - i + 1;
            const date = new Date(prevMonth.getFullYear(), prevMonth.getMonth(), day);
            // Oprava: Použijeme lokální formátování místo UTC
            const dateStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
            calendar.push({
                day,
                date: dateStr,
                isCurrentMonth: false,
                isToday: false
            });
        }
        
        // Dny aktuálního měsíce
        const today = new Date();
        const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
        for (let day = 1; day <= daysInMonth; day++) {
            const date = new Date(year, monthNum - 1, day);
            // Oprava: Použijeme lokální formátování místo UTC
            const dateStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
            calendar.push({
                day,
                date: dateStr,
                isCurrentMonth: true,
                isToday: dateStr === todayStr
            });
        }
        
        // Dny z následujícího měsíce - dokončíme mřížku na 35 nebo 42 dní
        const totalCells = Math.ceil(calendar.length / 7) * 7;
        const remainingCells = totalCells - calendar.length;
        for (let day = 1; day <= remainingCells; day++) {
            const date = new Date(year, monthNum, day);
            // Oprava: Použijeme lokální formátování místo UTC
            const dateStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
            calendar.push({
                day,
                date: dateStr,
                isCurrentMonth: false,
                isToday: false
            });
        }
        
        return calendar;
    };

    const getShiftsForDate = (dateStr) => {
        return kalendarData[dateStr] || [];
    };

    const formatTime = (timeStr) => {
        return timeStr.substring(0, 5);
    };

    const getHolidayIcon = (nazev) => {
        if (nazev.includes('vánoční') || nazev.includes('Štědrý')) return '🎄';
        if (nazev.includes('Nový rok')) return '🎉';
        if (nazev.includes('Velikonoční') || nazev.includes('Velký pátek')) return '🐰';
        if (nazev.includes('Svátek práce')) return '⚒️';
        if (nazev.includes('vítězství')) return '🕊️';
        if (nazev.includes('Cyril') || nazev.includes('Jan Hus')) return '⛪';
        if (nazev.includes('státnosti') || nazev.includes('samostatného')) return '🇨🇿';
        if (nazev.includes('svobodu')) return '🕊️';
        return '🎊';
    };

    const handleShiftClick = async (shift, event) => {
        event.stopPropagation();
        

        
        // Kontrola oprávnění s informativní hláškou - převádíme na string pro správné porovnání
        if (!['ADMIN', 'VEDOUCI'].includes(user?.role) && String(shift.user_id) !== String(user?.id)) {
            setError('Nemáte oprávnění upravovat tuto směnu. Můžete upravovat pouze své vlastní směny.');
            return;
        }

        const today = new Date();
        const currentMonth = today.getFullYear() + '-' + String(today.getMonth() + 1).padStart(2, '0');
        const shiftMonth = shift.datum ? shift.datum.substring(0, 7) : month;
        
        // Kontrola měsíce s lepší chybovou hláškou
        if (!['ADMIN', 'VEDOUCI'].includes(user?.role) && shiftMonth < currentMonth) {
            setError('Nelze upravovat směny v minulých měsících. Obraťte se na administrátora.');
            return;
        }

        // Vše v pořádku, zobrazíme dialog pro mazání
        setError(''); // Vyčistíme předchozí chyby
        setShiftToDelete(shift);
        setShowConfirm(true);
    };

    const handleConfirmDelete = async () => {
        if (!shiftToDelete) return;

        try {
            const response = await fetch(`/api/shifts/${shiftToDelete.id}/`, {
                method: 'DELETE',
                credentials: 'include'
            });

            if (response.ok) {
                setError('');
                onRefresh();
            } else {
                const data = await response.json();
                setError('Chyba při mazání směny: ' + (data.error || 'Neznámá chyba'));
            }
        } catch (error) {
            setError('Chyba při mazání směny');
        }

        setShowConfirm(false);
        setShiftToDelete(null);
    };

    const handleCancelDelete = () => {
        setShowConfirm(false);
        setShiftToDelete(null);
    };

    if (loading) {
        return (
            <div className="shift-calendar">
                <div className="loading">📅 Načítání kalendáře...</div>
            </div>
        );
    }

    const calendar = generateCalendar(); // retained for previous logic but no longer used for grid

    return (
        <div className="shift-calendar">
            {/* CHYBOVÁ HLÁŠKA JAKO BANNER */}
            {error && (
                <div className="error-banner">
                    <div className="error-content">
                        <span className="error-icon">⚠️</span>
                        <span className="error-message">{error}</span>
                        <button 
                            onClick={() => setError('')} 
                            className="error-close"
                            title="Zavřít"
                        >
                            ✕
                        </button>
                    </div>
                </div>
            )}
            <div className="calendar-container">
                <UnifiedCalendar
                    month={month}
                    variant="full"
                    renderCellContent={(date) => {
                        const dateStr = format(date, 'yyyy-MM-dd');
                        const shifts = getShiftsForDate(dateStr);
                        const isSvatek = svatky[dateStr];
                        return (
                            <>
                                {isSvatek && (
                                    <div className="holiday-indicator" title={isSvatek.nazev}>
                                        {getHolidayIcon(isSvatek.nazev)}
                                    </div>
                                )}
                                <div className="shifts-container">
                                    {shifts.map((shift) => {
                                        const shiftClasses = [
                                            'shift-item',
                                            shift.user_id === user?.id ? 'mine' : 'other',
                                            shift.typ_smeny === 'dovolena' ? 'vacation' : '',
                                            shift.typ_smeny === 'nemoc' ? 'sick' : '',
                                            !shift.je_domaci_prodejna && user?.id === shift.user_id ? 'foreign-store' : ''
                                        ].filter(Boolean).join(' ');
                                        return (
                                            <div
                                                key={shift.id}
                                                className={shiftClasses}
                                                onClick={(e) => handleShiftClick(shift, e)}
                                                title={`${shift.user_jmeno} - ${formatTime(shift.cas_od)}-${formatTime(shift.cas_do)}`}
                                            >
                                                <div className="shift-content">
                                                    <div className="shift-name">{shift.user_jmeno}</div>
                                                    <div className="shift-time">{formatTime(shift.cas_od)}-{formatTime(shift.cas_do)}</div>
                                                </div>
                                                {!shift.je_domaci_prodejna && user?.id === shift.user_id && (
                                                    <div className="foreign-indicator">📍</div>
                                                )}
                                                {shift.typ_smeny === 'dovolena' && (
                                                    <div className="vacation-indicator">🏖️</div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            </>
                        );
                    }}
                />
            </div>

            {/* KONFIRMAČNÍ DIALOG */}
            {showConfirm && shiftToDelete && (
                <div className="confirm-overlay" onClick={handleCancelDelete}>
                    <div className="confirm-dialog" onClick={(e) => e.stopPropagation()}>
                        <h3>Smazat směnu</h3>
                        <div className="shift-details">
                            <p><strong>Prodejce:</strong> {shiftToDelete.user_jmeno}</p>
                            <p><strong>Datum:</strong> {new Date(shiftToDelete.datum || shiftToDelete.date || '').toLocaleDateString('cs-CZ')}</p>
                            <p><strong>Čas:</strong> {formatTime(shiftToDelete.cas_od)}-{formatTime(shiftToDelete.cas_do)}</p>
                            <p><strong>Prodejna:</strong> {shiftToDelete.prodejna || prodejna}</p>
                        </div>
                        <p className="confirm-question">Opravdu chcete tuto směnu smazat?</p>
                        <div className="confirm-buttons">
                            <button className="btn-cancel" onClick={handleCancelDelete}>
                                Zrušit
                            </button>
                            <button className="btn-delete" onClick={handleConfirmDelete}>
                                Smazat
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default ShiftCalendar; 