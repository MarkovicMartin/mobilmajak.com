import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import AccessList from './AccessList';
import AccessForm from './AccessForm';
import AccessFilter from './AccessFilter';
import { copyToClipboard, showCopySuccess, showCopyError } from '../../utils/clipboard';
import './AccessModule.css';

const AccessModule = () => {
    const { user } = useAuth();
    const [accesses, setAccesses] = useState([]);
    const [filteredAccesses, setFilteredAccesses] = useState([]);
    const [stores, setStores] = useState([]);
    const [categories, setCategories] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showForm, setShowForm] = useState(false);
    const [editingAccess, setEditingAccess] = useState(null);
    const [filters, setFilters] = useState({
        store: '',
        category: '',
        search: ''
    });

    // Aliasy prodejen - mapování alternativních názvů
    const STORE_ALIASES = {
        'Zlín': 'Čepkov',
        'Zlin': 'Čepkov'
    };

    // Funkce pro získání správného názvu prodejny včetně aliasů
    const getStoreNameWithAlias = (storeName) => {
        if (!storeName) return '';
        
        // Pokud prodejna existuje přímo, vrátí ji
        const directMatch = accesses.some(access => 
            access.store.toLowerCase() === storeName.toLowerCase()
        );
        
        if (directMatch) {
            return storeName;
        }
        
        // Pokud neexistuje, zkusí alias
        const alias = STORE_ALIASES[storeName];
        if (alias) {
            const aliasMatch = accesses.some(access => 
                access.store.toLowerCase() === alias.toLowerCase()
            );
            
            if (aliasMatch) {
                return alias;
            }
        }
        
        // Pokud ani alias neexistuje, vrátí původní název
        return storeName;
    };

    useEffect(() => {
        loadData();
    }, []);

    useEffect(() => {
        applyFilters();
    }, [accesses, filters]);

    // Automatické nastavení filtru podle domovské prodejny uživatele
    useEffect(() => {
        if (user && user.prodejna && accesses.length > 0 && !filters.store) {
            // Získání správného názvu prodejny včetně aliasů
            const homeStore = getStoreNameWithAlias(user.prodejna);
            
            // Automaticky nastavit filtr na domovskou prodejnu (nebo její alias)
            setFilters(prev => ({
                ...prev,
                store: homeStore
            }));
        }
    }, [user, accesses, filters.store]);

    const loadData = async () => {
        setLoading(true);
        try {
            await Promise.all([
                loadAccesses(),
                loadStores(),
                loadCategories()
            ]);
        } catch (err) {
            setError('Chyba při načítání dat: ' + err.message);
        } finally {
            setLoading(false);
        }
    };

    const loadAccesses = async () => {
        const response = await fetch('/api/pristupy/', {
            credentials: 'include',
            headers: {
                'X-CSRFToken': getCsrfToken(),
            }
        });

        if (!response.ok) {
            throw new Error('Nepodařilo se načíst přístupy');
        }

        const data = await response.json();
        setAccesses(data);
    };

    const loadStores = async () => {
        const response = await fetch('/api/pristupy/stores/', {
            credentials: 'include',
            headers: {
                'X-CSRFToken': getCsrfToken(),
            }
        });

        if (response.ok) {
            const data = await response.json();
            setStores(data);
        }
    };

    const loadCategories = async () => {
        const response = await fetch('/api/pristupy/categories/', {
            credentials: 'include',
            headers: {
                'X-CSRFToken': getCsrfToken(),
            }
        });

        if (response.ok) {
            const data = await response.json();
            setCategories(data);
        }
    };

    const getCsrfToken = () => {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    };

    const applyFilters = () => {
        let filtered = [...accesses];

        if (filters.store) {
            // Získání správného názvu prodejny včetně aliasů
            const storeToFilter = getStoreNameWithAlias(filters.store);
            
            filtered = filtered.filter(access => 
                access.store.toLowerCase().includes(storeToFilter.toLowerCase())
            );
        }

        if (filters.category) {
            filtered = filtered.filter(access => 
                access.category && access.category.toLowerCase().includes(filters.category.toLowerCase())
            );
        }

        if (filters.search) {
            const searchTerm = filters.search.toLowerCase();
            filtered = filtered.filter(access => 
                access.company_name.toLowerCase().includes(searchTerm) ||
                access.description.toLowerCase().includes(searchTerm) ||
                access.website_url.toLowerCase().includes(searchTerm)
            );
        }

        setFilteredAccesses(filtered);
    };

    const handleCreateAccess = () => {
        setEditingAccess(null);
        setShowForm(true);
    };

    const handleEditAccess = (access) => {
        setEditingAccess(access);
        setShowForm(true);
    };

    const handleDeleteAccess = async (accessId) => {
        if (!window.confirm('Opravdu chcete smazat tento přístup?')) {
            return;
        }

        try {
            const response = await fetch(`/api/pristupy/${accessId}/`, {
                method: 'DELETE',
                credentials: 'include',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                }
            });

            if (response.ok) {
                await loadAccesses();
                setError(null);
            } else {
                const errorData = await response.json();
                setError(errorData.error || 'Chyba při mazání přístupu');
            }
        } catch (err) {
            setError('Chyba při mazání přístupu: ' + err.message);
        }
    };

    const handleFormSubmit = async (accessData) => {
        try {
            const url = editingAccess ? `/api/pristupy/${editingAccess.id}/` : '/api/pristupy/';
            const method = editingAccess ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method,
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify(accessData)
            });

            if (response.ok) {
                setShowForm(false);
                setEditingAccess(null);
                await loadAccesses();
                setError(null);
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Chyba při ukládání přístupu');
            }
        } catch (err) {
            setError('Chyba při ukládání: ' + err.message);
        }
    };

    const handleFormCancel = () => {
        setShowForm(false);
        setEditingAccess(null);
    };

    const handleRevealPassword = async (accessId) => {
        try {
            const response = await fetch(`/api/pristupy/${accessId}/reveal_password/`, {
                credentials: 'include',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                }
            });

            if (response.ok) {
                const data = await response.json();
                
                // Bezpečné kopírování do schránky s fallback
                const result = await copyToClipboard(data.password);
                
                if (result.success) {
                    showCopySuccess('Heslo', result.method);
                    await loadAccesses(); // Refresh to update last_used
                } else {
                    showCopyError(result.error);
                    // Zobrazíme heslo v alert jako backup
                    alert(`Heslo: ${data.password}\n\n(Zkopírujte ručně)`);
                }
            } else {
                setError('Chyba při získávání hesla');
            }
        } catch (err) {
            setError('Chyba při získávání hesla: ' + err.message);
        }
    };

    const canEdit = user && (user.role === 'ADMIN' || user.role === 'PRODEJCE');
    const canDelete = user && user.role === 'ADMIN';

    if (loading) {
        return (
            <div className="access-module">
                <div className="loading">
                    <div className="spinner"></div>
                    <p>Načítání přístupů...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="access-module">
            <div className="access-header">
                <h2>🔐 Přístupy</h2>
                <p className="access-description">
                    Správa přístupů k webovým službám pro všechny prodejny
                </p>
                {canEdit && (
                    <button 
                        className="btn-primary"
                        onClick={handleCreateAccess}
                    >
                        ➕ Přidat přístup
                    </button>
                )}
            </div>

            {error && (
                <div className="error-message">
                    ❌ {error}
                    <button onClick={() => setError(null)}>✕</button>
                </div>
            )}

            {showForm && (
                <AccessForm
                    access={editingAccess}
                    stores={stores}
                    categories={categories}
                    onSubmit={handleFormSubmit}
                    onCancel={handleFormCancel}
                />
            )}

            {/* Informace o domovské prodejně */}
            {user && user.prodejna && (
                <div className="home-store-info">
                    <div className="info-content">
                        <span className="info-icon">🏪</span>
                        <span className="info-text">
                            Vaše domovská prodejna: <strong>{user.prodejna}</strong>
                            {(() => {
                                const actualStore = getStoreNameWithAlias(user.prodejna);
                                return actualStore !== user.prodejna ? (
                                    <span className="alias-info"> (zobrazuje se jako <strong>{actualStore}</strong>)</span>
                                ) : null;
                            })()}
                        </span>
                        {(() => {
                            const homeStore = getStoreNameWithAlias(user.prodejna);
                            return filters.store === homeStore && (
                                <button 
                                    className="btn-show-all"
                                    onClick={() => setFilters(prev => ({ ...prev, store: '' }))}
                                    title="Zobrazit přístupy ze všech prodejen"
                                >
                                    📋 Zobrazit všechny prodejny
                                </button>
                            );
                        })()}
                        {(() => {
                            const homeStore = getStoreNameWithAlias(user.prodejna);
                            return filters.store !== homeStore && filters.store !== '' && (
                                <button 
                                    className="btn-show-home"
                                    onClick={() => setFilters(prev => ({ ...prev, store: homeStore }))}
                                    title="Zobrazit pouze přístupy z domovské prodejny"
                                >
                                    🏠 Zobrazit domovskou prodejnu
                                </button>
                            );
                        })()}
                    </div>
                </div>
            )}

            <AccessFilter
                filters={filters}
                onFiltersChange={setFilters}
                stores={stores}
                categories={categories}
            />

            <div className="access-stats">
                <div className="stats-card">
                    <h4>📊 Statistiky</h4>
                    <p>Celkem přístupů: <strong>{accesses.length}</strong></p>
                    <p>Zobrazených: <strong>{filteredAccesses.length}</strong></p>
                </div>
                
                <div className="stores-overview">
                    <h4>🏪 Prodejny</h4>
                    {stores.map(store => (
                        <div key={store.store} className="store-stat">
                            <span>{store.store}</span>
                            <span className="count">{store.count}</span>
                        </div>
                    ))}
                </div>
            </div>

            <AccessList
                accesses={filteredAccesses}
                canEdit={canEdit}
                canDelete={canDelete}
                onEdit={handleEditAccess}
                onDelete={handleDeleteAccess}
                onRevealPassword={handleRevealPassword}
            />
        </div>
    );
};

export default AccessModule; 