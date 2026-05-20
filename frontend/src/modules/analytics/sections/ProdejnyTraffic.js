
import React, { useState, useEffect } from 'react';
import {
    ResponsiveContainer,
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
} from 'recharts';
import api from '../../../services/api';
import AnalyticsSectionWrapper from '../AnalyticsSectionWrapper';
import CustomDropdown from '../../../components/CustomDropdown';
import './Prodejnyzakaznici.css';

const ProdejnyTrafficView = ({ isComparison = false }) => {
    // --- State ---
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);
    const [stores, setStores] = useState([]); // List of stores for dropdown

    // Filters - podobné jako v CelkovaCisla
    const [filters, setFilters] = useState(() => {
        const now = new Date();
        const start = new Date(now.getFullYear(), now.getMonth(), 1);
        const fmt = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
        return {
            period: 'custom',
            start_date: fmt(start),
            end_date: fmt(now),
            selected_month: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`,
            stredisko: '', // Empty = All
            granularity: 'daily'
        };
    });
    const [dateError, setDateError] = useState('');
    const [dateDraft, setDateDraft] = useState(() => ({
        start_date: filters.start_date,
        end_date: filters.end_date,
    }));

    const isValidISODate = (str) => {
        if (!/^\d{4}-\d{2}-\d{2}$/.test(str)) return false;
        const [y, m, d] = str.split('-').map(Number);
        const dt = new Date(y, m - 1, d);
        return dt.getFullYear() === y && dt.getMonth() === m - 1 && dt.getDate() === d;
    };

    // --- Actions ---
    const loadData = async () => {
        setLoading(true);
        setError(null);
        try {
            const params = new URLSearchParams({
                granularity: filters.granularity
            });

            // Určení datumového rozsahu podle period
            if (filters.period === 'monthly_select' && filters.selected_month) {
                const [year, month] = filters.selected_month.split('-');
                const startDate = new Date(year, month - 1, 1);
                const endDate = new Date(year, month, 0);
                const fmt = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
                params.append('date_from', fmt(startDate));
                params.append('date_to', fmt(endDate));
            } else {
                params.append('date_from', filters.start_date);
                params.append('date_to', filters.end_date);
            }

            if (filters.stredisko) params.append('stredisko', filters.stredisko);

            const res = await api.get(`/analytics/prodejny-zakaznici/traffic/?${params}`);

            if (res.data.success) {
                setData(res.data);

                // Update stores list if provided by backend (first load)
                if (res.data.available_stores && res.data.available_stores.length > 0) {
                    // Map strings to objects {value, label}
                    const storeOptions = res.data.available_stores.map(s => ({
                        value: s,
                        label: s
                    }));
                    storeOptions.unshift({ value: '', label: '🏠 Všechny prodejny' });
                    setStores(storeOptions);
                } else if (!stores.length) {
                    // Fallback stores if API didn't return them (legacy)
                    setStores([
                        { value: '', label: '🏠 Všechny prodejny' },
                        { value: 'Čepkov', label: 'Čepkov' },
                        { value: 'Globus', label: 'Globus' },
                        { value: 'Šternberk', label: 'Šternberk' },
                        { value: 'Přerov', label: 'Přerov' },
                        { value: 'Vsetín', label: 'Vsetín' },
                        { value: 'Centrála', label: 'Centrála' }
                    ]);
                }

            } else {
                setError(res.data.error || 'Chyba při načítání dat');
            }
        } catch (e) {
            console.error(e);
            setError(e.message || 'Nepodařilo se načíst data');
        } finally {
            setLoading(false);
        }
    };

    // Reload on filter change
    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(() => {
        if ((filters.period === 'custom' && filters.start_date && filters.end_date) ||
            (filters.period === 'monthly_select' && filters.selected_month)) {
            loadData();
        }
    }, [filters]);

    // --- Helpers ---
    const setQuickRange = (type) => {
        const now = new Date();
        const fmt = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
        let from, to;

        switch (type) {
            case 'today':
                from = new Date(now); to = new Date(now);
                break;
            case 'yesterday':
                const y = new Date(now); y.setDate(now.getDate() - 1);
                from = y; to = y;
                break;
            case 'thisWeek':
                const day = (now.getDay() + 6) % 7; // Mon=0
                from = new Date(now.getFullYear(), now.getMonth(), now.getDate() - day);
                to = new Date(now);
                break;
            case 'thisMonth':
                from = new Date(now.getFullYear(), now.getMonth(), 1);
                to = new Date(now.getFullYear(), now.getMonth() + 1, 0);
                break;
            case 'prevMonth':
                from = new Date(now.getFullYear(), now.getMonth() - 1, 1);
                to = new Date(now.getFullYear(), now.getMonth(), 0);
                break;
            default: return;
        }

        const range = {
            start_date: fmt(from),
            end_date: fmt(to),
        };
        setDateDraft(range);
        setFilters(prev => ({
            ...prev,
            period: 'custom',
            ...range,
        }));
        setDateError('');
    };

    const handleFilterChange = (key, value) => {
        setFilters(prev => ({
            ...prev,
            [key]: value
        }));
    };

    const onDateDraftChange = (field, value) => {
        setDateDraft(prev => ({ ...prev, [field]: value }));
        setDateError('');
    };

    const applyCustomDates = () => {
        const { start_date, end_date } = dateDraft;
        if (!isValidISODate(start_date) || !isValidISODate(end_date)) {
            setDateError('Neplatné datum. Zkontrolujte prosím zadání.');
            return;
        }
        let start = start_date;
        let end = end_date;
        if (new Date(start) > new Date(end)) {
            [start, end] = [end, start];
        }
        setDateError('');
        setDateDraft({ start_date: start, end_date: end });
        setFilters(prev => {
            if (prev.period === 'custom' && prev.start_date === start && prev.end_date === end) {
                return prev;
            }
            return { ...prev, period: 'custom', start_date: start, end_date: end };
        });
    };

    const onDateKeyDown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            applyCustomDates();
        }
    };

    // --- Heatmap Logic ---
    const renderHeatmap = () => {
        if (!data?.heatmap) return null;

        const daysLabel = { 2: 'Pondělí', 3: 'Úterý', 4: 'Středa', 5: 'Čtvrtek', 6: 'Pátek', 7: 'Sobota', 1: 'Neděle' };
        const daysShort = { 2: 'Po', 3: 'Út', 4: 'St', 5: 'Čt', 6: 'Pá', 7: 'So', 1: 'Ne' };
        const orderedDays = [2, 3, 4, 5, 6, 7, 1]; // Po-Ne

        // Hours 8 to 20
        const startHour = 8;
        // const endHour = 20; // unused
        const hours = Array.from({ length: 13 }, (_, i) => i + startHour); // 8..20

        // Determine max value for opacity
        const maxVal = Math.max(...data.heatmap.map(d => d.visits_avg), 1);

        const getColor = (val) => {
            if (val === 0) return '#f1f5f9';
            const intensity = val / maxVal;

            // Gradient from light blue to dark blue
            if (intensity < 0.2) return 'rgba(219, 234, 254, 1)'; // very light blue
            if (intensity < 0.4) return 'rgba(191, 219, 254, 1)'; // light blue
            if (intensity < 0.6) return 'rgba(147, 197, 253, 1)'; // medium blue
            if (intensity < 0.8) return 'rgba(96, 165, 250, 1)';  // strong blue
            return 'rgba(59, 130, 246, 1)'; // dark blue
        };

        return (
            <div className="traffic-heatmap-viz">
                {/* Header row: Empty corner + Hour labels */}
                <div key="h-empty" className="heatmap-label"></div>
                {hours.map(h => (
                    <div key={`h-${h}`} className="heatmap-label" style={{ fontWeight: 600 }}>
                        {h}:00
                    </div>
                ))}

                {/* Rows: Day label + cells for each hour */}
                {orderedDays.map(dId => {
                    const rowData = data.heatmap.filter(d => d.weekday === dId);
                    return (
                        <React.Fragment key={`row-${dId}`}>
                            <div className="heatmap-label" style={{ fontWeight: 700, color: '#1e293b', justifyContent: 'flex-end', paddingRight: 8 }}>
                                {daysShort[dId]}
                            </div>
                            {hours.map(h => {
                                const cell = rowData.find(d => d.hour === h);
                                const val = cell ? cell.visits_avg : 0;
                                const displayVal = Math.round(val);
                                return (
                                    <div
                                        key={`cell-${dId}-${h}`}
                                        className="heatmap-cell"
                                        style={{ backgroundColor: getColor(val) }}
                                        title={`${daysLabel[dId]} ${h}:00 - Průměr ${val.toFixed(1)} zákazníků`}
                                    >
                                        {displayVal > 0 && (
                                            <span style={{
                                                fontSize: 13,
                                                color: val / maxVal > 0.5 ? 'white' : '#1e293b',
                                                fontWeight: 600
                                            }}>
                                                {displayVal}
                                            </span>
                                        )}
                                    </div>
                                );
                            })}
                        </React.Fragment>
                    );
                })}
            </div>
        );
    };

    return (
        <div className={`traffic-view ${isComparison ? 'is-comparison' : ''}`}>
            <div className="traffic-dashboard">
                {loading && (
                    <div className="traffic-loading">
                        <div className="traffic-loading-spinner"></div>
                    </div>
                )}

                {/* --- 1. FILTERS (stejný styl jako CelkovaCisla) --- */}
                <div className="celkova-cisla-filters" style={{ marginBottom: 20 }}>
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
                                            if (selectedValue === 'custom') {
                                                setDateDraft({
                                                    start_date: filters.start_date,
                                                    end_date: filters.end_date,
                                                });
                                                handleFilterChange('period', 'custom');
                                            } else if (selectedValue.startsWith('month:')) {
                                                const ym = selectedValue.split(':')[1];
                                                setFilters(prev => ({
                                                    ...prev,
                                                    period: 'monthly_select',
                                                    selected_month: ym,
                                                    start_date: '',
                                                    end_date: ''
                                                }));
                                                setDateError('');
                                            }
                                        }}
                                    />
                                );
                            })()}
                        </div>

                        {/* Vlastní období */}
                        {filters.period === 'custom' && (
                            <>
                                <div className="filter-group">
                                    <label>Od:</label>
                                    <input
                                        type="date"
                                        value={dateDraft.start_date}
                                        max={dateDraft.end_date || undefined}
                                        onChange={(e) => onDateDraftChange('start_date', e.target.value)}
                                        onBlur={applyCustomDates}
                                        onKeyDown={onDateKeyDown}
                                    />
                                </div>
                                <div className="filter-group">
                                    <label>Do:</label>
                                    <input
                                        type="date"
                                        value={dateDraft.end_date}
                                        min={dateDraft.start_date || undefined}
                                        onChange={(e) => onDateDraftChange('end_date', e.target.value)}
                                        onBlur={applyCustomDates}
                                        onKeyDown={onDateKeyDown}
                                    />
                                </div>
                            </>
                        )}

                        {dateError && filters.period === 'custom' && (
                            <div className="error-container" style={{ marginTop: 8 }}>{dateError}</div>
                        )}

                        {/* Rychlé volby období */}
                        {!isComparison && (
                            <div className="filter-group quick-filters">
                                <label>Rychlé volby:</label>
                                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                    <button className="refresh-btn" onClick={() => setQuickRange('today')}>Dnešek</button>
                                    <button className="refresh-btn" onClick={() => setQuickRange('yesterday')}>Včerejšek</button>
                                    <button className="refresh-btn" onClick={() => setQuickRange('thisWeek')}>Tento týden</button>
                                    <button className="refresh-btn" onClick={() => setQuickRange('thisMonth')}>Tento měsíc</button>
                                    <button className="refresh-btn" onClick={() => setQuickRange('prevMonth')}>Minulý měsíc</button>
                                </div>
                            </div>
                        )}

                        {/* Prodejna Selector */}
                        <div className="filter-group">
                            <label>Prodejna:</label>
                            <select
                                value={filters.stredisko}
                                onChange={(e) => handleFilterChange('stredisko', e.target.value)}
                            >
                                {stores.map((s, i) => (
                                    <option key={i} value={s.value}>{s.label}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                </div>

                {error && <div className="error-banner" style={{ background: '#fee2e2', color: '#b91c1c', padding: 12, borderRadius: 8 }}>{error}</div>}

                {data && (
                    <>
                        {/* --- 2. SUMMARY TILES --- */}
                        <div className="traffic-summary-row">
                            <div className="traffic-tile">
                                <div className="traffic-tile-header">
                                    <span className="traffic-tile-title">Celková návštěvnost</span>
                                    <span className="traffic-tile-icon">👥</span>
                                </div>
                                <div className="traffic-tile-value">{data.summary.total_visits}</div>
                                <div className="traffic-tile-meta" style={{ marginTop: 8 }}>Počet unikátních zákazníků</div>
                            </div>

                            <div className="traffic-tile">
                                <div className="traffic-tile-header">
                                    <span className="traffic-tile-title">Denní průměr</span>
                                    <span className="traffic-tile-icon">📊</span>
                                </div>
                                <div className="traffic-tile-value">{data.summary.daily_avg}</div>
                                <div className="traffic-tile-meta">Průměr na jeden den</div>
                            </div>

                            {/* Insight Tile - Nejsilnější hodina */}
                            <div className="traffic-tile">
                                <div className="traffic-tile-header">
                                    <span className="traffic-tile-title">Nejsilnější hodina</span>
                                    <span className="traffic-tile-icon">⏰</span>
                                </div>
                                <div className="traffic-tile-value" style={{ fontSize: 22 }}>
                                    {data.heatmap && data.heatmap.length > 0
                                        ? (() => {
                                            const max = data.heatmap.reduce((p, c) => (p.visits_avg > c.visits_avg ? p : c));
                                            return `${max.hour}:00 (${Math.round(max.visits_avg)})`;
                                        })()
                                        : '—'
                                    }
                                </div>
                                <div className="traffic-tile-meta">Průměrně nejvíce lidí</div>
                            </div>

                            {/* Insight Tile - Nejslabší hodina */}
                            <div className="traffic-tile">
                                <div className="traffic-tile-header">
                                    <span className="traffic-tile-title">Nejslabší hodina</span>
                                    <span className="traffic-tile-icon">🕐</span>
                                </div>
                                <div className="traffic-tile-value" style={{ fontSize: 22 }}>
                                    {data.heatmap && data.heatmap.length > 0
                                        ? (() => {
                                            // Filtrujeme pouze nenulové hodnoty
                                            const nonZero = data.heatmap.filter(d => d.visits_avg > 0);
                                            if (nonZero.length === 0) return '—';
                                            const min = nonZero.reduce((p, c) => (p.visits_avg < c.visits_avg ? p : c));
                                            return `${min.hour}:00 (${Math.round(min.visits_avg)})`;
                                        })()
                                        : '—'
                                    }
                                </div>
                                <div className="traffic-tile-meta">Průměrně nejméně lidí</div>
                            </div>
                        </div>

                        {/* --- 3. TIMELINE CHART --- */}
                        <div className="traffic-chart-container">
                            <div className="traffic-chart-header">
                                <span className="traffic-chart-title">Vývoj v čase</span>
                                <div className="traffic-chart-controls">
                                    <button
                                        className={`traffic-quick-btn ${filters.granularity === 'daily' ? 'active' : ''}`}
                                        onClick={() => handleFilterChange('granularity', 'daily')}
                                    >
                                        Po dnech
                                    </button>
                                    <button
                                        className={`traffic-quick-btn ${filters.granularity === 'hourly' ? 'active' : ''}`}
                                        onClick={() => handleFilterChange('granularity', 'hourly')}
                                    >
                                        Po hodinách
                                    </button>
                                </div>
                            </div>

                            <div style={{ width: '100%', height: 350 }}>
                                <ResponsiveContainer width="100%" height="100%">
                                    <AreaChart data={data.timeline} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                                        <defs>
                                            <linearGradient id="colorVisits" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
                                                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                            </linearGradient>
                                        </defs>
                                        <XAxis
                                            dataKey="date"
                                            tick={{ fontSize: 12 }}
                                            tickFormatter={val => val.length > 10 ? val.substring(11, 16) : val.substring(5)}
                                        />
                                        <YAxis />
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                        <Tooltip
                                            labelFormatter={val => val}
                                            formatter={(value) => [value, 'Návštěvnost']}
                                        />
                                        <Area
                                            type="monotone"
                                            dataKey="visits"
                                            stroke="#3b82f6"
                                            strokeWidth={2}
                                            fillOpacity={1}
                                            fill="url(#colorVisits)"
                                            activeDot={{ r: 6 }}
                                            animationDuration={800}
                                        />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        {/* --- 4. HEATMAP --- */}
                        <div className="traffic-heatmap-card">
                            <div className="traffic-chart-header">
                                <div>
                                    <div className="traffic-chart-title">Heatmapa vytíženosti</div>
                                    <div style={{ color: '#64748b', fontSize: 13, marginTop: 4 }}>
                                        Kdy chodí zákazníci nejčastěji (průměrné hodnoty za vybrané období)
                                    </div>
                                </div>
                                {!isComparison && (
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#64748b' }}>
                                            <div style={{ width: 20, height: 20, background: '#f1f5f9', borderRadius: 4 }}></div>
                                            <span>Nízká</span>
                                            <div style={{ width: 20, height: 20, background: 'rgba(147, 197, 253, 1)', borderRadius: 4 }}></div>
                                            <span>Střední</span>
                                            <div style={{ width: 20, height: 20, background: 'rgba(59, 130, 246, 1)', borderRadius: 4 }}></div>
                                            <span>Vysoká</span>
                                        </div>
                                    </div>
                                )}
                            </div>
                            {renderHeatmap()}
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

const ProdejnyZakaznici = () => {
    const [isComparison, setIsComparison] = useState(false);

    return (
        <AnalyticsSectionWrapper title="Prodejny & Zákazníci" icon="👣">
            <div className={`traffic-dashboard-container ${isComparison ? 'comparison-mode' : ''}`}>
                <div className="traffic-controls" style={{
                    display: 'flex',
                    justifyContent: 'flex-end',
                    padding: '0 20px 10px',
                    marginBottom: '10px'
                }}>
                    <button
                        className={`comparison-toggle ${isComparison ? 'active' : ''}`}
                        onClick={() => setIsComparison(!isComparison)}
                        style={{
                            padding: '8px 16px',
                            background: isComparison ? '#e74c3c' : '#3498db',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontWeight: '600',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px'
                        }}
                    >
                        {isComparison ? '🛑 Zrušit srovnání' : '🆚 Srovnání'}
                    </button>
                </div>

                <div className="traffic-views" style={{
                    display: 'flex',
                    flexDirection: isComparison ? 'row' : 'column',
                    gap: isComparison ? '20px' : '0'
                }}>
                    <div className="view-pane left-pane" style={{
                        flex: 1,
                        minWidth: 0,
                        transition: 'all 0.3s ease'
                    }}>
                        <ProdejnyTrafficView isComparison={isComparison} />
                    </div>

                    {isComparison && (
                        <div className="view-pane right-pane" style={{
                            flex: 1,
                            minWidth: 0,
                            borderLeft: '1px dashed #cbd3da',
                            paddingLeft: '20px'
                        }}>
                            <ProdejnyTrafficView isComparison={isComparison} />
                        </div>
                    )}
                </div>
            </div>
        </AnalyticsSectionWrapper>
    );
};

export default ProdejnyZakaznici;
