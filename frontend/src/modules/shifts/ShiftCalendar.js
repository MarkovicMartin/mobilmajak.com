import React, { useState, useEffect, useMemo, useCallback } from 'react';
import ConfirmModal from '../../components/ConfirmModal';
import Modal from '../../components/Modal';
import './ShiftCalendar.css';
import UnifiedCalendar from './UnifiedCalendar';
import { shiftRoleLabel } from './shiftRoleLabels';
import { groupDayShiftsByStore } from './shiftRosterUtils';
import { format, parse, startOfMonth, endOfMonth, eachDayOfInterval } from 'date-fns';
import { userMayEditShiftMonth, userMayEditShiftOnDate } from './shiftEditPolicy';
import { isStoreExpectingShift, getClosureNotice } from '../../constants/prodejnaZavreni';
import { isBackofficeCalendarFilter, BACKOFFICE_CALENDAR_COLOR } from './shiftBackoffice';

const isWorkShift = (shift) => shift.typ_smeny === 'prace';

const isAbsenceShift = (shift) => shift.typ_smeny === 'dovolena' || shift.typ_smeny === 'nemoc';

const storeDisplayName = (store) => store.nazev_kratkiy || store.nazev || '';

/** Vrátí mezeru v obsazení (jen směny typu práce), nebo null. */
const getStaffingGap = (shifts, stores, allStores, dateStr, selectedProdejnaId = null) => {
    const workShifts = shifts.filter(isWorkShift);
    if (allStores && stores.length > 0) {
        const openStores = dateStr
            ? stores.filter((s) => isStoreExpectingShift(s, dateStr))
            : stores;
        if (!openStores.length) return null;

        const staffedIds = new Set(workShifts.map((s) => s.prodejna_id));
        const missing = openStores.filter((s) => !staffedIds.has(s.id));
        if (!missing.length) return null;
        const allEmpty = missing.length === openStores.length;
        const gapStores = allEmpty ? openStores : missing;
        return {
            kind: allEmpty ? 'all-empty' : 'partial',
            missing,
            labels: gapStores.map((s) => `chybí ${storeDisplayName(s)}`),
            title: allEmpty
                ? 'Žádná pracovní směna na žádné otevřené prodejně'
                : `Bez směny: ${missing.map(storeDisplayName).join(', ')}`,
        };
    }
    if (workShifts.length === 0) {
        let store = null;
        if (dateStr && selectedProdejnaId && selectedProdejnaId !== 'vse') {
            store = stores.find((s) => String(s.id) === String(selectedProdejnaId));
            if (store && !isStoreExpectingShift(store, dateStr)) return null;
        }
        const storeName = store ? storeDisplayName(store) : null;
        return {
            kind: 'all-empty',
            missing: store ? [store] : [],
            labels: storeName ? [`chybí ${storeName}`] : ['chybí směna'],
            title: 'Žádná pracovní směna v tento den',
        };
    }
    return null;
};

