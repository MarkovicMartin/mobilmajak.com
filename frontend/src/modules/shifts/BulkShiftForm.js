import React, { useState, useEffect } from 'react';
import Modal from '../../components/Modal';
import { userAPI, storeAPI } from '../../services/api';
import './BulkShiftForm.css';
import UnifiedCalendar from './UnifiedCalendar';
import { isBackofficeUser, isAdminUser, BACKOFFICE_LOCATION, isBackofficeLocation, isBackofficeWorkShift, isHomeOfficeWorkShift, getAdminWorkMode, ADMIN_WORK_HOME_OFFICE, ADMIN_WORK_BACKOFFICE, ADMIN_WORK_STORE } from './shiftBackoffice';
import { isSenimoStore, extraPoziceSelectEnabled } from './shiftStoreHelpers';
import { format } from 'date-fns';
import { userMayEditShiftOnDate } from './shiftEditPolicy';

function BulkShiftForm({ user, onClose, onSuccess, initialDates = [], initialMonth = null }) {
    const [formData, setFormData] = useState(() => {
        const backoffice = isBackofficeUser(user);
        const admin = isAdminUser(user);
        return {
            prodejna: backoffice ? BACKOFFICE_LOCATION : (user?.prodejna_id || null),
            admin_work_mode: admin ? ADMIN_WORK_HOME_OFFICE : null,
            cas_od: '08:00',
            cas_do: '20:00',
            typ_smeny: 'prace',
            brigadnik_rezim: 'prodejce',
            pozice_smeny: backoffice ? 'backoffice' : 'prodej',
            poznamka: '',
            user_id: (user && ['ADMIN', 'VEDOUCI'].includes(user.role)) ? user.id : undefined,
        };
    });
    const [users, setUsers] = useState([]);
    const [stores, setStores] = useState([]);
    const [selectedDates, setSelectedDates] = useState(
        () => new Set(Array.isArray(initialDates) ? initialDates : []),
    );
    const [currentMonth, setCurrentMonth] = useState(() => {
        if (initialMonth) return initialMonth;
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [result, setResult] = useState(null);
    const [vacationBalance, setVacationBalance] = useState(null);

    // Automatické nastavení času pro Senimo
    useEffect(() => {
        (async () => {
            try {
                const data = await storeAPI.getStoreChoices();
                const list = data.stores || [];
                setStores(list);
                setFormData(prev => {
                    if (isBackofficeLocation(prev.prodejna)) return prev;
                    return { ...prev, prodejna: prev.prodejna || user?.prodejna_id || (list[0]?.id ?? null) };
                });
            } catch (_e) {}
        })();
    }, [user]);

    useEffect(() => {
        if (!(user && ['ADMIN', 'VEDOUCI'].includes(user.role))) return;
        const selected = users.find((u) => u.id === formData.user_id);
        if (!selected) return;
        if (isBackofficeUser(selected)) {
            setFormData((prev) => ({
                ...prev,
                prodejna: BACKOFFICE_LOCATION,
                pozice_smeny: 'backoffice',
                admin_work_mode: null,
            }));
        } else if (isAdminUser(selected)) {
            setFormData((prev) => ({
                ...prev,
                admin_work_mode: ADMIN_WORK_HOME_OFFICE,
                pozice_smeny: 'prodej',
                prodejna: prev.prodejna && !isBackofficeLocation(prev.prodejna) ? prev.prodejna : (stores[0]?.id ?? null),
            }));
        } else if (selected.prodejna_id) {
            setFormData((prev) => ({
                ...prev,
                prodejna: selected.prodejna_id,
                admin_work_mode: null,
            }));
        }
    }, [formData.user_id, users, user, stores]);

    useEffect(() => {
        if (isBackofficeLocation(formData.prodejna)) return;
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

    useEffect(() => {
        if (formData.typ_smeny === 'dovolena') {
            setFormData((prev) => ({ ...prev, cas_od: '08:00', cas_do: '16:00' }));
        }
    }, [formData.typ_smeny]);

    useEffect(() => {
        const targetUserId = formData.user_id || user?.id;
        if (!targetUserId) return;
        const rok = currentMonth.split('-')[0];
        (async () => {
            try {
                const params = new URLSearchParams({ rok });
                if (formData.user_id && ['ADMIN', 'VEDOUCI'].includes(user?.role)) {
                    params.set('user_id', String(formData.user_id));
                }
                const res = await fetch(`/api/shifts/vacation-balance/?${params}`, { credentials: 'include' });
                if (res.ok) {
                    setVacationBalance(await res.json());
                } else {
                    setVacationBalance(null);
                }
            } catch {
                setVacationBalance(null);
            }
        })();
    }, [formData.user_id, currentMonth, user]);

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

    const selectedUser = users.find((u) => u.id === formData.user_id) || user;
    const selectedStore = stores.find((s) => s.id === formData.prodejna);
    const servisPoziceEnabled = Boolean(selectedStore?.povolena_pozice_servis);
    const isSenimo = isSenimoStore(selectedStore);
    const extraPoziceEnabled = extraPoziceSelectEnabled(selectedStore);
    const backofficeUser = isBackofficeUser(selectedUser);
    const adminUser = isAdminUser(selectedUser);
    const isAbsence = formData.typ_smeny === 'dovolena' || formData.typ_smeny === 'nemoc';
    const adminWorkMode = adminUser
        ? (formData.admin_work_mode ?? getAdminWorkMode(formData.prodejna, formData.pozice_smeny))
        : null;
    const homeOfficeShift = isHomeOfficeWorkShift(
        selectedUser,
        formData.typ_smeny,
        formData.pozice_smeny,
        adminWorkMode,
    );
    const backofficeShift = isBackofficeWorkShift(
        selectedUser,
        formData.typ_smeny,
        formData.pozice_smeny,
        formData.prodejna,
        adminWorkMode,
    );
    const storeWorkShift = !isAbsence && !homeOfficeShift && !backofficeShift;
    const showPoziceSelect = storeWorkShift && formData.typ_smeny === 'prace' && (
        (adminUser && adminWorkMode === ADMIN_WORK_STORE) ||
        (!adminUser && (extraPoziceEnabled || backofficeUser) && !isBackofficeLocation(formData.prodejna))
    );
    const isBrigadnikShift = selectedUser?.role === 'BRIGADNIK' && formData.typ_smeny === 'prace';

    const handleSubmit = async () => {
        if (selectedDates.size === 0) {
            setError('Vyberte alespoň jeden den');
            return;
        }
        if (backofficeShift && !formData.poznamka?.trim()) {
            setError('U směny Backoffice je povinná poznámka – popište, co jste ten den dělali.');
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
            if (!isBrigadnikShift) {
                delete requestData.brigadnik_rezim;
            }
            if (!showPoziceSelect) {
                delete requestData.pozice_smeny;
            }
            if (homeOfficeShift || backofficeShift) {
                delete requestData.prodejna;
            }
            if (adminUser) {
                if (adminWorkMode === ADMIN_WORK_HOME_OFFICE) {
                    requestData.pozice_smeny = 'home_office';
                    delete requestData.prodejna;
                } else if (adminWorkMode === ADMIN_WORK_BACKOFFICE) {
                    requestData.pozice_smeny = 'backoffice';
                    delete requestData.prodejna;
                } else if (!showPoziceSelect) {
                    requestData.pozice_smeny = 'prodej';
                }
                delete requestData.admin_work_mode;
            } else if (backofficeShift) {
                requestData.pozice_smeny = 'backoffice';
            }
            if (isAbsence) {
                delete requestData.prodejna;
            }
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

    return (
        <Modal
            title="📝 Hromadné vytváření směn"
            onClose={onClose}
            size="md"
            contentClassName="bulk-shift-modal"
            bodyClassName="bulk-shift-body"
            footer={(
                <>
                    <button type="button" className="btn-cancel" onClick={onClose}>
                        Zrušit
                    </button>
                    <button
                        type="button"
                        className="btn-submit"
                        onClick={handleSubmit}
                        disabled={loading || selectedDates.size === 0}
                    >
                        {loading ? 'Přidávám…' : `Přidat směny (${selectedDates.size})`}
                    </button>
                </>
            )}
        >
                {vacationBalance?.eligible && (
                    <div className="vacation-balance-banner" style={{ margin: '0 1rem' }}>
                        🏖️ Dovolená {vacationBalance.rok}: zbývá{' '}
                        <strong>{vacationBalance.zbyva_h} h</strong>
                        {' '}(čerpáno {vacationBalance.cerpano_h} / fond {vacationBalance.fond_h} h
                        {vacationBalance.odeceno_deficit_h > 0
                            ? `, vč. ${vacationBalance.odeceno_deficit_h} h deficit fondu`
                            : ''})
                    </div>
                )}

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
                                {!isAbsence && adminUser && (
                                    <div className="form-group">
                                        <label className="form-label">Místo práce:</label>
                                        <select
                                            className="form-select"
                                            value={adminWorkMode}
                                            onChange={(e) => {
                                                const mode = e.target.value;
                                                if (mode === ADMIN_WORK_STORE) {
                                                    setFormData(prev => ({
                                                        ...prev,
                                                        admin_work_mode: mode,
                                                        pozice_smeny: 'prodej',
                                                        prodejna: prev.prodejna && !isBackofficeLocation(prev.prodejna)
                                                            ? prev.prodejna
                                                            : (stores[0]?.id ?? null),
                                                    }));
                                                } else if (mode === ADMIN_WORK_HOME_OFFICE) {
                                                    setFormData(prev => ({
                                                        ...prev,
                                                        admin_work_mode: mode,
                                                        pozice_smeny: 'home_office',
                                                    }));
                                                } else {
                                                    setFormData(prev => ({
                                                        ...prev,
                                                        admin_work_mode: mode,
                                                        prodejna: BACKOFFICE_LOCATION,
                                                        pozice_smeny: 'backoffice',
                                                    }));
                                                }
                                            }}
                                        >
                                            <option value={ADMIN_WORK_HOME_OFFICE}>Home office</option>
                                            <option value={ADMIN_WORK_BACKOFFICE}>Backoffice (popis v poznámce)</option>
                                            <option value={ADMIN_WORK_STORE}>Prodejna</option>
                                        </select>
                                    </div>
                                )}
                                {!isAbsence && storeWorkShift && (
                                <div className="form-group">
                                    <label className="form-label">Pobočka:</label>
                                    <select
                                        className="form-select"
                                        value={backofficeShift ? BACKOFFICE_LOCATION : (formData.prodejna || '')}
                                        onChange={(e) => {
                                            const raw = e.target.value;
                                            if (raw === BACKOFFICE_LOCATION) {
                                                setFormData(prev => ({
                                                    ...prev,
                                                    prodejna: BACKOFFICE_LOCATION,
                                                    pozice_smeny: 'backoffice',
                                                }));
                                            } else {
                                                setFormData(prev => ({
                                                    ...prev,
                                                    prodejna: Number(raw),
                                                    pozice_smeny: prev.pozice_smeny === 'backoffice' ? 'prodej' : prev.pozice_smeny,
                                                }));
                                            }
                                        }}
                                    >
                                        {backofficeUser && (
                                            <option value={BACKOFFICE_LOCATION}>Backoffice</option>
                                        )}
                                        {stores.map(s => (
                                            <option key={s.id} value={s.id}>
                                                {backofficeUser ? `${s.nazev} (výpomoc)` : s.nazev}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                )}

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

                                {isBrigadnikShift && (
                                    <div className="form-group">
                                        <label className="form-label">Režim brigádníka:</label>
                                        <select
                                            className="form-select"
                                            value={formData.brigadnik_rezim}
                                            onChange={(e) => setFormData(prev => ({...prev, brigadnik_rezim: e.target.value}))}
                                        >
                                            <option value="prodejce">Jako prodejce (100 bodů/h + provize)</option>
                                            <option value="vypomoc">Výpomoc (150 bodů/h, bez provize)</option>
                                        </select>
                                    </div>
                                )}

                                {showPoziceSelect && (
                                    <div className="form-group">
                                        <label className="form-label">Pozice na směně:</label>
                                        <select
                                            className="form-select"
                                            value={formData.pozice_smeny}
                                            onChange={(e) => setFormData(prev => ({ ...prev, pozice_smeny: e.target.value }))}
                                        >
                                            <option value="prodej">Prodej</option>
                                            {isSenimo && <option value="skoleni">Školení</option>}
                                            {servisPoziceEnabled && <option value="servis">Servisní technik</option>}
                                            {!isBrigadnikShift && <option value="vypomoc">Výpomoc</option>}
                                        </select>
                                        {!isBrigadnikShift && formData.pozice_smeny === 'vypomoc' && (
                                            <div className="time-info">
                                                Výpomoc nemění odměnu – jen slot na prodejně a případně cíle.
                                            </div>
                                        )}
                                    </div>
                                )}

                                {!isAbsence && (
                                <>
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
                                </>
                                )}

                                {isAbsence && (
                                    <p className="time-info" style={{ gridColumn: '1 / -1' }}>
                                        ℹ️ Dovolená a nemoc nejsou vázané na prodejnu.
                                    </p>
                                )}
                            </div>

                            <div className="form-group" style={{marginTop: '20px'}}>
                                <label className="form-label">
                                    {backofficeShift ? 'Co jste ten den dělali *' : 'Poznámka (volitelné)'}:
                                </label>
                                <textarea
                                    className="form-textarea"
                                    placeholder={backofficeShift
                                        ? 'Např. fakturace, objednávky u dodavatelů…'
                                        : 'Doplňující informace ke směně...'}
                                    value={formData.poznamka}
                                    onChange={(e) => setFormData(prev => ({...prev, poznamka: e.target.value }))}
                                    required={backofficeShift}
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
                                    enableDragSelect
                                    isDateEnabled={(date) => {
                                        if (user?.role === 'ADMIN') return true;
                                        const dateStr = format(date, 'yyyy-MM-dd');
                                        return userMayEditShiftOnDate(user, dateStr);
                                    }}
                                    onDateClick={(dateStr) => handleDateToggle(dateStr)}
                                    onDateDragSelect={(dateStr) => handleDateToggle(dateStr)}
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
        </Modal>
    );
}

export default BulkShiftForm; 