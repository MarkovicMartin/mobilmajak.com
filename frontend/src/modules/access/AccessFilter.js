import React, { useMemo } from 'react';
import { Select } from '../../components/ui';
import './AccessFilter.css';

const AccessFilter = ({ filters, onFiltersChange, stores, categories }) => {
    const handleFilterChange = (key, value) => {
        onFiltersChange(prev => ({
            ...prev,
            [key]: value
        }));
    };

    const clearFilters = () => {
        onFiltersChange({
            store: '',
            category: '',
            search: ''
        });
    };

    const hasActiveFilters = filters.store || filters.category || filters.search;

    const storeOptions = useMemo(() => [
        { value: '', label: 'Všechny prodejny' },
        ...stores.map((store) => ({
            value: store.store,
            label: `${store.store} (${store.count})`,
        })),
    ], [stores]);

    const categoryOptions = useMemo(() => [
        { value: '', label: 'Všechny kategorie' },
        ...categories.map((category) => ({
            value: category,
            label: category,
        })),
    ], [categories]);

    return (
        <div className="access-filter">
            <div className="filter-header">
                <h4>Filtrování a vyhledávání</h4>
                {hasActiveFilters && (
                    <button
                        type="button"
                        className="btn btn--ghost btn--sm btn-clear-filters"
                        onClick={clearFilters}
                        title="Vymazat všechny filtry"
                    >
                        Vymazat filtry
                    </button>
                )}
            </div>

            <div className="filter-controls">
                <div className="filter-group">
                    <label htmlFor="search-input">
                        Vyhledávání
                    </label>
                    <input
                        id="search-input"
                        type="text"
                        placeholder="Hledat podle názvu, popisu nebo URL..."
                        value={filters.search}
                        onChange={(e) => handleFilterChange('search', e.target.value)}
                        className="search-input"
                    />
                </div>

                <div className="filter-group">
                    <label htmlFor="store-filter">
                        Prodejna
                    </label>
                    <Select
                        id="store-filter"
                        value={filters.store}
                        onChange={(value) => handleFilterChange('store', value)}
                        options={storeOptions}
                        placeholder="Všechny prodejny"
                        aria-label="Filtrovat podle prodejny"
                    />
                </div>

                <div className="filter-group">
                    <label htmlFor="category-filter">
                        Kategorie
                    </label>
                    <Select
                        id="category-filter"
                        value={filters.category}
                        onChange={(value) => handleFilterChange('category', value)}
                        options={categoryOptions}
                        placeholder="Všechny kategorie"
                        aria-label="Filtrovat podle kategorie"
                    />
                </div>
            </div>

            {hasActiveFilters && (
                <div className="active-filters">
                    <span className="filters-label">Aktivní filtry:</span>
                    <div className="filter-tags">
                        {filters.search && (
                            <div className="filter-tag">
                                Vyhledávání: "{filters.search}"
                                <button 
                                    onClick={() => handleFilterChange('search', '')}
                                    className="remove-filter"
                                >
                                    ✕
                                </button>
                            </div>
                        )}
                        {filters.store && (
                            <div className="filter-tag">
                                Prodejna: {filters.store}
                                <button 
                                    onClick={() => handleFilterChange('store', '')}
                                    className="remove-filter"
                                >
                                    ✕
                                </button>
                            </div>
                        )}
                        {filters.category && (
                            <div className="filter-tag">
                                Kategorie: {filters.category}
                                <button 
                                    onClick={() => handleFilterChange('category', '')}
                                    className="remove-filter"
                                >
                                    ✕
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default AccessFilter; 