import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { AnalyticsDateInput } from '../../components/AnalyticsDateRange';
import { userAPI, storeAPI } from '../../services/api';
import { useModalKeyboard } from '../../utils/useModalKeyboard';
import './ShiftForm.css';

function ShiftForm({ user, onClose, onSuccess, initialDatum = '' }) {
    const [formData, setFormData] = useState({
        datum: initialDatum || '',
        prodejna: user?.prodejna_id || null,
        cas_od: '08:00',
        cas_do: '20:00',
        typ_smeny: 'prace',
        brigadnik_rezim: 'prodejce',
        poznamka: '',
        // user_id pouze pro ADMIN/VEDOUCI (jinak necháváme nevyplněné)
        user_id: (user && ['ADMIN', 'VEDOUCI'].includes(user.role)) ? user.id : undefined,
    });
    const [users, setUsers] = useState([]);
    const [stores, setStores] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [existingShiftInfo, setExistingShiftInfo] = useState(null);
    const [vacationBalance, setVacationBalance] = useState(null);
    const shiftFormRef = useRef(null);

    useModalKeyboard(true, { onClose, formRef: shiftFormRef });

    // Načtení prodejen z DB (choices)
    useEffect(() => {
        (async () => {
            try {
                const data = await storeAPI.getStoreChoices();
                const list = data.stores || [];
                setStores(list);
                // Nastav výchozí prodejnu
                setFormData(prev => ({
                    ...prev,
                    prodejna: prev.prodejna || user?.prodejna_id || (list[0]?.id ?? null)
                }));
            } catch (_e) {
                // fallback bez store listu
            }
        })();
    }, [user]);

    // Automatické nastavení času podle prodejny (podle názvu)
    useEffect(() => {
        const storeName = stores.find(s => s.id === formData.prodejna)?.nazev;
        if (storeName === 'Senimo') {
            // Zkontrolujeme, zda je to sobota
            if (formData.datum) {
                const datum = new Date(formData.datum);
                const denVTydnu = datum.getDay(); // 0 = neděle, 6 = sobota
                
                if (denVTydnu === 6) { // Sobota
                    setFormData(prev => ({
                        ...prev,
                        cas_od: '09:00',
                        cas_do: '12:00'
                    }));
                } else { // Ostatní dny
                    setFormData(prev => ({
                        ...prev,
                        cas_od: '09:00',
                        cas_do: '18:00'
                    }));
                }
            } else {
                // Výchozí čas pro Senimo (všední den)
                setFormData(prev => ({
                    ...prev,
                    cas_od: '09:00',
                    cas_do: '18:00'
                }));
            }
        } else {
            // Standardní čas pro ostatní prodejny
            setFormData(prev => ({
                ...prev,
                cas_od: '08:00',
                cas_do: '20:00'
            }));
        }
    }, [formData.prodejna, formData.datum, stores]);

    // Načtení uživatelů pro ADMIN/VEDOUCI
    useEffect(() => {
        const canAssignOthers = user && ['ADMIN', 'VEDOUCI'].includes(user.role);
        if (!canAssignOthers) return;
        (async () => {
            try {
                const resp = await userAPI.getUsers();
                if (resp.success) {
                    setUsers(resp.users.filter(u => u.aktivni));
                    // default na sebe, pokud ještě není
                    setFormData(prev => ({ ...prev, user_id: prev.user_id || user.id }));
                }
            } catch (_e) {
                // tiše ignorujeme, UI funguje bez seznamu
            }
        })();
    }, [user]);

    // Když se změní vybraný uživatel, nastav výchozí prodejnu podle jeho domovské prodejny
    useEffect(() => {
        if (!users || users.length === 0) return;
        if (!(user && ['ADMIN', 'VEDOUCI'].includes(user.role))) return;
        const selected = users.find(u => u.id === formData.user_id);
        if (selected && selected.prodejna_id) {
            setFormData(prev => ({ ...prev, prodejna: selected.prodejna_id }));
        }
    }, [formData.user_id, users, user]);

    useEffect(() => {
        const targetUserId = formData.user_id || user?.id;
        if (!targetUserId) return;
        const rok = formData.datum
            ? new Date(formData.datum).getFullYear()
            : new Date().getFullYear();
        (async () => {
            try {
                const params = new URLSearchParams({ rok: String(rok) });
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
    }, [formData.user_id, formData.datum, user]);

    useEffect(() => {
        if (formData.typ_smeny === 'dovolena') {
            setFormData((prev) => ({ ...prev, cas_od: '08:00', cas_do: '16:00' }));
        }
    }, [formData.typ_smeny]);

    const handleClose = () => {
        setError('');
        setExistingShiftInfo(null);
        onClose();
    };

    const selectedUser = users.find((u) => u.id === formData.user_id) || user;
    const isAbsence = formData.typ_smeny === 'dovolena' || formData.typ_smeny === 'nemoc';
    const isBrigadnikShift = selectedUser?.role === 'BRIGADNIK' && formData.typ_smeny === 'prace';

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        setExistingShiftInfo(null);

        try {
            const payload = { ...formData };
            if (!isBrigadnikShift) {
                delete payload.brigadnik_rezim;
            }
            if (isAbsence) {
                delete payload.prodejna;
            }
            // Pokud není ADMIN/VEDOUCI, neposíláme user_id
            if (!(user && ['ADMIN', 'VEDOUCI'].includes(user.role))) {
                delete payload.user_id;
            }

            const response = await fetch('/api/shifts/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                onSuccess();
            } else {
                const data = await response.json();
                
                // Specifické zpracování pro duplicitní směnu (409 Conflict)
                if (response.status === 409 && data.existing_shift) {
                    setError(data.error);
                    setExistingShiftInfo(data.existing_shift);
                } else {
                    setError(data.error || 'Chyba při vytváření směny');
                    setExistingShiftInfo(null);
                }
            }
        } catch (error) {
            setError('Chyba při vytváření směny');
        } finally {
            setLoading(false);
        }
    };

    return createPortal(
        <div className="shift-form-overlay" onClick={handleClose}>
            <div
                className="shift-form-modal"
                onClick={(e) => e.stopPropagation()}
                role="dialog"
                aria-labelledby="shift-form-title"
            >
                <div className="shift-form-header">
                    <h3 id="shift-form-title">➕ Přidat novou směnu</h3>
                    <button
                        type="button"
                        className="modal-close"
                        onClick={handleClose}
                        aria-label="Zavřít"
                    >
                        ✕
                    </button>
                </div>

                <form ref={shiftFormRef} className="shift-form-shell" onSubmit={handleSubmit}>
                    <div className="shift-form-body">
                        {vacationBalance?.eligible && (
                            <div className="vacation-balance-banner">
                                🏖️ Dovolená {vacationBalance.rok}: zbývá{' '}
                                <strong>{vacationBalance.zbyva_h} h</strong>
                                {' '}(čerpáno {vacationBalance.cerpano_h} / fond {vacationBalance.fond_h} h
                                {vacationBalance.odeceno_deficit_h > 0
                                    ? `, vč. ${vacationBalance.odeceno_deficit_h} h deficit fondu`
                                    : ''}
                                {vacationBalance.prevod_h > 0 ? `, převod ${vacationBalance.prevod_h} h` : ''})
                            </div>
                        )}
                    {(user && ['ADMIN', 'VEDOUCI'].includes(user.role)) && (
                        <div className="form-group">
                            <label>Uživatel:</label>
                            <select
                                value={formData.user_id ?? ''}
                                onChange={(e) => setFormData({ ...formData, user_id: Number(e.target.value) })}
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
                    <div className="form-group shift-form-date-group">
                        <AnalyticsDateInput
                            label="Datum:"
                            value={formData.datum}
                            onApply={(datum) => setFormData(prev => ({ ...prev, datum }))}
                            wrapperClassName="form-group shift-form-date-group"
                            showError={false}
                            required
                        />
                    </div>

                    {!isAbsence && (
                    <>
                    <div className="form-group">
                        <label>Prodejna:</label>
                        <select
                            value={formData.prodejna || ''}
                            onChange={(e) => setFormData({...formData, prodejna: Number(e.target.value)})}
                        >
                            {stores.map(s => (
                                <option key={s.id} value={s.id}>
                                    {s.nazev}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="shift-form-datetime-row">
                        <div className="form-group">
                            <label>Od:</label>
                            <input
                                type="time"
                                value={formData.cas_od}
                                onChange={(e) => setFormData({...formData, cas_od: e.target.value})}
                                required
                            />
                        </div>
                        <div className="form-group">
                            <label>Do:</label>
                            <input
                                type="time"
                                value={formData.cas_do}
                                onChange={(e) => setFormData({...formData, cas_do: e.target.value})}
                                required
                            />
                        </div>
                    </div>

                    {formData.prodejna === 'Senimo' && (
                        <div className="time-info">
                            ℹ️ Senimo: Po-Pá 9:00-18:00, So 9:00-12:00
                        </div>
                    )}
                    
                    {formData.prodejna !== 'Senimo' && (
                        <div className="time-info">
                            ℹ️ Standardní směna: 8:00-20:00
                        </div>
                    )}
                    </>
                    )}

                    {isAbsence && (
                        <div className="time-info">
                            ℹ️ Dovolená a nemoc nejsou vázané na prodejnu – v kalendáři se zobrazí kompaktně.
                        </div>
                    )}

                    <div className="form-group">
                        <label>Typ směny:</label>
                        <select
                            value={formData.typ_smeny}
                            onChange={(e) => setFormData({...formData, typ_smeny: e.target.value})}
                        >
                            <option value="prace">💼 Práce</option>
                            <option value="dovolena">🏖️ Dovolená</option>
                            <option value="nemoc">🏥 Nemocenská</option>
                        </select>
                    </div>

                    {isBrigadnikShift && (
                        <div className="form-group">
                            <label>Režim brigádníka:</label>
                            <select
                                value={formData.brigadnik_rezim}
                                onChange={(e) => setFormData({...formData, brigadnik_rezim: e.target.value})}
                            >
                                <option value="prodejce">Jako prodejce (100 bodů/h + provize)</option>
                                <option value="vypomoc">Výpomoc (150 bodů/h, bez provize)</option>
                            </select>
                        </div>
                    )}

                    <div className="form-group">
                        <label>Poznámka:</label>
                        <textarea
                            value={formData.poznamka}
                            onChange={(e) => setFormData({...formData, poznamka: e.target.value})}
                            placeholder="Volitelná poznámka..."
                        />
                    </div>

                        {error && (
                            <div className="error-message">
                                <div>{error}</div>
                                {existingShiftInfo && (
                                    <div className="existing-shift-info">
                                        <strong>Stávající směna:</strong><br/>
                                        📅 {existingShiftInfo.cas_od}-{existingShiftInfo.cas_do}<br/>
                                        📋 {existingShiftInfo.typ_smeny === 'prace' ? 'Práce' : 
                                            existingShiftInfo.typ_smeny === 'dovolena' ? 'Dovolená' : 'Nemoc'}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    <div className="shift-form-actions">
                        <button type="button" onClick={handleClose} className="btn-cancel">
                            Zrušit
                        </button>
                        <button type="submit" disabled={loading} className="btn-submit">
                            {loading ? 'Ukládání...' : 'Uložit směnu'}
                        </button>
                    </div>
                </form>
            </div>
        </div>,
        document.body
    );
}

export default ShiftForm; 