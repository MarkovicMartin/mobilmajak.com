import React, { useState, useEffect } from 'react';
import AnalyticsSectionWrapper from '../AnalyticsSectionWrapper';
import CustomDropdown from '../../../components/CustomDropdown';
import './Servis.css';

const Servis = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [detailOpen, setDetailOpen] = useState(false);
    const [detailLoading, setDetailLoading] = useState(false);
    const [detailError, setDetailError] = useState(null);
    const [detailType, setDetailType] = useState(null); // 'prodejna' | 'technik' | 'typ_servisu'
    const [selectedEntity, setSelectedEntity] = useState(null); // prodejna obj nebo {technik} nebo {typ_servisu}
    const [prodejnaDetail, setProdejnaDetail] = useState(null);
    
    // Filtry
    const [filters, setFilters] = useState(()=>{
        const now = new Date();
        const fmt = (d)=> `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
        return {
            period: 'custom',
            start_date: fmt(new Date(now.getFullYear(), now.getMonth(), 1)),
            end_date: fmt(now),
            prodejna_id: ''
        };
    });
    const [dateError, setDateError] = useState('');

    // Načtení dat z API
    const fetchData = async () => {
        setLoading(true);
        setError(null);
        
        try {
            const params = new URLSearchParams();
            Object.keys(filters).forEach(key => {
                if (filters[key] !== undefined && filters[key] !== null && filters[key] !== '') {
                    params.append(key, filters[key]);
                }
            });
            
            const response = await fetch(`/api/analytics/servis/?${params}`, {
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
            console.error('Chyba při načítání servisních dat:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    // Načtení detailu prodejny (popup)
    const openProdejnaDetail = async (prodejna) => {
        setDetailType('prodejna');
        setSelectedEntity(prodejna);
        setDetailOpen(true);
        setDetailLoading(true);
        setDetailError(null);
        setProdejnaDetail(null);

        try {
            const params = new URLSearchParams();
            // stejné filtry jako hlavní dotaz
            Object.keys(filters).forEach(key => {
                if (filters[key] !== undefined && filters[key] !== null && filters[key] !== '') {
                    params.append(key, filters[key]);
                }
            });
            if (prodejna.id_prodejny) params.set('prodejna_id', prodejna.id_prodejny);
            if (prodejna.stredisko) params.set('stredisko', prodejna.stredisko);

            const response = await fetch(`/api/analytics/servis/prodejna-detail/?${params}`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include'
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const result = await response.json();
            if (!result.success) throw new Error(result.error || 'Chyba detailu prodejny');
            setProdejnaDetail(result.detail.breakdown);
        } catch (e) {
            setDetailError(e.message);
        } finally {
            setDetailLoading(false);
        }
    };

    const openTechnikDetail = async (technikName) => {
        setDetailType('technik');
        setSelectedEntity({ technik: technikName });
        setDetailOpen(true);
        setDetailLoading(true);
        setDetailError(null);
        setProdejnaDetail(null);

        try {
            const params = new URLSearchParams();
            Object.keys(filters).forEach(key => {
                if (filters[key] !== undefined && filters[key] !== null && filters[key] !== '') {
                    params.append(key, filters[key]);
                }
            });
            params.set('technik', technikName);
            const response = await fetch(`/api/analytics/servis/technik-detail/?${params}`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include'
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const result = await response.json();
            if (!result.success) throw new Error(result.error || 'Chyba detailu technika');
            setProdejnaDetail(result.detail.breakdown);
        } catch (e) {
            setDetailError(e.message);
        } finally {
            setDetailLoading(false);
        }
    };

    const openTypServisu = async (typServisu) => {
        setDetailType('typ_servisu');
        setSelectedEntity({ typ_servisu: typServisu.kategorie_1, nazev: typServisu.kategorie_1, obrat: typServisu.obrat, polozky: typServisu.polozky });
        setDetailOpen(true);
        setDetailLoading(true);
        setDetailError(null);
        setProdejnaDetail(null);

        try {
            const params = new URLSearchParams();
            Object.keys(filters).forEach(key => {
                if (filters[key] !== undefined && filters[key] !== null && filters[key] !== '') {
                    params.append(key, filters[key]);
                }
            });
            params.set('typ_servisu', typServisu.kategorie_1);
            params.set('limit', '200');

            const response = await fetch(`/api/analytics/servis/typ-items/?${params}`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include'
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const result = await response.json();
            if (!result.success) throw new Error(result.error || 'Chyba načítání položek typu servisu');
            
            // Uložím seznam položek do stavu
            setProdejnaDetail({ typ_servisu_items: result.items, typ_servisu_count: result.count });
        } catch (e) {
            setDetailError(e.message);
        } finally {
            setDetailLoading(false);
        }
    };

    const closeDetail = () => {
        setDetailOpen(false);
        setSelectedEntity(null);
        setDetailType(null);
        setProdejnaDetail(null);
        setDetailError(null);
    };

    // Načtení položek pro segment (sluzby|prislusenstvi|prace)
    const loadSegmentItems = async (segment) => {
        if (!selectedEntity) return;
        setDetailLoading(true);
        setDetailError(null);
        try {
            const params = new URLSearchParams();
            Object.keys(filters).forEach(key => {
                if (filters[key] !== undefined && filters[key] !== null && filters[key] !== '') {
                    params.append(key, filters[key]);
                }
            });
            let endpoint = '';
            if (detailType === 'prodejna') {
                if (selectedEntity.id_prodejny) params.set('prodejna_id', selectedEntity.id_prodejny);
                if (selectedEntity.stredisko) params.set('stredisko', selectedEntity.stredisko);
                endpoint = '/api/analytics/servis/prodejna-items/';
            } else {
                params.set('technik', selectedEntity.technik);
                endpoint = '/api/analytics/servis/technik-items/';
            }
            params.set('segment', segment);
            params.set('limit', '200');

            const response = await fetch(`${endpoint}?${params}`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include'
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const result = await response.json();
            if (!result.success) throw new Error(result.error || 'Chyba načítání položek');
            setProdejnaDetail(prev => ({ ...prev, [`${segment}_items`]: result.items, [`${segment}_count`]: result.count }));
        } catch (e) {
            setDetailError(e.message);
        } finally {
            setDetailLoading(false);
        }
    };

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

    // ===== Helpers – stejné UX jako v Celková čísla =====
    const isValidISODate = (str) => {
        if (!/^\d{4}-\d{2}-\d{2}$/.test(str)) return false;
        const [y,m,d] = str.split('-').map(Number);
        const dt = new Date(y, m-1, d);
        return dt.getFullYear()===y && dt.getMonth()===m-1 && dt.getDate()===d;
    };
    const setQuickRange = (type) => {
        const now = new Date();
        const fmt = (d)=> `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
        let from, to;
        if (type==='today') {
            from = new Date(now.getFullYear(), now.getMonth(), now.getDate());
            to = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        } else if (type==='yesterday') {
            const y = new Date(now); y.setDate(now.getDate()-1);
            from = new Date(y.getFullYear(), y.getMonth(), y.getDate());
            to = new Date(y.getFullYear(), y.getMonth(), y.getDate());
        } else if (type==='thisWeek') {
            const day = (now.getDay()+6)%7; // pondělí=0
            from = new Date(now.getFullYear(), now.getMonth(), now.getDate()-day);
            to = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        } else if (type==='thisMonth') {
            from = new Date(now.getFullYear(), now.getMonth(), 1);
            to = new Date(now.getFullYear(), now.getMonth()+1, 0);
        } else if (type==='prevMonth') {
            from = new Date(now.getFullYear(), now.getMonth()-1, 1);
            to = new Date(now.getFullYear(), now.getMonth(), 0);
        }
        setDateError('');
        setFilters(prev => ({...prev, period:'custom', start_date: fmt(from), end_date: fmt(to)}));
    };
    const onDateChange = (name, value) => {
        if (!isValidISODate(value)) { setDateError('Neplatné datum'); return; }
        setDateError('');
        setFilters(prev=>{
            const next = {...prev, [name]: value};
            if (next.start_date && next.end_date && new Date(next.start_date)>new Date(next.end_date)) {
                [next.start_date, next.end_date] = [next.end_date, next.start_date];
            }
            return next;
        });
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

    if (loading) {
        return (
            <div className="servis-loading">
                <div className="loading-spinner"></div>
                <p>Načítám servisní data...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="servis-error">
                <h3>Chyba při načítání dat</h3>
                <p>{error}</p>
                <button onClick={fetchData} className="retry-button">
                    Zkusit znovu
                </button>
            </div>
        );
    }

    return (
        <AnalyticsSectionWrapper title="Servis analytika" icon="🔧">
            <div className="servis">

            {/* Filtry */}
            <div className="servis-filters">
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
                            
                            const currentValue = filters.period === 'monthly_select' && filters.selected_month ? 
                                `month:${filters.selected_month}` : 'custom';
                            
                            return (
                                <CustomDropdown
                                    options={opts}
                                    value={currentValue}
                                    placeholder="Vyberte období"
                                    onChange={(selectedValue) => {
                                        if (selectedValue === 'custom') {
                                            // Nastavit na custom režim
                                            setFilters(prev => ({...prev, period: 'custom'}));
                                            setDateError('');
                                        } else if (selectedValue.startsWith('month:')) {
                                            const ym = selectedValue.split(':')[1];
                                            // Nastavíme start_date a end_date podle vybraného měsíce
                                            const [year, month] = ym.split('-');
                                            const startDate = `${year}-${month}-01`;
                                            // Opraveno: explicitní výpočet posledního dne měsíce (31 dní pro leden, atd.)
                                            const monthIndex = parseInt(month) - 1; // převedeme na 0-based index (leden=0)
                                            const lastDay = new Date(parseInt(year), monthIndex + 1, 0).getDate(); // poslední den měsíce
                                            const endDate = `${year}-${month}-${String(lastDay).padStart(2, '0')}`;
                                            const updatedFilters = {...filters, period: 'monthly_select', selected_month: ym, start_date: startDate, end_date: endDate};
                                            setFilters(updatedFilters);
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
                                    value={filters.start_date}
                                    max={filters.end_date||undefined}
                                    onChange={(e) => onDateChange('start_date', e.target.value)}
                                />
                            </div>
                            <div className="filter-group">
                                <label>Do:</label>
                                <input 
                                    type="date" 
                                    value={filters.end_date}
                                    min={filters.start_date||undefined}
                                    onChange={(e) => onDateChange('end_date', e.target.value)}
                                />
                            </div>
                        </>
                    )}

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

                    {/* Prodejna */}
                    <div className="filter-group">
                        <label>Prodejna:</label>
                        <select 
                            value={filters.prodejna_id} 
                            onChange={(e) => handleFilterChange('prodejna_id', e.target.value)}
                        >
                            <option value="">Všechny prodejny</option>
                            <option value="1">Globus</option>
                            <option value="2">Čepkov</option>
                            <option value="3">Přerov</option>
                            <option value="4">Šternberk</option>
                            <option value="5">Vsetín</option>
                        </select>
                    </div>

                    {/* Tlačítko obnovit */}
                    <button 
                        onClick={fetchData} 
                        disabled={loading || !!dateError}
                        className="refresh-btn"
                    >
                        🔄 Obnovit data
                    </button>
                </div>
                {dateError && <div className="servis-error" style={{marginTop:8}}>{dateError}</div>}
            </div>

            {data && (
                <>
                    {/* Medaile / odznaky */}
                    {data.awards && (
                        <div className="servis-metrics" style={{marginTop: 0}}>
                            <div className="metric-card" title="Nejlepší celkově (součet všeho)">
                                <div className="metric-icon">🥇</div>
                                <div className="metric-content">
                                    <h3>Nejlepší prodejco/technik</h3>
                                    <div className="metric-value">{data.awards.top_all?.technik || '—'}</div>
                                    <div className="metric-subtitle">Obrat bez DPH: {formatCurrency(data.awards.top_all?.obrat_bez_dph)}</div>
                                </div>
                            </div>
                            <div className="metric-card" title="Nejlepší servisní technik (služby + servisní práce)">
                                <div className="metric-icon">🛠️</div>
                                <div className="metric-content">
                                    <h3>Nejlepší servisní technik</h3>
                                    <div className="metric-value">{data.awards.top_service?.technik || '—'}</div>
                                    <div className="metric-subtitle">Servisní obrat: {formatCurrency(data.awards.top_service?.service_score)}</div>
                                </div>
                            </div>
                            <div className="metric-card" title="Nejlepší prodavač (mimo servis)">
                                <div className="metric-icon">🛍️</div>
                                <div className="metric-content">
                                    <h3>Nejlepší prodavač</h3>
                                    <div className="metric-value">{data.awards.top_seller?.technik || '—'}</div>
                                    <div className="metric-subtitle">Obrat mimo servis: {formatCurrency(data.awards.top_seller?.seller_score)}</div>
                                </div>
                            </div>
                        </div>
                    )}
                    {/* Hlavní metriky */}
                    <div className="servis-metrics">
                        <div className="metric-card">
                            <div className="metric-icon">💰</div>
                            <div className="metric-content">
                                <h3>Obrat ze servisu (bez DPH)</h3>
                                <div className="metric-value">{formatCurrency(data.aggregations.celkovy_obrat_bez_dph)}</div>
                            </div>
                        </div>

                        <div className="metric-card">
                            <div className="metric-icon">📈</div>
                            <div className="metric-content">
                                <h3>Marže v procentech</h3>
                                <div className="metric-value">{data.aggregations.marze_procenta}%</div>
                            </div>
                        </div>

                        <div className="metric-card">
                            <div className="metric-icon">💹</div>
                            <div className="metric-content">
                                <h3>Marže v korunách</h3>
                                <div className="metric-value">{formatCurrency(data.aggregations.marze_korun)}</div>
                            </div>
                        </div>

                        <div className="metric-card">
                            <div className="metric-icon">🔧</div>
                            <div className="metric-content">
                                <h3>Celkem servisních položek</h3>
                                <div className="metric-value">{formatNumber(data.aggregations.celkem_polozek)}</div>
                                <div className="metric-subtitle">kusů: {formatNumber(data.aggregations.celkem_kusu)}</div>
                            </div>
                        </div>

                        <div className="metric-card">
                            <div className="metric-icon">⚡</div>
                            <div className="metric-content">
                                <h3>Z toho čistě služby</h3>
                                <div className="metric-value">{formatNumber(data.ciste_sluzby.celkem_polozek)}</div>
                                <div className="metric-subtitle">obrat bez DPH: {formatCurrency(data.ciste_sluzby.celkovy_obrat_bez_dph)}</div>
                            </div>
                        </div>

                        <div className="metric-card">
                            <div className="metric-icon">📋</div>
                            <div className="metric-content">
                                <h3>Počet dokladů</h3>
                                <div className="metric-value">{formatNumber(data.aggregations.pocet_dokladu)}</div>
                                <div className="metric-subtitle">průměrný obrat bez DPH na objednávku: {formatCurrency(data.aggregations.prumerna_objednavka_bez_dph)}</div>
                            </div>
                        </div>
                    </div>

                    {/* Rozklad podle prodejen */}
                    <div className="servis-breakdown">
                        <h3>📈 Rozklad podle prodejen</h3>
                        <div className="breakdown-cards">
                            {data.breakdown.prodejny.map((prodejna, index) => (
                                <div key={index} className="breakdown-card clickable" onClick={() => openProdejnaDetail(prodejna)}>
                                    <h4>{prodejna.stredisko || `Prodejna ${prodejna.id_prodejny}`}</h4>
                                    <div className="breakdown-metrics">
                                        <div><strong>Obrat bez DPH:</strong> {formatCurrency(prodejna.obrat_bez_dph)}</div>
                                        <div><strong>Marže:</strong> {formatCurrency(prodejna.marze)}</div>
                                        <div className="click-hint">Klikni pro detailní rozpad</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Modal s detailem prodejny */}
                    {detailOpen && (
                        <div className="modal-overlay" onClick={closeDetail}>
                            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                                <div className="modal-header">
                                    <h4>
                                        {detailType === 'prodejna' ? 'Rozpad prodejny' : 
                                         detailType === 'technik' ? 'Rozpad technika' : 
                                         'Detail typu servisu'}: {
                                             detailType === 'prodejna' ? (selectedEntity?.stredisko || selectedEntity?.id_prodejny) : 
                                             detailType === 'technik' ? selectedEntity?.technik :
                                             selectedEntity?.nazev
                                         }
                                    </h4>
                                    <button className="modal-close" onClick={closeDetail}>✕</button>
                                </div>
                                <div className="modal-body">
                                    {detailLoading && <div className="modal-loading">Načítám…</div>}
                                    {detailError && <div className="modal-error">{detailError}</div>}
                                    {prodejnaDetail && detailType === 'typ_servisu' && (
                                        <div className="typ-servisu-detail">
                                            <div className="typ-servisu-summary">
                                                <h5>📊 Přehled typu servisu: {selectedEntity?.nazev}</h5>
                                                <div><strong>Celkový obrat bez DPH:</strong> {formatCurrency(selectedEntity?.obrat)}</div>
                                                <div><strong>Počet položek:</strong> {formatNumber(selectedEntity?.polozky)}</div>
                                            </div>
                                            {prodejnaDetail?.typ_servisu_items && (
                                                <div className="items-list">
                                                    <h6>Seznam položek ({formatNumber(prodejnaDetail.typ_servisu_count)}):</h6>
                                                    <ul>
                                                        {prodejnaDetail.typ_servisu_items.map((it, i) => (
                                                            <li key={i}>
                                                                {it.objednavka ? (
                                                                    <a 
                                                                        href={`https://www.mobilmajak.cz/admin/objednavky/objednavka-${it.objednavka}`}
                                                                        target="_blank"
                                                                        rel="noopener noreferrer"
                                                                        className="order-link"
                                                                    >
                                                                        <code>{it.objednavka}</code>
                                                                    </a>
                                                                ) : (
                                                                    <code>—</code>
                                                                )} — {it.nazev} 
                                                                {it.kod && <span style={{color: '#666'}}> ({it.kod})</span>}
                                                                {it.cena_ks_bez_dph && <span style={{color: '#28a745', marginLeft: '8px'}}>{formatCurrency(it.cena_ks_bez_dph * it.pocet_kusu)}</span>}
                                                                {it.stredisko && <span style={{color: '#6c757d', fontSize: '0.9em'}}> - {it.stredisko}</span>}
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                    {prodejnaDetail && detailType !== 'typ_servisu' && (
                                        <div className="detail-grid">
                                            <div className="detail-card" onClick={() => loadSegmentItems('sluzby')} style={{cursor:'pointer'}}>
                                                <h5>⚡ Služby</h5>
                                                <div><strong>Obrat bez DPH:</strong> {formatCurrency(prodejnaDetail.sluzby.obrat_bez_dph)}</div>
                                                <div><strong>Marže:</strong> {formatCurrency(prodejnaDetail.sluzby.marze)}</div>
                                                <div><strong>Položky:</strong> {formatNumber(prodejnaDetail.sluzby.polozky)}</div>
                                                <div><strong>Doklady:</strong> {formatNumber(prodejnaDetail.sluzby.doklady)}</div>
                                                {prodejnaDetail?.sluzby_items && (
                                                    <div className="items-list">
                                                        <h6>Položky ({formatNumber(prodejnaDetail.sluzby_count)}):</h6>
                                                        <ul>
                                                            {prodejnaDetail.sluzby_items.map((it, i) => (
                                                                <li key={i}>
                                                                    {it.objednavka ? (
                                                                        <a 
                                                                            href={`https://www.mobilmajak.cz/admin/objednavky/objednavka-${it.objednavka}`}
                                                                            target="_blank"
                                                                            rel="noopener noreferrer"
                                                                            className="order-link"
                                                                        >
                                                                            <code>{it.objednavka}</code>
                                                                        </a>
                                                                    ) : (
                                                                        <code>—</code>
                                                                    )} — {it.nazev}
                                                                </li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                )}
                                            </div>
                                            <div className="detail-card" onClick={() => loadSegmentItems('prislusenstvi')} style={{cursor:'pointer'}}>
                                                <h5>🧰 Příslušenství k servisu</h5>
                                                <div><strong>Obrat bez DPH:</strong> {formatCurrency(prodejnaDetail.prislusenstvi_k_servisu.obrat_bez_dph)}</div>
                                                <div><strong>Marže:</strong> {formatCurrency(prodejnaDetail.prislusenstvi_k_servisu.marze)}</div>
                                                <div><strong>Položky:</strong> {formatNumber(prodejnaDetail.prislusenstvi_k_servisu.polozky)}</div>
                                                <div><strong>Doklady:</strong> {formatNumber(prodejnaDetail.prislusenstvi_k_servisu.doklady)}</div>
                                                {prodejnaDetail?.prislusenstvi_items && (
                                                    <div className="items-list">
                                                        <h6>Položky ({formatNumber(prodejnaDetail.prislusenstvi_count)}):</h6>
                                                        <ul>
                                                            {prodejnaDetail.prislusenstvi_items.map((it, i) => (
                                                                <li key={i}>
                                                                    {it.objednavka ? (
                                                                        <a 
                                                                            href={`https://www.mobilmajak.cz/admin/objednavky/objednavka-${it.objednavka}`}
                                                                            target="_blank"
                                                                            rel="noopener noreferrer"
                                                                            className="order-link"
                                                                        >
                                                                            <code>{it.objednavka}</code>
                                                                        </a>
                                                                    ) : (
                                                                        <code>—</code>
                                                                    )} — {it.nazev}
                                                                </li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                )}
                                            </div>
                                            <div className="detail-card" onClick={() => loadSegmentItems('prace')} style={{cursor:'pointer'}}>
                                                <h5>🔧 Servisní práce</h5>
                                                <div><strong>Obrat bez DPH:</strong> {formatCurrency(prodejnaDetail.servisni_prace.obrat_bez_dph)}</div>
                                                <div><strong>Marže:</strong> {formatCurrency(prodejnaDetail.servisni_prace.marze)}</div>
                                                <div><strong>Položky:</strong> {formatNumber(prodejnaDetail.servisni_prace.polozky)}</div>
                                                <div><strong>Doklady:</strong> {formatNumber(prodejnaDetail.servisni_prace.doklady)}</div>
                                                {prodejnaDetail?.prace_items && (
                                                    <div className="items-list">
                                                        <h6>Položky ({formatNumber(prodejnaDetail.prace_count)}):</h6>
                                                        <ul>
                                                            {prodejnaDetail.prace_items.map((it, i) => (
                                                                <li key={i}>
                                                                    {it.objednavka ? (
                                                                        <a 
                                                                            href={`https://www.mobilmajak.cz/admin/objednavky/objednavka-${it.objednavka}`}
                                                                            target="_blank"
                                                                            rel="noopener noreferrer"
                                                                            className="order-link"
                                                                        >
                                                                            <code>{it.objednavka}</code>
                                                                        </a>
                                                                    ) : (
                                                                        <code>—</code>
                                                                    )} — {it.nazev}
                                                                </li>
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

                    {/* Rozklad podle servisních techniků */}
                    <div className="servis-breakdown">
                        <h3>🧑‍🔧 Servisní technici</h3>
                        {data.breakdown && data.breakdown.technici && data.breakdown.technici.length > 0 ? (
                            <div className="breakdown-cards">
                                {data.breakdown.technici.map((tech, index) => (
                                    <div key={index} className="breakdown-card clickable" onClick={() => openTechnikDetail(tech.technik)}>
                                        <h4>{tech.technik || 'Neznámý technik'}</h4>
                                        <div className="breakdown-metrics">
                                            <div><strong>Obrat bez DPH:</strong> {formatCurrency(tech.obrat_bez_dph)}</div>
                                            <div><strong>Marže:</strong> {formatCurrency(tech.marze)}</div>
                                            <div className="click-hint">Klikni pro detailní rozpad</div>

                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="breakdown-empty">
                                <p><strong>Žádná data k zobrazení.</strong> V tomto období nejsou u servisních záznamů vyplněni technici.</p>
                                <p>Tip: Zkus jiné období nebo konkrétní prodejnu. Data se berou z tabulky <code>WEB_PRODEJE_ALL</code> (pole <code>Technik</code>).</p>
                            </div>
                        )}
                    </div>

                    {/* Typy servisu */}
                    <div className="servis-top">
                        <h3>🔧 Typy servisu</h3>
                        <div className="top-list">
                            {data.breakdown.typy_servisu.map((typ, index) => (
                                <div key={index} className="top-item clickable" onClick={() => openTypServisu(typ)}>
                                    <div className="top-rank">{index + 1}</div>
                                    <div className="top-name">{typ.kategorie_1 || 'Neznámý typ'}</div>
                                    <div className="top-value">{formatCurrency(typ.obrat)}</div>
                                    <div className="top-count">{formatNumber(typ.polozky)} položek</div>
                                    <div className="click-hint">Klikni pro položky</div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Nejčastější servisní služby */}
                    <div className="servis-top">
                        <h3>🏆 Nejčastější servisní služby</h3>
                        <div className="top-list">
                            {data.breakdown.top_servisni_sluzby.map((sluzba, index) => (
                                <div key={index} className="top-item">
                                    <div className="top-rank">{index + 1}</div>
                                    <div className="top-name">
                                        <code>{sluzba.kod}</code> - {sluzba.nazev}
                                    </div>
                                    <div className="top-value">{formatNumber(sluzba.celkem_kusu)} kusů</div>
                                    <div className="top-count">{formatCurrency(sluzba.obrat)}</div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Analýza podle značek telefonů */}
                    {data.breakdown.znacky_telefonu.length > 0 && (
                        <div className="servis-top">
                            <h3>📱 Analýza podle značek telefonů</h3>
                            <div className="top-list">
                                {data.breakdown.znacky_telefonu.map((znacka, index) => (
                                    <div key={index} className="top-item">
                                        <div className="top-rank">{index + 1}</div>
                                        <div className="top-name">{znacka.kategorie_2}</div>
                                        <div className="top-value">{formatCurrency(znacka.obrat)}</div>
                                        <div className="top-count">{formatNumber(znacka.polozky)} položek</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Metadata */}
                    <div className="servis-meta">
                        <p>
                            <strong>Celkem záznamů:</strong> {data.meta.total_records} | 
                            <strong>Vygenerováno:</strong> {new Date(data.meta.generated_at).toLocaleString('cs-CZ')}
                        </p>
                    </div>
                </>
            )}
            </div>
        </AnalyticsSectionWrapper>
    );
};

export default Servis; 