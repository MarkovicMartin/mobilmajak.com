import React, { useState, useEffect } from 'react';
import { userAPI, storeAPI } from '../../services/api';
import './ShiftForm.css';

const PRODEJNY = ['Globus', 'Senimo', 'Zlín', 'Přerov', 'Vsetín', 'Šternberk'];

function ShiftForm({ user, onClose, onSuccess }) {
    const [formData, setFormData] = useState({
        datum: '',
        prodejna: user?.prodejna_id || null,
        cas_od: '08:00',
        cas_do: '20:00',
        typ_smeny: 'prace',
        poznamka: '',
        // user_id pouze pro ADMIN/VEDOUCI (jinak necháváme nevyplněné)
        user_id: (user && ['ADMIN', 'VEDOUCI'].includes(user.role)) ? user.id : undefined,
    });
    const [users, setUsers] = useState([]);
    const [stores, setStores] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [existingShiftInfo, setExistingShiftInfo] = useState(null);

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

    const handleClose = () => {
        setError('');
        setExistingShiftInfo(null);
        onClose();
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        setExistingShiftInfo(null);

        try {
            const payload = { ...formData };
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

    return (
        <div className="modal-overlay" onClick={handleClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <h3>➕ Přidat novou směnu</h3>
                
                <form onSubmit={handleSubmit}>
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
                    <div className="form-group">
                        <label>Datum:</label>
                        <input
                            type="date"
                            value={formData.datum}
                            onChange={(e) => setFormData({...formData, datum: e.target.value})}
                            required
                        />
                    </div>

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

                    <div className="form-row">
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

                    <div className="form-actions">
                        <button type="button" onClick={handleClose} className="btn-cancel">
                            Zrušit
                        </button>
                        <button type="submit" disabled={loading} className="btn-submit">
                            {loading ? 'Ukládání...' : 'Uložit směnu'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

export default ShiftForm; 