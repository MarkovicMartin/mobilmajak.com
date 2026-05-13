import React, { useState, useEffect } from 'react';
import {
    ComposedChart,
    Bar,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    PieChart,
    Pie,
    Cell
} from 'recharts';
import AnalyticsSectionWrapper from '../AnalyticsSectionWrapper';
import CustomDropdown from '../../../components/CustomDropdown';
import './SectionStyles.css';

const SalespersonBreakdown = ({ filters }) => {
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [open, setOpen] = useState(null); // {prodejce_id, kind, receipts}

    const formatNumber = (n)=> new Intl.NumberFormat('cs-CZ').format(n||0);

    useEffect(()=>{
        const load = async ()=>{
            setLoading(true); setError(null);
            try{
                const p = new URLSearchParams();
                Object.keys(filters).forEach(k=>{ if(filters[k]) p.append(k, filters[k]); });
                const res = await fetch(`/api/analytics/prodejni-analytika/phones-accessories/by-salesperson/?${p}`, { credentials:'include' });
                if(!res.ok) throw new Error(`HTTP ${res.status}`);
                const json = await res.json();
                if(!json.success) throw new Error(json.error||'Chyba');
                setRows((json.rows||[]).sort((a,b)=> (b.phones_kusy||0)-(a.phones_kusy||0)));
            }catch(e){ setError(e.message);} finally{ setLoading(false);}    
        };
        load();
    }, [JSON.stringify(filters)]);

    const openReceipts = async (prodejce_id, kind) => {
        setOpen({ prodejce_id, kind, loading:true, receipts:[], error:null });
        try{
            const p = new URLSearchParams();
            Object.keys(filters).forEach(k=>{ if(filters[k]) p.append(k, filters[k]); });
            p.set('prodejce_id', String(prodejce_id));
            p.set('kind', kind);
            const res = await fetch(`/api/analytics/prodejni-analytika/phones-accessories/salesperson-receipts/?${p}`, { credentials:'include' });
            if(!res.ok) throw new Error(`HTTP ${res.status}`);
            const json = await res.json();
            if(!json.success) throw new Error(json.error||'Chyba');
            setOpen(prev=> ({ ...(prev||{}), loading:false, receipts: json.receipts||[] }));
        }catch(e){ setOpen(prev=> ({ ...(prev||{}), loading:false, error: e.message })); }
    };

    if (loading) return <div>Načítám prodejce…</div>;
    if (error) return <div className="error-container">{error}</div>;
    if (!rows.length) return <div>Žádná data</div>;

    return (
        <div>
            <div style={{overflowX:'auto'}}>
                <table className="table" style={{width:'100%', borderCollapse:'separate', borderSpacing:0}}>
                    <thead>
                        <tr>
                            <th style={{textAlign:'left', padding:'8px'}}>Prodejce</th>
                            <th style={{textAlign:'right', padding:'8px'}}>Telefony (ks)</th>
                            <th style={{textAlign:'right', padding:'8px'}}>Příslušenství ≥ 100 (ks)</th>
                            <th style={{textAlign:'right', padding:'8px'}}>Přísl./telefon</th>
                            <th style={{textAlign:'right', padding:'8px'}}>Doklady pouze telefon</th>
                            <th style={{textAlign:'center', padding:'8px'}}>Detail</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((r, i)=>{
                            const ratio = (r.accessories_kusy||0) && (r.phones_kusy||0) ? (r.accessories_kusy/r.phones_kusy) : 0;
                            const name = `${r.jmeno||''} ${r.prijmeni||''}`.trim() || `ID ${r.id_prodejce}`;
                            return (
                                <tr key={i} style={{background: i%2? '#fafafa':'#fff'}}>
                                    <td style={{padding:'8px'}}>{name}</td>
                                    <td style={{padding:'8px', textAlign:'right'}}>{formatNumber(r.phones_kusy)}</td>
                                    <td style={{padding:'8px', textAlign:'right'}}>{formatNumber(r.accessories_kusy)}</td>
                                    <td style={{padding:'8px', textAlign:'right'}}>{ratio.toFixed(2)}</td>
                                    <td style={{padding:'8px', textAlign:'right'}}>{formatNumber(r.phones_only_docs)}</td>
                                    <td style={{padding:'8px', textAlign:'center'}}>
                                        <button className="refresh-btn" onClick={()=> openReceipts(r.id_prodejce, 'without')}>Jen telefon</button>
                                        <button className="refresh-btn" style={{marginLeft:6}} onClick={()=> openReceipts(r.id_prodejce, 'with')}>S přísluš.</button>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            {open && (
                <div className="modal-overlay" onClick={()=> setOpen(null)}>
                    <div className="modal-content" onClick={(e)=> e.stopPropagation()}>
                        <div className="modal-header">
                            <h4>Doklady prodejce {open.prodejce_id} — {open.kind==='without'?'jen telefon':'s příslušenstvím'}</h4>
                            <button className="modal-close" onClick={()=> setOpen(null)}>✕</button>
                        </div>
                        <div className="modal-body">
                            {open.loading && <div>Načítám…</div>}
                            {open.error && <div className="error-container">{open.error}</div>}
                            {!open.loading && !open.error && (
                                <ul>
                                    {(open.receipts||[]).map((it, idx)=> (
                                        <li key={idx}><code>{it.doklad}</code> — {it.date} — {it.stredisko||'Prodejna'} — telefony: {formatNumber(it.phones_kusy||0)}</li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

const ProdejniAnalytika = ({ currentUser }) => {
    const [selectedAnalysis, setSelectedAnalysis] = useState('phones_accessories');
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);
    const [receiptItems, setReceiptItems] = useState(null);
    const [receiptLoading, setReceiptLoading] = useState(false);
    const [receiptError, setReceiptError] = useState(null);
    const [filters, setFilters] = useState(()=>{
        const now = new Date();
        const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
        const iso = (d)=> `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
        return {
            period: 'custom',
            start_date: iso(startOfMonth),
            end_date: iso(now),
            selected_month: `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`,
            prodejna_id: '',
            kanal: 'all',
            kategorie: 'all'
        };
    });
    const [dateError, setDateError] = useState('');
    const [quickKey, setQuickKey] = useState('custom');

    // Barvy pro grafy
    const chartColors = [
        '#8884d8', '#82ca9d', '#ffc658', '#ff7c7c', '#8dd1e1',
        '#d084d0', '#87d068', '#ffb347', '#ff6b6b', '#4ecdc4',
        '#ffe66d', '#ff8b94', '#95e1d3', '#fad390', '#f8b500'
    ];

    // Načtení dat z API
    const fetchData = async () => {
        setLoading(true);
        setError(null);
        
        try {
            const params = new URLSearchParams({
                period: filters.period,
                kanal: filters.kanal,
                ...(filters.start_date && { start_date: filters.start_date }),
                ...(filters.end_date && { end_date: filters.end_date }),
                ...(filters.selected_month && { selected_month: filters.selected_month }),
                ...(filters.prodejna_id && { prodejna_id: filters.prodejna_id })
            });

            let url = '/api/analytics/prodejni-analytika/';
            if (selectedAnalysis === 'phones_accessories') {
                url = '/api/analytics/prodejni-analytika/phones-accessories/';
            } else {
                params.set('type', selectedAnalysis);
                params.set('kategorie', filters.kategorie);
            }

            const response = await fetch(`${url}?${params}`, {
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            
            if (result.success) {
                setData(result);
                setReceiptItems(null);
                setReceiptError(null);
            } else {
                setError(result.error || 'Chyba při načítání dat');
            }
        } catch (err) {
            setError(`Chyba při načítání dat: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    // Načtení dat při změně filtrů nebo typu analýzy
    useEffect(() => {
        fetchData();
    }, [selectedAnalysis, filters]);

    const handleFilterChange = (key, value) => {
        setFilters(prev => ({
            ...prev,
            [key]: value
        }));
    };

    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('cs-CZ', {
            style: 'currency',
            currency: 'CZK'
        }).format(amount);
    };

    const formatNumber = (number) => {
        return new Intl.NumberFormat('cs-CZ').format(number);
    };

    // Custom tooltip pro grafy
    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            return (
                <div className="custom-tooltip">
                    <h4>{label}</h4>
                    {payload.map((entry, index) => (
                        <div key={index} className="tooltip-item">
                            <span 
                                className="tooltip-color" 
                                style={{ backgroundColor: entry.color }}
                            ></span>
                            <span className="tooltip-label">{entry.dataKey}:</span>
                            <span className="tooltip-value">
                                {entry.dataKey === 'obrat' || entry.dataKey === 'zisk' 
                                    ? formatCurrency(entry.value) 
                                    : formatNumber(entry.value)}
                            </span>
                        </div>
                    ))}
                </div>
            );
        }
        return null;
    };

    // Debug informace
    console.log('ProdejniAnalytika - Debug:', {
        loading,
        error,
        data,
        selectedAnalysis,
        filters
    });

    if (loading) {
        return (
            <div className="analytics-section">
                <div className="loading-container">
                    <div className="loading-spinner"></div>
                    <p>Načítám analytická data...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="analytics-section">
                <div className="error-container">
                    <h3>❌ Chyba při načítání dat</h3>
                    <p>{error}</p>
                    <button onClick={fetchData} className="retry-button">
                        🔄 Zkusit znovu
                    </button>
                </div>
            </div>
        );
    }

    return (
        <AnalyticsSectionWrapper title="Prodejní analytika" icon="🎯">
            <div className="analytics-section">
            <div className="section-filters">
                <div className="filter-group">
                    <label>Typ analýzy:</label>
                    <select 
                        value={selectedAnalysis} 
                        onChange={(e) => setSelectedAnalysis(e.target.value)}
                    >
                        {/* Skryté možnosti - lze obnovit v budoucnu */}
                        {/* <option value="categories">📊 Prodeje podle kategorií</option> */}
                        {/* <option value="stores">🏪 Prodeje podle prodejen</option> */}
                        {/* <option value="time">📈 Prodeje v čase</option> */}
                        {/* <option value="products">📱 Prodeje podle produktů</option> */}
                        <option value="phones_accessories">📱+🔌 Telefony a příslušenství ≥ 100 Kč</option>
                    </select>
                </div>

                <div className="filter-group">
                    <label>Období:</label>
                    {(()=>{
                        const monthNames=['leden','únor','březen','duben','květen','červen','červenec','srpen','září','říjen','listopad','prosinec'];
                        const opts=[];
                        
                        // Generujeme měsíce od ledna 2024 do aktuálního měsíce
                        const startYear = 2024;
                        const startMonth = 0; // leden = 0
                        const now = new Date();
                        const currentYear = now.getFullYear();
                        const currentMonth = now.getMonth();
                        
                        for(let year = startYear; year <= currentYear; year++) {
                            const monthStart = (year === startYear) ? startMonth : 0;
                            const monthEnd = (year === currentYear) ? currentMonth : 11;
                            
                            for(let month = monthStart; month <= monthEnd; month++) {
                                const ym = `${year}-${String(month + 1).padStart(2, '0')}`;
                                const label = `${monthNames[month].charAt(0).toUpperCase() + monthNames[month].slice(1)} ${year}`;
                                opts.push({value: `month:${ym}`, label});
                            }
                        }
                        
                        // Přidáme vlastní období na začátek
                        opts.unshift({value: 'custom', label: '🗓️ Vlastní období'});
                        
                        // Řadíme měsíce od nejnovějšího k nejstaršímu (kromě první možnosti)
                        const customOption = opts.shift();
                        opts.reverse();
                        opts.unshift(customOption);
                        
                        const currentValue = filters.period==='monthly_select' ? `month:${filters.selected_month}` : 'custom';
                        return (
                            <CustomDropdown
                                options={opts}
                                value={currentValue}
                                placeholder="Vyberte období"
                                onChange={(selectedValue) => {
                                    if (selectedValue === 'custom'){
                                        handleFilterChange('period','custom');
                                    } else if (selectedValue.startsWith('month:')){
                                        const ym = selectedValue.split(':')[1];
                                        setFilters(prev=>({...prev, period:'monthly_select', selected_month: ym}));
                                        setDateError('');
                                    }
                                }}
                            />
                        );
                    })()}
                </div>

                {filters.period === 'custom' && (
                    <>
                        <div className="filter-group">
                            <label>Od:</label>
                            <input type="date" value={filters.start_date} onChange={(e)=>{
                                const v=e.target.value; if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) { setDateError('Neplatné datum'); return; }
                                setDateError(''); handleFilterChange('start_date', v);
                            }} />
                        </div>
                        <div className="filter-group">
                            <label>Do:</label>
                            <input type="date" value={filters.end_date} onChange={(e)=>{
                                const v=e.target.value; if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) { setDateError('Neplatné datum'); return; }
                                setDateError(''); handleFilterChange('end_date', v);
                            }} />
                        </div>
                        <div className="filter-group" style={{minWidth:240}}>
                            <label>Rychlé volby:</label>
                            <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
                                {['today','yesterday','thisWeek','thisMonth','prevMonth'].map(key=> (
                                    <button key={key} className="refresh-btn" onClick={()=>{
                                        const now=new Date();
                                        const iso=(d)=> `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
                                        let from,to; if(key==='today'){from=to=new Date(now.getFullYear(),now.getMonth(),now.getDate());}
                                        else if(key==='yesterday'){const y=new Date(now); y.setDate(now.getDate()-1); from=to=new Date(y.getFullYear(),y.getMonth(),y.getDate());}
                                        else if(key==='thisWeek'){const day=(now.getDay()+6)%7; from=new Date(now.getFullYear(),now.getMonth(),now.getDate()-day); to=new Date(now.getFullYear(),now.getMonth(),now.getDate());}
                                        else if(key==='thisMonth'){from=new Date(now.getFullYear(),now.getMonth(),1); to=new Date(now.getFullYear(),now.getMonth()+1,0);} 
                                        else if(key==='prevMonth'){from=new Date(now.getFullYear(),now.getMonth()-1,1); to=new Date(now.getFullYear(),now.getMonth(),0);} 
                                        setFilters(prev=>({...prev, start_date: iso(from), end_date: iso(to)})); setQuickKey(key);
                                    }}>{
                                        key==='today'?'Dnešek': key==='yesterday'?'Včerejšek': key==='thisWeek'?'Tento týden': key==='thisMonth'?'Tento měsíc':'Minulý měsíc'
                                    }</button>
                                ))}
                            </div>
                        </div>
                    </>
                )}
                {dateError && <div className="error-container">{dateError}</div>}

                <div className="filter-group">
                    <label>Kanál:</label>
                    <select 
                        value={filters.kanal} 
                        onChange={(e) => handleFilterChange('kanal', e.target.value)}
                    >
                        <option value="all">Všechny kanály</option>
                        <option value="prodejna">Prodejny</option>
                        <option value="eshop">E-shop</option>
                        <option value="allegro">ALLEGRO</option>
                    </select>
                </div>
            </div>

            <div className="section-content">
                {data && (
                    <>
                        {/* Základní metriky - zobrazují se jen pokud nejsme u telefonů/příslušenství */}
                        {selectedAnalysis !== 'phones_accessories' && (
                            <div className="metrics-overview">
                                <div className="metric-card">
                                    <h4>Celkový obrat</h4>
                                    <div className="metric-value">
                                        {formatCurrency(data.aggregations?.celkovy_obrat || 0)}
                                    </div>
                                </div>
                                <div className="metric-card">
                                    <h4>Celková marže</h4>
                                    <div className="metric-value">
                                        {formatCurrency(data.aggregations?.celkovy_zisk || 0)}
                                    </div>
                                </div>
                                <div className="metric-card">
                                    <h4>Marže</h4>
                                    <div className="metric-value">
                                        {data.aggregations?.marze_procenta || 0}%
                                    </div>
                                </div>
                                <div className="metric-card">
                                    <h4>Počet položek</h4>
                                    <div className="metric-value">
                                        {formatNumber(data.aggregations?.celkem_polozek || 0)}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Speciální metriky pro telefony a příslušenství */}
                        {selectedAnalysis === 'phones_accessories' && data.aggregations && (
                            <>
                                <div className="analysis-section" style={{marginBottom: '20px'}}>
                                    <h3>📱 Finanční údaje pouze za prodané telefony</h3>
                                    <p style={{color: '#666', marginBottom: '15px'}}>Následující data zobrazují obrat a marži <strong>pouze za prodané telefony</strong> (bez příslušenství).</p>
                                </div>
                                <div className="metrics-overview">
                                    <div className="metric-card">
                                        <h4>Celkový obrat</h4>
                                        <div className="metric-value">
                                            {formatCurrency(data.aggregations.celkovy_obrat)}
                                        </div>
                                    </div>
                                    <div className="metric-card">
                                        <h4>Celková marže</h4>
                                        <div className="metric-value">
                                            {formatCurrency(data.aggregations.celkovy_zisk)}
                                        </div>
                                    </div>
                                    <div className="metric-card">
                                        <h4>Marže</h4>
                                        <div className="metric-value">
                                            {data.aggregations.marze_procenta}%
                                        </div>
                                    </div>
                                    <div className="metric-card">
                                        <h4>Počet položek</h4>
                                        <div className="metric-value">
                                            {formatNumber(data.aggregations.celkem_polozek)}
                                        </div>
                                    </div>
                                </div>
                            </>
                        )}

                        {/* Grafy / výstupy podle typu analýzy */}
                        {selectedAnalysis === 'categories' && data.categories && (
                            <div className="analysis-section">
                                <h3>📊 Prodeje podle kategorií</h3>
                                
                                {/* Top kategorie - sloupcový graf */}
                                {data.categories.top_categories && data.categories.top_categories.length > 0 && (
                                    <div className="chart-container">
                                        <h4>Top kategorie podle obratu</h4>
                                        <div className="chart-wrapper">
                                            <ResponsiveContainer width="100%" height={400}>
                                                <ComposedChart data={data.categories.top_categories.slice(0, 10)}>
                                                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                                                    <XAxis 
                                                        dataKey="kategorie" 
                                                        tick={{ fontSize: 12 }}
                                                        angle={-45}
                                                        textAnchor="end"
                                                        height={80}
                                                    />
                                                    <YAxis tick={{ fontSize: 12 }} />
                                                    <Tooltip content={<CustomTooltip />} />
                                                    <Legend />
                                                    <Bar dataKey="obrat" fill="#8884d8" name="Obrat" />
                                                    <Line type="monotone" dataKey="zisk" stroke="#82ca9d" name="Zisk" />
                                                </ComposedChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>
                                )}

                                {/* Časová řada kategorií */}
                                {data.categories.time_series && data.categories.time_series.length > 0 && (
                                    <div className="chart-container">
                                        <h4>Vývoj prodejů kategorií v čase</h4>
                                        <div className="chart-wrapper">
                                            <ResponsiveContainer width="100%" height={400}>
                                                <ComposedChart data={data.categories.time_series}>
                                                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                                                    <XAxis 
                                                        dataKey={filters.period === 'daily' ? 'date' : 'month'} 
                                                        tick={{ fontSize: 12 }}
                                                        tickFormatter={(value) => {
                                                            if (typeof value === 'string') {
                                                                return value;
                                                            }
                                                            // Pro datetime.date objekty
                                                            if (value && value.getMonth) {
                                                                return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}`;
                                                            }
                                                            return value;
                                                        }}
                                                    />
                                                    <YAxis tick={{ fontSize: 12 }} />
                                                    <Tooltip content={<CustomTooltip />} />
                                                    <Legend />
                                                    <Line type="monotone" dataKey="obrat" stroke="#8884d8" name="Obrat" />
                                                </ComposedChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        {selectedAnalysis === 'stores' && data.stores && (
                            <div className="analysis-section">
                                <h3>🏪 Prodeje podle prodejen</h3>
                                
                                {/* Top prodejny - sloupcový graf */}
                                {data.stores.top_stores && data.stores.top_stores.length > 0 && (
                                    <div className="chart-container">
                                        <h4>Top prodejny podle obratu</h4>
                                        <div className="chart-wrapper">
                                            <ResponsiveContainer width="100%" height={400}>
                                                <ComposedChart data={data.stores.top_stores}>
                                                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                                                    <XAxis 
                                                        dataKey="stredisko" 
                                                        tick={{ fontSize: 12 }}
                                                        angle={-45}
                                                        textAnchor="end"
                                                        height={80}
                                                    />
                                                    <YAxis tick={{ fontSize: 12 }} />
                                                    <Tooltip content={<CustomTooltip />} />
                                                    <Legend />
                                                    <Bar dataKey="obrat" fill="#8884d8" name="Obrat" />
                                                    <Line type="monotone" dataKey="zisk" stroke="#82ca9d" name="Zisk" />
                                                </ComposedChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>
                                )}

                                {/* Časová řada prodejen */}
                                {data.stores.time_series && data.stores.time_series.length > 0 && (
                                    <div className="chart-container">
                                        <h4>Vývoj prodejů prodejen v čase</h4>
                                        <div className="chart-wrapper">
                                            <ResponsiveContainer width="100%" height={400}>
                                                <ComposedChart data={data.stores.time_series}>
                                                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                                                    <XAxis 
                                                        dataKey={filters.period === 'daily' ? 'date' : 'month'} 
                                                        tick={{ fontSize: 12 }}
                                                        tickFormatter={(value) => {
                                                            if (typeof value === 'string') {
                                                                return value;
                                                            }
                                                            // Pro datetime.date objekty
                                                            if (value && value.getMonth) {
                                                                return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}`;
                                                            }
                                                            return value;
                                                        }}
                                                    />
                                                    <YAxis tick={{ fontSize: 12 }} />
                                                    <Tooltip content={<CustomTooltip />} />
                                                    <Legend />
                                                    <Line type="monotone" dataKey="obrat" stroke="#8884d8" name="Obrat" />
                                                </ComposedChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        {selectedAnalysis === 'time' && data.time && (
                            <div className="analysis-section">
                                <h3>📈 Prodeje v čase</h3>
                                
                                {/* Časová řada */}
                                {data.time.time_series && data.time.time_series.length > 0 && (
                                    <div className="chart-container">
                                        <h4>Vývoj prodejů v čase</h4>
                                        <div className="chart-wrapper">
                                            <ResponsiveContainer width="100%" height={400}>
                                                <ComposedChart data={data.time.time_series}>
                                                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                                                    <XAxis 
                                                        dataKey={filters.period === 'daily' ? 'date' : 'month'} 
                                                        tick={{ fontSize: 12 }}
                                                        tickFormatter={(value) => {
                                                            if (typeof value === 'string') {
                                                                return value;
                                                            }
                                                            // Pro datetime.date objekty
                                                            if (value && value.getMonth) {
                                                                return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}`;
                                                            }
                                                            return value;
                                                        }}
                                                    />
                                                    <YAxis tick={{ fontSize: 12 }} />
                                                    <Tooltip content={<CustomTooltip />} />
                                                    <Legend />
                                                    <Line type="monotone" dataKey="obrat" stroke="#8884d8" name="Obrat" />
                                                    <Line type="monotone" dataKey="zisk" stroke="#82ca9d" name="Zisk" />
                                                    <Bar dataKey="polozky" fill="#ffc658" name="Počet položek" />
                                                </ComposedChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>
                                )}

                                {/* Trendy */}
                                <div className="trend-metrics">
                                    <div className="trend-card">
                                        <h4>Růst za období</h4>
                                        <div className={`trend-value ${data.time.growth_rate >= 0 ? 'positive' : 'negative'}`}>
                                            {data.time.growth_rate >= 0 ? '+' : ''}{data.time.growth_rate}%
                                        </div>
                                    </div>
                                    {data.time.prediction && (
                                        <div className="trend-card">
                                            <h4>Predikce příští období</h4>
                                            <div className="prediction-value">
                                                {formatCurrency(data.time.prediction)}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        {selectedAnalysis === 'products' && data.products && (
                            <div className="analysis-section">
                                <h3>📱 Prodeje podle produktů</h3>
                                
                                {/* Top produkty - sloupcový graf */}
                                {data.products.top_products && data.products.top_products.length > 0 && (
                                    <div className="chart-container">
                                        <h4>Top produkty podle obratu</h4>
                                        <div className="chart-wrapper">
                                            <ResponsiveContainer width="100%" height={400}>
                                                <ComposedChart data={data.products.top_products.slice(0, 15)}>
                                                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                                                    <XAxis 
                                                        dataKey="nazev" 
                                                        tick={{ fontSize: 12 }}
                                                        angle={-45}
                                                        textAnchor="end"
                                                        height={80}
                                                    />
                                                    <YAxis tick={{ fontSize: 12 }} />
                                                    <Tooltip content={<CustomTooltip />} />
                                                    <Legend />
                                                    <Bar dataKey="obrat" fill="#8884d8" name="Obrat" />
                                                    <Line type="monotone" dataKey="kusy" stroke="#82ca9d" name="Počet kusů" />
                                                </ComposedChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>
                                )}

                                {/* Časová řada produktů */}
                                {data.products.time_series && data.products.time_series.length > 0 && (
                                    <div className="chart-container">
                                        <h4>Vývoj prodejů produktů v čase</h4>
                                        <div className="chart-wrapper">
                                            <ResponsiveContainer width="100%" height={400}>
                                                <ComposedChart data={data.products.time_series}>
                                                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                                                    <XAxis 
                                                        dataKey={filters.period === 'daily' ? 'date' : 'month'} 
                                                        tick={{ fontSize: 12 }}
                                                        tickFormatter={(value) => {
                                                            if (typeof value === 'string') {
                                                                return value;
                                                            }
                                                            // Pro datetime.date objekty
                                                            if (value && value.getMonth) {
                                                                return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}`;
                                                            }
                                                            return value;
                                                        }}
                                                    />
                                                    <YAxis tick={{ fontSize: 12 }} />
                                                    <Tooltip content={<CustomTooltip />} />
                                                    <Legend />
                                                    <Line type="monotone" dataKey="obrat" stroke="#8884d8" name="Obrat" />
                                                </ComposedChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                        {selectedAnalysis === 'phones_accessories' && data && data.totals && (
                            <div className="analysis-section">
                                <h3>📱+🔌 Telefony a příslušenství ≥ 100 Kč</h3>
                                <div className="metrics-overview">
                                    <div className="metric-card">
                                        <h4>Prodáno telefonů (kusy)</h4>
                                        <div className="metric-value">{formatNumber(data.totals.phones||0)}</div>
                                        <div className="metric-subtitle" style={{fontSize: '0.8em', color: '#666', marginTop: '4px'}}>(minus storna)</div>
                                    </div>
                                    <div className="metric-card"><h4>Položky příslušenství/služeb ≥ 100 Kč</h4><div className="metric-value">{formatNumber(data.totals.accessories_items_over_threshold||0)}</div></div>
                                    <div className="metric-card"><h4>Příslušenství na 1 telefon</h4><div className="metric-value">{(data.totals.accessories_per_phone||0).toFixed(2)}</div></div>
                                </div>
                                <div className="metrics-overview">
                                    <div className="metric-card"><h4>Doklady s příslušenstvím ≥ 100</h4><div className="metric-value">{formatNumber(data.receipts?.with_accessory||0)}</div></div>
                                    <div className="metric-card"><h4>Doklady pouze s telefonem</h4><div className="metric-value">{formatNumber(data.receipts?.without_accessory||0)}</div></div>
                                </div>

                                {Array.isArray(data.receipts?.without_accessory_list) && (
                                    <div className="chart-container">
                                        <h4>🧾 Doklady pouze s telefonem (bez položky ≥ 100 Kč)</h4>
                                        <div className="items-list">
                                            <ul>
                                                {data.receipts.without_accessory_list.map((r, idx)=> (
                                                    <li key={idx}>
                                                        <button className="refresh-btn" onClick={async()=>{
                                                            setReceiptLoading(true); setReceiptError(null); setReceiptItems(null);
                                                            try{
                                                                const p = new URLSearchParams({ doklad: r.doklad, threshold: '100' });
                                                                const res = await fetch(`/api/analytics/prodejni-analytika/phones-accessories/receipt-items/?${p}`, { credentials:'include' });
                                                                if(!res.ok) throw new Error(`HTTP ${res.status}`);
                                                                const json = await res.json();
                                                                if(!json.success) throw new Error(json.error||'Chyba');
                                                                setReceiptItems({ doklad: r.doklad, items: json.items });
                                                            }catch(e){ setReceiptError(e.message);} finally{ setReceiptLoading(false);} 
                                                        }}>Detail</button>
                                                        <code style={{marginLeft:8}}>{r.doklad}</code> — {r.date} — {r.stredisko||'Prodejna'} — telefony: {formatNumber(r.phones_kusy||0)}
                                                    </li>
                                                ))}
                                            </ul>
                                            {receiptLoading && <div style={{marginTop:8}}>Načítám položky…</div>}
                                            {receiptError && <div className="error-container" style={{marginTop:8}}>{receiptError}</div>}
                                            {receiptItems && (
                                                <div style={{marginTop:10}}>
                                                    <h4>Položky dokladu <code>{receiptItems.doklad}</code></h4>
                                                    <ul>
                                                        {receiptItems.items.map((it,i)=> (
                                                            <li key={i}>{it.nazev} {it.kod? `(${it.kod})`:''} — {formatNumber(it.pocet_kusu||0)} ks — {new Intl.NumberFormat('cs-CZ', { style:'currency', currency:'CZK'}).format(it.cena_ks_vcl_dph||0)} {it.over_threshold? '🔸':''}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}

                                {/* Rozpad po prodejcích */}
                                <div className="chart-container">
                                    <h4>👤 Rozpad po prodejcích</h4>
                                    <SalespersonBreakdown filters={filters} />
                                </div>
                            </div>
                        )}
                    </>
                )}
            </div>
            </div>
        </AnalyticsSectionWrapper>
    );
};

export default ProdejniAnalytika; 