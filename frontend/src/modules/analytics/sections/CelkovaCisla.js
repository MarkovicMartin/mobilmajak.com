import React, { useState, useEffect, useRef } from 'react';
import AnalyticsSectionWrapper from '../AnalyticsSectionWrapper';
import CustomDropdown from '../../../components/CustomDropdown';
import AnalyticsDateRange from '../../../components/AnalyticsDateRange';
import { formatISODate } from '../../../utils/analyticsDateRange';
import './CelkovaCisla.css';

const CategoryTimeseries = ({ filters, defaultGroupBy, defaultSelected }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [dimension, setDimension] = useState('kategorie');
    const [groupBy, setGroupBy] = useState('monthly');
    const [selected, setSelected] = useState([]);
    const [tip, setTip] = useState({ visible: false, x: 0, y: 0, text: '' });

    useEffect(() => {
        const load = async () => {
            setLoading(true); setError(null);
            try {
                const p = new URLSearchParams();
                Object.keys(filters).forEach(k => { if (filters[k] !== undefined && filters[k] !== null && filters[k] !== '') p.append(k, filters[k]); });
                p.set('dimension', dimension); p.set('group_by', groupBy);
                selected.forEach(v => p.append('selected[]', v));
                const res = await fetch(`/api/analytics/celkova-cisla/categories-timeseries/?${p}`, { credentials: 'include' });
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const json = await res.json();
                if (!json.success && json.data === undefined) throw new Error(json.error || 'Chyba');
                setData(json);
                if (!selected.length) {
                    const avail = (json.available || []);
                    // prefer defaultSelected if exist in available
                    let desired = [];
                    if (Array.isArray(defaultSelected) && defaultSelected.length) {
                        const low = avail.map(a => String(a).toLowerCase());
                        defaultSelected.forEach(name => {
                            const i = low.indexOf(String(name).toLowerCase());
                            if (i !== -1) desired.push(avail[i]);
                        });
                    }
                    if (desired.length) { setSelected(desired); }
                    else if (Array.isArray(json.selected)) { setSelected(json.selected); }
                }
            } catch (e) { setError(e.message); } finally { setLoading(false); }
        };
        load();
    }, [filters, dimension, groupBy, JSON.stringify(selected)]);

    // React on default group-by from parent quick selection
    useEffect(() => {
        if (defaultGroupBy) { setGroupBy(defaultGroupBy); }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [defaultGroupBy]);

    const fmt = new Intl.NumberFormat('cs-CZ');
    if (loading) return <div className="celkova-cisla-top"><h3>📅 Prodeje v čase</h3><div>Načítám…</div></div>;
    if (error) return <div className="celkova-cisla-top"><h3>📅 Prodeje v čase</h3><div className="celkova-cisla-error">{error}</div></div>;
    if (!data) return null;

    return (
        <div className="celkova-cisla-top">
            <h3>📅 Prodeje v čase</h3>
            <div className="filter-row" style={{ marginBottom: 10 }}>
                <div className="filter-group">
                    <label>Dimenze</label>
                    <select value={dimension} onChange={(e) => setDimension(e.target.value)}>
                        <option value="kategorie">Kategorie</option>
                        <option value="kategorie_1">Podkategorie</option>
                        <option value="stredisko">Prodejny</option>
                    </select>
                </div>
                <div className="filter-group">
                    <label>Agregace</label>
                    <select value={groupBy} onChange={(e) => setGroupBy(e.target.value)}>
                        <option value="monthly">Měsíčně</option>
                        <option value="weekly">Týdně</option>
                        <option value="daily">Denně</option>
                    </select>
                </div>
                <div className="filter-group" style={{ flex: 1 }}>
                    <label>Výběr (max 6)</label>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        {(data.available || []).slice(0, 20).map((name, i) => {
                            const sel = selected.includes(name);
                            return (
                                <button key={i} className="refresh-btn" style={{ background: sel ? '#2ecc71' : '#e0e0e0', color: sel ? '#fff' : '#2c3e50', padding: '6px 10px' }} onClick={() => {
                                    setSelected(prev => { const next = sel ? prev.filter(v => v !== name) : [...prev, name]; return next.slice(-6); });
                                }}>{name || 'Nezařazeno'}</button>
                            );
                        })}
                    </div>
                </div>
            </div>
            <div style={{ overflowX: 'auto' }}>
                <svg width="100%" height="360" viewBox="0 0 940 360" preserveAspectRatio="xMidYMid meet">
                    {(() => {
                        const series = data.data || []; const all = [].concat(...series.map(s => s.points));
                        const dates = Array.from(new Set(all.map(p => p.date))).sort();
                        const left = 70, right = 920, top = 40, bottom = 320; const w = right - left, h = bottom - top;
                        const maxYraw = Math.max(1, ...all.map(p => p.kusy || 0)); const pow = Math.pow(10, Math.floor(Math.log10(maxYraw))); const nice = [2, 5, 10].find(k => maxYraw <= k * pow) || 10; const yMax = nice * pow;
                        const py = v => bottom - (h * (v / yMax)); const groupW = dates.length ? w / dates.length : w; const palette = ['#e74c3c', '#3498db', '#27ae60', '#9b59b6', '#f39c12', '#2ecc71'];
                        const barGap = 4; const barW = Math.max(8, Math.min(26, (groupW - 8) / Math.max(1, series.length) - barGap));
                        return (
                            <g>
                                {[0, 1, 2, 3, 4, 5].map(i => { const val = (yMax / 5) * i; const y = py(val); return (<g key={i}><line x1={left} y1={y} x2={right} y2={y} stroke="#eef1f5" /><text x={left - 10} y={y + 4} fontSize="10" textAnchor="end" fill="#7f8c8d">{fmt.format(Math.round(val))}</text></g>); })}
                                <line x1={left} y1={bottom} x2={right} y2={bottom} stroke="#cbd3da" />
                                <line x1={left} y1={top} x2={left} y2={bottom} stroke="#cbd3da" />
                                {dates.map((d, i) => { const x = left + groupW * (i + 0.5); return (<text key={i} transform={`translate(${x}, ${bottom + 22}) rotate(-30)`} fontSize="10" textAnchor="end" fill="#7f8c8d">{String(d).slice(0, 10)}</text>); })}
                                {series.map((s, si) => {
                                    const color = palette[si % palette.length]; return (
                                        <g key={si}>
                                            {dates.map((d, i) => { const p = s.points.find(pt => pt.date === d) || { kusy: 0, obrat: 0 }; const center = left + groupW * (i + 0.5); const total = (series.length * barW) + Math.max(0, series.length - 1) * barGap; const x0 = center - total / 2; const x = x0 + si * (barW + barGap); const y = py(p.kusy || 0); const hh = bottom - y; const obratText = new Intl.NumberFormat('cs-CZ', { style: 'currency', currency: 'CZK', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(Math.round(p.obrat || 0)); return <rect key={i} x={x} y={y} width={barW} height={hh} fill={color} rx="3" onMouseEnter={() => setTip({ visible: true, x: x + barW / 2, y: y - 10, text: `${fmt.format(p.kusy || 0)} ks • ${obratText} bez DPH` })} onMouseLeave={() => setTip(prev => ({ ...prev, visible: false }))} onMouseMove={() => setTip(prev => ({ ...prev, x: x + barW / 2, y: y - 10 }))} /> })}
                                            <rect x={left} y={top - 28 + si * 16} width="10" height="10" fill={color} rx="2" />
                                            <text x={left + 16} y={top - 19 + si * 16} fontSize="12" fill="#2c3e50">{s.key || 'Nezařazeno'}</text>
                                        </g>
                                    );
                                })}
                                {tip.visible && (<g pointerEvents="none" transform={`translate(${tip.x}, ${tip.y})`}><rect x={-45} y={-24} width={90} height={20} rx="4" fill="#fff" stroke="#cbd3da" /><text y={-10} textAnchor="middle" fontSize="12" fill="#2c3e50">{tip.text}</text></g>)}
                            </g>
                        );
                    })()}
                </svg>
            </div>
        </div>
    );
};

const CelkovaCislaView = ({ isComparison = false }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [detailOpen, setDetailOpen] = useState(false);
    const inlinePanelRef = useRef(null);
    const [detailLoading, setDetailLoading] = useState(false);
    const [detailError, setDetailError] = useState(null);
    const [detailChannel, setDetailChannel] = useState(null); // 'prodejna' | 'eshop' | 'allegro' | 'servis'
    const [detailData, setDetailData] = useState(null);
    const [selectedEntity, setSelectedEntity] = useState(null); // např. { stredisko }

    // Detailní ALLEGRO modal - stejné jako v Eshop modulu
    const [allegroDetailOpen, setAllegroDetailOpen] = useState(false);
    const [allegroDetailLoading, setAllegroDetailLoading] = useState(false);
    const [allegroDetailError, setAllegroDetailError] = useState(null);
    const [allegroDetailData, setAllegroDetailData] = useState(null);

    // Detailní E-SHOP modal - stejné jako v Eshop modulu
    const [eshopDetailOpen, setEshopDetailOpen] = useState(false);
    const [eshopDetailLoading, setEshopDetailLoading] = useState(false);
    const [eshopDetailError, setEshopDetailError] = useState(null);
    const [eshopDetailData, setEshopDetailData] = useState(null);

    // Detailní ZÁSILKOVNA modal
    const [zasilkovnaDetailOpen, setZasilkovnaDetailOpen] = useState(false);
    const [zasilkovnaDetailLoading, setZasilkovnaDetailLoading] = useState(false);
    const [zasilkovnaDetailError, setZasilkovnaDetailError] = useState(null);
    const [zasilkovnaDetailData, setZasilkovnaDetailData] = useState(null);

    // Detailní SERVIS modal
    const [servisDetailOpen, setServisDetailOpen] = useState(false);
    const [servisDetailLoading, setServisDetailLoading] = useState(false);
    const [servisDetailError, setServisDetailError] = useState(null);
    const [servisDetailData, setServisDetailData] = useState(null);

    // Filtry
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

    // Načtení dat z API
    const fetchData = async () => {
        setLoading(true);
        setError(null);

        try {
            const params = new URLSearchParams();
            Object.keys(filters).forEach(key => {
                if (filters[key] && filters[key] !== '') {
                    params.append(key, filters[key]);
                }
            });

            console.log('CelkovaCisla: fetchData called with filters:', filters);
            console.log('CelkovaCisla: API URL:', `/api/analytics/celkova-cisla/?${params}`);

            const response = await fetch(`/api/analytics/celkova-cisla/?${params}`, {
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

            console.log('CelkovaCisla: API response:', result);

            if (result.success) {
                setData(result);
            } else {
                throw new Error(result.error || 'Chyba při načítání dat');
            }

        } catch (err) {
            console.error('Chyba při načítání celkových čísel:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    // Otevření detailu kanálu
    const openChannelDetail = async (channel) => {
        setDetailChannel(channel);
        setDetailOpen(true);
        setDetailLoading(true);
        setDetailError(null);
        setDetailData(null);
        setSelectedEntity(null);

        try {
            const p = new URLSearchParams();
            Object.keys(filters).forEach(k => { if (filters[k]) p.append(k, filters[k]); });
            if (channel === 'prodejna') {
                const res = await fetch(`/api/analytics/celkova-cisla/prodejna-detail/?${p}`, { credentials: 'include' });
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const json = await res.json();
                if (!json.success) throw new Error(json.error || 'Chyba detailu');
                setDetailData(json.breakdown || json);
            } else if (channel === 'servis') {
                const res = await fetch(`/api/analytics/celkova-cisla/servis-detail/?${p}`, { credentials: 'include' });
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const json = await res.json();
                if (!json.success) throw new Error(json.error || 'Chyba detailu');
                setDetailData(json.breakdown || json);
            } else {
                p.set('channel', channel);
                p.set('limit', '200');
                const res = await fetch(`/api/analytics/celkova-cisla/channel-items/?${p}`, { credentials: 'include' });
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const json = await res.json();
                if (!json.success) throw new Error(json.error || 'Chyba položek');
                setDetailData({ items: json.items, count: json.count });
            }
        } catch (e) {
            setDetailError(e.message);
        } finally {
            setDetailLoading(false);
        }
    };

    // Druhý drill – načti položky pro konkrétní prodejnu/servis (středisko)
    const loadProdejnaItems = async (stredisko) => {
        setSelectedEntity({ stredisko });
        setDetailLoading(true);
        setDetailError(null);
        try {
            const p = new URLSearchParams();
            Object.keys(filters).forEach(k => { if (filters[k]) p.append(k, filters[k]); });
            p.set('channel', detailChannel || 'prodejna');
            if (stredisko) p.set('stredisko', stredisko);
            p.set('limit', '200');
            const res = await fetch(`/api/analytics/celkova-cisla/channel-items/?${p}`, { credentials: 'include' });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const json = await res.json();
            if (!json.success) throw new Error(json.error || 'Chyba položek');
            setDetailData(prev => ({ ...(prev || {}), items: json.items, count: json.count }));
        } catch (e) {
            setDetailError(e.message);
        } finally {
            setDetailLoading(false);
        }
    };

    const closeDetail = () => {
        setDetailOpen(false);
        setDetailChannel(null);
        setDetailData(null);
        setSelectedEntity(null);
        setDetailError(null);
    };

    // Otevření detailního ALLEGRO modalu - používám stejný endpoint jako E-shop modul
    const openAllegroDetail = async () => {
        setAllegroDetailOpen(true);
        setAllegroDetailLoading(true);
        setAllegroDetailError(null);
        setAllegroDetailData(null);

        try {
            const params = new URLSearchParams();
            Object.keys(filters).forEach(key => {
                if (filters[key] && filters[key] !== '') {
                    params.append(key, filters[key]);
                }
            });
            params.set('channel', 'allegro'); // Důležité: používám stejný endpoint jako E-shop

            const response = await fetch(`/api/analytics/eshop/channel-detail/?${params}`, {
                credentials: 'include'
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const result = await response.json();
            if (!result.success) throw new Error(result.error || 'Chyba načítání ALLEGRO detailů');
            setAllegroDetailData(result);
        } catch (e) {
            setAllegroDetailError(e.message);
        } finally {
            setAllegroDetailLoading(false);
        }
    };

    // Načtení položek v ALLEGRO detailu - stejná logika jako E-shop
    const loadAllegroChannelItems = async (segment, value, extra = {}) => {
        setAllegroDetailLoading(true);
        setAllegroDetailError(null);
        try {
            const params = new URLSearchParams();
            Object.keys(filters).forEach(key => {
                if (filters[key] && filters[key] !== '') {
                    params.append(key, filters[key]);
                }
            });
            params.set('channel', 'allegro');
            params.set('segment', segment);
            if (value) params.set('value', value);
            if (extra.kod) params.set('kod', extra.kod);
            params.set('limit', '200');

            const response = await fetch(`/api/analytics/eshop/channel-items/?${params}`, {
                credentials: 'include'
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const result = await response.json();
            if (!result.success) throw new Error(result.error || 'Chyba načítání položek');
            setAllegroDetailData(prev => ({
                ...prev,
                breakdown: {
                    ...prev.breakdown,
                    [`${segment}_items`]: result.items,
                    [`${segment}_count`]: result.count
                }
            }));
        } catch (e) {
            setAllegroDetailError(e.message);
        } finally {
            setAllegroDetailLoading(false);
        }
    };

    // Zavření detailního ALLEGRO modalu
    const closeAllegroDetail = () => {
        setAllegroDetailOpen(false);
        setAllegroDetailData(null);
        setAllegroDetailError(null);
    };

    // Otevření detailního E-SHOP modalu - používám stejný endpoint jako E-shop modul
    const openEshopDetail = async () => {
        setEshopDetailOpen(true);
        setEshopDetailLoading(true);
        setEshopDetailError(null);
        setEshopDetailData(null);

        try {
            const params = new URLSearchParams();
            Object.keys(filters).forEach(key => {
                if (filters[key] && filters[key] !== '') {
                    params.append(key, filters[key]);
                }
            });
            params.set('channel', 'eshop'); // Důležité: používám stejný endpoint jako E-shop

            const response = await fetch(`/api/analytics/eshop/channel-detail/?${params}`, {
                credentials: 'include'
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const result = await response.json();
            if (!result.success) throw new Error(result.error || 'Chyba načítání E-shop detailů');
            setEshopDetailData(result);
        } catch (e) {
            setEshopDetailError(e.message);
        } finally {
            setEshopDetailLoading(false);
        }
    };

    // Načtení položek v E-SHOP detailu - stejná logika jako E-shop
    const loadEshopChannelItems = async (segment, value, extra = {}) => {
        setEshopDetailLoading(true);
        setEshopDetailError(null);
        try {
            const params = new URLSearchParams();
            Object.keys(filters).forEach(key => {
                if (filters[key] && filters[key] !== '') {
                    params.append(key, filters[key]);
                }
            });
            params.set('channel', 'eshop');
            params.set('segment', segment);
            params.set('value', value);
            Object.keys(extra).forEach(key => {
                if (extra[key] !== undefined && extra[key] !== null) {
                    params.append(key, extra[key]);
                }
            });

            const response = await fetch(`/api/analytics/eshop/channel-items/?${params}`, {
                credentials: 'include'
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const result = await response.json();
            if (!result.success) throw new Error(result.error || 'Chyba načítání položek');

            setEshopDetailData(prev => ({
                ...(prev || {}),
                items: result.items || []
            }));
        } catch (e) {
            setEshopDetailError(e.message);
        } finally {
            setEshopDetailLoading(false);
        }
    };

    // Zavření detailního E-SHOP modalu
    const closeEshopDetail = () => {
        setEshopDetailOpen(false);
        setEshopDetailData(null);
        setEshopDetailError(null);
    };

    // Otevření detailního ZÁSILKOVNA modalu
    const openZasilkovnaDetail = async () => {
        setZasilkovnaDetailOpen(true);
        setZasilkovnaDetailLoading(true);
        setZasilkovnaDetailError(null);
        setZasilkovnaDetailData(null);

        try {
            const params = new URLSearchParams();
            Object.keys(filters).forEach(key => {
                if (filters[key] && filters[key] !== '') {
                    params.append(key, filters[key]);
                }
            });

            const response = await fetch(`/api/analytics/celkova-cisla/zasilkovna-detail/?${params}`, {
                credentials: 'include'
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const result = await response.json();
            if (!result.success) throw new Error(result.error || 'Chyba načítání Zásilkovna detailů');
            setZasilkovnaDetailData(result);
        } catch (e) {
            setZasilkovnaDetailError(e.message);
        } finally {
            setZasilkovnaDetailLoading(false);
        }
    };

    // Zavření detailního ZÁSILKOVNA modalu
    const closeZasilkovnaDetail = () => {
        setZasilkovnaDetailOpen(false);
        setZasilkovnaDetailData(null);
        setZasilkovnaDetailError(null);
    };

    // Otevření detailního SERVIS modalu
    const openServisDetail = async () => {
        setServisDetailOpen(true);
        setServisDetailLoading(true);
        setServisDetailError(null);
        setServisDetailData(null);

        try {
            const params = new URLSearchParams();
            Object.keys(filters).forEach(key => {
                if (filters[key] && filters[key] !== '') {
                    params.append(key, filters[key]);
                }
            });

            const response = await fetch(`/api/analytics/celkova-cisla/servis-detail/?${params}`, {
                credentials: 'include'
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const result = await response.json();
            if (!result.success) throw new Error(result.error || 'Chyba načítání SERVIS detailů');
            setServisDetailData(result);
        } catch (e) {
            setServisDetailError(e.message);
        } finally {
            setServisDetailLoading(false);
        }
    };

    // Zavření detailního SERVIS modalu
    const closeServisDetail = () => {
        setServisDetailOpen(false);
        setServisDetailData(null);
        setServisDetailError(null);
    };

    // Auto-scroll na inline panel v comparison modu
    useEffect(() => {
        if (isComparison && inlinePanelRef.current) {
            const anyOpen = (detailOpen && detailChannel === 'prodejna') ||
                allegroDetailOpen || eshopDetailOpen || zasilkovnaDetailOpen || servisDetailOpen;
            if (anyOpen) {
                inlinePanelRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
    }, [isComparison, detailOpen, detailChannel, allegroDetailOpen, eshopDetailOpen, zasilkovnaDetailOpen, servisDetailOpen]);

    // Načtení dat při změně filtrů
    useEffect(() => {
        fetchData();
    }, [filters]);

    // Zpracování změny filtru
    const handleFilterChange = (filterName, value) => {
        setFilters(prev => ({
            ...prev,
            [filterName]: value
        }));
    };

    const applyDateRange = ({ start_date, end_date }) => {
        setFilters(prev => ({ ...prev, period: 'custom', start_date, end_date }));
    };

    // ===== Helpers pro datumy =====
    const monthStep = (ym, step) => {
        const [y, m] = ym.split('-').map(Number);
        const dt = new Date(y, m - 1 + step, 1);
        return dt.toISOString().slice(0, 7);
    };
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

    // Formátování čísel
    const formatNumber = (num) => {
        if (num === null || num === undefined) return '0';
        return new Intl.NumberFormat('cs-CZ').format(Math.round(num));
    };

    // Formátování měny
    const formatCurrency = (amount) => {
        if (amount === null || amount === undefined) return '0 Kč';
        return new Intl.NumberFormat('cs-CZ', {
            style: 'currency',
            currency: 'CZK',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount);
    };
    const isStoreLikeDetail = detailChannel === 'prodejna' || detailChannel === 'servis';
    const detailTitle = isStoreLikeDetail
        ? `Rozpad prodejen - ${detailChannel === 'servis' ? 'SERVIS' : 'PRODEJNA'}`
        : `Detail kanálu: ${detailChannel?.toUpperCase()}`;

    const renderStoreLikeDetail = () => (
        <div className="detail-grid">
            <div className="detail-card" style={{ gridColumn: '1/-1' }}>
                <h5>{detailChannel === 'servis' ? '🔧' : '🏪'} Prodejny</h5>
                <div className="breakdown-cards" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}>
                    {(detailData?.prodejny || []).map((p, i) => (
                        <div key={i} className="breakdown-card clickable" onClick={() => loadProdejnaItems(p.stredisko)}>
                            <h4>{p.stredisko || `ID ${p.id_prodejny || ''}`}</h4>
                            <div className="breakdown-metrics">
                                <div>Obrat bez DPH: <strong>{formatCurrency(p.obrat)}</strong></div>
                                <div>Marže: <strong>{formatCurrency(p.marze)}</strong></div>
                                <div>Položky: <strong>{formatNumber(p.polozky)}</strong></div>
                                <div>Doklady: <strong>{formatNumber(p.doklady)}</strong></div>
                                <div style={{ color: '#f39c12' }}>Výkupy: <strong>{formatCurrency(p.vykupy_suma)}</strong> ({formatNumber(p.vykupy_pocet)} ks)</div>
                            </div>
                            <div className="click-hint">Klikni pro položky</div>
                        </div>
                    ))}
                </div>
            </div>
            {detailData?.items && (
                <div className="detail-card" style={{ gridColumn: '1/-1' }}>
                    <h5>🧾 Položky {selectedEntity?.stredisko ? `– ${selectedEntity.stredisko}` : ''} ({formatNumber(detailData.count)})</h5>
                    <div className="items-list">
                        <ul>
                            {detailData.items.map((it, idx) => (
                                <li key={idx}><code>{it.doklad || it.objednavka || '—'}</code> — {it.nazev} {it.kod ? <span>(<code>{it.kod}</code>)</span> : null}</li>
                            ))}
                        </ul>
                    </div>
                </div>
            )}
        </div>
    );

    const renderAllegroContent = () => (
        <>
            {allegroDetailLoading && <div className="modal-loading">Načítám…</div>}
            {allegroDetailError && <div className="modal-error">{allegroDetailError}</div>}
            {allegroDetailData && allegroDetailData.breakdown && (
                <div className="detail-grid">
                    <div className="detail-card" style={{ cursor: 'pointer' }}>
                        <h5>🏷️ Kategorie</h5>
                        {(allegroDetailData.breakdown.kategorie || []).slice(0, 8).map((it, i) => (
                            <div key={i} className="top-item clickable" onClick={() => loadAllegroChannelItems('kategorie', it.kategorie)}>
                                <span className="top-name">{it.kategorie || 'Nezařazeno'}</span>
                                <span className="top-value">{formatCurrency(it.obrat_bez_dph)}</span>
                                <span className="top-count">({formatNumber(it.polozky)} položek)</span>
                            </div>
                        ))}
                        {allegroDetailData.breakdown.kategorie_items && (
                            <div className="items-list">
                                <h6>Položky ({formatNumber(allegroDetailData.breakdown.kategorie_count)}):</h6>
                                <ul>{allegroDetailData.breakdown.kategorie_items.map((it, i) => <li key={i}><code>{it.objednavka || '—'}</code> — {it.nazev}</li>)}</ul>
                            </div>
                        )}
                    </div>
                    <div className="detail-card" style={{ cursor: 'pointer' }}>
                        <h5>📂 Podkategorie</h5>
                        {(allegroDetailData.breakdown.kategorie_1 || []).slice(0, 8).map((it, i) => (
                            <div key={i} className="top-item clickable" onClick={() => loadAllegroChannelItems('kategorie_1', it.kategorie_1)}>
                                <span className="top-name">{it.kategorie_1 || 'Nezařazeno'}</span>
                                <span className="top-value">{formatCurrency(it.obrat_bez_dph)}</span>
                                <span className="top-count">({formatNumber(it.polozky)} položek)</span>
                            </div>
                        ))}
                        {allegroDetailData.breakdown.kategorie_1_items && (
                            <div className="items-list">
                                <h6>Položky ({formatNumber(allegroDetailData.breakdown.kategorie_1_count)}):</h6>
                                <ul>{allegroDetailData.breakdown.kategorie_1_items.map((it, i) => <li key={i}><code>{it.objednavka || '—'}</code> — {it.nazev}</li>)}</ul>
                            </div>
                        )}
                    </div>
                    <div className="detail-card" style={{ cursor: 'pointer' }}>
                        <h5>📁 Značky/produkty</h5>
                        {(allegroDetailData.breakdown.kategorie_2 || []).slice(0, 8).map((it, i) => (
                            <div key={i} className="top-item clickable" onClick={() => loadAllegroChannelItems('kategorie_2', it.kategorie_2)}>
                                <span className="top-name">{it.kategorie_2 || 'Nezařazeno'}</span>
                                <span className="top-value">{formatCurrency(it.obrat_bez_dph)}</span>
                                <span className="top-count">({formatNumber(it.polozky)} položek)</span>
                            </div>
                        ))}
                        {allegroDetailData.breakdown.kategorie_2_items && (
                            <div className="items-list">
                                <h6>Položky ({formatNumber(allegroDetailData.breakdown.kategorie_2_count)}):</h6>
                                <ul>{allegroDetailData.breakdown.kategorie_2_items.map((it, i) => <li key={i}><code>{it.objednavka || '—'}</code> — {it.nazev}</li>)}</ul>
                            </div>
                        )}
                    </div>
                    <div className="detail-card" style={{ cursor: 'pointer' }}>
                        <h5>🏆 Top produkty</h5>
                        {(allegroDetailData.breakdown.top_produkty || []).slice(0, 10).map((it, i) => (
                            <div key={i} className="top-item clickable" onClick={() => loadAllegroChannelItems('produkt', null, { kod: it.kod })}>
                                <span className="top-name">{it.nazev || it.kod}</span>
                                <span className="top-value">{formatNumber(it.celkem_kusu)} ks</span>
                                <span className="top-count">{formatCurrency(it.obrat_bez_dph)}</span>
                            </div>
                        ))}
                        {allegroDetailData.breakdown.produkt_items && (
                            <div className="items-list">
                                <h6>Položky ({formatNumber(allegroDetailData.breakdown.produkt_count)}):</h6>
                                <ul>{allegroDetailData.breakdown.produkt_items.map((it, i) => <li key={i}><code>{it.objednavka || '—'}</code> — {it.nazev}</li>)}</ul>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </>
    );

    const renderEshopContent = () => (
        <>
            {eshopDetailLoading && <div className="modal-loading">Načítám…</div>}
            {eshopDetailError && <div className="modal-error">{eshopDetailError}</div>}
            {eshopDetailData && eshopDetailData.breakdown && (
                <div>
                    <div className="breakdown-metrics-row">
                        <div>Obrat bez DPH: <strong>{formatCurrency(eshopDetailData.breakdown.obrat_bez_dph || 0)}</strong></div>
                        <div>Marže bez DPH: <strong>{formatCurrency(eshopDetailData.breakdown.zisk || 0)}</strong></div>
                        <div>Položky: <strong>{formatNumber(eshopDetailData.breakdown.polozky || 0)}</strong></div>
                        <div>Objednávky: <strong>{formatNumber(eshopDetailData.breakdown.objednavky || 0)}</strong></div>
                    </div>
                    <div className="detail-grid">
                        <div className="detail-card" style={{ cursor: 'pointer' }}>
                            <h5>🏷️ Kategorie</h5>
                            {(eshopDetailData.breakdown.kategorie || []).slice(0, 8).map((it, i) => (
                                <div key={i} className="top-item clickable" onClick={() => loadEshopChannelItems('kategorie', it.kategorie)}>
                                    <span className="top-name">{it.kategorie || 'Nezařazeno'}</span>
                                    <span className="top-value">{formatCurrency(it.obrat_bez_dph)}</span>
                                    <span className="top-count">({formatNumber(it.polozky)} položek)</span>
                                </div>
                            ))}
                            {eshopDetailData.breakdown.kategorie_items && (
                                <div className="items-list">
                                    <h6>Položky ({formatNumber(eshopDetailData.breakdown.kategorie_count)}):</h6>
                                    <ul>{eshopDetailData.breakdown.kategorie_items.map((it, i) => <li key={i}><code>{it.objednavka || '—'}</code> — {it.nazev}</li>)}</ul>
                                </div>
                            )}
                        </div>
                        <div className="detail-card" style={{ cursor: 'pointer' }}>
                            <h5>🏪 Podkategorie</h5>
                            {(eshopDetailData.breakdown.kategorie_1 || []).slice(0, 8).map((it, i) => (
                                <div key={i} className="top-item clickable" onClick={() => loadEshopChannelItems('kategorie_1', it.kategorie_1)}>
                                    <span className="top-name">{it.kategorie_1 || 'Nezařazeno'}</span>
                                    <span className="top-value">{formatCurrency(it.obrat_bez_dph)}</span>
                                    <span className="top-count">({formatNumber(it.polozky)} položek)</span>
                                </div>
                            ))}
                            {eshopDetailData.breakdown.kategorie_1_items && (
                                <div className="items-list">
                                    <h6>Položky ({formatNumber(eshopDetailData.breakdown.kategorie_1_count)}):</h6>
                                    <ul>{eshopDetailData.breakdown.kategorie_1_items.map((it, i) => <li key={i}><code>{it.objednavka || '—'}</code> — {it.nazev}</li>)}</ul>
                                </div>
                            )}
                        </div>
                        <div className="detail-card" style={{ cursor: 'pointer' }}>
                            <h5>📦 Značky/produkty</h5>
                            {(eshopDetailData.breakdown.kategorie_2 || []).slice(0, 8).map((it, i) => (
                                <div key={i} className="top-item clickable" onClick={() => loadEshopChannelItems('kategorie_2', it.kategorie_2)}>
                                    <span className="top-name">{it.kategorie_2 || 'Nezařazeno'}</span>
                                    <span className="top-value">{formatCurrency(it.obrat_bez_dph)}</span>
                                    <span className="top-count">({formatNumber(it.polozky)} položek)</span>
                                </div>
                            ))}
                            {eshopDetailData.breakdown.kategorie_2_items && (
                                <div className="items-list">
                                    <h6>Položky ({formatNumber(eshopDetailData.breakdown.kategorie_2_count)}):</h6>
                                    <ul>{eshopDetailData.breakdown.kategorie_2_items.map((it, i) => <li key={i}><code>{it.objednavka || '—'}</code> — {it.nazev}</li>)}</ul>
                                </div>
                            )}
                        </div>
                        <div className="detail-card" style={{ cursor: 'pointer' }}>
                            <h5>🏆 Top produkty</h5>
                            {(eshopDetailData.breakdown.produkt || []).slice(0, 8).map((it, i) => (
                                <div key={i} className="top-item clickable" onClick={() => loadEshopChannelItems('produkt', it.kod, { kod: it.kod })}>
                                    <span className="top-name">{it.nazev || it.kod || 'Nezařazeno'}</span>
                                    <span className="top-value">{formatCurrency(it.obrat_bez_dph)}</span>
                                    <span className="top-count">({formatNumber(it.polozky)} položek)</span>
                                </div>
                            ))}
                            {eshopDetailData.breakdown.produkt_items && (
                                <div className="items-list">
                                    <h6>Položky ({formatNumber(eshopDetailData.breakdown.produkt_count)}):</h6>
                                    <ul>{eshopDetailData.breakdown.produkt_items.map((it, i) => <li key={i}><code>{it.objednavka || '—'}</code> — {it.nazev}</li>)}</ul>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </>
    );

    const renderZasilkovnaContent = () => (
        <>
            {zasilkovnaDetailLoading && <div className="modal-loading">Načítám...</div>}
            {zasilkovnaDetailError && <div className="modal-error">{zasilkovnaDetailError}</div>}
            {!zasilkovnaDetailLoading && !zasilkovnaDetailError && zasilkovnaDetailData && (
                <div>
                    <div style={{ marginBottom: '20px', padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
                        <h5>📊 Souhrn</h5>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginTop: '10px' }}>
                            <div><strong>Celkové provize:</strong><div style={{ fontSize: '1.3em', color: '#27ae60' }}>{formatCurrency(zasilkovnaDetailData.celkove_provize)}</div></div>
                            <div><strong>Počet prodejen:</strong><div style={{ fontSize: '1.3em', color: '#3498db' }}>{zasilkovnaDetailData.pocet_prodejen}</div></div>
                            <div><strong>Počet měsíců:</strong><div style={{ fontSize: '1.3em', color: '#9b59b6' }}>{zasilkovnaDetailData.pocet_mesicu}</div></div>
                        </div>
                    </div>
                    <h5>🏪 Rozpad podle prodejen</h5>
                    <div className="detail-grid" style={{ marginTop: '15px' }}>
                        {(zasilkovnaDetailData.prodejny || []).map((prodejna, index) => (
                            <div key={index} className="detail-card" style={{ borderLeft: `4px solid ${prodejna.barva || '#0066cc'}` }}>
                                <h5>{prodejna.nazev_plny || prodejna.nazev}</h5>
                                <div style={{ marginTop: '10px' }}>
                                    <div><strong>Celkové provize:</strong> {formatCurrency(prodejna.celkove_provize)}</div>
                                    <div style={{ fontSize: '0.9em', marginTop: '8px', paddingTop: '8px', borderTop: '1px dashed #e0e0e0' }}>
                                        <div>Za zpracování: {formatCurrency(prodejna.za_zpracovani)}</div>
                                        <div>Za dobírku: {formatCurrency(prodejna.za_vyber_dobirky)}</div>
                                        <div>Ostatní: {formatCurrency(prodejna.ostatni_provize)}</div>
                                    </div>
                                    <div style={{ marginTop: '8px', fontSize: '0.85em', color: '#7f8c8d' }}>Počet měsíců: {prodejna.pocet_mesicu}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                    {zasilkovnaDetailData.mesice && zasilkovnaDetailData.mesice.length > 0 && (
                        <>
                            <h5 style={{ marginTop: '30px' }}>📅 Rozpad podle měsíců</h5>
                            <div style={{ marginTop: '15px', maxHeight: '400px', overflowY: 'auto' }}>
                                <table style={{ width: '100%', fontSize: '0.9em' }}>
                                    <thead style={{ position: 'sticky', top: 0, background: '#f8f9fa' }}>
                                        <tr>
                                            <th style={{ padding: '8px', textAlign: 'left' }}>Měsíc</th>
                                            <th style={{ padding: '8px', textAlign: 'left' }}>Prodejna</th>
                                            <th style={{ padding: '8px', textAlign: 'right' }}>Provize</th>
                                            <th style={{ padding: '8px', textAlign: 'right' }}>Zpracování</th>
                                            <th style={{ padding: '8px', textAlign: 'right' }}>Dobírka</th>
                                            <th style={{ padding: '8px', textAlign: 'right' }}>Ostatní</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {zasilkovnaDetailData.mesice.map((mesic, index) => (
                                            <tr key={index} style={{ borderBottom: '1px solid #e9ecef' }}>
                                                <td style={{ padding: '8px' }}>{mesic.mesic}/{mesic.rok}</td>
                                                <td style={{ padding: '8px' }}>{mesic.nazev_plny || mesic.nazev}</td>
                                                <td style={{ padding: '8px', textAlign: 'right', fontWeight: 'bold' }}>{formatCurrency(mesic.provize)}</td>
                                                <td style={{ padding: '8px', textAlign: 'right' }}>{formatCurrency(mesic.za_zpracovani)}</td>
                                                <td style={{ padding: '8px', textAlign: 'right' }}>{formatCurrency(mesic.za_vyber_dobirky)}</td>
                                                <td style={{ padding: '8px', textAlign: 'right' }}>{formatCurrency(mesic.ostatni_provize)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </>
                    )}
                </div>
            )}
        </>
    );

    const renderServisContent = () => (
        <>
            {servisDetailLoading && <div className="modal-loading">Načítám...</div>}
            {servisDetailError && <div className="modal-error">{servisDetailError}</div>}
            {!servisDetailLoading && !servisDetailError && servisDetailData && (
                <div>
                    <div style={{ marginBottom: '20px', padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
                        <h5>📊 Souhrn</h5>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginTop: '10px' }}>
                            <div><strong>Celkový obrat:</strong><div style={{ fontSize: '1.3em', color: '#27ae60' }}>{formatCurrency(servisDetailData.celkovy_obrat)}</div></div>
                            <div><strong>Celková marže:</strong><div style={{ fontSize: '1.3em', color: '#3498db' }}>{formatCurrency(servisDetailData.celkova_marze)}</div></div>
                            <div><strong>Počet položek:</strong><div style={{ fontSize: '1.3em', color: '#9b59b6' }}>{formatNumber(servisDetailData.celkem_polozky)}</div></div>
                            <div><strong>Počet dokladů:</strong><div style={{ fontSize: '1.3em', color: '#f39c12' }}>{formatNumber(servisDetailData.celkem_doklady)}</div></div>
                        </div>
                    </div>
                    <h5>🏪 Rozpad podle prodejen</h5>
                    <div className="detail-grid" style={{ marginTop: '15px' }}>
                        {(servisDetailData.prodejny || []).map((prodejna, index) => (
                            <div key={index} className="detail-card" style={{ borderLeft: `4px solid ${prodejna.barva || '#0066cc'}` }}>
                                <h5>{prodejna.nazev_plny || prodejna.nazev || 'Nezařazeno'}</h5>
                                <div style={{ marginTop: '10px' }}>
                                    <div><strong>Obrat bez DPH:</strong> {formatCurrency(prodejna.obrat)}</div>
                                    <div><strong>Marže bez DPH:</strong> {formatCurrency(prodejna.marze)}</div>
                                    <div style={{ fontSize: '0.9em', marginTop: '8px', paddingTop: '8px', borderTop: '1px dashed #e0e0e0' }}>
                                        <div>Položky: {formatNumber(prodejna.polozky)}</div>
                                        <div>Doklady: {formatNumber(prodejna.doklady)}</div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </>
    );

    return (
        <div className={`celkova-cisla-view ${isComparison ? 'is-comparison' : ''}`}>

            {/* Filtry */}
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
                                        console.log('CelkovaCisla: CustomDropdown onChange:', selectedValue);
                                        if (selectedValue === 'custom') {
                                            handleFilterChange('period', 'custom');
                                        } else if (selectedValue.startsWith('month:')) {
                                            const ym = selectedValue.split(':')[1];
                                            console.log('CelkovaCisla: Setting month:', ym);
                                            setFilters(prev => {
                                                const newFilters = {
                                                    ...prev,
                                                    period: 'monthly_select',
                                                    selected_month: ym,
                                                    start_date: '', // Vyčistit start_date
                                                    end_date: ''    // Vyčistit end_date
                                                };
                                                console.log('CelkovaCisla: New filters:', newFilters);
                                                return newFilters;
                                            });
                                            setDateError('');
                                        }
                                    }}
                                />
                            );
                        })()}
                    </div>

                    {/* Vybraný měsíc – výběr je přímo v hlavním rolovátku */}

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
                    <div className="filter-group refresh-group">
                        <button
                            className="refresh-btn main-refresh"
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

            {/* Data zobrazení */}
            {data && !loading && (
                <>
                    {/* Hlavní metriky */}
                    <div className="celkova-cisla-metrics">
                        <div className="metric-card">
                            <div className="metric-icon">💰</div>
                            <div className="metric-content">
                                <h3>Celkový obrat</h3>
                                <div className="metric-value">{formatCurrency(data.aggregations.celkovy_obrat)}</div>
                                <div className="metric-subtitle">s DPH</div>
                            </div>
                        </div>

                        <div className="metric-card">
                            <div className="metric-icon">💳</div>
                            <div className="metric-content">
                                <h3>Obrat bez DPH</h3>
                                <div className="metric-value">{formatCurrency(data.aggregations.celkovy_obrat_bez_dph)}</div>
                                <div className="metric-subtitle">bez DPH (21%)</div>
                            </div>
                        </div>

                        <div className="metric-card">
                            <div className="metric-icon">📈</div>
                            <div className="metric-content">
                                <h3>Celková marže bez DPH</h3>
                                <div className="metric-value">{formatCurrency(data.aggregations.celkovy_zisk)}</div>
                                <div className="metric-subtitle">{data.aggregations.marze_procenta}% marže</div>
                            </div>
                        </div>

                        <div className="metric-card">
                            <div className="metric-icon">🛍️</div>
                            <div className="metric-content">
                                <h3>Počet položek</h3>
                                <div className="metric-value">{formatNumber(data.aggregations.celkem_polozek)}</div>
                                <div className="metric-subtitle">{formatNumber(data.aggregations.celkem_kusu)} kusů</div>
                            </div>
                        </div>

                        <div className="metric-card">
                            <div className="metric-icon">🧾</div>
                            <div className="metric-content">
                                <h3>Počet dokladů</h3>
                                <div className="metric-value">{formatNumber(data.aggregations.pocet_dokladu)}</div>
                                <div className="metric-subtitle">Průměrný obrat na objednávku s DPH: {formatCurrency(data.aggregations.prumerna_objednavka)}</div>
                            </div>
                        </div>

                        {/* VÝKUPY - Nová dlaždice */}
                        <div className="metric-card" style={{ borderLeft: '4px solid #f39c12' }}>
                            <div className="metric-icon">🔄</div>
                            <div className="metric-content">
                                <h3>Výkupy</h3>
                                <div className="metric-value">{formatNumber(data.aggregations.vykupy_pocet)} ks</div>
                                <div className="metric-subtitle">Cena: {formatCurrency(data.aggregations.vykupy_suma)} bez DPH</div>
                            </div>
                        </div>
                    </div>

                    {/* Rozklad podle kanálů */}
                    <div className="celkova-cisla-breakdown">
                        <h3>📊 Rozklad podle prodejních kanálů</h3>
                        <div className="breakdown-cards">
                            <div className="breakdown-card clickable" onClick={() => openChannelDetail('prodejna')}>
                                <h4>🏪 Prodejna</h4>
                                <div className="breakdown-metrics">
                                    <div>Obrat bez DPH: <strong>{formatCurrency(data.breakdown.kanaly.prodejna.obrat)}</strong></div>
                                    <div>Marže bez DPH: <strong>{formatCurrency(data.breakdown.kanaly.prodejna.marze)}</strong></div>
                                    <div>Položky: <strong>{formatNumber(data.breakdown.kanaly.prodejna.polozky)}</strong></div>
                                </div>
                            </div>

                            <div className="breakdown-card clickable" onClick={openEshopDetail}>
                                <h4>🌐 E-shop (bez ALLEGRO)</h4>
                                <div className="breakdown-metrics">
                                    <div>Obrat bez DPH: <strong>{formatCurrency(data.breakdown.kanaly.eshop.obrat)}</strong></div>
                                    <div>Marže bez DPH: <strong>{formatCurrency(data.breakdown.kanaly.eshop.marze)}</strong></div>
                                    <div>Položky: <strong>{formatNumber(data.breakdown.kanaly.eshop.polozky)}</strong></div>
                                    <div>Objednávky: <strong>{formatNumber(data.breakdown.kanaly.eshop.objednavky)}</strong></div>
                                </div>
                            </div>

                            <div className="breakdown-card clickable" onClick={openAllegroDetail}>
                                <h4>🛒 ALLEGRO</h4>
                                <div className="breakdown-metrics">
                                    <div>Obrat bez DPH: <strong>{formatCurrency(data.breakdown.kanaly.allegro.obrat)}</strong></div>
                                    <div>Marže bez DPH: <strong>{formatCurrency(data.breakdown.kanaly.allegro.marze)}</strong></div>
                                    <div>Položky: <strong>{formatNumber(data.breakdown.kanaly.allegro.polozky)}</strong></div>
                                    <div>Objednávky: <strong>{formatNumber(data.breakdown.kanaly.allegro.objednavky)}</strong></div>
                                </div>
                                <div style={{ fontSize: '0.9em', opacity: 0.7, marginTop: '8px' }}>
                                    Klikněte pro detailní analýzu kategorií a produktů
                                </div>
                            </div>

                            <div className="breakdown-card clickable" onClick={openServisDetail}>
                                <h4>🔧 SERVIS</h4>
                                <div className="breakdown-metrics">
                                    <div>Obrat bez DPH: <strong>{formatCurrency(data.breakdown.kanaly.servis.obrat)}</strong></div>
                                    <div>Marže bez DPH: <strong>{formatCurrency(data.breakdown.kanaly.servis.marze)}</strong></div>
                                    <div>Položky: <strong>{formatNumber(data.breakdown.kanaly.servis.polozky)}</strong></div>
                                </div>
                                <div style={{ fontSize: '0.9em', opacity: 0.7, marginTop: '8px' }}>
                                    Klikněte pro detailní rozpad podle prodejen
                                </div>
                            </div>

                            {/* NOVÁ DLAŽDICE - ZÁSILKOVNA */}
                            <div className="breakdown-card clickable" onClick={openZasilkovnaDetail}>
                                <h4>📦 Zásilkovna (provize)</h4>
                                <div className="breakdown-metrics">
                                    {data.zasilkovna && data.zasilkovna.celkove_provize > 0 ? (
                                        <>
                                            <div>Celková provize bez DPH: <strong>{formatCurrency(data.zasilkovna.celkove_provize)}</strong></div>
                                            {data.zasilkovna.detail_prodejen && data.zasilkovna.detail_prodejen.length > 0 && (
                                                <div>Prodejen: <strong>{data.zasilkovna.detail_prodejen.length}</strong></div>
                                            )}
                                            {data.zasilkovna.detail_prodejen && data.zasilkovna.detail_prodejen[0] && data.zasilkovna.detail_prodejen[0].pocet_mesicu && (
                                                <div>Měsíců: <strong>{data.zasilkovna.detail_prodejen[0].pocet_mesicu}</strong></div>
                                            )}
                                        </>
                                    ) : (
                                        <div style={{ opacity: 0.6, fontStyle: 'italic' }}>
                                            Žádná data pro vybrané období
                                        </div>
                                    )}
                                </div>
                                <div style={{ fontSize: '0.9em', opacity: 0.7, marginTop: '8px' }}>
                                    Klikněte pro detailní rozpad podle prodejen
                                </div>
                            </div>
                        </div>

                        {isComparison && detailOpen && detailChannel === 'prodejna' && (
                            <div className="inline-detail-panel" ref={inlinePanelRef}>
                                <div className="inline-detail-header">
                                    <h4>{detailTitle}{selectedEntity?.stredisko ? ` – ${selectedEntity.stredisko}` : ''}</h4>
                                    <button className="modal-close" onClick={closeDetail}>✕</button>
                                </div>
                                <div className="inline-detail-body">
                                    {detailLoading && <div className="modal-loading">Načítám…</div>}
                                    {detailError && <div className="modal-error">{detailError}</div>}
                                    {!detailLoading && !detailError && detailData && renderStoreLikeDetail()}
                                </div>
                            </div>
                        )}

                        {isComparison && eshopDetailOpen && (
                            <div className="inline-detail-panel" ref={!detailOpen ? inlinePanelRef : undefined}>
                                <div className="inline-detail-header">
                                    <h4>Detail kanálu: E-shop (bez ALLEGRO)</h4>
                                    <button className="modal-close" onClick={closeEshopDetail}>✕</button>
                                </div>
                                <div className="inline-detail-body">{renderEshopContent()}</div>
                            </div>
                        )}

                        {isComparison && allegroDetailOpen && (
                            <div className="inline-detail-panel" ref={!detailOpen && !eshopDetailOpen ? inlinePanelRef : undefined}>
                                <div className="inline-detail-header">
                                    <h4>Detail kanálu: Allegro</h4>
                                    <button className="modal-close" onClick={closeAllegroDetail}>✕</button>
                                </div>
                                <div className="inline-detail-body">{renderAllegroContent()}</div>
                            </div>
                        )}

                        {isComparison && servisDetailOpen && (
                            <div className="inline-detail-panel" ref={!detailOpen && !eshopDetailOpen && !allegroDetailOpen ? inlinePanelRef : undefined}>
                                <div className="inline-detail-header">
                                    <h4>🔧 SERVIS - Rozpad podle prodejen</h4>
                                    <button className="modal-close" onClick={closeServisDetail}>✕</button>
                                </div>
                                <div className="inline-detail-body">{renderServisContent()}</div>
                            </div>
                        )}

                        {isComparison && zasilkovnaDetailOpen && (
                            <div className="inline-detail-panel" ref={!detailOpen && !eshopDetailOpen && !allegroDetailOpen && !servisDetailOpen ? inlinePanelRef : undefined}>
                                <div className="inline-detail-header">
                                    <h4>📦 Zásilkovna - Rozpad podle prodejen</h4>
                                    <button className="modal-close" onClick={closeZasilkovnaDetail}>✕</button>
                                </div>
                                <div className="inline-detail-body">{renderZasilkovnaContent()}</div>
                            </div>
                        )}
                    </div>

                    {/* Interaktivní graf kategorií / prodejen */}
                    <CategoryTimeseries
                        filters={filters}
                        defaultGroupBy={quickKey === 'today' || quickKey === 'yesterday' ? 'daily' : quickKey === 'prevMonth' ? 'weekly' : (quickKey === 'thisWeek' || quickKey === 'thisMonth') ? 'daily' : undefined}
                        defaultSelected={['PŘÍSLUŠENSTVÍ', 'NOVÉ TELEFONY']}
                    />

                    {/* (původní seznamy skryty ve prospěch grafu) */}

                    {/* Modal s detailem kanálu / prodejny */}
                    {detailOpen && !isComparison && (
                        <div className="modal-overlay" onClick={closeDetail}>
                            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                                <div className="modal-header">
                                    <h4>{detailTitle}{selectedEntity?.stredisko ? ` – ${selectedEntity.stredisko}` : ''}</h4>
                                    <button className="modal-close" onClick={closeDetail}>✕</button>
                                </div>
                                <div className="modal-body">
                                    {detailLoading && <div className="modal-loading">Načítám…</div>}
                                    {detailError && <div className="modal-error">{detailError}</div>}
                                    {!detailLoading && !detailError && isStoreLikeDetail && detailData && renderStoreLikeDetail()}
                                    {!detailLoading && !detailError && !isStoreLikeDetail && detailData && (
                                        <div className="detail-grid">
                                            <div className="detail-card" style={{ gridColumn: '1/-1' }}>
                                                <h5>📦 Položky ({formatNumber(detailData.count)})</h5>
                                                <div className="items-list">
                                                    <ul>
                                                        {(detailData.items || []).map((it, idx) => (
                                                            <li key={idx}><code>{it.objednavka || it.doklad || '—'}</code> — {it.nazev} {it.kod ? <span>(<code>{it.kod}</code>)</span> : null}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Detailní ALLEGRO modal - pouze mimo comparison mode */}
                    {allegroDetailOpen && !isComparison && (
                        <div className="modal-overlay" onClick={closeAllegroDetail}>
                            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                                <div className="modal-header">
                                    <h4>Detail kanálu: Allegro</h4>
                                    <button className="modal-close" onClick={closeAllegroDetail}>✕</button>
                                </div>
                                <div className="modal-body">{renderAllegroContent()}</div>
                            </div>
                        </div>
                    )}

                    {/* Detailní E-SHOP modal - pouze mimo comparison mode */}
                    {eshopDetailOpen && !isComparison && (
                        <div className="modal-overlay" onClick={closeEshopDetail}>
                            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                                <div className="modal-header">
                                    <h4>Detail kanálu: E-shop (bez ALLEGRO)</h4>
                                    <button className="modal-close" onClick={closeEshopDetail}>✕</button>
                                </div>
                                <div className="modal-body">{renderEshopContent()}</div>
                            </div>
                        </div>
                    )}

                    {/* ZÁSILKOVNA Detail Modal - pouze mimo comparison mode */}
                    {zasilkovnaDetailOpen && !isComparison && (
                        <div className="modal-overlay" onClick={closeZasilkovnaDetail}>
                            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                                <div className="modal-header">
                                    <h4>📦 Zásilkovna - Rozpad podle prodejen</h4>
                                    <button className="modal-close" onClick={closeZasilkovnaDetail}>✕</button>
                                </div>
                                <div className="modal-body">{renderZasilkovnaContent()}</div>
                            </div>
                        </div>
                    )}

                    {/* Meta informace */}
                    <div className="celkova-cisla-meta">
                        <p>
                            📊 Zobrazeno {formatNumber(data.meta.total_records)} záznamů
                            | ⏰ Aktualizováno: {new Date(data.meta.generated_at).toLocaleString('cs-CZ')}
                        </p>
                    </div>
                </>
            )}

            {/* SERVIS Detail Modal - pouze mimo comparison mode */}
            {servisDetailOpen && !isComparison && (
                <div className="modal-overlay" onClick={closeServisDetail}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h4>🔧 SERVIS - Rozpad podle prodejen</h4>
                            <button className="modal-close" onClick={closeServisDetail}>✕</button>
                        </div>
                        <div className="modal-body">{renderServisContent()}</div>
                    </div>
                </div>
            )}
        </div>
    );
};

const CelkovaCisla = () => {
    const [isComparison, setIsComparison] = useState(false);

    return (
        <AnalyticsSectionWrapper title="Celková čísla" icon="💰">
            <div className={`celkova-cisla-container ${isComparison ? 'comparison-mode' : ''}`}>
                <div className="celkova-cisla-controls" style={{
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

                <div className="celkova-cisla-views" style={{
                    display: 'flex',
                    gap: isComparison ? '20px' : '0'
                }}>
                    <div className="view-pane left-pane" style={{
                        flex: 1,
                        minWidth: 0, // fix for flexbox overflow
                        transition: 'all 0.3s ease'
                    }}>
                        <CelkovaCislaView isComparison={isComparison} />
                    </div>

                    {isComparison && (
                        <div className="view-pane right-pane" style={{
                            flex: 1,
                            minWidth: 0,
                            borderLeft: '1px dashed #cbd3da',
                            paddingLeft: '20px'
                        }}>
                            <CelkovaCislaView isComparison={isComparison} />
                        </div>
                    )}
                </div>
            </div>
        </AnalyticsSectionWrapper>
    );
};

export default CelkovaCisla; 