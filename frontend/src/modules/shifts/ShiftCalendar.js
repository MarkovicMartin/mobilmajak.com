import React, { useState, useEffect, useMemo, useCallback } from 'react';
import './ShiftCalendar.css';
import UnifiedCalendar from './UnifiedCalendar';
import { format, parse, startOfMonth, endOfMonth, eachDayOfInterval } from 'date-fns';

const STAFFING_MANAGER_ROLES = ['ADMIN', 'VEDOUCI'];

const isWorkShift = (shift) => shift.typ_smeny === 'prace';

const storeDisplayName = (store) => store.nazev_kratkiy || store.nazev || '';

/** Vrátí mezeru v obsazení (jen směny typu práce), nebo null. */
const getStaffingGap = (shifts, stores, allStores) => {
    const workShifts = shifts.filter(isWorkShift);
    if (allStores && stores.length > 0) {
        const staffedIds = new Set(workShifts.map((s) => s.prodejna_id));
        const missing = stores.filter((s) => !staffedIds.has(s.id));
        if (!missing.length) return null;
        const allEmpty = missing.length === stores.length;
        return {
            kind: allEmpty ? 'all-empty' : 'partial',
            missing,
            label: allEmpty ? '0 směn' : `−${missing.length}`,
            title: allEmpty
                ? 'Žádná pracovní směna na žádné prodejně'
                : `Bez směny: ${missing.map(storeDisplayName).join(', ')}`,
        };
    }
    if (workShifts.length === 0) {
        return {
            kind: 'all-empty',
            missing: [],
            label: '0 směn',
            title: 'Žádná pracovní směna v tento den',
        };
    }
    return null;
};

const getShiftStyle = (shift) => {
    if (shift.typ_smeny === 'dovolena' || shift.typ_smeny === 'nemoc') {
        return undefined;
    }
    const color = shift.prodejna_barva || '#1a73e8';
    return {
        backgroundColor: color,
        borderLeft: `3px solid ${color}`,
    };
};

