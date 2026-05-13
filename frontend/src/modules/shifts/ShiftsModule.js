import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import ShiftCalendar from './ShiftCalendar';
import ShiftForm from './ShiftForm';
import BulkShiftForm from './BulkShiftForm';
import ShiftOverview from './ShiftOverview';
import AttendancePanel from './AttendancePanel';
import './ShiftsModule.css';

// Mapování názvů prodejen na ID podle databáze
const PRODEJNY_MAP = {
    'Globus': 1,
    'Senimo': 2,
    'Zlín': 3,
    'Přerov': 4,
    'Vsetín': 5,
    'Šternberk': 6
};

const PRODEJNY_NAMES = Object.keys(PRODEJNY_MAP);

function ShiftsModule() {
    const { user } = useAuth(); // Použijeme AuthContext místo vlastního načítání
    const [activeView, setActiveView] = useState('calendar');
    // Inicializace s domovskou prodejnou uživatele
    const [selectedProdejna, setSelectedProdejna] = useState(null);
    
    console.log('ShiftsModule render - user:', user);
    console.log('ShiftsModule render - selectedProdejna:', selectedProdejna);
    const [currentMonth, setCurrentMonth] = useState(() => {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    });
    const [showForm, setShowForm] = useState(false);
    const [showBulkForm, setShowBulkForm] = useState(false);
    const [refreshTrigger, setRefreshTrigger] = useState(0);
    const [loading, setLoading] = useState(false);

    // Aktualizace vybrané prodejny když se načte uživatel
    useEffect(() => {
        console.log('useEffect triggered - user:', user);
        if (user?.prodejna_id) {
            console.log('Nastavuji domovskou prodejnu uživatele:', user.prodejna_id);
            setSelectedProdejna(user.prodejna_id);
        } else if (user && !selectedProdejna) {
            // Fallback pokud uživatel nemá prodejna_id
            console.log('Uživatel nemá prodejna_id, nastavuji výchozí prodejnu: 1');
            setSelectedProdejna(1);
        }
    }, [user]); // Odstranil jsem selectedProdejna z dependencies

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
            const url = `/api/shifts/export/?mesic=${currentMonth}${selectedProdejna ? `&prodejna=${selectedProdejna}` : ''}`;
            const response = await fetch(url, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const blob = await response.blob();

                // Odvodíme správnou příponu podle odpovědi serveru
                // (backend vrací .xlsx, případně .csv fallback).
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
                link.download = `smeny_${currentMonth}_${selectedProdejna || 'vsechny'}.${extension}`;
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

    if (loading) {
        return (
            <div className="shifts-module">
                <div className="loading">Načítání...</div>
            </div>
        );
    }

    return (
        <div className="shifts-module">
            <div className="shifts-header">
                <h2>📅 Správa směn</h2>
                
                {/* Navigace mezi pohledy */}
                <div className="view-tabs">
                    <button 
                        className={activeView === 'calendar' ? 'active' : ''}
                        onClick={() => setActiveView('calendar')}
                    >
                        📅 Kalendář
                    </button>
                    <button 
                        className={activeView === 'overview' ? 'active' : ''}
                        onClick={() => setActiveView('overview')}
                    >
                        📊 Přehled hodin
                    </button>
                    <button 
                        className={activeView === 'attendance' ? 'active' : ''}
                        onClick={() => setActiveView('attendance')}
                    >
                        ⏰ Docházka
                    </button>
                </div>
            </div>

            {/* Ovládací panel */}
            <div className="shifts-controls">
                {activeView === 'calendar' && (
                    <>
                        {/* Výběr prodejny */}
                        <div className="prodejna-selector">
                            <label>Prodejna:</label>
                            <select 
                                value={selectedProdejna} 
                                onChange={(e) => setSelectedProdejna(e.target.value)}
                            >
                                {PRODEJNY_NAMES.map(prodejna => (
                                    <option key={prodejna} value={PRODEJNY_MAP[prodejna]}>
                                        {prodejna}
                                        {user && prodejna === user.prodejna && ' (domácí)'}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Navigace měsíců */}
                        <div className="month-navigation">
                            <button onClick={() => handleMonthChange('prev')}>
                                ◀ Předchozí
                            </button>
                            <span className="current-month">
                                {formatMonthName(currentMonth)}
                            </span>
                            <button onClick={() => handleMonthChange('next')}>
                                Následující ▶
                            </button>
                        </div>

                        {/* Akční tlačítka */}
                        <div className="action-buttons">
                            <button 
                                className="btn-primary" 
                                onClick={() => setShowForm(true)}
                            >
                                ➕ Přidat směnu
                            </button>
                            <button 
                                className="btn-secondary" 
                                onClick={() => setShowBulkForm(true)}
                            >
                                📝 Hromadně
                            </button>
                            {user?.role === 'ADMIN' && (
                                <button 
                                    className="btn-export" 
                                    onClick={handleExport}
                                >
                                    📊 Export
                                </button>
                            )}
                        </div>
                    </>
                )}
            </div>

            {/* Obsah */}
            <div className="shifts-content">
                {activeView === 'calendar' && selectedProdejna && (
                    <ShiftCalendar
                        prodejna={selectedProdejna}
                        month={currentMonth}
                        user={user}
                        refreshTrigger={refreshTrigger}
                        onRefresh={() => {
                            // Místo obnovení celé stránky jen obnovíme kalendář
                            setRefreshTrigger(prev => prev + 1);
                        }}
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
                    <AttendancePanel
                        user={user}
                    />
                )}
            </div>

            {/* Modální okna */}
            {showForm && (
                <ShiftForm
                    user={user}
                    onClose={() => setShowForm(false)}
                    onSuccess={() => {
                        setShowForm(false);
                        // Obnovíme kalendář po úspěšném vytvoření směny
                        setRefreshTrigger(prev => prev + 1);
                    }}
                />
            )}

            {showBulkForm && (
                <BulkShiftForm
                    user={user}
                    onClose={() => setShowBulkForm(false)}
                    onSuccess={() => {
                        setShowBulkForm(false);
                        // Obnovíme kalendář po úspěšném vytvoření směn
                        setRefreshTrigger(prev => prev + 1);
                    }}
                />
            )}
        </div>
    );
}

export default ShiftsModule; 