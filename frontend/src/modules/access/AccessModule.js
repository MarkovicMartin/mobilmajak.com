import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import AccessList from './AccessList';
import AccessForm from './AccessForm';
import AccessFilter from './AccessFilter';
import { PageHeader } from '../../components/ui';
import { copyToClipboard } from '../../utils/clipboard';
import './AccessModule.css';

const AccessModule = () => {
    const { user, isAdmin } = useAuth();
    const canManageAdminAccess = isAdmin();
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
    const homeStoreFilterInitialized = useRef(false);

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

    // Jednou při načtení předvybrat domovskou prodejnu (ne při ručním vymazání filtru)
    useEffect(() => {
        if (homeStoreFilterInitialized.current) return;
        if (!user?.prodejna || accesses.length === 0) return;
        homeStoreFilterInitialized.current = true;
        const homeStore = getStoreNameWithAlias(user.prodejna);
        if (homeStore) {
            setFilters((prev) => ({ ...prev, store: homeStore }));
        }
    }, [user, accesses]);

    // Kategorie filtr jen pro ADMIN — u ostatních vynulovat
    useEffect(() => {
        if (!canManageAdminAccess && filters.category) {
            setFilters((prev) => ({ ...prev, category: '' }));
        }
    }, [canManageAdminAccess, filters.category]);

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
                (access.company_name || '').toLowerCase().includes(searchTerm) ||
                (access.description || '').toLowerCase().includes(searchTerm) ||
                (access.website_url || '').toLowerCase().includes(searchTerm)
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
        const formatApiError = (data) => {
            if (!data) return 'Chyba při ukládání přístupu';
            if (typeof data === 'string') return data;
            if (data.error) return data.error;
            if (data.detail) return typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
            return Object.entries(data)
                .map(([key, val]) => `${key}: ${[].concat(val).join(', ')}`)
                .join('; ');
        };

        try {
            const url = editingAccess ? `/api/pristupy/${editingAccess.id}/` : '/api/pristupy/';
            const method = editingAccess ? 'PATCH' : 'POST';

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
                return;
            }

            let errorData = null;
            try {
                errorData = await response.json();
            } catch {
                errorData = null;
            }
            throw new Error(formatApiError(errorData));
        } catch (err) {
            setError('Chyba při ukládání: ' + err.message);
            throw err;
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

            if (!response.ok) {
                setError('Chyba při získávání hesla');
                return { success: false };
            }

            const data = await response.json();
            const result = await copyToClipboard(data.password);

            if (result.success) {
                await loadAccesses();
                return { success: true };
            }

            return {
                success: false,
                password: data.password,
                error: result.error,
            };
        } catch (err) {
            setError('Chyba při získávání hesla: ' + err.message);
            return { success: false };
        }
    };

    const canEdit = !!user;
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
            <PageHeader
                title="Přístupy"
                actions={canEdit ? (
                    <button
                        type="button"
                        className="btn btn--primary"
                        onClick={handleCreateAccess}
                    >
                        Přidat přístup
                    </button>
                ) : null}
            />

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
                    canUseAdminCategory={canManageAdminAccess}
                    onSubmit={handleFormSubmit}
                    onCancel={handleFormCancel}
                />
            )}

            <AccessFilter
                filters={filters}
                onFiltersChange={setFilters}
                stores={stores}
                categories={categories}
                showCategoryFilter={canManageAdminAccess}
            />

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