function ShiftCalendar({ prodejna, month, user, refreshTrigger, onRefresh, allStores = false, stores = [], showAllEmployees = false }) {
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
            
            const url = `/api/shifts/calendar/?mesic=${month}&prodejna=${encodeURIComponent(prodejna)}`;
            const response = await fetch(url, {
                    credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
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

    const getShiftsForDate = (dateStr) => kalendarData[dateStr] || [];

    const isStaffingManager = showAllEmployees && STAFFING_MANAGER_ROLES.includes(user?.role);

    const monthCoverage = useMemo(() => {
        if (!isStaffingManager) {
            return { gapDays: 0, allEmptyDays: 0, partialDays: 0 };
        }
        const monthStart = startOfMonth(parse(`${month}-01`, 'yyyy-MM-dd', new Date()));
        const days = eachDayOfInterval({ start: monthStart, end: endOfMonth(monthStart) });
        let gapDays = 0;
        let allEmptyDays = 0;
        let partialDays = 0;
        days.forEach((day) => {
            const dateStr = format(day, 'yyyy-MM-dd');
            if (svatky[dateStr]) return;
            const gap = getStaffingGap(getShiftsForDate(dateStr), stores, allStores);
            if (!gap) return;
            gapDays += 1;
            if (gap.kind === 'all-empty') allEmptyDays += 1;
            else partialDays += 1;
        });
        return { gapDays, allEmptyDays, partialDays };
    }, [isStaffingManager, month, kalendarData, stores, allStores, svatky]);

    const getExtraCellClass = useCallback((dateStr) => {
        const classes = [];
        if (svatky[dateStr]) classes.push('holiday');
        if (!dateStr.startsWith(month) || !isStaffingManager || svatky[dateStr]) {
            return classes.join(' ');
        }
        const gap = getStaffingGap(kalendarData[dateStr] || [], stores, allStores);
        if (gap) classes.push(gap.kind === 'all-empty' ? 'staffing-empty' : 'staffing-partial');
        return classes.join(' ');
    }, [month, svatky, isStaffingManager, kalendarData, stores, allStores]);

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
            {isStaffingManager && monthCoverage.gapDays > 0 && (
                <div className="staffing-summary-banner" role="alert">
                    <span className="staffing-summary-icon" aria-hidden="true">⚠️</span>
                    <div className="staffing-summary-text">
                        <strong>Neúplné obsazení směn</strong>
                        {' — '}
                        {monthCoverage.gapDays} {monthCoverage.gapDays === 1 ? 'den' : monthCoverage.gapDays < 5 ? 'dny' : 'dní'} v měsíci
                        {monthCoverage.allEmptyDays > 0 && (
                            <span className="staffing-summary-detail">
                                {' '}({monthCoverage.allEmptyDays} bez jediné směny
                                {monthCoverage.partialDays > 0 && `, ${monthCoverage.partialDays} s chybějící prodejnou`})
                            </span>
                        )}
                        {monthCoverage.allEmptyDays === 0 && monthCoverage.partialDays > 0 && (
                            <span className="staffing-summary-detail">
                                {' '}(chybí směna na některé prodejně)
                            </span>
                        )}
                        . Označené dny v kalendáři níže.
                    </div>
                </div>
            )}

            {isStaffingManager && allStores && monthCoverage.gapDays === 0 && stores.length > 0 && (
                <div className="staffing-summary-banner staffing-summary-banner--ok" role="status">
                    <span aria-hidden="true">✓</span>
                    <span>V tomto měsíci má každá prodejna na každý pracovní den alespoň jednu směnu.</span>
                </div>
            )}

            {allStores && stores.length > 0 && (
                <div className="shifts-store-legend" aria-label="Legenda prodejen">
                    {stores.map((store) => (
                        <span key={store.id} className="legend-item">
                            <span
                                className="legend-swatch"
                                style={{ backgroundColor: store.barva || '#0066cc' }}
                            />
                            {store.nazev_kratkiy || store.nazev}
                        </span>
                    ))}
                    {isStaffingManager && (
                        <>
                            <span className="legend-item legend-item--alert">
                                <span className="legend-swatch legend-swatch--empty" />
                                Bez směny
                            </span>
                            <span className="legend-item legend-item--alert">
                                <span className="legend-swatch legend-swatch--partial" />
                                Chybí prodejna
                            </span>
                        </>
                    )}
                </div>
            )}

            <div className="calendar-container">
                <UnifiedCalendar
                    month={month}
                    variant="full"
                    getExtraCellClass={getExtraCellClass}
                    renderCellContent={(date) => {
                        const dateStr = format(date, 'yyyy-MM-dd');
                        const shifts = getShiftsForDate(dateStr);
                        const isSvatek = svatky[dateStr];
                        const inMonth = dateStr.startsWith(month);
                        const staffingGap = inMonth && !isSvatek && isStaffingManager
                            ? getStaffingGap(shifts, stores, allStores)
                            : null;
                        return (
                            <>
                                {isSvatek && (
                                    <div className="holiday-indicator" title={isSvatek.nazev}>
                                        {getHolidayIcon(isSvatek.nazev)}
                                    </div>
                                )}
                                {staffingGap && (
                                    <div
                                        className={`staffing-alert staffing-alert--${staffingGap.kind}`}
                                        title={staffingGap.title}
                                    >
                                        ⚠ {staffingGap.label}
                                    </div>
                                )}
                                <div className="shifts-container">
                                    {shifts.map((shift) => {
                                        const shiftClasses = [
                                            'shift-item',
                                            shift.user_id === user?.id || !showAllEmployees ? 'mine' : 'other',
                                            shift.typ_smeny === 'dovolena' ? 'vacation' : '',
                                            shift.typ_smeny === 'nemoc' ? 'sick' : '',
                                            allStores ? 'shift-item--store-colored' : '',
                                            !allStores && !shift.je_domaci_prodejna && user?.id === shift.user_id
                                                ? 'foreign-store'
                                                : '',
                                        ].filter(Boolean).join(' ');
                                        const titleParts = [
                                            allStores && shift.prodejna_nazev ? shift.prodejna_nazev : null,
                                            shift.user_jmeno,
                                            `${formatTime(shift.cas_od)}-${formatTime(shift.cas_do)}`,
                                        ].filter(Boolean);
                                        return (
                                            <div
                                                key={shift.id}
                                                className={shiftClasses}
                                                style={allStores ? getShiftStyle(shift) : undefined}
                                                onClick={(e) => handleShiftClick(shift, e)}
                                                title={titleParts.join(' · ')}
                                            >
                                                <div className="shift-content">
                                                    {allStores && shift.prodejna_nazev && (
                                                        <div className="shift-store">{shift.prodejna_nazev}</div>
                                                    )}
                                                    <div className="shift-name">{shift.user_jmeno}</div>
                                                    <div className="shift-time">
                                                        {formatTime(shift.cas_od)}-{formatTime(shift.cas_do)}
                                                    </div>
                                                </div>
                                                {!allStores && !shift.je_domaci_prodejna && user?.id === shift.user_id && (
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
                            <p><strong>Prodejna:</strong> {shiftToDelete.prodejna_nazev || shiftToDelete.prodejna || prodejna}</p>
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