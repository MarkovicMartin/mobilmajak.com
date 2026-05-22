import React, { useState, useEffect } from 'react';
import { getApiEndpoints } from '../../../config/apiConfig';
import AnalyticsSectionWrapper from '../AnalyticsSectionWrapper';
import CustomDropdown from '../../../components/CustomDropdown';
import AnalyticsDateRange from '../../../components/AnalyticsDateRange';
import { formatISODate } from '../../../utils/analyticsDateRange';
import {
    VICEPRACE_LABEL,
    VICEPRACE_LEADER_LABEL,
    formatVicepraceObrat,
} from '../../../constants/viceprace';
import './SectionStyles.css';

const formatCurrency = (value) => {
    const n = Number(value) || 0;
    return new Intl.NumberFormat('cs-CZ', {
        style: 'currency',
        currency: 'CZK',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(Math.round(n));
};

const ProdejnyPolozky = () => {
    const [salesData, setSalesData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [lastUpdate, setLastUpdate] = useState(null);

    // Filtry - NOVÁ LOGIKA jako v CelkovaCisla
    const [filters, setFilters] = useState(() => {
        const now = new Date();
        const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
        const formatLocal = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
        return {
            period: 'custom',
            start_date: formatLocal(startOfMonth),
            end_date: formatLocal(now),
            selected_month: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`,
            kanal: 'all',
            prodejna_id: '',
            kategorie: ''
        };
    });
    const [dateError, setDateError] = useState('');
    const [quickKey, setQuickKey] = useState('custom'); // today|yesterday|thisWeek|thisMonth|prevMonth|custom

    const applyDateRange = ({ start_date, end_date }) => {
        setFilters(prev => ({ ...prev, period: 'custom', start_date, end_date }));
        setQuickKey('custom');
    };

    // ===== Helpers pro datumy =====
    const setQuickRange = (type) => {
        const now = new Date();
        let from, to;
        if (type === 'today') {
            from = new Date(now.getFullYear(), now.getMonth(), now.getDate());
            to = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        } else if (type === 'yesterday') {
            const y = new Date(now);
            y.setDate(now.getDate() - 1);
            from = new Date(y.getFullYear(), y.getMonth(), y.getDate());
            to = new Date(y.getFullYear(), y.getMonth(), y.getDate());
        } else if (type === 'thisWeek') {
            const day = (now.getDay() + 6) % 7; // 0=Mon
            from = new Date(now.getFullYear(), now.getMonth(), now.getDate() - day);
            to = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        } else if (type === 'thisMonth') {
            from = new Date(now.getFullYear(), now.getMonth(), 1);
            to = new Date(now.getFullYear(), now.getMonth() + 1, 0);
        } else if (type === 'prevMonth') {
            from = new Date(now.getFullYear(), now.getMonth() - 1, 1);
            to = new Date(now.getFullYear(), now.getMonth(), 0);
        }
        setDateError('');
        setFilters(prev => ({
            ...prev,
            period: 'custom',
            start_date: formatISODate(from),
            end_date: formatISODate(to)
        }));
        setQuickKey(type);
    };

    // Načtení dat z API
    const fetchData = async () => {
        setLoading(true);
        setError(null);

        try {
            const endpoints = getApiEndpoints();
            const params = new URLSearchParams();
            Object.keys(filters).forEach(key => {
                if (filters[key] && filters[key] !== '') {
                    params.append(key, filters[key]);
                }
            });

            console.log('ProdejnyPolozky: fetchData called with filters:', filters);
            console.log('ProdejnyPolozky: API URL:', `${endpoints.webProdejePolozky}?${params}`);

            const response = await fetch(`${endpoints.webProdejePolozky}?${params}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();

            console.log('ProdejnyPolozky: API response:', result);

            if (result.success && Array.isArray(result.data)) {
                setSalesData(result.data);
                setLastUpdate(result.lastUpdate || result.generated_at || new Date().toISOString());
            } else {
                throw new Error(result.error || 'Chyba při načítání dat');
            }

        } catch (err) {
            console.error('Chyba při načítání dat:', err);
            setError(err.message);
            setSalesData([]);
        } finally {
            setLoading(false);
        }
    };

    // Zpracování změny filtru
    const handleFilterChange = (filterName, value) => {
        setFilters(prev => ({
            ...prev,
            [filterName]: value
        }));
    };

    // Načtení dat při změně filtrů
    useEffect(() => {
        fetchData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [filters]);

    // Celkový počet položek nad 100 Kč (bez sčítání podmnožin)
    const totalPolozky = salesData.reduce((sum, item) => sum + (item.polozky_nad_100 || 0), 0);
    // "Z toho" služby a "Z toho" Sunshine
    const totalSluzby = salesData.reduce((sum, item) => sum + (item.sluzby_celkem || 0), 0);
    const totalSunshine = salesData.reduce((sum, item) => sum + (item.sunshine || 0), 0);
    const totalObrat = salesData.reduce((sum, item) => sum + (item.celkovy_obrat || 0), 0);
    const totalAktivniDoklady = salesData.reduce((sum, item) => sum + (item.unikatni_doklady || 0), 0);
    const avgHodnotaUctenky = totalAktivniDoklady > 0
        ? formatCurrency(totalObrat / totalAktivniDoklady)
        : formatCurrency(0);
    const avgPolDok = salesData.length > 0
        ? (salesData.reduce((sum, item) => sum + (item.pol_dok || 0), 0) / salesData.length).toFixed(2)
        : 0;
    const aktivnichProdejcu = salesData.filter(item => item.polozky_nad_100 > 0).length;

    const nejlepsiProdejce = salesData.reduce((best, current) =>
        (current.polozky_nad_100 > (best.polozky_nad_100 || 0)) ? current : best, {});

    const totalViceprace = salesData.reduce((sum, item) => sum + (item.viceprace_obrat || 0), 0);
    const nejlepsiDyskar = salesData.reduce((best, current) =>
        ((current.viceprace_obrat || 0) > (best.viceprace_obrat || 0)) ? current : best, {});

    return (
        <AnalyticsSectionWrapper title="Prodejny - Položky" icon="📱">
            <div className="analytics-section">

                {/* Filtry - NOVÁ SEKCE jako v CelkovaCisla */}
                <div className="celkova-cisla-filters">
                    <div className="filter-row">
                        {/* Období – custom dropdown s měsíci */}
                        <div className="filter-group">
                            <label>Období:</label>
                            {(() => {
                                const monthNames = ['leden', 'únor', 'březen', 'duben', 'květen', 'červen', 'červenec', 'srpen', 'září', 'říjen', 'listopad', 'prosinec'];
                                const opts = [];

                                // Generujeme měsíce od ledna 2024 do aktuálního měsíce
                                const startYear = 2024;
                                const startMonth = 0; // leden = 0
                                const now = new Date();
                                const currentYear = now.getFullYear();
                                const currentMonth = now.getMonth();

                                for (let year = startYear; year <= currentYear; year++) {
                                    const monthStart = (year === startYear) ? startMonth : 0;
                                    const monthEnd = (year === currentYear) ? currentMonth : 11;

                                    for (let month = monthStart; month <= monthEnd; month++) {
                                        const ym = `${year}-${String(month + 1).padStart(2, '0')}`;
                                        const label = `${monthNames[month].charAt(0).toUpperCase() + monthNames[month].slice(1)} ${year}`;
                                        opts.push({ value: `month:${ym}`, label });
                                    }
                                }

                                // Přidáme vlastní období na začátek
                                opts.unshift({ value: 'custom', label: '🗓️ Vlastní období' });

                                // Řadíme měsíce od nejnovějšího k nejstaršímu (kromě první možnosti)
                                const customOption = opts.shift();
                                opts.reverse();
                                opts.unshift(customOption);

                                const currentValue = filters.period === 'monthly_select' ? `month:${filters.selected_month}` : 'custom';
                                return (
                                    <CustomDropdown
                                        options={opts}
                                        value={currentValue}
                                        placeholder="Vyberte období"
                                        onChange={(selectedValue) => {
                                            console.log('ProdejnyPolozky: CustomDropdown onChange:', selectedValue);
                                            if (selectedValue === 'custom') {
                                                handleFilterChange('period', 'custom');
                                            } else if (selectedValue.startsWith('month:')) {
                                                const ym = selectedValue.split(':')[1];
                                                console.log('ProdejnyPolozky: Setting month:', ym);
                                                setFilters(prev => {
                                                    const newFilters = {
                                                        ...prev,
                                                        period: 'monthly_select',
                                                        selected_month: ym,
                                                        start_date: '',
                                                        end_date: ''
                                                    };
                                                    console.log('ProdejnyPolozky: New filters:', newFilters);
                                                    return newFilters;
                                                });
                                                setDateError('');
                                            }
                                        }}
                                    />
                                );
                            })()}
                        </div>

                        {/* Vlastní období */}
                        {filters.period === 'custom' && (
                            <AnalyticsDateRange
                                startDate={filters.start_date}
                                endDate={filters.end_date}
                                onApply={applyDateRange}
                                onErrorChange={setDateError}
                                showError={false}
                            />
                        )}

                        {/* Rychlé volby období */}
                        <div className="filter-group" style={{ minWidth: 240 }}>
                            <label>Rychlé volby:</label>
                            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                <button className="refresh-btn" onClick={() => setQuickRange('today')}>Dnešek</button>
                                <button className="refresh-btn" onClick={() => setQuickRange('yesterday')}>Včerejšek</button>
                                <button className="refresh-btn" onClick={() => setQuickRange('thisWeek')}>Tento týden</button>
                                <button className="refresh-btn" onClick={() => setQuickRange('thisMonth')}>Tento měsíc</button>
                                <button className="refresh-btn" onClick={() => setQuickRange('prevMonth')}>Minulý měsíc</button>
                            </div>
                        </div>

                        {/* Prodejní kanál */}
                        <div className="filter-group">
                            <label>Kanál:</label>
                            <select
                                value={filters.kanal}
                                onChange={(e) => handleFilterChange('kanal', e.target.value)}
                            >
                                <option value="all">Všechny kanály</option>
                                <option value="prodejna">Prodejna</option>
                                <option value="eshop">E-shop</option>
                                <option value="allegro">ALLEGRO</option>
                                <option value="servis">Servis</option>
                            </select>
                        </div>

                        {/* Refresh button */}
                        <div className="filter-group">
                            <button
                                className="refresh-btn"
                                onClick={fetchData}
                                disabled={loading || !!dateError}
                            >
                                {loading ? '🔄' : '🔄'} Obnovit
                            </button>
                        </div>
                    </div>
                    {dateError && <div className="celkova-cisla-error" style={{ marginTop: 8 }}>{dateError}</div>}
                </div>

                {/* Loading state */}
                {loading && (
                    <div className="celkova-cisla-loading">
                        <div className="loading-spinner"></div>
                        <p>Načítám data...</p>
                    </div>
                )}

                {/* Error state */}
                {error && (
                    <div className="celkova-cisla-error">
                        <h3>❌ Chyba při načítání dat</h3>
                        <p>{error}</p>
                        <button onClick={fetchData}>Zkusit znovu</button>
                    </div>
                )}

                {/* Last update info */}
                {lastUpdate && !loading && !error && (
                    <div className="last-update">
                        <small>
                            Poslední aktualizace: {new Date(lastUpdate).toLocaleString('cs-CZ')}
                        </small>
                    </div>
                )}

                <div className="section-content">
                    <div className="stats-cards">
                        <div className="stat-card">
                            <h4>Celkem položek nad 100 Kč</h4>
                            <div className="stat-value">{totalPolozky}</div>
                            <div className="stat-change">Z {aktivnichProdejcu} aktivních prodejců</div>
                        </div>
                        <div className="stat-card">
                            <h4>Z toho Služby</h4>
                            <div className="stat-value">{totalSluzby}</div>
                            <div className="stat-change positive">Prodejní kódy služeb</div>
                        </div>
                        <div className="stat-card">
                            <h4>Průměrná hodnota účtenky</h4>
                            <div className="stat-value">{avgHodnotaUctenky}</div>
                            <div className="stat-change">Obrat s DPH / aktivní účtenky</div>
                        </div>
                        <div className="stat-card">
                            <h4>Průměr položek/účtenka</h4>
                            <div className="stat-value">{avgPolDok}</div>
                            <div className="stat-change">Průměr všech prodejců</div>
                        </div>
                        <div className="stat-card">
                            <h4>Nejlepší prodejce</h4>
                            <div className="stat-value">{nejlepsiProdejce.prodejce || 'N/A'}</div>
                            <div className="stat-change positive">{nejlepsiProdejce.polozky_nad_100 || 0} položek</div>
                        </div>
                        <div className="stat-card">
                            <h4>{VICEPRACE_LEADER_LABEL}</h4>
                            <div className="stat-value">{nejlepsiDyskar.prodejce || 'N/A'}</div>
                            <div className="stat-change positive">
                                {formatVicepraceObrat(nejlepsiDyskar.viceprace_obrat)} · celkem {formatVicepraceObrat(totalViceprace)}
                            </div>
                        </div>
                    </div>

                    <div className="data-table">
                        <h4>
                            Přehled prodejců
                            {loading && <span className="loading-spinner"> ⟳</span>}
                        </h4>

                        {salesData.length > 0 ? (
                            <div className="sellers-cards">
                                {salesData.map((item, index) => (
                                    <div key={index} className="seller-card">
                                        <div className="seller-header">
                                            <div className="seller-info">
                                                <h5 className="seller-name">{item.prodejce}</h5>
                                                <span className="seller-store">{item.prodejna}</span>
                                            </div>
                                            <div className="seller-rank">
                                                <span className="rank-number">#{index + 1}</span>
                                            </div>
                                        </div>

                                        <div className="seller-main-metrics">
                                            <div className="metric-item primary">
                                                <span className="metric-label">Položky nad 100 Kč</span>
                                                <span className="metric-value highlight-blue">{item.polozky_nad_100 || 0}</span>
                                            </div>
                                            <div className="metric-item primary">
                                                <span className="metric-label">Z toho Služby</span>
                                                <span className="metric-value highlight-green">{item.sluzby_celkem || 0}</span>
                                            </div>
                                            <div className="metric-item primary">
                                                <span className="metric-label">Prům. hodnota účtenky</span>
                                                <span className="metric-value highlight-yellow">
                                                    {formatCurrency(item.prumer_hodnota_uctenky ?? 0)}
                                                </span>
                                            </div>
                                            <div className="metric-item">
                                                <span className="metric-label">Průměr pol./účt.</span>
                                                <span className="metric-value">{(item.pol_dok || 0).toFixed(2)}</span>
                                            </div>
                                            <div className="metric-item">
                                                <span className="metric-label">Unikátní doklady</span>
                                                <span className="metric-value">{item.unikatni_doklady || 0}</span>
                                            </div>
                                            <div className="metric-item">
                                                <span className="metric-label">Položky ≥ 29 Kč</span>
                                                <span className="metric-value">{item.polozky_nad_29 || 0}</span>
                                            </div>
                                        </div>

                                        <div className="seller-services">
                                            <h6>Detail</h6>
                                            <div className="services-grid">
                                                <div className="service-item service-item-servis" title={item.servisni_prace != null ? '10 % marže servisních prací' : 'Uživatel nemá technik_id'}>
                                                    <span className="service-name">Servis</span>
                                                    <span className="service-count">{item.servis_provize ?? 0}</span>
                                                </div>
                                                <div className="service-item service-item-viceprace" title="Kód P63615, obrat s DPH, nepočítá se do položek nad 100 Kč ani do bodů">
                                                    <span className="service-name">{VICEPRACE_LABEL}</span>
                                                    <span className="service-count">{formatVicepraceObrat(item.viceprace_obrat)}</span>
                                                </div>
                                                <div className="service-item">
                                                    <span className="service-name">CT300</span>
                                                    <span className="service-count">{item.ct300 || 0}</span>
                                                </div>
                                                <div className="service-item">
                                                    <span className="service-name">CT600</span>
                                                    <span className="service-count">{item.ct600 || 0}</span>
                                                </div>
                                                <div className="service-item">
                                                    <span className="service-name">CT1200</span>
                                                    <span className="service-count">{item.ct1200 || 0}</span>
                                                </div>
                                                <div className="service-item">
                                                    <span className="service-name">AKT</span>
                                                    <span className="service-count">{item.akt || 0}</span>
                                                </div>
                                                <div className="service-item">
                                                    <span className="service-name">ZAH250</span>
                                                    <span className="service-count">{item.zah250 || 0}</span>
                                                </div>
                                                <div className="service-item">
                                                    <span className="service-name">NAP</span>
                                                    <span className="service-count">{item.nap || 0}</span>
                                                </div>
                                                <div className="service-item">
                                                    <span className="service-name">ZAH500</span>
                                                    <span className="service-count">{item.zah500 || 0}</span>
                                                </div>
                                                <div className="service-item">
                                                    <span className="service-name">KOP250</span>
                                                    <span className="service-count">{item.kop250 || 0}</span>
                                                </div>
                                                <div className="service-item">
                                                    <span className="service-name">KOP500</span>
                                                    <span className="service-count">{item.kop500 || 0}</span>
                                                </div>
                                                <div className="service-item">
                                                    <span className="service-name">PZ1</span>
                                                    <span className="service-count">{item.pz1 || 0}</span>
                                                </div>
                                                <div className="service-item">
                                                    <span className="service-name">KNZ</span>
                                                    <span className="service-count">{item.knz || 0}</span>
                                                </div>
                                                <div className="service-item">
                                                    <span className="service-name">Sklíčka</span>
                                                    <span className="service-count">{item.sklicka || 0}</span>
                                                </div>
                                                <div className="service-item">
                                                    <span className="service-name">Lepení</span>
                                                    <span className="service-count">{item.lepeni || 0}</span>
                                                </div>
                                                <div className="service-item highlight">
                                                    <span className="service-name font-bold">Výkup</span>
                                                    <span className="service-count font-bold">{item.vykupy || 0}</span>
                                                </div>
                                                <div className="service-item highlight-yellow">
                                                    <span className="service-name">SUNSHINE</span>
                                                    <span className="service-count">{item.sunshine || 0}</span>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="seller-performance">
                                            <div className="performance-bar">
                                                <div
                                                    className="performance-fill"
                                                    style={{
                                                        width: `${Math.min((item.polozky_nad_100 / Math.max(...salesData.map(s => s.polozky_nad_100 || 0))) * 100, 100)}%`
                                                    }}
                                                ></div>
                                            </div>
                                            <span className="performance-text">Výkonnost: {Math.round((item.polozky_nad_100 / Math.max(...salesData.map(s => s.polozky_nad_100 || 0))) * 100)}%</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="no-data">
                                {loading ? 'Načítám data...' : 'Žádná data k zobrazení'}
                            </div>
                        )}
                    </div>

                    <div className="summary-section">
                        <div className="summary-card">
                            <h4>🏆 Žebříček všech prodejců</h4>
                            <div className="top-sellers">
                                {salesData
                                    .sort((a, b) => (b.polozky_nad_100 || 0) - (a.polozky_nad_100 || 0))
                                    .map((seller, index) => (
                                        <div key={index} className={`top-seller ${index === 0 ? 'winner' : index === 1 ? 'second' : index === 2 ? 'third' : ''}`}>
                                            <span className="position">{index + 1}.</span>
                                            <span className="name">{seller.prodejce}</span>
                                            <span className="score">{seller.polozky_nad_100} položek</span>
                                            <span className="store">({seller.prodejna})</span>
                                        </div>
                                    ))
                                }
                            </div>
                        </div>

                        <div className="summary-card">
                            <h4>📈 Přehled prodejen</h4>
                            <div className="store-summary">
                                {salesData.reduce((stores, item) => {
                                    const existing = stores.find(s => s.name === item.prodejna);
                                    if (existing) {
                                        existing.polozky += item.polozky_nad_100 || 0;
                                        existing.sluzby += item.sluzby_celkem || 0;
                                        existing.prodejci++;
                                    } else {
                                        stores.push({
                                            name: item.prodejna,
                                            polozky: item.polozky_nad_100 || 0,
                                            sluzby: item.sluzby_celkem || 0,
                                            prodejci: 1
                                        });
                                    }
                                    return stores;
                                }, [])
                                    .map((store, index) => (
                                        <div key={index} className="store-item">
                                            <strong>{store.name}</strong>
                                            <span>{store.polozky} položek • {store.sluzby} služeb • {store.prodejci} prodejců</span>
                                        </div>
                                    ))}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </AnalyticsSectionWrapper>
    );
};

export default ProdejnyPolozky; 