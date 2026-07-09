import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { storeAPI } from '../../services/api';
import { PageHeader, Select } from '../../components/ui';
import ShiftCalendar from './ShiftCalendar';
import ShiftForm from './ShiftForm';
import BulkShiftForm from './BulkShiftForm';
import ShiftOverview from './ShiftOverview';
import AttendancePanel from './AttendancePanel';
import PayrollPanel from './PayrollPanel';
import AttendanceLogPanel from './AttendanceLogPanel';
import AbsentStoresPanel from './AbsentStoresPanel';
import VacationPanel from './VacationPanel';
import ShiftsNav from './ShiftsNav';
import { BACKOFFICE_LOCATION } from './shiftBackoffice';
import './ShiftsModule.css';

const ALL_PRODEJNY = 'vse';

/** Výchozí filtr kalendáře: admin + brigádník = všechny (prodejny / vlastní směny), prodejce = domácí prodejna. */
function defaultCalendarProdejna(user) {
    if (!user) return ALL_PRODEJNY;
    if (user.role === 'ADMIN' || user.role === 'BRIGADNIK') {
        return ALL_PRODEJNY;
    }
    if (user.prodejna_id) {
        return String(user.prodejna_id);
    }
    return ALL_PRODEJNY;
}

function ShiftsModule() {
    const location = useLocation();
    const { user } = useAuth();
    const [activeView, setActiveView] = useState('calendar');
    const [stores, setStores] = useState([]);
    const [selectedProdejna, setSelectedProdejna] = useState(() => defaultCalendarProdejna(user));
    const [currentMonth, setCurrentMonth] = useState(() => {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    });
    const [showForm, setShowForm] = useState(false);
    const [showBulkForm, setShowBulkForm] = useState(false);
    const [bulkInitialDates, setBulkInitialDates] = useState([]);
    const [formInitialDatum, setFormInitialDatum] = useState('');
    const [editShift, setEditShift] = useState(null);
    const [refreshTrigger, setRefreshTrigger] = useState(0);
    const [shiftsSeeAllEmployees, setShiftsSeeAllEmployees] = useState(false);
    const adminDefaultStoresSet = useRef(false);

    useEffect(() => {
        (async () => {
            try {
                const data = await storeAPI.getStoreChoices();
                if (data.success && Array.isArray(data.stores)) {
                    setStores(data.stores);
                }
            } catch (_e) {
                /* ignore */
            }
        })();
    }, []);

    useEffect(() => {
        if (!user || adminDefaultStoresSet.current) return;
        setSelectedProdejna(defaultCalendarProdejna(user));
        adminDefaultStoresSet.current = true;
    }, [user]);

    const isAdmin = user?.role === 'ADMIN';

    useEffect(() => {
        const st = location.state;
        if (!st) return;
        if (st.view) {
            const adminOnlyViews = new Set(['vacation', 'payroll', 'absent-stores', 'attendance-log']);
            if (adminOnlyViews.has(st.view) && !isAdmin) {
                setActiveView('calendar');
            } else {
                setActiveView(st.view);
            }
        }
        if (st.month) setCurrentMonth(st.month);
        if (st.datum) {
            setActiveView('calendar');
            if (st.openForm) {
                setFormInitialDatum(st.datum);
                setShowForm(true);
            }
        }
    }, [location.key, location.state?.view, isAdmin]);

    const handleMonthChange = (direction) => {
        const [year, month] = currentMonth.split('-').map(Number);
        const date = new Date(year, month - 1, 1);

        if (direction === 'prev') {
            date.setMonth(date.getMonth() - 1);
        } else {
            date.setMonth(date.getMonth() + 1);
        }

        const newMonth = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
        setCurrentMonth(newMonth);
    };

    const formatMonthName = (monthStr) => {
        const [year, month] = monthStr.split('-').map(Number);
        const date = new Date(year, month - 1);
        return date.toLocaleDateString('cs-CZ', { month: 'long', year: 'numeric' });
    };

    const handleExport = async () => {
        try {
            const prodejnaParam = selectedProdejna === ALL_PRODEJNY ? '' : `&prodejna=${selectedProdejna}`;
            const url = `/api/shifts/export/?mesic=${currentMonth}${prodejnaParam}`;
            const response = await fetch(url, {
                credentials: 'include',
            });

            if (response.ok) {
                const blob = await response.blob();

                let extension = 'xlsx';
                const disposition = response.headers.get('Content-Disposition') || '';
                const dispMatch = disposition.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
                if (dispMatch && dispMatch[1]) {
                    const extMatch = dispMatch[1].match(/\.([a-z0-9]+)$/i);
                    if (extMatch) extension = extMatch[1].toLowerCase();
                } else {
                    const contentType = (response.headers.get('Content-Type') || '').toLowerCase();
                    if (contentType.includes('csv') || contentType.startsWith('text/')) {
                        extension = 'csv';
                    } else if (contentType.includes('spreadsheetml')) {
                        extension = 'xlsx';
                    }
                }

                const downloadUrl = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = downloadUrl;
                link.download = `smeny_${currentMonth}_${selectedProdejna === ALL_PRODEJNY ? 'vsechny' : selectedProdejna}.${extension}`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                window.URL.revokeObjectURL(downloadUrl);
            } else {
                alert('Chyba při exportu dat');
            }
        } catch (error) {
            console.error('Chyba při exportu:', error);
            alert('Chyba při exportu dat');
        }
    };

    const storeLabel = (store) => {
        const name = store.nazev_kratkiy || store.nazev;
        if (user?.prodejna_id && store.id === user.prodejna_id) {
            return `${name} (domácí)`;
        }
        return name;
    };

    const storeSelectOptions = useMemo(() => [
        {
            value: ALL_PRODEJNY,
            label: shiftsSeeAllEmployees || user?.role === 'ADMIN'
                ? 'Všechny prodejny'
                : 'Moje směny (všechny prodejny)',
        },
        ...stores.map((store) => ({
            value: String(store.id),
            label: storeLabel(store),
        })),
        {
            value: BACKOFFICE_LOCATION,
            label: 'Backoffice',
        },
    ], [stores, user?.prodejna_id, user?.role, shiftsSeeAllEmployees]);

    const showMonthControls = activeView === 'calendar' || activeView === 'overview' || activeView === 'payroll';

    return (
        <div className="shifts-module">
            <PageHeader title="Směny" />

            <ShiftsNav
                activeView={activeView}
                onViewChange={setActiveView}
                isAdmin={isAdmin}
            />

            {showMonthControls && (
                <div className="shifts-controls">
                    <div className="shifts-controls__calendar-row">
                        {activeView === 'calendar' && (
                            <div className="prodejna-selector">
                                <label htmlFor="shifts-prodejna-select">Prodejna</label>
                                <Select
                                    id="shifts-prodejna-select"
                                    options={storeSelectOptions}
                                    value={selectedProdejna}
                                    onChange={setSelectedProdejna}
                                    aria-label="Filtr prodejny"
                                />
                            </div>
                        )}

                        <div className="month-navigation">
                            <button type="button" onClick={() => handleMonthChange('prev')}>
                                ◀ Předchozí
                            </button>
                            <span className="current-month">
                                {formatMonthName(currentMonth)}
                            </span>
                            <button type="button" onClick={() => handleMonthChange('next')}>
                                Následující ▶
                            </button>
                        </div>

                        {activeView === 'calendar' && (
                            <div className="action-buttons">
                                <button
                                    type="button"
                                    className="btn-primary"
                                    onClick={() => {
                                        setFormInitialDatum('');
                                        setEditShift(null);
                                        setShowForm(true);
                                    }}
                                >
                                    ➕ Přidat směnu
                                </button>
                                <button
                                    type="button"
                                    className="btn-secondary"
                                    onClick={() => {
                                        setBulkInitialDates([]);
                                        setShowBulkForm(true);
                                    }}
                                >
                                    📝 Hromadně
                                </button>
                                {user?.role === 'ADMIN' && (
                                    <button
                                        type="button"
                                        className="btn-export"
                                        onClick={handleExport}
                                    >
                                        📊 Export
                                    </button>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            )}

            <div className="shifts-content">
                {activeView === 'calendar' && selectedProdejna && (
                    <ShiftCalendar
                        prodejna={selectedProdejna}
                        month={currentMonth}
                        user={user}
                        allStores={selectedProdejna === ALL_PRODEJNY}
                        stores={stores}
                        refreshTrigger={refreshTrigger}
                        onRefresh={() => setRefreshTrigger((prev) => prev + 1)}
                        onRequestBulkAdd={(dates) => {
                            setBulkInitialDates(dates);
                            setShowBulkForm(true);
                        }}
                        onRequestSingleAdd={(dateStr) => {
                            setFormInitialDatum(dateStr);
                            setEditShift(null);
                            setShowForm(true);
                        }}
                        onRequestEdit={(shift) => {
                            setEditShift(shift);
                            setFormInitialDatum('');
                            setShowForm(true);
                        }}
                        onFeatureFlagsChange={({ shiftsSeeAllEmployees: enabled }) => {
                            setShiftsSeeAllEmployees(Boolean(enabled));
                        }}
                    />
                )}

                {activeView === 'overview' && (
                    <ShiftOverview
                        user={user}
                        month={currentMonth}
                    />
                )}

                {activeView === 'vacation' && isAdmin && (
                    <VacationPanel user={user} />
                )}

                {activeView === 'attendance' && (
                    <AttendancePanel user={user} />
                )}

                {activeView === 'payroll' && user?.role === 'ADMIN' && (
                    <PayrollPanel
                        month={currentMonth}
                        onExport={handleExport}
                    />
                )}

                {activeView === 'absent-stores' && user?.role === 'ADMIN' && (
                    <AbsentStoresPanel />
                )}

                {activeView === 'attendance-log' && user?.role === 'ADMIN' && (
                    <AttendanceLogPanel month={currentMonth} />
                )}
            </div>

            {showForm && (
                <ShiftForm
                    key={editShift?.id ?? `new-${formInitialDatum || 'blank'}`}
                    user={user}
                    initialDatum={formInitialDatum}
                    editShift={editShift}
                    onClose={() => {
                        setShowForm(false);
                        setFormInitialDatum('');
                        setEditShift(null);
                    }}
                    onSuccess={() => {
                        setShowForm(false);
                        setFormInitialDatum('');
                        setEditShift(null);
                        setRefreshTrigger((prev) => prev + 1);
                    }}
                />
            )}

            {showBulkForm && (
                <BulkShiftForm
                    user={user}
                    initialDates={bulkInitialDates}
                    initialMonth={currentMonth}
                    onClose={() => {
                        setShowBulkForm(false);
                        setBulkInitialDates([]);
                    }}
                    onSuccess={() => {
                        setShowBulkForm(false);
                        setBulkInitialDates([]);
                        setRefreshTrigger((prev) => prev + 1);
                    }}
                />
            )}
        </div>
    );
}

export default ShiftsModule;
