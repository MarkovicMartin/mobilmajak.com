import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { userAPI, storeAPI } from '../services/api';
import { prepareUserSubmitData, formatUserApiError, estimateNextUserId } from '../utils/userForm';
import {
    MZDA_DOPLNEK_TEMPLATES,
    createDoplnekFromTemplate,
    sumDoplnkyBody,
} from '../constants/mzdaDoplnkyTemplates';
import { formatBodyCount } from '../utils/formatBody';
import { manualNumberInputClass, preventNumberInputWheel } from '../utils/manualNumberInput';
import { useModalKeyboard } from '../utils/useModalKeyboard';
import {
    USER_ROLE_OPTIONS,
    BRIGADNIK_DEFAULT_BODY_ZA_HODINU,
    roleLabel,
    isBrigadnikRole,
} from '../constants/userRoles';
import './UserManagement.css';

const UserManagement = () => {
    const { user: currentUser } = useAuth();
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [formError, setFormError] = useState(null);
    const [submitting, setSubmitting] = useState(false);
    const [showAddForm, setShowAddForm] = useState(false);
    const [editingUser, setEditingUser] = useState(null);
    const [stores, setStores] = useState([]);
    const [showInactiveUsers, setShowInactiveUsers] = useState(false);
    const userFormRef = useRef(null);
    const [formData, setFormData] = useState({
        uzivatelske_jmeno: '',
        jmeno: '',
        prijmeni: '',
        heslo: '',
        role: 'PRODEJCE',
        aktivni: true,
        prodejna: '',
        technik_id: '',
        moduly: [],
        telefon: '',
        email: '',
        adresa: '',
        poznamka: '',
        mzda_zaklad: '',
        mzda_doplnky: [],
        vedouci_prodejna_id: '',
    });

    const nextUserIdPreview = estimateNextUserId(users);

    const { activeUsers, inactiveUsers } = useMemo(() => {
        const active = [];
        const inactive = [];
        (users || []).forEach((u) => {
            if (u.aktivni) active.push(u);
            else inactive.push(u);
        });
        return { activeUsers: active, inactiveUsers: inactive };
    }, [users]);

    const availableModules = ['analytics', 'shifts', 'news', 'access'];

    useEffect(() => {
        loadUsers();
        loadStores();
    }, []);

    const loadStores = async () => {
        try {
            const response = await storeAPI.getStoreChoices();
            if (response.success) {
                setStores(response.stores);
            }
        } catch (error) {
            console.error('Chyba při načítání prodejen:', error);
        }
    };

    const loadUsers = async () => {
        try {
            setLoading(true);
            const response = await userAPI.getUsers();
            if (response.success) {
                setUsers(response.users);
            } else {
                setError(response.message);
            }
        } catch (error) {
            setError('Chyba při načítání uživatelů');
        } finally {
            setLoading(false);
        }
    };

    const handleInputChange = (e) => {
        const { name, value, type, checked } = e.target;
        if (name === 'role') {
            setFormData((prev) => {
                const next = { ...prev, role: value };
                if (value === 'BRIGADNIK' && (prev.mzda_zaklad === '' || prev.mzda_zaklad == null)) {
                    next.mzda_zaklad = String(BRIGADNIK_DEFAULT_BODY_ZA_HODINU);
                }
                return next;
            });
            return;
        }
        setFormData((prev) => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value,
        }));
    };

    const handleModuleChange = (module) => {
        setFormData(prev => ({
            ...prev,
            moduly: prev.moduly.includes(module)
                ? prev.moduly.filter(m => m !== module)
                : [...prev.moduly, module]
        }));
    };

    const resetForm = () => {
        setFormData({
            uzivatelske_jmeno: '',
            jmeno: '',
            prijmeni: '',
            heslo: '',
            role: 'PRODEJCE',
            aktivni: true,
            prodejna: '',
            technik_id: '',
            moduly: [],
            telefon: '',
            email: '',
            adresa: '',
            poznamka: '',
            mzda_zaklad: '',
            mzda_doplnky: [],
            vedouci_prodejna_id: '',
        });
        setEditingUser(null);
        setShowAddForm(false);
        setFormError(null);
    };

    useModalKeyboard(showAddForm, { onClose: resetForm, formRef: userFormRef });

    const handleSubmit = async (e) => {
        e.preventDefault();
        setFormError(null);

        const prepared = prepareUserSubmitData(formData, editingUser);
        if (prepared.error) {
            setFormError(prepared.error);
            return;
        }

        try {
            setSubmitting(true);
            let response;
            if (editingUser) {
                response = await userAPI.updateUser(editingUser.id, prepared.data);
            } else {
                response = await userAPI.createUser(prepared.data);
            }

            if (response.success) {
                await loadUsers();
                resetForm();
                setError(null);
            } else {
                setFormError(formatUserApiError(response));
            }
        } catch (err) {
            console.error('Chyba při odesílání formuláře:', err);
            setFormError(
                formatUserApiError(err.response?.data) || 'Chyba při ukládání uživatele'
            );
        } finally {
            setSubmitting(false);
        }
    };

    const handleEdit = (user) => {
        setFormError(null);
        setEditingUser(user);
        setFormData({
            uzivatelske_jmeno: user.uzivatelske_jmeno,
            jmeno: user.jmeno,
            prijmeni: user.prijmeni,
            heslo: '',
            role: user.role,
            aktivni: user.aktivni,
            prodejna: user.prodejna_id || user.prodejna || '',
            technik_id: user.technik_id != null ? String(user.technik_id) : '',
            moduly: user.moduly || [],
            telefon: user.telefon || '',
            email: user.email || '',
            adresa: user.adresa || '',
            poznamka: user.poznamka || '',
            mzda_zaklad: user.mzda_zaklad != null ? String(user.mzda_zaklad) : '',
            mzda_doplnky: Array.isArray(user.mzda_doplnky) ? [...user.mzda_doplnky] : [],
            vedouci_prodejna_id: user.vedouci_prodejna_id != null ? String(user.vedouci_prodejna_id) : '',
        });
        setShowAddForm(true);
    };

    const handleDoplnekChange = (index, field, value) => {
        setFormData((prev) => {
            const next = [...(prev.mzda_doplnky || [])];
            next[index] = { ...next[index], [field]: value };
            return { ...prev, mzda_doplnky: next };
        });
    };

    const addDoplnek = (template) => {
        setFormData((prev) => ({
            ...prev,
            mzda_doplnky: [
                ...(prev.mzda_doplnky || []),
                template ? createDoplnekFromTemplate(template) : { kod: '', nazev: '', castka: 0 },
            ],
        }));
    };

    const removeDoplnek = (index) => {
        setFormData((prev) => ({
            ...prev,
            mzda_doplnky: (prev.mzda_doplnky || []).filter((_, i) => i !== index),
        }));
    };

    const isBrigadnik = isBrigadnikRole(formData.role);

    const mzdaFixniPreview = () => {
        const doplnky = sumDoplnkyBody(formData.mzda_doplnky);
        if (isBrigadnik) {
            return doplnky;
        }
        const fixni = parseFloat(formData.mzda_zaklad) || 0;
        return fixni + doplnky;
    };

    const handleDelete = async (userId) => {
        if (!window.confirm('Opravdu chcete smazat tohoto uživatele?')) {
            return;
        }

        try {
            const response = await userAPI.deleteUser(userId);
            if (response.success) {
                await loadUsers();
                setError(null);
            } else {
                setError(response.message);
            }
        } catch (err) {
            setError('Chyba při mazání uživatele');
        }
    };

    const renderUserRow = (user) => (
        <tr key={user.id} className={user.id === currentUser.id ? 'current-user' : ''}>
            <td>{user.id}</td>
            <td>{user.technik_id ?? '—'}</td>
            <td>{user.uzivatelske_jmeno}</td>
            <td>{user.jmeno}</td>
            <td>{user.prijmeni}</td>
            <td>
                <span className={`role-badge ${user.role.toLowerCase()}`}>
                    {roleLabel(user.role)}
                </span>
            </td>
            <td>
                <span className="prodejna-text">{user.prodejna || '—'}</span>
            </td>
            <td>
                <span className={`status-badge ${user.aktivni ? 'active' : 'inactive'}`}>
                    {user.aktivni ? 'Aktivní' : 'Neaktivní'}
                </span>
            </td>
            <td>
                <div className="modules-list">
                    {user.moduly && user.moduly.length > 0 ? (
                        user.moduly.map((module) => (
                            <span key={module} className="module-tag">
                                {module === 'analytics' && 'Analytika'}
                                {module === 'shifts' && 'Směny'}
                                {module === 'news' && 'Novinky'}
                                {module === 'access' && 'Přístupy'}
                            </span>
                        ))
                    ) : (
                        <span className="no-modules">Žádné moduly</span>
                    )}
                </div>
            </td>
            <td>
                <div className="action-buttons">
                    <button
                        type="button"
                        className="edit-btn"
                        onClick={() => handleEdit(user)}
                        disabled={user.id === currentUser.id}
                    >
                        Upravit
                    </button>
                    <button
                        type="button"
                        className="delete-btn"
                        onClick={() => handleDelete(user.id)}
                        disabled={user.id === currentUser.id}
                    >
                        Smazat
                    </button>
                </div>
            </td>
        </tr>
    );

    if (!currentUser || currentUser.role !== 'ADMIN') {
        return (
            <div className="user-management-container">
                <div className="error-message">
                    Nemáte oprávnění k přístupu k této sekci.
                </div>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="user-management-container">
                <div className="loading">Načítání uživatelů...</div>
            </div>
        );
    }

    return (
        <div className="user-management-container">
            <div className="user-management-header">
                <h1>Správa uživatelů</h1>
                <button
                    className="add-user-btn"
                    onClick={() => {
                        setFormError(null);
                        setShowAddForm(true);
                    }}
                >
                    + Přidat uživatele
                </button>
            </div>

            {error && (
                <div className="error-message">
                    {error}
                </div>
            )}

            {showAddForm && (
                <div className="user-form-overlay">
                    <div className="user-form">
                        <div className="form-header">
                            <h2>{editingUser ? 'Upravit uživatele' : 'Přidat nového uživatele'}</h2>
                            <button className="close-btn" onClick={resetForm}>×</button>
                        </div>

                        <form ref={userFormRef} onSubmit={handleSubmit}>
                            {formError && (
                                <div className="form-error-message" role="alert">
                                    {formError.split('\n').map((line, i) => (
                                        <div key={i}>{line}</div>
                                    ))}
                                </div>
                            )}

                            <div className="form-row">
                                {editingUser ? (
                                    <div className="form-group">
                                        <label>Systémové ID</label>
                                        <input
                                            type="text"
                                            value={editingUser.id}
                                            disabled
                                            className="input-readonly"
                                        />
                                    </div>
                                ) : (
                                    <div className="form-group">
                                        <label>Systémové ID</label>
                                        <div className="auto-id-hint">
                                            Přiřadí se automaticky (odhad: <strong>{nextUserIdPreview}</strong>)
                                        </div>
                                    </div>
                                )}
                                <div className="form-group">
                                    <label>Technik ID (EDA/Pohoda) *</label>
                                    <input
                                        type="number"
                                        name="technik_id"
                                        className={manualNumberInputClass()}
                                        value={formData.technik_id}
                                        onChange={handleInputChange}
                                        onWheel={preventNumberInputWheel}
                                        required
                                        min="0"
                                        placeholder="např. 108"
                                    />
                                </div>
                            </div>

                            <div className="form-row">
                                <div className="form-group">
                                    <label>Uživatelské jméno *</label>
                                    <input
                                        type="text"
                                        name="uzivatelske_jmeno"
                                        value={formData.uzivatelske_jmeno}
                                        onChange={handleInputChange}
                                        required
                                    />
                                </div>
                            </div>

                            <div className="form-row">
                                <div className="form-group">
                                    <label>Jméno *</label>
                                    <input
                                        type="text"
                                        name="jmeno"
                                        value={formData.jmeno}
                                        onChange={handleInputChange}
                                        required
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Příjmení *</label>
                                    <input
                                        type="text"
                                        name="prijmeni"
                                        value={formData.prijmeni}
                                        onChange={handleInputChange}
                                        required
                                    />
                                </div>
                            </div>

                            <div className="form-row">
                                <div className="form-group">
                                    <label>Heslo {!editingUser && '*'}</label>
                                    <input
                                        type="password"
                                        name="heslo"
                                        value={formData.heslo}
                                        onChange={handleInputChange}
                                        required={!editingUser}
                                        minLength={editingUser ? undefined : 6}
                                        placeholder={editingUser ? 'Ponechte prázdné pro zachování' : 'Min. 6 znaků'}
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Role *</label>
                                    <select
                                        name="role"
                                        value={formData.role}
                                        onChange={handleInputChange}
                                        required
                                    >
                                        {USER_ROLE_OPTIONS.map((opt) => (
                                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                                        ))}
                                        {formData.role === 'VEDOUCI' && (
                                            <option value="VEDOUCI">Vedoucí (systémová role)</option>
                                        )}
                                    </select>
                                    <small className="field-hint">
                                        <strong>Vedoucí (role):</strong> může v modulu Směny zadávat a upravovat směny ostatních.
                                        Pro odměnu za vedení pobočky použijte níže „Vedoucí prodejny“ (+2000 bodů v doplňcích), role Prodejce stačí.
                                    </small>
                                </div>
                            </div>

                            <div className="form-group">
                                <label>Domovská prodejna</label>
                                <select
                                    name="prodejna"
                                    value={formData.prodejna}
                                    onChange={handleInputChange}
                                >
                                    <option value="">-- Vyberte prodejnu --</option>
                                    {stores.map(store => (
                                        <option key={store.id} value={store.id}>
                                            {store.nazev}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div className="form-group">
                                <label>Vedoucí prodejny (přiřazení pobočky)</label>
                                <select
                                    name="vedouci_prodejna_id"
                                    value={formData.vedouci_prodejna_id}
                                    onChange={handleInputChange}
                                >
                                    <option value="">— není vedoucí —</option>
                                    {stores.map((store) => (
                                        <option key={store.id} value={store.id}>
                                            {store.nazev}
                                        </option>
                                    ))}
                                </select>
                                <small className="field-hint">
                                    Přiřazení synchronizuje doplněk „vedoucí pobočky“ (2000 bodů). Částku lze upravit níže v doplňcích.
                                </small>
                            </div>

                            <div className="form-group">
                                <label>
                                    <input
                                        type="checkbox"
                                        name="aktivni"
                                        checked={formData.aktivni}
                                        onChange={handleInputChange}
                                    />
                                    Aktivní uživatel
                                </label>
                            </div>

                            <fieldset className="form-fieldset mzda-fieldset">
                                <legend>Fixní body a doplňky</legend>
                                <div className="form-group">
                                    <label>
                                        {isBrigadnik ? 'Body za hodinu' : 'Fixní body'}
                                    </label>
                                    <input
                                        type="number"
                                        name="mzda_zaklad"
                                        className={manualNumberInputClass()}
                                        min="0"
                                        step="1"
                                        value={formData.mzda_zaklad}
                                        onChange={handleInputChange}
                                        onWheel={preventNumberInputWheel}
                                        placeholder={isBrigadnik ? String(BRIGADNIK_DEFAULT_BODY_ZA_HODINU) : 'např. 15000'}
                                    />
                                    {isBrigadnik && (
                                        <small className="field-hint">
                                            Ve výplatě: odpracované hodiny × tato sazba (výchozí {BRIGADNIK_DEFAULT_BODY_ZA_HODINU} bodů/h) + doplňky + provize.
                                        </small>
                                    )}
                                </div>
                                <div className="doplnky-section">
                                    <label>Volitelné doplňky</label>
                                    {(formData.mzda_doplnky || []).map((d, idx) => (
                                        <div key={idx} className="doplnek-row">
                                            <input
                                                type="text"
                                                placeholder="Název"
                                                value={d.nazev || ''}
                                                onChange={(e) => handleDoplnekChange(idx, 'nazev', e.target.value)}
                                            />
                                            <input
                                                type="number"
                                                className={manualNumberInputClass()}
                                                min="0"
                                                step="1"
                                                placeholder="Body"
                                                value={d.castka ?? ''}
                                                onChange={(e) => handleDoplnekChange(idx, 'castka', e.target.value)}
                                                onWheel={preventNumberInputWheel}
                                            />
                                            <button type="button" className="doplnek-remove" onClick={() => removeDoplnek(idx)}>×</button>
                                        </div>
                                    ))}
                                    <div className="doplnky-actions">
                                        <button type="button" className="btn-secondary-sm" onClick={() => addDoplnek(null)}>
                                            + Přidat doplněk
                                        </button>
                                        {MZDA_DOPLNEK_TEMPLATES.filter((t) => t.kod !== 'vedouci_pobocky').map((tpl) => (
                                            <button
                                                key={tpl.kod}
                                                type="button"
                                                className="btn-secondary-sm"
                                                onClick={() => addDoplnek(tpl)}
                                            >
                                                + {tpl.nazev} ({tpl.castka} bodů)
                                            </button>
                                        ))}
                                    </div>
                                </div>
                                <p className="mzda-preview">
                                    {isBrigadnik ? (
                                        <>
                                            Doplňky: <strong>{formatBodyCount(mzdaFixniPreview())}</strong>
                                            {' '}(fixní část z hodin se počítá ve výplatě podle směn)
                                        </>
                                    ) : (
                                        <>
                                            Fixní body celkem: <strong>{formatBodyCount(mzdaFixniPreview())}</strong>
                                        </>
                                    )}
                                </p>
                            </fieldset>

                            <div className="form-group">
                                <label>Povolené moduly</label>
                                <div className="modules-grid">
                                    {availableModules.map(module => (
                                        <label key={module} className="module-checkbox">
                                            <input
                                                type="checkbox"
                                                checked={formData.moduly.includes(module)}
                                                onChange={() => handleModuleChange(module)}
                                            />
                                            {module === 'analytics' && 'Analytika'}
                                            {module === 'shifts' && 'Směny'}
                                            {module === 'news' && 'Novinky'}
                                            {module === 'access' && 'Přístupy'}
                                        </label>
                                    ))}
                                </div>
                            </div>

                            <div className="form-actions">
                                <button type="button" onClick={resetForm} className="cancel-btn">
                                    Zrušit
                                </button>
                                <button type="submit" className="save-btn" disabled={submitting}>
                                    {submitting
                                        ? 'Ukládám…'
                                        : editingUser
                                            ? 'Uložit změny'
                                            : 'Vytvořit uživatele'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            <div className="users-table">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Technik ID</th>
                            <th>Uživatelské jméno</th>
                            <th>Jméno</th>
                            <th>Příjmení</th>
                            <th>Role</th>
                            <th>Prodejna</th>
                            <th>Status</th>
                            <th>Moduly</th>
                            <th>Akce</th>
                        </tr>
                    </thead>
                    <tbody>
                        {activeUsers.map(renderUserRow)}
                    </tbody>
                </table>

                {inactiveUsers.length > 0 && (
                    <div className="inactive-users-section">
                        <button
                            type="button"
                            className="inactive-users-toggle"
                            onClick={() => setShowInactiveUsers((v) => !v)}
                            aria-expanded={showInactiveUsers}
                        >
                            <span className="toggle-icon">{showInactiveUsers ? '▼' : '▶'}</span>
                            Neaktivní uživatelé
                            <span className="inactive-count">({inactiveUsers.length})</span>
                        </button>
                        {showInactiveUsers && (
                            <table className="users-table-inactive">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Technik ID</th>
                                        <th>Uživatelské jméno</th>
                                        <th>Jméno</th>
                                        <th>Příjmení</th>
                                        <th>Role</th>
                                        <th>Prodejna</th>
                                        <th>Status</th>
                                        <th>Moduly</th>
                                        <th>Akce</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {inactiveUsers.map(renderUserRow)}
                                </tbody>
                            </table>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default UserManagement; 