import React from 'react';
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

    return (
        <div className="access-filter">
            <div className="filter-header">
                <h4>🔍 Filtrování a vyhledávání</h4>
                {hasActiveFilters && (
                    <button 
                        className="btn-clear-filters"
                        onClick={clearFilters}
                        title="Vymazat všechny filtry"
                    >
                        🗑️ Vymazat filtry
                    </button>
                )}
            </div>

            <div className="filter-controls">
                <div className="filter-group">
                    <label htmlFor="search-input">
                        🔎 Vyhledávání
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
                        🏪 Prodejna
                    </label>
                    <select
                        id="store-filter"
                        value={filters.store}
                        onChange={(e) => handleFilterChange('store', e.target.value)}
                        className="filter-select"
                    >
                        <option value="">Všechny prodejny</option>
                        {stores.map(store => (
                            <option key={store.store} value={store.store}>
                                {store.store} ({store.count})
                            </option>
                        ))}
                    </select>
                </div>

                <div className="filter-group">
                    <label htmlFor="category-filter">
                        📁 Kategorie
                    </label>
                    <select
                        id="category-filter"
                        value={filters.category}
                        onChange={(e) => handleFilterChange('category', e.target.value)}
                        className="filter-select"
                    >
                        <option value="">Všechny kategorie</option>
                        {categories.map(category => (
                            <option key={category} value={category}>
                                {category}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {hasActiveFilters && (
                <div className="active-filters">
                    <span className="filters-label">Aktivní filtry:</span>
                    <div className="filter-tags">
                        {filters.search && (
                            <div className="filter-tag">
                                🔎 "{filters.search}"
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
                                🏪 {filters.store}
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
                                📁 {filters.category}
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