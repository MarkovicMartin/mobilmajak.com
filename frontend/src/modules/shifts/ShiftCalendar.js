import React, { useState, useEffect, useMemo, useCallback } from 'react';
import ConfirmModal from '../../components/ConfirmModal';
import './ShiftCalendar.css';
import UnifiedCalendar from './UnifiedCalendar';
import { format, parse, startOfMonth, endOfMonth, eachDayOfInterval, isBefore } from 'date-fns';

const STAFFING_MANAGER_ROLES = ['ADMIN', 'VEDOUCI'];

const isWorkShift = (shift) => shift.typ_smeny === 'prace';

const isAbsenceShift = (shift) => shift.typ_smeny === 'dovolena' || shift.typ_smeny === 'nemoc';

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

function ShiftCalendar({
    prodejna,
    month,
    user,
    refreshTrigger,
    onRefresh,
    onRequestBulkAdd,
    onRequestSingleAdd,
    allStores = false,
    stores = [],
    showAllEmployees = false,
}) {
    const [kalendarData, setKalendarData] = useState({});
    const [svatky, setSvatky] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [showConfirm, setShowConfirm] = useState(false);
    const [shiftToDelete, setShiftToDelete] = useState(null);
    const [dragPreviewDates, setDragPreviewDates] = useState(() => new Set());

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

    const formatShiftDate = (shift, dateStr) => {
        const raw = shift?.datum || shift?.date || dateStr || '';
        if (!raw) return '—';
        const parsed = parse(String(raw).slice(0, 10), 'yyyy-MM-dd', new Date());
        if (Number.isNaN(parsed.getTime())) return String(raw);
        return parsed.toLocaleDateString('cs-CZ');
    };

    const handleShiftClick = (shift, dateStr, event) => {
        event.stopPropagation();

        if (!['ADMIN', 'VEDOUCI'].includes(user?.role) && String(shift.user_id) !== String(user?.id)) {
            setError('Nemáte oprávnění upravovat tuto směnu. Můžete upravovat pouze své vlastní směny.');
            return;
        }

        const today = new Date();
        const currentMonth = today.getFullYear() + '-' + String(today.getMonth() + 1).padStart(2, '0');
        const shiftDatum = shift.datum || shift.date || dateStr;
        const shiftMonth = shiftDatum ? String(shiftDatum).substring(0, 7) : month;
        
        // Kontrola měsíce s lepší chybovou hláškou
        if (!['ADMIN', 'VEDOUCI'].includes(user?.role) && shiftMonth < currentMonth) {
            setError('Nelze upravovat směny v minulých měsících. Obraťte se na administrátora.');
            return;
        }

        // Vše v pořádku, zobrazíme dialog pro mazání
        setError('');
        setShiftToDelete({ ...shift, datum: shiftDatum });
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

    useEffect(() => {
        setDragPreviewDates(new Set());
    }, [month, prodejna]);

    const isDateSelectable = useCallback((date) => {
        if (svatky[format(date, 'yyyy-MM-dd')]) return false;
        if (user && ['ADMIN', 'VEDOUCI'].includes(user.role)) return true;
        const firstOfMonth = parse(`${month}-01`, 'yyyy-MM-dd', new Date());
        return !isBefore(date, firstOfMonth);
    }, [month, svatky, user]);

    const handlePickDate = useCallback((dateStr) => {
        setDragPreviewDates((prev) => {
            const next = new Set(prev);
            if (next.has(dateStr)) next.delete(dateStr);
            else next.add(dateStr);
            return next;
        });
    }, []);

    const handleSingleDayAdd = useCallback((dateStr) => {
        if (!onRequestSingleAdd) return;
        if (!isDateSelectable(parse(dateStr, 'yyyy-MM-dd', new Date()))) return;
        onRequestSingleAdd(dateStr);
    }, [onRequestSingleAdd, isDateSelectable]);

    const handleDragSelectComplete = useCallback((dates) => {
        setDragPreviewDates(new Set());
        if (!dates?.length || !onRequestBulkAdd) return;
        onRequestBulkAdd(dates);
    }, [onRequestBulkAdd]);

    const isSellerView = user?.role === 'PRODEJCE' || user?.role === 'VEDOUCI';

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

            {!allStores && isSellerView && (
                <div className="shifts-legend shifts-legend--seller" aria-label="Legenda směn">
                    <span className="legend-item">
                        <span className="legend-swatch legend-swatch--mine" />
                        Moje směna
                    </span>
                    <span className="legend-item">
                        <span className="legend-swatch legend-swatch--counter" />
                        Protisměna
                    </span>
                </div>
            )}

            <p className="calendar-pick-hint">
                <strong>Klik na den</strong> = přidat směnu · <strong>táhněte přes dny</strong> = hromadně · <strong>klik na směnu</strong> = smazat
            </p>

            <div className="calendar-container">
                <UnifiedCalendar
                    month={month}
                    variant="full"
                    selectedDates={dragPreviewDates}
                    enableDragSelect
                    isDateEnabled={isDateSelectable}
                    onDateClick={(dateStr) => handleSingleDayAdd(dateStr)}
                    onDateDragSelect={(dateStr) => handlePickDate(dateStr)}
                    onDragSelectComplete={handleDragSelectComplete}
                    getExtraCellClass={getExtraCellClass}
                    renderCellContent={(date) => {
                        const dateStr = format(date, 'yyyy-MM-dd');
                        const shifts = getShiftsForDate(dateStr);
                        const workShifts = shifts.filter(isWorkShift);
                        const absenceShifts = shifts.filter(isAbsenceShift);
                        const isSvatek = svatky[dateStr];
                        const inMonth = dateStr.startsWith(month);
                        const staffingGap = inMonth && !isSvatek && isStaffingManager
                            ? getStaffingGap(workShifts, stores, allStores)
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
                                    {workShifts.map((shift) => {
                                        const isOwnShift = String(shift.user_id) === String(user?.id);
                                        const isCounterShift = !isOwnShift && !allStores;
                                        const shiftClasses = [
                                            'shift-item',
                                            isOwnShift ? 'mine' : 'other',
                                            isCounterShift ? 'counter-shift' : '',
                                            allStores ? 'shift-item--store-colored' : '',
                                            !allStores && !shift.je_domaci_prodejna && isOwnShift
                                                ? 'foreign-store'
                                                : '',
                                        ].filter(Boolean).join(' ');
                                        const servisBadge = shift.pozice_smeny === 'servis'
                                            ? (shift.servis_uroven === 'zauceni' ? 'Servis (zašk.)' : 'Servis')
                                            : null;
                                        const titleParts = [
                                            allStores && shift.prodejna_nazev ? shift.prodejna_nazev : null,
                                            isCounterShift ? `Protisměna: ${shift.user_jmeno}` : shift.user_jmeno,
                                            servisBadge,
                                            `${formatTime(shift.cas_od)}-${formatTime(shift.cas_do)}`,
                                        ].filter(Boolean);
                                        return (
                                            <div
                                                key={shift.id}
                                                className={shiftClasses}
                                                style={allStores ? getShiftStyle(shift) : undefined}
                                                onMouseDown={(e) => e.stopPropagation()}
                                                onClick={(e) => handleShiftClick(shift, dateStr, e)}
                                                title={titleParts.join(' · ')}
                                            >
                                                <div className="shift-content">
                                                    {allStores && shift.prodejna_nazev && (
                                                        <div className="shift-store">{shift.prodejna_nazev}</div>
                                                    )}
                                                    <div className="shift-name">
                                                        {isCounterShift && (
                                                            <span className="counter-shift-badge">Protisměna</span>
                                                        )}
                                                        {shift.user_jmeno}
                                                    </div>
                                                    <div className="shift-time">
                                                        {formatTime(shift.cas_od)}-{formatTime(shift.cas_do)}
                                                    </div>
                                                    {servisBadge && (
                                                        <div className="shift-servis-badge">{servisBadge}</div>
                                                    )}
                                                </div>
                                                {!allStores && !shift.je_domaci_prodejna && user?.id === shift.user_id && (
                                                    <div className="foreign-indicator">📍</div>
                                                )}
                                            </div>
                                        );
                                    })}
                                    {absenceShifts.length > 0 && (
                                        <div className="shifts-absences">
                                            {absenceShifts.map((shift) => {
                                                const isVacation = shift.typ_smeny === 'dovolena';
                                                const label = isVacation ? 'Dovolená' : 'Nemoc';
                                                return (
                                                    <div
                                                        key={shift.id}
                                                        className={`shift-item shift-item--absence ${isVacation ? 'vacation' : 'sick'}`}
                                                        onMouseDown={(e) => e.stopPropagation()}
                                                        onClick={(e) => handleShiftClick(shift, dateStr, e)}
                                                        title={`${shift.user_jmeno} · ${label}`}
                                                    >
                                                        <span className="shift-absence-icon" aria-hidden="true">
                                                            {isVacation ? '🏖️' : '🏥'}
                                                        </span>
                                                        <span className="shift-absence-name">{shift.user_jmeno}</span>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                            </>
                        );
                    }}
                />
            </div>

            {showConfirm && shiftToDelete && (
                <ConfirmModal
                    title="Smazat směnu"
                    onClose={handleCancelDelete}
                    onConfirm={handleConfirmDelete}
                    confirmLabel="Smazat"
                >
                    <div className="confirm-details">
                        <p><strong>Prodejce:</strong> {shiftToDelete.user_jmeno}</p>
                        <p><strong>Datum:</strong> {formatShiftDate(shiftToDelete)}</p>
                        <p><strong>Typ:</strong> {shiftToDelete.typ_smeny === 'dovolena' ? 'Dovolená' : shiftToDelete.typ_smeny === 'nemoc' ? 'Nemoc' : 'Práce'}</p>
                        {!isAbsenceShift(shiftToDelete) && (
                            <>
                                <p><strong>Čas:</strong> {formatTime(shiftToDelete.cas_od)}-{formatTime(shiftToDelete.cas_do)}</p>
                                <p><strong>Prodejna:</strong> {shiftToDelete.prodejna_nazev || shiftToDelete.prodejna || prodejna}</p>
                            </>
                        )}
                    </div>
                    <p className="confirm-question">Opravdu chcete tuto směnu smazat?</p>
                </ConfirmModal>
            )}
        </div>
    );
}

export default ShiftCalendar; 