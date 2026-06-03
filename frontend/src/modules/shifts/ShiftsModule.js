import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { storeAPI } from '../../services/api';
import ShiftCalendar from './ShiftCalendar';
import ShiftForm from './ShiftForm';
import BulkShiftForm from './BulkShiftForm';
import ShiftOverview from './ShiftOverview';
import AttendancePanel from './AttendancePanel';
import PayrollPanel from './PayrollPanel';
import AttendanceLogPanel from './AttendanceLogPanel';
import AbsentStoresPanel from './AbsentStoresPanel';
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
    const { user } = useAuth();
    const isShiftCalendarAdmin = user?.role === 'ADMIN';
    const [activeView, setActiveView] = useState('calendar');
    const [stores, setStores] = useState([]);
    const [selectedProdejna, setSelectedProdejna] = useState(() => defaultCalendarProdejna(user));
    const [currentMonth, setCurrentMonth] = useState(() => {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    });
    const [showForm, setShowForm] = useState(false);
    const [showBulkForm, setShowBulkForm] = useState(false);
    const [refreshTrigger, setRefreshTrigger] = useState(0);
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

    return (
        <div className="shifts-module">
            <div className="shifts-header">
                <h2>📅 Správa směn</h2>

                <div className="view-tabs">
                    <button
                        type="button"
                        className={activeView === 'calendar' ? 'active' : ''}
                        onClick={() => setActiveView('calendar')}
                    >
                        📅 Kalendář
                    </button>
                    <button
                        type="button"
                        className={activeView === 'overview' ? 'active' : ''}
                        onClick={() => setActiveView('overview')}
                    >
                        📊 Přehled hodin
                    </button>
                    <button
                        type="button"
                        className={activeView === 'attendance' ? 'active' : ''}
                        onClick={() => setActiveView('attendance')}
                    >
                        ⏰ Docházka
                    </button>
                    {user?.role === 'ADMIN' && (
                        <>
                            <button
                                type="button"
                                className={activeView === 'payroll' ? 'active' : ''}
                                onClick={() => setActiveView('payroll')}
                            >
                                💰 Výplata
                            </button>
                            <button
                                type="button"
                                className={activeView === 'absent-stores' ? 'active' : ''}
                                onClick={() => setActiveView('absent-stores')}
                            >
                                🚨 Není v práci
                            </button>
                            <button
                                type="button"
                                className={activeView === 'attendance-log' ? 'active' : ''}
                                onClick={() => setActiveView('attendance-log')}
                            >
                                📋 Docházka log
                            </button>
                        </>
                    )}
                </div>
            </div>

            <div className="shifts-controls">
                {activeView === 'calendar' && (
                    <div className="shifts-controls__calendar-row">
                        <div className="prodejna-selector">
                            <label htmlFor="shifts-prodejna-select">Prodejna:</label>
                            <select
                                id="shifts-prodejna-select"
                                value={selectedProdejna}
                                onChange={(e) => setSelectedProdejna(e.target.value)}
                            >
                                <option value={ALL_PRODEJNY}>
                                    {isShiftCalendarAdmin ? 'Všechny prodejny' : 'Moje směny (všechny prodejny)'}
                                </option>
                                {stores.map((store) => (
                                    <option key={store.id} value={store.id}>
                                        {storeLabel(store)}
                                    </option>
                                ))}
                            </select>
                        </div>

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

                        <div className="action-buttons">
                            <button
                                type="button"
                                className="btn-primary"
                                onClick={() => setShowForm(true)}
                            >
                                ➕ Přidat směnu
                            </button>
                            <button
                                type="button"
                                className="btn-secondary"
                                onClick={() => setShowBulkForm(true)}
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
                    </div>
                )}
            </div>

            <div className="shifts-content">
                {activeView === 'calendar' && selectedProdejna && (
                    <ShiftCalendar
                        prodejna={selectedProdejna}
                        month={currentMonth}
                        user={user}
                        allStores={selectedProdejna === ALL_PRODEJNY}
                        stores={stores}
                        showAllEmployees={isShiftCalendarAdmin}
                        refreshTrigger={refreshTrigger}
                        onRefresh={() => setRefreshTrigger((prev) => prev + 1)}
                    />
                )}

                {activeView === 'overview' && (
                    <ShiftOverview
                        user={user}
                        month={currentMonth}
                        onMonthChange={setCurrentMonth}
                    />
                )}

                {activeView === 'attendance' && (
                    <AttendancePanel user={user} />
                )}

                {activeView === 'payroll' && user?.role === 'ADMIN' && (
                    <PayrollPanel
                        month={currentMonth}
                        onMonthChange={setCurrentMonth}
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
                    user={user}
                    onClose={() => setShowForm(false)}
                    onSuccess={() => {
                        setShowForm(false);
                        setRefreshTrigger((prev) => prev + 1);
                    }}
                />
            )}

            {showBulkForm && (
                <BulkShiftForm
                    user={user}
                    onClose={() => setShowBulkForm(false)}
                    onSuccess={() => {
                        setShowBulkForm(false);
                        setRefreshTrigger((prev) => prev + 1);
                    }}
                />
            )}
        </div>
    );
}

export default ShiftsModule;
