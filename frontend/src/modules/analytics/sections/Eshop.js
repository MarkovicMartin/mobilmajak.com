import React, { useState, useEffect } from 'react';
import AnalyticsSectionWrapper from '../AnalyticsSectionWrapper';
import CustomDropdown from '../../../components/CustomDropdown';
import './Eshop.css';
// Sub-component for category analytics
const EshopCategoryAnalytics = ({ filters }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchAnalytics = async () => {
            setLoading(true);
            setError(null);
            try {
                const params = new URLSearchParams();
                Object.keys(filters).forEach(key => {
                    if (filters[key] !== undefined && filters[key] !== null) params.append(key, filters[key]);
                });
                const res = await fetch(`/api/analytics/eshop/categories-analytics/?${params}`, { credentials: 'include' });
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const json = await res.json();
                if (!json.success) throw new Error(json.error || 'Chyba načítání analytiky');
                setData(json);
            } catch (e) {
                setError(e.message);
            } finally {
                setLoading(false);
            }
        };
        fetchAnalytics();
    }, [filters]);

    const formatCurrency = (amount) => {
        if (amount === null || amount === undefined) return '0 Kč';
        return new Intl.NumberFormat('cs-CZ', { style: 'currency', currency: 'CZK', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(amount);
    };
    const formatNumber = (num) => new Intl.NumberFormat('cs-CZ').format(Math.round(num || 0));

    // Lokální filtrace logistických položek
    const shippingKeywords = [
        'zásilkovna', 'zasilkovna',
        'zásielkovňa', 'zasielkovna',
        'balíkovna', 'balikovna',
        'osobní odběr', 'osobni odber', 'osobný odber', 'osobny odber',
        'výdejní místo', 'vydejni misto'
    ];
    const isShippingName = (name) => {
        if (!name) return false;
        const n = String(name).toLowerCase();
        return shippingKeywords.some(kw => n.includes(kw));
    };
    const filterShipping = (arr, field) => {
        if (!Array.isArray(arr)) return [];
        return arr.filter(it => !isShippingName(field ? it[field] : it?.nazev));
    };

    // Časové řady kategorií
    const [tsLoading, setTsLoading] = useState(false);
    const [tsError, setTsError] = useState(null);
    const [tsData, setTsData] = useState(null);
    const [tsDimension, setTsDimension] = useState('kategorie');
    const [tsGroupBy, setTsGroupBy] = useState('monthly');
    const [tsSelected, setTsSelected] = useState([]);
    const [barTip, setBarTip] = useState({ visible: false, x: 0, y: 0, text: '' });

    useEffect(() => {
        const loadTs = async () => {
            setTsLoading(true);
            setTsError(null);
            try {
                const params = new URLSearchParams();
                Object.keys(filters).forEach(k => {
                    if (filters[k] !== undefined && filters[k] !== null) params.append(k, filters[k]);
                });
                params.set('dimension', tsDimension);
                params.set('group_by', tsGroupBy);
                tsSelected.forEach(v => params.append('selected[]', v));
                const res = await fetch(`/api/analytics/eshop/categories-timeseries/?${params}`, { credentials: 'include' });
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const json = await res.json();
                if (!json.success) throw new Error(json.error || 'Chyba načítání časových řad');
                setTsData(json);
                if (!tsSelected?.length && Array.isArray(json.selected)) setTsSelected(json.selected);
            } catch (e) {
                setTsError(e.message);
            } finally {
                setTsLoading(false);
            }
        };
        loadTs();
    }, [filters, tsDimension, tsGroupBy, JSON.stringify(tsSelected)]);

    if (loading) return <div className="eshop-top"><h3>📈 Kategorie analytika</h3><div>Načítám…</div></div>;
    if (error) return <div className="eshop-top"><h3>📈 Kategorie analytika</h3><div className="eshop-error">{error}</div></div>;
    if (!data) return null;

    return (
        <div className="eshop-top">
            <h3>📈 Kategorie analytika</h3>
            {/* Souhrn vratek */}
            <div className="breakdown-cards" style={{marginBottom:20}}>
                <div className="breakdown-card" style={{borderColor:'#2ecc71'}}>
                    <h4>🔄 Vratky (E‑shop)</h4>
                    <div className="breakdown-metrics">
                        <div><strong>Celkem objednávek:</strong> {formatNumber(data.returns?.total_objednavek || 0)} | <strong>z toho storno:</strong> {formatNumber(data.returns?.vraceno_objednavek || 0)} ({formatNumber(data.returns?.return_rate_orders || 0)} %)</div>
                        <div><strong>Celkem položek:</strong> {formatNumber(data.returns?.total_polozek || 0)} | <strong>z toho storno:</strong> {formatNumber(data.returns?.vraceno_polozek || 0)} ({formatNumber(data.returns?.return_rate_items || 0)} %)</div>
                        <div><strong>Celkem kusů:</strong> {formatNumber(data.returns?.total_kusu || 0)} | <strong>vrácené kusy:</strong> {formatNumber(data.returns?.vraceno_kusu || 0)}</div>
                        <div><strong>Vracená hodnota:</strong> {formatCurrency(data.returns?.vraceno_hodnota || 0)}</div>
                    </div>
                </div>
            </div>

            {/* Interaktivní graf časových řad */}
            <div className="eshop-top" style={{marginTop:20}}>
                <h4>📅 Prodeje v čase</h4>
                {/* Ovládací prvky */}
                <div className="filter-row" style={{marginBottom:10}}>
                    <div className="filter-group">
                        <label>Dimenze</label>
                        <select value={tsDimension} onChange={(e)=>setTsDimension(e.target.value)}>
                            <option value="kategorie">Kategorie</option>
                            <option value="kategorie_1">Podkategorie</option>
                            <option value="kategorie_2">Značky/produkty</option>
                        </select>
                    </div>
                    <div className="filter-group">
                        <label>Agregace</label>
                        <select value={tsGroupBy} onChange={(e)=>setTsGroupBy(e.target.value)}>
                            <option value="monthly">Měsíčně</option>
                            <option value="weekly">Týdně</option>
                            <option value="daily">Denně</option>
                        </select>
                    </div>
                    <div className="filter-group" style={{flex:1}}>
                        <label>Výběr položek (max 6)</label>
                        <div style={{display:'flex', gap:8, flexWrap:'wrap'}}>
                            {(tsData?.available || []).slice(0,20).map((name,i)=>{
                                const selected = tsSelected.includes(name);
                                return (
                                    <button key={i} onClick={()=>{
                                        setTsSelected(prev=>{
                                            const next = selected ? prev.filter(v=>v!==name) : [...prev, name];
                                            return next.slice(-6);
                                        });
                                    }} className="refresh-btn" style={{background:selected?'#2ecc71':'#e0e0e0', color:selected?'#fff':'#2c3e50', padding:'6px 10px'}}>
                                        {name || 'Nezařazeno'}
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                </div>
                {tsLoading && <div>Načítám…</div>}
                {tsError && <div className="eshop-error">{tsError}</div>}
                {!tsLoading && !tsError && (
                    <div style={{overflowX:'auto'}}>
                        <svg width="100%" height="380" viewBox="0 0 940 380" preserveAspectRatio="xMidYMid meet">
                            {
                                (()=>{
                                    const series = tsData?.data || [];
                                    const allPoints = [].concat(...series.map(s=>s.points));
                                    const dates = Array.from(new Set(allPoints.map(p=>p.date))).sort();
                                    const left = 70, right = 920, top = 40, bottom = 320;
                                    const width = right - left, height = bottom - top;
                                    const maxYraw = Math.max(1, ...allPoints.map(p=>p.kusy||0));
                                    const niceMax = (m)=>{ const pow=Math.pow(10, Math.floor(Math.log10(m))); const n=Math.ceil(m/pow); const k=n<=2?2:n<=5?5:10; return k*pow; };
                                    const yMax = niceMax(maxYraw*1.1);
                                    const py = v => bottom - (height * (v / yMax));
                                    const groupW = dates.length>0 ? width / dates.length : width;
                                    const palette = ['#e74c3c','#3498db','#27ae60','#9b59b6','#f39c12','#2ecc71'];
                                    const barGap = 4;
                                    const barW = Math.max(8, Math.min(26, (groupW - 8) / Math.max(1, series.length) - barGap));

                                    return (
                                        <g>
                                            {/* mřížka + osy */}
                                            {[0,1,2,3,4,5].map(i=>{
                                                const val = (yMax/5)*i;
                                                const y = py(val);
                                                return (
                                                    <g key={i}>
                                                        <line x1={left} y1={y} x2={right} y2={y} stroke="#eef1f5" />
                                                        <text x={left-10} y={y+4} fontSize="10" textAnchor="end" fill="#7f8c8d">{new Intl.NumberFormat('cs-CZ').format(Math.round(val))}</text>
                                                    </g>
                                                );
                                            })}
                                            <line x1={left} y1={bottom} x2={right} y2={bottom} stroke="#cbd3da" />
                                            <line x1={left} y1={top} x2={left} y2={bottom} stroke="#cbd3da" />

                                            {/* popisky X */}
                                            {dates.map((d,i)=>{
                                                const x = left + groupW*(i+0.5);
                                                return (
                                                    <text key={i} transform={`translate(${x}, ${bottom+22}) rotate(-30)`} fontSize="10" textAnchor="end" fill="#7f8c8d">{String(d).slice(0,10)}</text>
                                                );
                                            })}

                                            {/* sloupce pro kusy */}
                                            {series.map((s,si)=>{
                                                const color = palette[si%palette.length];
                                                return (
                                                    <g key={si}>
                                                        {dates.map((d,i)=>{
                                                            const p = s.points.find(pt=>pt.date===d) || {kusy:0};
                                                            const center = left + groupW*(i+0.5);
                                                            const groupTotal = (series.length*barW) + (Math.max(0,series.length-1)*barGap);
                                                            const x0 = center - groupTotal/2;
                                                            const x = x0 + si*(barW+barGap);
                                                            const y = py(p.kusy||0);
                                                            const h = bottom - y;
                                                            return (
                                                                <g key={i}>
                                                                    <rect
                                                                        x={x}
                                                                        y={y}
                                                                        width={barW}
                                                                        height={h}
                                                                        fill={color}
                                                                        rx="3"
                                                                        onMouseEnter={()=> setBarTip({ visible:true, x: x + barW/2, y: y - 10, text: `${new Intl.NumberFormat('cs-CZ').format(p.kusy||0)} ks` })}
                                                                        onMouseLeave={()=> setBarTip(prev => ({ ...prev, visible:false }))}
                                                                        onMouseMove={()=> setBarTip(prev => ({ ...prev, x: x + barW/2, y: y - 10 }))}
                                                                    >
                                                                        <title>{`${s.key || 'Nezařazeno'} — ${new Intl.NumberFormat('cs-CZ').format(p.kusy||0)} ks`}</title>
                                                                    </rect>
                                                                </g>
                                                            );
                                                        })}
                                                        {/* legenda */}
                                                        <rect x={left} y={top-28+si*16} width="10" height="10" fill={color} rx="2" />
                                                        <text x={left+16} y={top-19+si*16} fontSize="12" fill="#2c3e50">{s.key || 'Nezařazeno'}</text>
                                                    </g>
                                                );
                                            })}
                                            {/* tooltip */}
                                            {barTip.visible && (
                                                <g pointerEvents="none" transform={`translate(${barTip.x}, ${barTip.y})`}>
                                                    <rect x={-45} y={-24} width={90} height={20} rx="4" fill="#ffffff" stroke="#cbd3da" />
                                                    <text y={-10} textAnchor="middle" fontSize="12" fill="#2c3e50">{barTip.text}</text>
                                                </g>
                                            )}
                                        </g>
                                    );
                                })()}
                        </svg>
                    </div>
                )}
            </div>
        </div>
    );
};

const Eshop = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [detailOpen, setDetailOpen] = useState(false);
    const [detailLoading, setDetailLoading] = useState(false);
    const [detailError, setDetailError] = useState(null);
    const [detailChannel, setDetailChannel] = useState(null); // 'eshop' | 'allegro'
    const [channelDetail, setChannelDetail] = useState(null);
    
    // Filtry
    const [filters, setFilters] = useState(()=>{
        const now=new Date();
        const fmt=(d)=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
        return { period:'custom', start_date:fmt(new Date(now.getFullYear(), now.getMonth(), 1)), end_date:fmt(now), exclude_allegro:false };
    });
    const [dateError, setDateError] = useState('');

    // Rychlé volby rozsahu
    const setQuickRange = (type) => {
        const now = new Date();
        const fmt=(d)=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
        let from, to;
        if (type==='today') { from = new Date(now.getFullYear(), now.getMonth(), now.getDate()); to = new Date(now.getFullYear(), now.getMonth(), now.getDate()); }
        else if (type==='yesterday') { const y=new Date(now); y.setDate(now.getDate()-1); from=new Date(y.getFullYear(), y.getMonth(), y.getDate()); to=new Date(y.getFullYear(), y.getMonth(), y.getDate()); }
        else if (type==='thisWeek') { const day=(now.getDay()+6)%7; from=new Date(now.getFullYear(), now.getMonth(), now.getDate()-day); to=new Date(now.getFullYear(), now.getMonth(), now.getDate()); }
        else if (type==='thisMonth') { from=new Date(now.getFullYear(), now.getMonth(), 1); to=new Date(now.getFullYear(), now.getMonth()+1, 0); }
        else if (type==='prevMonth') { from=new Date(now.getFullYear(), now.getMonth()-1, 1); to=new Date(now.getFullYear(), now.getMonth(), 0); }
        setDateError('');
        setFilters(prev=> ({...prev, period:'custom', start_date: fmt(from), end_date: fmt(to)}));
    };

    // Načtení dat z API
    const fetchData = async () => {
        setLoading(true);
        setError(null);
        
        try {
            const params = new URLSearchParams();
            Object.keys(filters).forEach(key => {
                if (filters[key] !== undefined && filters[key] !== null) {
                    params.append(key, filters[key]);
                }
            });
            
            const response = await fetch(`/api/analytics/eshop/?${params}`, {
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
            
            if (result.success) {
                setData(result);
            } else {
                throw new Error(result.error || 'Chyba při načítání dat');
            }
            
        } catch (err) {
            console.error('Chyba při načítání E-shop dat:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    // Načtení dat při změně filtrů
    useEffect(() => {
        fetchData();
    }, [filters]);

    // Otevření detailu kanálu (modal)
    const openChannelDetail = async (channel) => {
        setDetailChannel(channel);
        setDetailOpen(true);
        setDetailLoading(true);
        setDetailError(null);
        setChannelDetail(null);

        try {
            const params = new URLSearchParams();
            Object.keys(filters).forEach(key => {
                if (filters[key] !== undefined && filters[key] !== null) {
                    params.append(key, filters[key]);
                }
            });
            params.set('channel', channel);

            const response = await fetch(`/api/analytics/eshop/channel-detail/?${params}`, {
                credentials: 'include'
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const result = await response.json();
            if (!result.success) throw new Error(result.error || 'Chyba detailu kanálu');
            setChannelDetail(result.breakdown);
        } catch (e) {
            setDetailError(e.message);
        } finally {
            setDetailLoading(false);
        }
    };

    const closeDetail = () => {
        setDetailOpen(false);
        setChannelDetail(null);
        setDetailChannel(null);
        setDetailError(null);
    };

    // Načtení položek v detailu
    const loadChannelItems = async (segment, value, extra = {}) => {
        setDetailLoading(true);
        setDetailError(null);
        try {
            const params = new URLSearchParams();
            Object.keys(filters).forEach(key => {
                if (filters[key] !== undefined && filters[key] !== null) {
                    params.append(key, filters[key]);
                }
            });
            params.set('channel', detailChannel);
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
            setChannelDetail(prev => ({ ...prev, [`${segment}_items`]: result.items, [`${segment}_count`]: result.count }));
        } catch (e) {
            setDetailError(e.message);
        } finally {
            setDetailLoading(false);
        }
    };

    // Zpracování změny filtru
    const handleFilterChange = (filterName, value) => {
        setFilters(prev => ({
            ...prev,
            [filterName]: value
        }));
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

    // Filtrace logistických/pickup položek, které v analytice nechceme zobrazovat
    const shippingKeywords = [
        'zásilkovna', 'zasilkovna',
        'zásielkovňa', 'zasielkovna',
        'balíkovna', 'balikovna',
        'osobní odběr', 'osobni odber', 'osobný odber', 'osobny odber',
        'výdejní místo', 'vydejni misto'
    ];
    const isShippingName = (name) => {
        if (!name) return false;
        const n = String(name).toLowerCase();
        return shippingKeywords.some(kw => n.includes(kw));
    };
    const filterShipping = (arr, field) => {
        if (!Array.isArray(arr)) return [];
        return arr.filter(it => !isShippingName(field ? it[field] : it?.nazev));
    };

    return (
        <AnalyticsSectionWrapper title="E-shop analytika" icon="🛒">
            <div className="eshop-analytics">

            {/* Filtry */}
            <div className="eshop-filters">
                <div className="filter-row">
                    {/* Období – custom dropdown s měsíci */}
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
                            
                            // Najděme správnou hodnotu - zatím vždy custom, protože eshop používá vlastní období
                            const currentValue = 'custom';
                            
                            return (
                                <CustomDropdown
                                    options={opts}
                                    value={currentValue}
                                    placeholder="Vyberte období"
                                    onChange={(selectedValue) => {
                                        if (selectedValue === 'custom') {
                                            // Už je nastaveno na custom
                                        } else if (selectedValue.startsWith('month:')) {
                                            const ym = selectedValue.split(':')[1];
                                            // Nastavíme start_date a end_date podle vybraného měsíce
                                            const [year, month] = ym.split('-');
                                            const startDate = `${year}-${month}-01`;
                                            // Opraveno: explicitní výpočet posledního dne měsíce (31 dní pro leden, atd.)
                                            const monthIndex = parseInt(month) - 1; // převedeme na 0-based index (leden=0)
                                            const lastDay = new Date(parseInt(year), monthIndex + 1, 0).getDate(); // poslední den měsíce
                                            const endDate = `${year}-${month}-${String(lastDay).padStart(2, '0')}`;
                                            setFilters(prev=>({...prev, start_date: startDate, end_date: endDate}));
                                            setDateError('');
                                        }
                                    }}
                                />
                            );
                        })()}
                    </div>

                    {/* Vlastní období */}
                    {true && (
                        <>
                            <div className="filter-group">
                                <label>Od:</label>
                                <input type="date" value={filters.start_date} max={filters.end_date||undefined} onChange={(e)=>{
                                    const v=e.target.value; if(!/^\d{4}-\d{2}-\d{2}$/.test(v)){setDateError('Neplatné datum');return;} setDateError(''); setFilters(prev=>{ const next={...prev,start_date:v}; if(new Date(next.start_date)>new Date(next.end_date)) [next.start_date,next.end_date]=[next.end_date,next.start_date]; return next;});
                                }}/>
                            </div>
                            <div className="filter-group">
                                <label>Do:</label>
                                <input type="date" value={filters.end_date} min={filters.start_date||undefined} onChange={(e)=>{
                                    const v=e.target.value; if(!/^\d{4}-\d{2}-\d{2}$/.test(v)){setDateError('Neplatné datum');return;} setDateError(''); setFilters(prev=>{ const next={...prev,end_date:v}; if(new Date(next.start_date)>new Date(next.end_date)) [next.start_date,next.end_date]=[next.end_date,next.start_date]; return next;});
                                }}/>
                            </div>
                        </>
                    )}

                    {/* Vyloučit ALLEGRO */}
                    <div className="filter-group">
                        <label>
                            <input
                                type="checkbox"
                                checked={filters.exclude_allegro}
                                onChange={(e) => handleFilterChange('exclude_allegro', e.target.checked)}
                            />
                            Vyloučit ALLEGRO
                        </label>
                    </div>

                    {/* Rychlé volby */}
                    <div className="filter-group" style={{minWidth:240}}>
                        <label>Rychlé volby:</label>
                        <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
                            <button className="refresh-btn" onClick={()=>setQuickRange('today')}>Dnešek</button>
                            <button className="refresh-btn" onClick={()=>setQuickRange('yesterday')}>Včerejšek</button>
                            <button className="refresh-btn" onClick={()=>setQuickRange('thisWeek')}>Tento týden</button>
                            <button className="refresh-btn" onClick={()=>setQuickRange('thisMonth')}>Tento měsíc</button>
                            <button className="refresh-btn" onClick={()=>setQuickRange('prevMonth')}>Minulý měsíc</button>
                        </div>
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
                {dateError && <div className="eshop-error" style={{marginTop:8}}>{dateError}</div>}
            </div>

            {/* Loading state */}
            {loading && (
                <div className="eshop-loading">
                    <div className="loading-spinner"></div>
                    <p>Načítám E-shop data...</p>
                </div>
            )}

            {/* Error state */}
            {error && (
                <div className="eshop-error">
                    <h3>❌ Chyba při načítání dat</h3>
                    <p>{error}</p>
                    <button onClick={fetchData}>Zkusit znovu</button>
                </div>
            )}

            {/* Data zobrazení */}
            {data && data.metrics && !loading && (
                <>
                    {/* Hlavní metriky – přeuspořádané do dvou sloupců (E‑shop vlevo, Allegro vpravo) a počty po straně */}
                    <div className="eshop-metrics" style={{gridTemplateColumns: 'repeat(3, minmax(280px, 1fr))'}}>
                        {/* Sloupec 1: E‑shop */}
                        <div style={{display:'grid', gap:20}}>
                            <div className="metric-card">
                                <div className="metric-icon">🛒</div>
                                <div className="metric-content">
                                    <h3>Obrat e‑shopu (bez DPH)</h3>
                                    <div className="metric-value">{formatCurrency(data.metrics.eshop_obrat_bez_dph)}</div>
                                </div>
                            </div>
                            <div className="metric-card">
                                <div className="metric-icon">📈</div>
                                <div className="metric-content">
                                    <h3>Marže bez DPH</h3>
                                    <div className="metric-value">{formatCurrency(data.metrics.eshop_zisk)}</div>
                                </div>
                            </div>
                        </div>

                        {/* Sloupec 2: Allegro */}
                        <div style={{display:'grid', gap:20}}>
                            <div className="metric-card">
                                <div className="metric-icon">🛒</div>
                                <div className="metric-content">
                                    <h3>Obrat Allegro (bez DPH)</h3>
                                    <div className="metric-value">{formatCurrency(data.metrics.allegro_obrat_bez_dph)}</div>
                                </div>
                            </div>
                            <div className="metric-card">
                                <div className="metric-icon">💹</div>
                                <div className="metric-content">
                                    <h3>Marže bez DPH</h3>
                                    <div className="metric-value">{formatCurrency(data.metrics.allegro_zisk)}</div>
                                </div>
                            </div>
                        </div>

                        {/* Sloupec 3: Počty */}
                        <div style={{display:'grid', gap:20}}>
                            <div className="metric-card">
                                <div className="metric-icon">🧾</div>
                                <div className="metric-content">
                                    <h3>Počet objednávek</h3>
                                    <div className="metric-value">{formatNumber(data.metrics.pocet_objednavek)}</div>
                                </div>
                            </div>
                            <div className="metric-card">
                                <div className="metric-icon">🛍️</div>
                                <div className="metric-content">
                                    <h3>Počet položek</h3>
                                    <div className="metric-value">{formatNumber(data.metrics.pocet_polozek)}</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Rozklad E-shop kanálů (klikací dlaždice stejně jako v Servis) */}
                    {data.channels && (
                        <div className="eshop-breakdown">
                            <h3>📊 Rozklad E-shop kanálů</h3>
                            <div className="breakdown-cards">
                                <div className="breakdown-card clickable" onClick={() => openChannelDetail('eshop')}>
                                    <h4>🌐 E-shop (bez ALLEGRO)</h4>
                                    <div className="breakdown-metrics">
                                        <div>Obrat bez DPH: <strong>{formatCurrency(data.channels.eshop.obrat_bez_dph)}</strong></div>
                                        <div>Marže bez DPH: <strong>{formatCurrency(data.channels.eshop.zisk)}</strong></div>
                                        <div>Položky: <strong>{formatNumber(data.channels.eshop.polozky)}</strong></div>
                                        <div>Objednávky: <strong>{formatNumber(data.channels.eshop.objednavky)}</strong></div>
                                    </div>
                                </div>

                                <div className="breakdown-card clickable" onClick={() => openChannelDetail('allegro')}>
                                    <h4>🛒 ALLEGRO</h4>
                                    <div className="breakdown-metrics">
                                        <div>Obrat bez DPH: <strong>{formatCurrency(data.channels.allegro.obrat_bez_dph)}</strong></div>
                                        <div>Marže bez DPH: <strong>{formatCurrency(data.channels.allegro.zisk)}</strong></div>
                                        <div>Položky: <strong>{formatNumber(data.channels.allegro.polozky)}</strong></div>
                                        <div>Objednávky: <strong>{formatNumber(data.channels.allegro.objednavky)}</strong></div>
                                    </div>
                                </div>

                                {/* Nová dlaždice: Dopravné (součet bez DPH) */}
                                <div className="breakdown-card">
                                    <h4>🚚 Dopravné</h4>
                                    <div className="breakdown-metrics">
                                        <div>Obrat bez DPH: <strong>{formatCurrency(data.channels?.shipping?.obrat_bez_dph || 0)}</strong></div>
                                        <div style={{opacity:0.7}}>Zobrazuje pouze součet bez DPH u položek: Zásilkovna, Zásielkovňa, Balíkovna, Osobní odběr, Česká pošta, Allegro doručení…</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Kategorie analytika (grafické seznamy + vratky) */}
                    <EshopCategoryAnalytics filters={filters} />

                    {/* Modal s detailem kanálu */}
                    {detailOpen && (
                        <div className="modal-overlay" onClick={closeDetail}>
                            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                                <div className="modal-header">
                                    <h4>Detail kanálu: {detailChannel === 'eshop' ? 'E‑shop' : 'Allegro'}</h4>
                                    <button className="modal-close" onClick={closeDetail}>✕</button>
                                </div>
                                <div className="modal-body">
                                    {detailLoading && <div className="modal-loading">Načítám…</div>}
                                    {detailError && <div className="modal-error">{detailError}</div>}
                                    {channelDetail && (
                                        <div className="detail-grid">
                                            <div className="detail-card" style={{cursor:'pointer'}}>
                                                <h5>🏷️ Kategorie</h5>
                                    {filterShipping(channelDetail.kategorie || [], 'kategorie').slice(0,8).map((it, i) => (
                                                    <div key={i} className="top-item clickable" onClick={() => loadChannelItems('kategorie', it.kategorie)}>
                                                        <span className="top-name">{it.kategorie || 'Nezařazeno'}</span>
                                                        <span className="top-value">{formatCurrency(it.obrat_bez_dph)}</span>
                                                        <span className="top-count">({formatNumber(it.polozky)} položek)</span>
                                                    </div>
                                                ))}
                                                {channelDetail.kategorie_items && (
                                                    <div className="items-list">
                                                        <h6>Položky ({formatNumber(channelDetail.kategorie_count)}):</h6>
                                                        <ul>
                                                            {channelDetail.kategorie_items.map((it, i) => (
                                                                <li key={i}><code>{it.objednavka || '—'}</code> — {it.nazev}</li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                )}
                                            </div>
                                            <div className="detail-card" style={{cursor:'pointer'}}>
                                                <h5>📂 Podkategorie</h5>
                                    {filterShipping(channelDetail.kategorie_1 || [], 'kategorie_1').slice(0,8).map((it, i) => (
                                                    <div key={i} className="top-item clickable" onClick={() => loadChannelItems('kategorie_1', it.kategorie_1)}>
                                                        <span className="top-name">{it.kategorie_1 || 'Nezařazeno'}</span>
                                                        <span className="top-value">{formatCurrency(it.obrat_bez_dph)}</span>
                                                        <span className="top-count">({formatNumber(it.polozky)} položek)</span>
                                                    </div>
                                                ))}
                                                {channelDetail.kategorie_1_items && (
                                                    <div className="items-list">
                                                        <h6>Položky ({formatNumber(channelDetail.kategorie_1_count)}):</h6>
                                                        <ul>
                                                            {channelDetail.kategorie_1_items.map((it, i) => (
                                                                <li key={i}><code>{it.objednavka || '—'}</code> — {it.nazev}</li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                )}
                                            </div>
                                            <div className="detail-card" style={{cursor:'pointer'}}>
                                                <h5>📁 Značky/produkty</h5>
                                    {filterShipping(channelDetail.kategorie_2 || [], 'kategorie_2').slice(0,8).map((it, i) => (
                                                    <div key={i} className="top-item clickable" onClick={() => loadChannelItems('kategorie_2', it.kategorie_2)}>
                                                        <span className="top-name">{it.kategorie_2 || 'Nezařazeno'}</span>
                                                        <span className="top-value">{formatCurrency(it.obrat_bez_dph)}</span>
                                                        <span className="top-count">({formatNumber(it.polozky)} položek)</span>
                                                    </div>
                                                ))}
                                                {channelDetail.kategorie_2_items && (
                                                    <div className="items-list">
                                                        <h6>Položky ({formatNumber(channelDetail.kategorie_2_count)}):</h6>
                                                        <ul>
                                                            {channelDetail.kategorie_2_items.map((it, i) => (
                                                                <li key={i}><code>{it.objednavka || '—'}</code> — {it.nazev}</li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                )}
                                            </div>
                                            <div className="detail-card" style={{cursor:'pointer'}}>
                                                <h5>🏆 Top produkty</h5>
                                                {filterShipping(channelDetail.top_produkty || []).slice(0,10).map((it, i) => (
                                                    <div key={i} className="top-item clickable" onClick={() => loadChannelItems('produkt', null, { kod: it.kod })}>
                                                        <span className="top-name">{it.nazev || it.kod}</span>
                                                        <span className="top-value">{formatNumber(it.celkem_kusu)} ks</span>
                                                        <span className="top-count">{formatCurrency(it.obrat_bez_dph)}</span>
                                                    </div>
                                                ))}
                                                {channelDetail.produkt_items && (
                                                    <div className="items-list">
                                                        <h6>Položky ({formatNumber(channelDetail.produkt_count)}):</h6>
                                                        <ul>
                                                            {channelDetail.produkt_items.map((it, i) => (
                                                                <li key={i}><code>{it.objednavka || '—'}</code> — {it.nazev}</li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}
                    {/* Meta informace */}
                    <div className="eshop-meta">
                        <p>
                            📊 Zobrazeno {formatNumber(data.meta.total_records || 0)} e‑shop záznamů
                            | ⏰ Aktualizováno: {data.meta?.generated_at ? new Date(data.meta.generated_at).toLocaleString('cs-CZ') : ''}
                            | 🗄️ Zdroj: {data.meta?.data_source || 'WEB_PRODEJE_ALL'}
                        </p>
                    </div>
                </>
            )}
            </div>
        </AnalyticsSectionWrapper>
    );
};

export default Eshop; 