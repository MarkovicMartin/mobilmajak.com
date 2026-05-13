import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { userAPI, storeAPI } from '../services/api';
import './UserManagement.css';

const UserManagement = () => {
    const { user: currentUser } = useAuth();
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showAddForm, setShowAddForm] = useState(false);
    const [editingUser, setEditingUser] = useState(null);
    const [stores, setStores] = useState([]);
    const [formData, setFormData] = useState({
        id: '',
        uzivatelske_jmeno: '',
        jmeno: '',
        prijmeni: '',
        heslo: '',
        role: 'PRODEJCE',
        aktivni: true,
        prodejna: '',
        moduly: [],
        telefon: '',
        email: '',
        adresa: '',
        poznamka: ''
    });

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
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
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
            id: '',
            uzivatelske_jmeno: '',
            jmeno: '',
            prijmeni: '',
            heslo: '',
            role: 'PRODEJCE',
            aktivni: true,
            prodejna: '',
            moduly: [],
            telefon: '',
            email: '',
            adresa: '',
            poznamka: ''
        });
        setEditingUser(null);
        setShowAddForm(false);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        try {
            // Příprava dat pro odeslání - jednotná logika pro vytváření i editaci
            const submitData = { ...formData };

            // Převod prodejna na prodejna_id pro backend
            if (submitData.prodejna) {
                const pid = parseInt(submitData.prodejna, 10);
                if (!Number.isNaN(pid)) {
                    submitData.prodejna_id = pid;
                } else {
                    // Pokud není číslo, nastavíme null
                    submitData.prodejna_id = null;
                }
            } else {
                submitData.prodejna_id = null;
            }

            // Odstraníme pole 'prodejna', protože backend ho nezná
            delete submitData.prodejna;

            let response;
            if (editingUser) {
                // Aktualizace existujícího uživatele
                // Pro editaci backend očekává 'nove_heslo' místo 'heslo'
                if (submitData.heslo && submitData.heslo.trim()) {
                    submitData.nove_heslo = submitData.heslo.trim();
                }
                delete submitData.heslo; // backend neočekává pole 'heslo' při editaci

                response = await userAPI.updateUser(editingUser.id, submitData);
            } else {
                // Vytvoření nového uživatele
                // Při vytváření backend očekává pole 'heslo'
                if (!submitData.heslo || submitData.heslo.length < 6) {
                    setError('Heslo musí mít alespoň 6 znaků');
                    return;
                }

                response = await userAPI.createUser(submitData);
            }

            if (response.success) {
                await loadUsers(); // Znovu načíst seznam uživatelů
                resetForm();
                setError(null);
            } else {
                setError(response.message || 'Chyba při ukládání uživatele');
                // Zobrazíme také detailní chyby z backendu pro debug
                if (response.errors) {
                    console.error('Chyby validace:', response.errors);
                    const errorMessages = Object.entries(response.errors)
                        .map(([field, errors]) => `${field}: ${Array.isArray(errors) ? errors.join(', ') : errors}`)
                        .join('\n');
                    setError(response.message + '\n\nDetaily:\n' + errorMessages);
                }
            }
        } catch (error) {
            console.error('Chyba při odesílání formuláře:', error);
            setError('Chyba při ukládání uživatele');
        }
    };

    const handleEdit = (user) => {
        setEditingUser(user);
        setFormData({
            id: user.id,
            uzivatelske_jmeno: user.uzivatelske_jmeno,
            jmeno: user.jmeno,
            prijmeni: user.prijmeni,
            heslo: '', // Heslo necháme prázdné pro editaci
            role: user.role,
            aktivni: user.aktivni,
            prodejna: user.prodejna_id || user.prodejna || '',
            moduly: user.moduly || [],
            telefon: user.telefon || '',
            email: user.email || '',
            adresa: user.adresa || '',
            poznamka: user.poznamka || ''
        });
        setShowAddForm(true);
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
        } catch (error) {
            setError('Chyba při mazání uživatele');
        }
    };

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
                    onClick={() => setShowAddForm(true)}
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

                        <form onSubmit={handleSubmit}>
                            <div className="form-row">
                                <div className="form-group">
                                    <label>ID uživatele *</label>
                                    <input
                                        type="number"
                                        name="id"
                                        value={formData.id}
                                        onChange={handleInputChange}
                                        required
                                        disabled={editingUser} // ID nelze měnit při editaci
                                    />
                                </div>
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
                                        placeholder={editingUser ? 'Ponechte prázdné pro zachování' : ''}
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
                                        <option value="PRODEJCE">Prodejce</option>
                                        <option value="VEDOUCI">Vedoucí</option>
                                        <option value="ADMIN">Administrátor</option>
                                    </select>
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
                                <button type="submit" className="save-btn">
                                    {editingUser ? 'Uložit změny' : 'Vytvořit uživatele'}
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
                        {users.map(user => (
                            <tr key={user.id} className={user.id === currentUser.id ? 'current-user' : ''}>
                                <td>{user.id}</td>
                                <td>{user.uzivatelske_jmeno}</td>
                                <td>{user.jmeno}</td>
                                <td>{user.prijmeni}</td>
                                <td>
                                    <span className={`role-badge ${user.role.toLowerCase()}`}>
                                        {user.role === 'ADMIN' ? 'Administrátor' : user.role === 'VEDOUCI' ? 'Vedoucí' : 'Prodejce'}
                                    </span>
                                </td>
                                <td>
                                    <span className="prodejna-text">
                                        {user.prodejna || '—'}
                                    </span>
                                </td>
                                <td>
                                    <span className={`status-badge ${user.aktivni ? 'active' : 'inactive'}`}>
                                        {user.aktivni ? 'Aktivní' : 'Neaktivní'}
                                    </span>
                                </td>
                                <td>
                                    <div className="modules-list">
                                        {user.moduly && user.moduly.length > 0 ? (
                                            user.moduly.map(module => (
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
                                            className="edit-btn"
                                            onClick={() => handleEdit(user)}
                                            disabled={user.id === currentUser.id}
                                        >
                                            Upravit
                                        </button>
                                        <button
                                            className="delete-btn"
                                            onClick={() => handleDelete(user.id)}
                                            disabled={user.id === currentUser.id}
                                        >
                                            Smazat
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default UserManagement; 