const getShiftStyle = (shift) => {
    if (shift.typ_smeny === 'dovolena' || shift.typ_smeny === 'nemoc') {
        return undefined;
    }
    const color = shift.prodejna_barva || '#1b2848';
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
    onRequestEdit,
    allStores = false,
    stores = [],
    onFeatureFlagsChange,
}) {
    const [kalendarData, setKalendarData] = useState({});
    const [seeAllEmployees, setSeeAllEmployees] = useState(false);
    const [svatky, setSvatky] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [showActionModal, setShowActionModal] = useState(false);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [selectedShift, setSelectedShift] = useState(null);
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
                setSeeAllEmployees(Boolean(data.see_all_employees));
                setSvatky(data.svatky || {});
                onFeatureFlagsChange?.({
                    shiftsSeeAllEmployees: Boolean(data.shifts_see_all_employees),
                });
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

    const showStaffingGaps = seeAllEmployees && !isBackofficeCalendarFilter(prodejna);

    const monthCoverage = useMemo(() => {
        if (!showStaffingGaps) {
            return { gapDays: 0, allEmptyDays: 0, partialDays: 0, gapsByDate: {} };
        }
        const monthStart = startOfMonth(parse(`${month}-01`, 'yyyy-MM-dd', new Date()));
        const days = eachDayOfInterval({ start: monthStart, end: endOfMonth(monthStart) });
        const gapsByDate = {};
        let gapDays = 0;
        let allEmptyDays = 0;
        let partialDays = 0;
        days.forEach((day) => {
            const dateStr = format(day, 'yyyy-MM-dd');
            const gap = getStaffingGap(getShiftsForDate(dateStr), stores, allStores, dateStr, prodejna);
            if (!gap) return;
            gapsByDate[dateStr] = gap;
            gapDays += 1;
            if (gap.kind === 'all-empty') allEmptyDays += 1;
            else partialDays += 1;
        });
        return { gapDays, allEmptyDays, partialDays, gapsByDate };
    }, [showStaffingGaps, month, kalendarData, stores, allStores, prodejna]);

    const staffingGapsByDate = monthCoverage.gapsByDate;

    const getExtraCellClass = useCallback((dateStr) => {
        const classes = [];
        if (svatky[dateStr]) classes.push('holiday');
        if (!dateStr.startsWith(month) || !showStaffingGaps) {
            return classes.join(' ');
        }
        const gap = staffingGapsByDate[dateStr];
        if (gap) classes.push(gap.kind === 'all-empty' ? 'staffing-empty' : 'staffing-partial');
        return classes.join(' ');
    }, [month, svatky, showStaffingGaps, staffingGapsByDate]);

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

        const shiftDatum = shift.datum || shift.date || dateStr;
        const shiftMonth = shiftDatum ? String(shiftDatum).substring(0, 7) : month;
        
        if (!userMayEditShiftMonth(user, shiftMonth)) {
            setError('Směny v minulých měsících může upravovat jen vedoucí nebo administrátor.');
            return;
        }

        // Vše v pořádku, zobrazíme dialog s akcemi
        setError('');
        setSelectedShift({ ...shift, datum: shiftDatum });
        setShowActionModal(true);
    };

    const handleEditShift = () => {
        if (!selectedShift || !onRequestEdit) return;
        const shift = selectedShift;
        setShowActionModal(false);
        setSelectedShift(null);
        onRequestEdit(shift);
    };

    const handleRequestDelete = () => {
        setShowActionModal(false);
        setShowDeleteConfirm(true);
    };

    const handleConfirmDelete = async () => {
        if (!selectedShift) return;

        try {
            const response = await fetch(`/api/shifts/${selectedShift.id}/`, {
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

        setShowDeleteConfirm(false);
        setSelectedShift(null);
    };

    const handleCancelAction = () => {
        setShowActionModal(false);
        setSelectedShift(null);
    };

    const handleCancelDelete = () => {
        setShowDeleteConfirm(false);
        setSelectedShift(null);
    };

    useEffect(() => {
        setDragPreviewDates(new Set());
    }, [month, prodejna]);

    const isDateSelectable = useCallback((date) => {
        return userMayEditShiftOnDate(user, format(date, 'yyyy-MM-dd'));
    }, [user]);

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

    const isBackofficeView = isBackofficeCalendarFilter(prodejna);
    const useStoreColors = allStores || isBackofficeView;

    const renderShiftRow = (shift, dateStr, { hideStoreName = false } = {}) => {
        const isOwnShift = String(shift.user_id) === String(user?.id);
        const shiftClasses = [
            'shift-item',
            isOwnShift ? 'mine' : 'other',
            useStoreColors ? 'shift-item--store-colored' : '',
            hideStoreName ? 'shift-item--in-store-group' : '',
            !useStoreColors && !shift.je_domaci_prodejna && isOwnShift ? 'foreign-store' : '',
        ].filter(Boolean).join(' ');
        const roleLabel = shiftRoleLabel(shift, { short: true });
        const titleParts = [
            !hideStoreName && useStoreColors && shift.prodejna_nazev ? shift.prodejna_nazev : null,
            shift.user_jmeno,
            roleLabel,
            `${formatTime(shift.cas_od)}-${formatTime(shift.cas_do)}`,
            !useStoreColors && !shift.je_domaci_prodejna && isOwnShift ? 'výpomoc na jiné prodejně' : null,
        ].filter(Boolean);
        return (
            <div
                key={shift.id}
                className={shiftClasses}
                style={useStoreColors ? getShiftStyle(shift) : undefined}
                onMouseDown={(e) => e.stopPropagation()}
                onClick={(e) => handleShiftClick(shift, dateStr, e)}
                title={titleParts.join(' · ')}
            >
                <div className="shift-content">
                    {!hideStoreName && useStoreColors && shift.prodejna_nazev && (
                        <div className="shift-store">{shift.prodejna_nazev}</div>
                    )}
                    <div className="shift-name">
                        {shift.user_jmeno}
                    </div>
                    <div className="shift-time">
                        {formatTime(shift.cas_od)}-{formatTime(shift.cas_do)}
                    </div>
                    {roleLabel && (
                        <div className="shift-servis-badge shift-role-badge">{roleLabel}</div>
                    )}
                </div>
            </div>
        );
    };

    const isSellerView = (user?.role === 'PRODEJCE' || user?.role === 'VEDOUCI') && !isBackofficeView;
    const isAdminAllStores = user?.role === 'ADMIN' && allStores && seeAllEmployees;

    const renderWorkShifts = (workShifts, dateStr) => {
        if (isAdminAllStores) {
            return groupDayShiftsByStore(workShifts, stores).map((storeGroup) => (
                <div
                    key={storeGroup.prodejna_id}
                    className="shift-store-group"
                    style={{ '--shift-store-bg': storeGroup.prodejna_barva }}
                >
                    <div className="shift-store-group__head">{storeGroup.prodejna_nazev}</div>
                    <div className="shift-store-group__rows">
                        {storeGroup.shifts.map((shift) => renderShiftRow(shift, dateStr, { hideStoreName: true }))}
                    </div>
                </div>
            ));
        }
        return workShifts.map((shift) => renderShiftRow(shift, dateStr));
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
            {showStaffingGaps && monthCoverage.gapDays > 0 && (
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

            {showStaffingGaps && allStores && monthCoverage.gapDays === 0 && stores.length > 0 && (
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
                    <span className="legend-item">
                        <span
                            className="legend-swatch"
                            style={{ backgroundColor: BACKOFFICE_CALENDAR_COLOR }}
                        />
                        Backoffice
                    </span>
                    {showStaffingGaps && (
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
                        <span className="legend-swatch legend-swatch--other" />
                        Ostatní
                    </span>
                </div>
            )}

            <p className="calendar-pick-hint">
                <strong>Klik na den</strong> = přidat směnu · <strong>táhněte přes dny</strong> = hromadně · <strong>klik na směnu</strong> = upravit / smazat
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
                        const closureNotice = inMonth
                            ? getClosureNotice(dateStr, { stores, allStores, prodejnaId: prodejna })
                            : null;
                        const staffingGap = inMonth && showStaffingGaps
                            ? staffingGapsByDate[dateStr]
                            : null;
                        return (
                            <>
                                {isSvatek && (
                                    <div className="holiday-indicator" title={isSvatek.nazev}>
                                        {getHolidayIcon(isSvatek.nazev)}
                                    </div>
                                )}
                                {closureNotice && (
                                    <div
                                        className={`closure-notice closure-notice--${closureNotice.kind}`}
                                        title={closureNotice.title}
                                    >
                                        {closureNotice.kind === 'always_closed' ? '🔒' : '⛪'}
                                        {' '}
                                        {closureNotice.label}
                                    </div>
                                )}
                                {staffingGap && (
                                    <div
                                        className={`staffing-alert staffing-alert--${staffingGap.kind}`}
                                        title={staffingGap.title}
                                    >
                                        {staffingGap.labels.map((line) => (
                                            <div key={line} className="staffing-alert__line">
                                                ⚠ {line}
                                            </div>
                                        ))}
                                    </div>
                                )}
                                <div className="shifts-container">
                                    {renderWorkShifts(workShifts, dateStr)}
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

            {showActionModal && selectedShift && (
                <Modal
                    title="Směna"
                    onClose={handleCancelAction}
                    size="sm"
                    footer={(
                        <>
                            <button type="button" className="btn-cancel" onClick={handleCancelAction}>
                                Zrušit
                            </button>
                            <button type="button" className="btn-submit" onClick={handleEditShift}>
                                Upravit
                            </button>
                            <button type="button" className="btn-delete" onClick={handleRequestDelete}>
                                Smazat
                            </button>
                        </>
                    )}
                >
                    <div className="confirm-details">
                        <p><strong>Prodejce:</strong> {selectedShift.user_jmeno}</p>
                        <p><strong>Datum:</strong> {formatShiftDate(selectedShift)}</p>
                        <p><strong>Role:</strong> {shiftRoleLabel(selectedShift)}</p>
                        {!isAbsenceShift(selectedShift) && (
                            <>
                                <p><strong>Čas:</strong> {formatTime(selectedShift.cas_od)}-{formatTime(selectedShift.cas_do)}</p>
                                <p><strong>Prodejna:</strong> {selectedShift.prodejna_nazev || selectedShift.prodejna || prodejna}</p>
                            </>
                        )}
                    </div>
                </Modal>
            )}

            {showDeleteConfirm && selectedShift && (
                <ConfirmModal
                    title="Smazat směnu"
                    onClose={handleCancelDelete}
                    onConfirm={handleConfirmDelete}
                    confirmLabel="Smazat"
                >
                    <div className="confirm-details">
                        <p><strong>Prodejce:</strong> {selectedShift.user_jmeno}</p>
                        <p><strong>Datum:</strong> {formatShiftDate(selectedShift)}</p>
                        <p><strong>Role:</strong> {shiftRoleLabel(selectedShift)}</p>
                        {!isAbsenceShift(selectedShift) && (
                            <>
                                <p><strong>Čas:</strong> {formatTime(selectedShift.cas_od)}-{formatTime(selectedShift.cas_do)}</p>
                                <p><strong>Prodejna:</strong> {selectedShift.prodejna_nazev || selectedShift.prodejna || prodejna}</p>
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