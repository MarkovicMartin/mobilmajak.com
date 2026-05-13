import React, { useState, useEffect } from 'react';
import { userAPI, storeAPI } from '../../services/api';
import './BulkShiftForm.css';
import UnifiedCalendar from './UnifiedCalendar';
import { parse, isBefore } from 'date-fns';

const PRODEJNY = ['Globus', 'Senimo', 'Zlín', 'Přerov', 'Vsetín', 'Šternberk'];

function BulkShiftForm({ user, onClose, onSuccess }) {
    const [formData, setFormData] = useState({
        prodejna: user?.prodejna_id || null,
        cas_od: '08:00',
        cas_do: '20:00',
        typ_smeny: 'prace',
        poznamka: '',
        user_id: (user && ['ADMIN', 'VEDOUCI'].includes(user.role)) ? user.id : undefined,
    });
    const [users, setUsers] = useState([]);
    const [stores, setStores] = useState([]);
    const [selectedDates, setSelectedDates] = useState(new Set());
    const [currentMonth, setCurrentMonth] = useState(() => {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [result, setResult] = useState(null);

    // Automatické nastavení času pro Senimo
    useEffect(() => {
        (async () => {
            try {
                const data = await storeAPI.getStoreChoices();
                const list = data.stores || [];
                setStores(list);
                setFormData(prev => ({ ...prev, prodejna: prev.prodejna || user?.prodejna_id || (list[0]?.id ?? null) }));
            } catch (_e) {}
        })();
    }, [user]);

    useEffect(() => {
        const storeName = stores.find(s => s.id === formData.prodejna)?.nazev;
        if (storeName === 'Senimo') {
            setFormData(prev => ({
                ...prev,
                cas_od: '09:00',
                cas_do: '18:00'
            }));
        } else {
            setFormData(prev => ({
                ...prev,
                cas_od: '08:00',
                cas_do: '20:00'
            }));
        }
    }, [formData.prodejna, stores]);

    // Načtení uživatelů pro ADMIN/VEDOUCI
    useEffect(() => {
        const canAssignOthers = user && ['ADMIN', 'VEDOUCI'].includes(user.role);
        if (!canAssignOthers) return;
        (async () => {
            try {
                const resp = await userAPI.getUsers();
                if (resp.success) {
                    setUsers(resp.users.filter(u => u.aktivni));
                    setFormData(prev => ({ ...prev, user_id: prev.user_id || user.id }));
                }
            } catch (_e) {}
        })();
    }, [user]);

    const generateCalendar = () => {
        const [year, monthNum] = currentMonth.split('-').map(Number);
        const firstDay = new Date(year, monthNum - 1, 1);
        const lastDay = new Date(year, monthNum, 0);
        const daysInMonth = lastDay.getDate();
        const startDay = firstDay.getDay();
        
        const calendar = [];
        const daysFromPrevMonth = startDay === 0 ? 6 : startDay - 1;
        
        // Dny z předchozího měsíce (neaktivní)
        for (let i = daysFromPrevMonth; i > 0; i--) {
            const prevMonth = new Date(year, monthNum - 1, 0);
            const day = prevMonth.getDate() - i + 1;
            calendar.push({
                day,
                date: null,
                isCurrentMonth: false,
                isSelectable: false
            });
        }
        
        // Dny aktuálního měsíce
        const today = new Date();
        const currentMonthStart = new Date(year, monthNum - 1, 1);
        
        for (let day = 1; day <= daysInMonth; day++) {
            const date = new Date(year, monthNum - 1, day);
            // Oprava: Použijeme lokální formátování místo UTC
            const dateStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
            const isSelectable = (user && ['ADMIN', 'VEDOUCI'].includes(user.role)) || date >= currentMonthStart;
            
            calendar.push({
                day,
                date: dateStr,
                isCurrentMonth: true,
                isSelectable,
                isToday: date.toDateString() === today.toDateString()
            });
        }
        
        // Dny z následujícího měsíce (neaktivní)
        const totalCells = Math.ceil(calendar.length / 7) * 7;
        const remainingCells = totalCells - calendar.length;
        for (let day = 1; day <= remainingCells; day++) {
            calendar.push({
                day,
                date: null,
                isCurrentMonth: false,
                isSelectable: false
            });
        }
        
        return calendar;
    };

    const handleDateToggle = (dateStr) => {
        if (!dateStr) return;
        
        const newSelected = new Set(selectedDates);
        if (newSelected.has(dateStr)) {
            newSelected.delete(dateStr);
        } else {
            newSelected.add(dateStr);
        }
        setSelectedDates(newSelected);
    };

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

    const handleSubmit = async () => {
        if (selectedDates.size === 0) {
            setError('Vyberte alespoň jeden den');
            return;
        }

        setLoading(true);
        setError('');
        setResult(null);

        try {
            const requestData = {
                ...formData,
                datumy: Array.from(selectedDates)  // Oprava: backend očekává 'datumy'
            };
            if (!(user && ['ADMIN', 'VEDOUCI'].includes(user.role))) {
                delete requestData.user_id;
            }

            const response = await fetch('/api/shifts/bulk-create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify(requestData)
            });

            const data = await response.json();

            if (response.ok) {
                setResult(data);
                if (data.uspesne > 0) {  // Oprava: backend vrací 'uspesne'
                    setTimeout(() => {
                        onSuccess();
                    }, 2000);
                }
            } else {
                setError(data.error || 'Chyba při vytváření směn');
            }
        } catch (error) {
            console.error('Chyba při odesílání:', error);
            setError('Chyba při komunikaci se serverem');
        } finally {
            setLoading(false);
        }
    };

    const calendar = generateCalendar(); // kept for legacy but not used with UnifiedCalendar

    return (
        <div className="bulk-shift-overlay" onClick={onClose}>
            <div className="bulk-shift-modal" onClick={(e) => e.stopPropagation()}>
                {/* HLAVIČKA */}
                <div className="bulk-shift-header">
                    <h2 className="bulk-shift-title">
                        📝 Hromadné vytváření směn
                    </h2>
                    <button className="close-button" onClick={onClose}>
                        ✕
                    </button>
                </div>

                {/* OBSAH */}
                <div className="bulk-shift-content">
                    <div className="steps-container">
                        
                        {/* KROK 1: Základní informace */}
                        <div className="step-card">
                            <div className="step-header">
                                <div className="step-number">1</div>
                                <h3 className="step-title">Základní informace o směně</h3>
                            </div>
                            
                            <div className="form-grid">
                                {(user && ['ADMIN', 'VEDOUCI'].includes(user.role)) && (
                                    <div className="form-group">
                                        <label className="form-label">Uživatel:</label>
                                        <select
                                            className="form-select"
                                            value={formData.user_id ?? ''}
                                            onChange={(e) => setFormData(prev => ({...prev, user_id: Number(e.target.value)}))}
                                            disabled={!users.length}
                                        >
                                            <option value="" disabled>
                                                {users.length ? 'Vyberte uživatele…' : 'Načítám uživatele…'}
                                            </option>
                                            {users.map(u => (
                                                <option key={u.id} value={u.id}>
                                                    {u.jmeno} {u.prijmeni} (ID {u.id})
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                )}
                                <div className="form-group">
                                    <label className="form-label">Prodejna:</label>
                                    <select 
                                        className="form-select"
                                        value={formData.prodejna || ''}
                                        onChange={(e) => setFormData(prev => ({...prev, prodejna: Number(e.target.value)}))}
                                    >
                                        {stores.map(s => (
                                            <option key={s.id} value={s.id}>
                                                {s.nazev}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div className="form-group">
                                    <label className="form-label">Typ směny:</label>
                                    <select 
                                        className="form-select"
                                        value={formData.typ_smeny}
                                        onChange={(e) => setFormData(prev => ({...prev, typ_smeny: e.target.value}))}
                                    >
                                        <option value="prace">💼 Práce</option>
                                        <option value="dovolena">🏖️ Dovolená</option>
                                        <option value="nemoc">🏥 Nemoc</option>
                                    </select>
                                </div>

                                <div className="form-group">
                                    <label className="form-label">Od:</label>
                                    <input 
                                        type="time" 
                                        className="form-input"
                                        value={formData.cas_od}
                                        onChange={(e) => setFormData(prev => ({...prev, cas_od: e.target.value}))}
                                    />
                                </div>

                                <div className="form-group">
                                    <label className="form-label">Do:</label>
                                    <input 
                                        type="time" 
                                        className="form-input"
                                        value={formData.cas_do}
                                        onChange={(e) => setFormData(prev => ({...prev, cas_do: e.target.value}))}
                                    />
                                </div>
                            </div>

                            <div className="form-group" style={{marginTop: '20px'}}>
                                <label className="form-label">Poznámka (volitelné):</label>
                                <textarea 
                                    className="form-textarea"
                                    placeholder="Doplňující informace ke směně..."
                                    value={formData.poznamka}
                                    onChange={(e) => setFormData(prev => ({...prev, poznamka: e.target.value}))}
                                />
                            </div>
                        </div>

                        {/* KROK 2: Výběr dnů */}
                        <div className="step-card">
                            <div className="step-header">
                                <div className="step-number">2</div>
                                <h3 className="step-title">Vyberte dny pro směny</h3>
                            </div>

                            <div className="calendar-section">
                                <div className="calendar-header-info">
                                    <div className="month-selector">
                                        <button className="month-nav-btn" onClick={() => handleMonthChange('prev')}>◀</button>
                                        <span className="current-month-display">{formatMonthName(currentMonth)}</span>
                                        <button className="month-nav-btn" onClick={() => handleMonthChange('next')}>▶</button>
                                    </div>
                                    <div className="selected-count">Vybráno: {selectedDates.size} dnů</div>
                                </div>

                                <UnifiedCalendar
                                    month={currentMonth}
                                    variant="compact"
                                    selectedDates={selectedDates}
                                    isDateEnabled={(date) => {
                                        if (user && ['ADMIN', 'VEDOUCI'].includes(user.role)) return true;
                                        const firstOfMonth = parse(`${currentMonth}-01`, 'yyyy-MM-dd', new Date());
                                        return !isBefore(date, firstOfMonth);
                                    }}
                                    onDateClick={(dateStr) => handleDateToggle(dateStr)}
                                />
                            </div>
                        </div>

                        {/* VÝSLEDKY */}
                        {result && (
                            <div className="result-section">
                                <div className="success-message">
                                    ✅ Úspěšně vytvořeno: {result.uspesne} směn
                                </div>
                                {result.chyby && result.chyby.length > 0 && (
                                    <div style={{marginTop: '12px'}}>
                                        <strong>Chyby:</strong>
                                        <ul style={{margin: '8px 0', paddingLeft: '20px'}}>
                                            {result.chyby.map((error, idx) => (
                                                <li key={idx} style={{color: '#dc2626', fontSize: '14px'}}>
                                                    {error}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        )}

                        {error && (
                            <div className="error-message">
                                ⚠️ {error}
                            </div>
                        )}
                    </div>
                </div>

                {/* AKČNÍ TLAČÍTKA */
                /* Tlačítka jsou fixně viditelná (viz CSS .bulk-actions) a primární tlačítko má text 'Přidat směny' */}
                <div className="bulk-actions">
                    <button className="btn-cancel" onClick={onClose}>
                        Zrušit
                    </button>
                    <button 
                        className="btn-submit"
                        onClick={handleSubmit}
                        disabled={loading || selectedDates.size === 0}
                    >
                        {loading ? 'Přidávám…' : `Přidat směny (${selectedDates.size})`}
                    </button>
                </div>
            </div>
        </div>
    );
}

export default BulkShiftForm; 