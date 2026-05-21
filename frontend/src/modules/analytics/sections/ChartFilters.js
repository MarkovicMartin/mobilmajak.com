import React from 'react';
import AnalyticsDateRange from '../../../components/AnalyticsDateRange';
import './ChartFilters.css';

const ChartFilters = ({ filters, onFiltersChange, users = [] }) => {
    // Dostupné metriky
    const availableMetrics = [
        { key: 'polozky_nad_100', label: 'Položky nad 100 Kč', color: '#8884d8' },
        { key: 'sluzby_celkem', label: 'Služby celkem', color: '#82ca9d' },
        { key: 'prumer_polozek_uctu', label: 'Průměr položek/účtu', color: '#ffc658' },
        { key: 'ct300', label: 'CT300', color: '#ff7c7c' },
        { key: 'ct600', label: 'CT600', color: '#8dd1e1' },
        { key: 'ct1200', label: 'CT1200', color: '#d084d0' },
        { key: 'akt', label: 'AKT', color: '#87d068' },
        { key: 'zah250', label: 'ZAH250', color: '#ffb347' },
        { key: 'nap', label: 'NAP', color: '#ff6b6b' },
        { key: 'zah500', label: 'ZAH500', color: '#4ecdc4' },
        { key: 'kop250', label: 'KOP250', color: '#ffe66d' },
        { key: 'kop500', label: 'KOP500', color: '#ff8b94' },
        { key: 'pz1', label: 'PZ1', color: '#95e1d3' },
        { key: 'knz', label: 'KNZ', color: '#fad390' },
        { key: 'aligator', label: 'ALIGATOR', color: '#f8b500' }
    ];

    // Dostupné prodejny (zatím hardcoded, později z API)
    const availableStores = [
        'Čepkov',
        'Globus', 
        'OC Nisa',
        'Tesco',
        'Albert',
        'Kaufland'
    ];

    const handleMetricToggle = (metricKey) => {
        const currentMetrics = filters.metriky || ['polozky_nad_100'];
        let newMetrics;
        
        if (currentMetrics.includes(metricKey)) {
            // Odebrat metriku (ale ponechat alespoň jednu)
            newMetrics = currentMetrics.length > 1 
                ? currentMetrics.filter(m => m !== metricKey)
                : currentMetrics;
        } else {
            // Přidat metriku
            newMetrics = [...currentMetrics, metricKey];
        }
        
        onFiltersChange({ ...filters, metriky: newMetrics });
    };

    const handleStoreToggle = (store) => {
        const currentStores = filters.prodejny || [];
        let newStores;
        
        if (currentStores.includes(store)) {
            newStores = currentStores.filter(s => s !== store);
        } else {
            newStores = [...currentStores, store];
        }
        
        onFiltersChange({ ...filters, prodejny: newStores });
    };

    const applyDateRange = ({ start_date, end_date }) => {
        onFiltersChange({ ...filters, start_date, end_date });
    };

    const handleTypeChange = (type) => {
        // Při změně typu vymažeme datum filtry
        onFiltersChange({ 
            ...filters, 
            type: type,
            start_date: '',
            end_date: ''
        });
    };

    const resetFilters = () => {
        onFiltersChange({
            type: 'daily',
            start_date: '',
            end_date: '',
            prodejny: [],
            metriky: ['polozky_nad_100'],
            prodejce_id: ''
        });
    };

    return (
        <div className="chart-filters">
            <div className="filters-header">
                <h3>📊 Filtry grafu</h3>
                <button className="reset-btn" onClick={resetFilters}>
                    🔄 Reset
                </button>
            </div>

            {/* Typ dat */}
            <div className="filter-group">
                <label className="filter-label">📅 Typ zobrazení:</label>
                <div className="filter-options">
                    <label className="radio-option">
                        <input
                            type="radio"
                            name="dataType"
                            value="daily"
                            checked={filters.type === 'daily'}
                            onChange={(e) => handleTypeChange(e.target.value)}
                        />
                        Denní přehled
                    </label>
                    <label className="radio-option">
                        <input
                            type="radio"
                            name="dataType"
                            value="monthly"
                            checked={filters.type === 'monthly'}
                            onChange={(e) => handleTypeChange(e.target.value)}
                        />
                        Měsíční přehled
                    </label>
                </div>
            </div>

            {/* Období */}
            {filters.type === 'daily' && (
                <div className="filter-group">
                    <label className="filter-label">📆 Období:</label>
                    <AnalyticsDateRange
                        variant="inline"
                        startDate={filters.start_date || ''}
                        endDate={filters.end_date || ''}
                        onApply={applyDateRange}
                        errorClassName="chart-filters-date-error"
                    />
                </div>
            )}

            {/* Metriky */}
            <div className="filter-group">
                <label className="filter-label">📈 Metriky k zobrazení:</label>
                <div className="metrics-grid">
                    {availableMetrics.map(metric => (
                        <label key={metric.key} className="metric-option">
                            <input
                                type="checkbox"
                                checked={filters.metriky?.includes(metric.key) || 
                                        (metric.key === 'polozky_nad_100' && !filters.metriky)}
                                onChange={() => handleMetricToggle(metric.key)}
                            />
                            <span 
                                className="metric-color" 
                                style={{ backgroundColor: metric.color }}
                            ></span>
                            {metric.label}
                        </label>
                    ))}
                </div>
            </div>

            {/* Prodejny */}
            <div className="filter-group">
                <label className="filter-label">🏪 Prodejny:</label>
                <div className="stores-grid">
                    <label className="store-option all-stores">
                        <input
                            type="checkbox"
                            checked={filters.prodejny?.length === 0}
                            onChange={() => onFiltersChange({ ...filters, prodejny: [] })}
                        />
                        <strong>Všechny prodejny</strong>
                    </label>
                    {availableStores.map(store => (
                        <label key={store} className="store-option">
                            <input
                                type="checkbox"
                                checked={filters.prodejny?.includes(store) || false}
                                onChange={() => handleStoreToggle(store)}
                            />
                            {store}
                        </label>
                    ))}
                </div>
            </div>

            {/* Prodejce */}
            {users.length > 0 && (
                <div className="filter-group">
                    <label className="filter-label">👤 Prodejce:</label>
                    <select
                        value={filters.prodejce_id || ''}
                        onChange={(e) => onFiltersChange({ ...filters, prodejce_id: e.target.value })}
                        className="prodejce-select"
                    >
                        <option value="">Všichni prodejci</option>
                        {users.map(user => (
                            <option key={user.id} value={user.id}>
                                {user.jmeno} {user.prijmeni} ({user.uzivatelske_jmeno})
                            </option>
                        ))}
                    </select>
                </div>
            )}

            {/* Aktuální filtry souhrn */}
            <div className="current-filters">
                <small>
                    <strong>Aktuální filtry:</strong> {' '}
                    {filters.type === 'daily' ? 'Denní' : 'Měsíční'} | {' '}
                    {filters.metriky?.length || 1} metrik | {' '}
                    {filters.prodejny?.length === 0 ? 'Všechny prodejny' : `${filters.prodejny?.length || 0} prodejen`}
                    {filters.prodejce_id && ' | Konkrétní prodejce'}
                </small>
            </div>
        </div>
    );
};

export default ChartFilters; 