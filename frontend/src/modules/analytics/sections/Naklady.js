import React, { useCallback, useEffect, useMemo, useState } from 'react';
import AnalyticsSectionWrapper from '../AnalyticsSectionWrapper';
import { financeAPI } from '../../../services/api';
import {
    buildInitialCelkovaFilters,
    formatFiltersPeriodLabel,
} from './celkovaPeriodUtils';
import { movementLabel } from '../../finance/financeUtils';
import './Naklady.css';

const formatCurrency = (value) => {
    const n = Number(value) || 0;
    return new Intl.NumberFormat('cs-CZ', {
        style: 'currency',
        currency: 'CZK',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(Math.round(n));
};

const stavRozdiluClass = (stav) => {
    if (stav === 'minus') return 'naklady-kpi--minus';
    if (stav === 'plus') return 'naklady-kpi--plus';
    return 'naklady-kpi--vyrovnano';
};

const rowKey = (kat) => (kat.id == null ? 'null' : String(kat.id));

const Naklady = () => {
    const [filters, setFilters] = useState(() => buildInitialCelkovaFilters());
    const [data, setData] = useState(null);
    const [kategorieList, setKategorieList] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [toast, setToast] = useState('');
    const [expanded, setExpanded] = useState({});
    const [draftKat, setDraftKat] = useState({});
    const [savingId, setSavingId] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const params = {
                start_date: filters.start_date,
                end_date: filters.end_date,
            };
            if (filters.prodejna_id) params.prodejna_id = filters.prodejna_id;
            const [analytika, kats] = await Promise.all([
                financeAPI.getNakladyAnalytika(params),
                financeAPI.getKategorie(),
            ]);
            setData(analytika);
            setKategorieList(Array.isArray(kats) ? kats : []);
            setDraftKat({});
        } catch (e) {
            setError(e.response?.data?.error || e.message || 'Chyba načítání');
            setData(null);
        } finally {
            setLoading(false);
        }
    }, [filters.start_date, filters.end_date, filters.prodejna_id]);

    useEffect(() => {
        load();
    }, [load]);

    useEffect(() => {
        if (!toast) return undefined;
        const t = setTimeout(() => setToast(''), 4000);
        return () => clearTimeout(t);
    }, [toast]);

    const polozkyByKat = useMemo(() => {
        const map = {};
        (data?.polozky || []).forEach((p) => {
            const key = p.kategorie_id == null ? 'null' : String(p.kategorie_id);
            if (!map[key]) map[key] = [];
            map[key].push(p);
        });
        return map;
    }, [data]);

    const toggleRow = (key) => {
        setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));
    };

    const handleSaveKategorie = async (polozka) => {
        const selected = draftKat[polozka.id];
        const nextId = selected === undefined
            ? (polozka.kategorie_id || '')
            : selected;
        if (!nextId) {
            setToast('Vyberte kategorii.');
            return;
        }
        setSavingId(polozka.id);
        try {
            const res = await financeAPI.updateNaklad(polozka.id, {
                kategorie_id: Number(nextId),
                zaradit: true,
            });
            if (res?.pravidlo_created || res?.pravidlo_updated) {
                setToast('Pravidlo uloženo pro další podobné náklady');
            } else {
                setToast('Kategorie uložena.');
            }
            await load();
        } catch (err) {
            setToast(err.response?.data?.error || 'Uložení selhalo');
        } finally {
            setSavingId(null);
        }
    };

    const setThisMonth = () => {
        setFilters(buildInitialCelkovaFilters());
    };

    const setPrevMonth = () => {
        setFilters(buildInitialCelkovaFilters('prevMonth'));
    };

    return (
        <AnalyticsSectionWrapper>
            <div className="naklady-analytika">
                <div className="section-filters naklady-filters">
                    <div className="filter-group">
                        <label htmlFor="naklady-start">Od</label>
                        <input
                            id="naklady-start"
                            type="date"
                            value={filters.start_date || ''}
                            onChange={(e) => setFilters((f) => ({
                                ...f,
                                period: 'custom',
                                start_date: e.target.value,
                            }))}
                        />
                    </div>
                    <div className="filter-group">
                        <label htmlFor="naklady-end">Do</label>
                        <input
                            id="naklady-end"
                            type="date"
                            value={filters.end_date || ''}
                            onChange={(e) => setFilters((f) => ({
                                ...f,
                                period: 'custom',
                                end_date: e.target.value,
                            }))}
                        />
                    </div>
                    <div className="naklady-filter-actions">
                        <button type="button" className="toggle-btn" onClick={setThisMonth}>
                            Tento měsíc
                        </button>
                        <button type="button" className="toggle-btn" onClick={setPrevMonth}>
                            Minulý měsíc
                        </button>
                        <button type="button" className="refresh-btn" onClick={load} disabled={loading}>
                            Obnovit
                        </button>
                    </div>
                    <p className="naklady-period-label">{formatFiltersPeriodLabel(filters)}</p>
                </div>

                {toast && <p className="naklady-toast" role="status">{toast}</p>}
                {loading && <p className="naklady-loading">Načítám…</p>}
                {error && <p className="naklady-error">{error}</p>}

                {!loading && data && (
                    <>
                        <div className="naklady-kpi-row celkova-cisla-metrics">
                            <div className="metric-card">
                                <div className="metric-content">
                                    <h3>Příjmy (s DPH)</h3>
                                    <p className="metric-value">{formatCurrency(data.prijmy_s_dph)}</p>
                                </div>
                            </div>
                            <div className="metric-card">
                                <div className="metric-content">
                                    <h3>Náklady (s DPH)</h3>
                                    <p className="metric-value">{formatCurrency(data.naklady_s_dph)}</p>
                                </div>
                            </div>
                            <div className={`metric-card ${stavRozdiluClass(data.stav_rozdilu)}`}>
                                <div className="metric-content">
                                    <h3>Rozdíl</h3>
                                    <p className="metric-value">{formatCurrency(data.rozdil)}</p>
                                </div>
                            </div>
                        </div>

                        <div className="naklady-table-wrap">
                            <table className="naklady-table">
                                <thead>
                                    <tr>
                                        <th style={{ width: '2rem' }} />
                                        <th>Kategorie</th>
                                        <th>Počet</th>
                                        <th>Suma</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(data.kategorie || []).map((kat) => {
                                        const key = rowKey(kat);
                                        const open = !!expanded[key];
                                        const rows = polozkyByKat[key] || [];
                                        return (
                                            <React.Fragment key={key}>
                                                <tr
                                                    className="naklady-kat-row"
                                                    onClick={() => toggleRow(key)}
                                                >
                                                    <td className="naklady-expand">{open ? '▾' : '▸'}</td>
                                                    <td>{kat.nazev}</td>
                                                    <td>{kat.pocet}</td>
                                                    <td>{formatCurrency(kat.suma)}</td>
                                                </tr>
                                                {open && rows.map((p) => {
                                                    const current = draftKat[p.id] !== undefined
                                                        ? draftKat[p.id]
                                                        : (p.kategorie_id ? String(p.kategorie_id) : '');
                                                    const dirty = draftKat[p.id] !== undefined
                                                        && String(draftKat[p.id]) !== String(p.kategorie_id || '');
                                                    return (
                                                        <tr key={p.id} className="naklady-detail-row">
                                                            <td />
                                                            <td colSpan={3}>
                                                                <div className="naklady-detail">
                                                                    <span className="naklady-detail__meta">
                                                                        {p.datum} · {formatCurrency(p.castka)}
                                                                        {p.pokladna_label
                                                                            ? ` · kasa ${p.pokladna_label}`
                                                                            : ` · ${p.zdroj}`}
                                                                    </span>
                                                                    <span className="naklady-detail__popis">
                                                                        {movementLabel(p)}
                                                                    </span>
                                                                    <div className="naklady-detail__edit">
                                                                        <select
                                                                            value={current}
                                                                            onChange={(e) => setDraftKat((d) => ({
                                                                                ...d,
                                                                                [p.id]: e.target.value,
                                                                            }))}
                                                                            disabled={savingId === p.id}
                                                                        >
                                                                            <option value="">— kategorie —</option>
                                                                            {kategorieList.map((k) => (
                                                                                <option key={k.id} value={k.id}>
                                                                                    {k.nazev}
                                                                                </option>
                                                                            ))}
                                                                        </select>
                                                                        <button
                                                                            type="button"
                                                                            disabled={!dirty || savingId === p.id}
                                                                            onClick={() => handleSaveKategorie(p)}
                                                                        >
                                                                            Uložit
                                                                        </button>
                                                                    </div>
                                                                </div>
                                                            </td>
                                                        </tr>
                                                    );
                                                })}
                                                {open && rows.length === 0 && (
                                                    <tr className="naklady-detail-row">
                                                        <td />
                                                        <td colSpan={3}>Žádné položky</td>
                                                    </tr>
                                                )}
                                            </React.Fragment>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </>
                )}
            </div>
        </AnalyticsSectionWrapper>
    );
};

export default Naklady;
