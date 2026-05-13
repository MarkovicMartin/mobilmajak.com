import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { storeAPI } from '../services/api';
import './StoreManagement.css';

const StoreManagement = () => {
    const { user: currentUser } = useAuth();
    const [stores, setStores] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showAddForm, setShowAddForm] = useState(false);
    const [editingStore, setEditingStore] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [filterActive, setFilterActive] = useState('all');
    const [selectedStores, setSelectedStores] = useState([]);
    const [formData, setFormData] = useState({
        nazev: '',
        nazev_kratkiy: '',
        nazev_google_sheets: '',
        adresa: '',
        telefon: '',
        email: '',
        otevreno_od: '',
        otevreno_do: '',
        vedouci_prodejny: '',
        aktivni: true,
        barva: '#0066cc',
        poradi: 0,
        poznamka: ''
    });

    const loadStores = useCallback(async () => {
        try {
            setLoading(true);
            const response = await storeAPI.getStores({
                search: searchTerm,
                aktivni: filterActive === 'all' ? undefined : filterActive === 'active'
            });
            if (response.success) {
                setStores(response.stores);
            } else {
                setError(response.message);
            }
        } catch (error) {
            setError('Chyba při načítání prodejen');
        } finally {
            setLoading(false);
        }
    }, [searchTerm, filterActive]);

    useEffect(() => {
        loadStores();
    }, [loadStores]);

    useEffect(() => {
        const timeoutId = setTimeout(() => {
            loadStores();
        }, 300);
        return () => clearTimeout(timeoutId);
    }, [searchTerm, filterActive, loadStores]);

    const handleInputChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    const resetForm = () => {
        setFormData({
            nazev: '',
            nazev_kratkiy: '',
            nazev_google_sheets: '',
            adresa: '',
            telefon: '',
            email: '',
            otevreno_od: '',
            otevreno_do: '',
            vedouci_prodejny: '',
            aktivni: true,
            barva: '#0066cc',
            poradi: 0,
            poznamka: ''
        });
        setEditingStore(null);
        setShowAddForm(false);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        try {
            let response;
            if (editingStore) {
                response = await storeAPI.updateStore(editingStore.id, formData);
            } else {
                response = await storeAPI.createStore(formData);
            }

            if (response.success) {
                await loadStores();
                resetForm();
                setError(null);
            } else {
                setError(response.message);
            }
        } catch (error) {
            setError(error.response?.data?.message || 'Chyba při ukládání prodejny');
        }
    };

    const handleEdit = (store) => {
        setEditingStore(store);
        setFormData({
            nazev: store.nazev || '',
            nazev_kratkiy: store.nazev_kratkiy || '',
            nazev_google_sheets: store.nazev_google_sheets || '',
            adresa: store.adresa || '',
            telefon: store.telefon || '',
            email: store.email || '',
            otevreno_od: store.otevreno_od || '',
            otevreno_do: store.otevreno_do || '',
            vedouci_prodejny: store.vedouci_prodejny || '',
            aktivni: store.aktivni,
            barva: store.barva || '#0066cc',
            poradi: store.poradi || 0,
            poznamka: store.poznamka || ''
        });
        setShowAddForm(true);
    };

    const handleDelete = async (storeId) => {
        if (!window.confirm('Opravdu chcete smazat tuto prodejnu?')) {
            return;
        }

        try {
            const response = await storeAPI.deleteStore(storeId);
            if (response.success) {
                await loadStores();
                setError(null);
            } else {
                setError(response.message);
            }
        } catch (error) {
            setError('Chyba při mazání prodejny');
        }
    };

    const handleBulkStatusChange = async (newStatus) => {
        if (selectedStores.length === 0) {
            setError('Nejsou vybrány žádné prodejny');
            return;
        }

        try {
            const response = await storeAPI.bulkUpdateStatus(selectedStores, newStatus);
            if (response.success) {
                await loadStores();
                setSelectedStores([]);
                setError(null);
            } else {
                setError(response.message);
            }
        } catch (error) {
            setError('Chyba při hromadné aktualizaci');
        }
    };

    const handleStoreSelect = (storeId, checked) => {
        if (checked) {
            setSelectedStores(prev => [...prev, storeId]);
        } else {
            setSelectedStores(prev => prev.filter(id => id !== storeId));
        }
    };

    const handleSelectAll = (checked) => {
        if (checked) {
            setSelectedStores(stores.map(store => store.id));
        } else {
            setSelectedStores([]);
        }
    };

    if (!currentUser || currentUser.role !== 'ADMIN') {
        return (
            <div className="store-management-container">
                <div className="error-message">
                    Nemáte oprávnění k přístupu k této sekci.
                </div>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="store-management-container">
                <div className="loading">Načítání prodejen...</div>
            </div>
        );
    }

    const filteredStores = stores;

    return (
        <div className="store-management-container">
            <div className="store-management-header">
                <h1>🏪 Správa prodejen</h1>
                <button 
                    className="add-store-btn"
                    onClick={() => setShowAddForm(true)}
                >
                    + Přidat prodejnu
                </button>
            </div>

            {error && (
                <div className="error-message">
                    {error}
                    <button onClick={() => setError(null)}>×</button>
                </div>
            )}

            {/* Filtry a vyhledávání */}
            <div className="filters-section">
                <div className="search-box">
                    <input
                        type="text"
                        placeholder="Vyhledat prodejnu..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
                
                <div className="filter-buttons">
                    <button 
                        className={filterActive === 'all' ? 'active' : ''}
                        onClick={() => setFilterActive('all')}
                    >
                        Všechny ({stores.length})
                    </button>
                    <button 
                        className={filterActive === 'active' ? 'active' : ''}
                        onClick={() => setFilterActive('active')}
                    >
                        Aktivní ({stores.filter(s => s.aktivni).length})
                    </button>
                    <button 
                        className={filterActive === 'inactive' ? 'active' : ''}
                        onClick={() => setFilterActive('inactive')}
                    >
                        Neaktivní ({stores.filter(s => !s.aktivni).length})
                    </button>
                </div>
            </div>

            {/* Hromadné akce */}
            {selectedStores.length > 0 && (
                <div className="bulk-actions">
                    <span>Vybráno: {selectedStores.length} prodejen</span>
                    <button onClick={() => handleBulkStatusChange(true)}>
                        Aktivovat vybrané
                    </button>
                    <button onClick={() => handleBulkStatusChange(false)}>
                        Deaktivovat vybrané
                    </button>
                    <button onClick={() => setSelectedStores([])}>
                        Zrušit výběr
                    </button>
                </div>
            )}

            {showAddForm && (
                <div className="store-form-overlay">
                    <div className="store-form">
                        <div className="form-header">
                            <h2>{editingStore ? 'Upravit prodejnu' : 'Přidat novou prodejnu'}</h2>
                            <button className="close-btn" onClick={resetForm}>×</button>
                        </div>
                        
                        <form onSubmit={handleSubmit}>
                            <div className="form-row">
                                <div className="form-group">
                                    <label>Název prodejny *</label>
                                    <input
                                        type="text"
                                        name="nazev"
                                        value={formData.nazev}
                                        onChange={handleInputChange}
                                        required
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Krátký název *</label>
                                    <input
                                        type="text"
                                        name="nazev_kratkiy"
                                        value={formData.nazev_kratkiy}
                                        onChange={handleInputChange}
                                        required
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label>Název v Google Sheets</label>
                                <input
                                    type="text"
                                    name="nazev_google_sheets"
                                    value={formData.nazev_google_sheets}
                                    onChange={handleInputChange}
                                    placeholder="Jak se prodejna jmenuje v Google tabulce"
                                />
                            </div>

                            <div className="form-group">
                                <label>Adresa</label>
                                <textarea
                                    name="adresa"
                                    value={formData.adresa}
                                    onChange={handleInputChange}
                                    rows="2"
                                />
                            </div>

                            <div className="form-row">
                                <div className="form-group">
                                    <label>Telefon</label>
                                    <input
                                        type="tel"
                                        name="telefon"
                                        value={formData.telefon}
                                        onChange={handleInputChange}
                                    />
                                </div>
                                <div className="form-group">
                                    <label>E-mail</label>
                                    <input
                                        type="email"
                                        name="email"
                                        value={formData.email}
                                        onChange={handleInputChange}
                                    />
                                </div>
                            </div>

                            <div className="form-row">
                                <div className="form-group">
                                    <label>Otevřeno od</label>
                                    <input
                                        type="time"
                                        name="otevreno_od"
                                        value={formData.otevreno_od}
                                        onChange={handleInputChange}
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Otevřeno do</label>
                                    <input
                                        type="time"
                                        name="otevreno_do"
                                        value={formData.otevreno_do}
                                        onChange={handleInputChange}
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label>Vedoucí prodejny</label>
                                <input
                                    type="text"
                                    name="vedouci_prodejny"
                                    value={formData.vedouci_prodejny}
                                    onChange={handleInputChange}
                                />
                            </div>

                            <div className="form-row">
                                <div className="form-group">
                                    <label>Barva</label>
                                    <input
                                        type="color"
                                        name="barva"
                                        value={formData.barva}
                                        onChange={handleInputChange}
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Pořadí</label>
                                    <input
                                        type="number"
                                        name="poradi"
                                        value={formData.poradi}
                                        onChange={handleInputChange}
                                        min="0"
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label>
                                    <input
                                        type="checkbox"
                                        name="aktivni"
                                        checked={formData.aktivni}
                                        onChange={handleInputChange}
                                    />
                                    Aktivní prodejna
                                </label>
                            </div>

                            <div className="form-group">
                                <label>Poznámka</label>
                                <textarea
                                    name="poznamka"
                                    value={formData.poznamka}
                                    onChange={handleInputChange}
                                    rows="3"
                                />
                            </div>

                            <div className="form-actions">
                                <button type="button" onClick={resetForm} className="cancel-btn">
                                    Zrušit
                                </button>
                                <button type="submit" className="save-btn">
                                    {editingStore ? 'Uložit změny' : 'Vytvořit prodejnu'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            <div className="stores-table">
                <table>
                    <thead>
                        <tr>
                            <th>
                                <input
                                    type="checkbox"
                                    checked={selectedStores.length === stores.length && stores.length > 0}
                                    onChange={(e) => handleSelectAll(e.target.checked)}
                                />
                            </th>
                            <th>Název</th>
                            <th>Krátký název</th>
                            <th>Google Sheets</th>
                            <th>Vedoucí</th>
                            <th>Status</th>
                            <th>Pořadí</th>
                            <th>Barva</th>
                            <th>Akce</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredStores.map(store => (
                            <tr key={store.id}>
                                <td>
                                    <input
                                        type="checkbox"
                                        checked={selectedStores.includes(store.id)}
                                        onChange={(e) => handleStoreSelect(store.id, e.target.checked)}
                                    />
                                </td>
                                <td>{store.nazev}</td>
                                <td>{store.nazev_kratkiy}</td>
                                <td>{store.nazev_google_sheets || '—'}</td>
                                <td>{store.vedouci_prodejny || '—'}</td>
                                <td>
                                    <span className={`status-badge ${store.aktivni ? 'active' : 'inactive'}`}>
                                        {store.aktivni ? 'Aktivní' : 'Neaktivní'}
                                    </span>
                                </td>
                                <td>{store.poradi}</td>
                                <td>
                                    <div 
                                        className="color-preview" 
                                        style={{ backgroundColor: store.barva }}
                                        title={store.barva}
                                    ></div>
                                </td>
                                <td>
                                    <div className="action-buttons">
                                        <button 
                                            className="edit-btn"
                                            onClick={() => handleEdit(store)}
                                        >
                                            Upravit
                                        </button>
                                        <button 
                                            className="delete-btn"
                                            onClick={() => handleDelete(store.id)}
                                        >
                                            Smazat
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>

                {filteredStores.length === 0 && (
                    <div className="no-stores">
                        {searchTerm ? 'Žádné prodejny nenalezeny pro zadané vyhledávání.' : 'Žádné prodejny nebyly nalezeny.'}
                    </div>
                )}
            </div>
        </div>
    );
};

export default StoreManagement; 