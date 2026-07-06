import React, { useCallback, useEffect, useState } from 'react';
import { analyticsGet } from '../../../utils/analyticsRequest';
import AnalyticsSectionWrapper from '../AnalyticsSectionWrapper';
import AnalyticsPeriodFilterPanel from '../../../components/analytics/AnalyticsPeriodFilterPanel';
import { computeQuickRange, detectQuickRangePreset } from '../../../utils/analyticsQuickRange';
import api from '../../../services/api';
import './ZasilkovnaKonverze.css';

const fmtPct = (v) => (v == null ? '—' : `${Number(v).toFixed(1)} %`);
const fmtNum = (v) => new Intl.NumberFormat('cs-CZ').format(v || 0);

const ZasilkovnaKonverzeView = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [data, setData] = useState(null);
    const [stores, setStores] = useState([]);

    const [filters, setFilters] = useState(() => {
        const now = new Date();
        const start = new Date(now.getFullYear(), now.getMonth(), 1);
        const fmt = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
        return {
            period: 'custom',
            start_date: fmt(start),
            end_date: fmt(now),
            selected_month: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`,
            prodejna_id: '',
        };
    });
    const [dateError, setDateError] = useState('');
    const [quickKey, setQuickKey] = useState('thisMonth');

    useEffect(() => {
        api.get('/stores/').then((res) => {
            const list = res.data?.results || res.data || [];
            setStores(Array.isArray(list) ? list : []);
        }).catch(() => {});
    }, []);

    const loadData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const params = new URLSearchParams();
            if (filters.period === 'monthly_select' && filters.selected_month) {
                const [year, month] = filters.selected_month.split('-');
                const startDate = new Date(year, month - 1, 1);
                const endDate = new Date(year, month, 0);
                const fmt = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
                params.append('date_from', fmt(startDate));
                params.append('date_to', fmt(endDate));
            } else {
                params.append('date_from', filters.start_date);
                params.append('date_to', filters.end_date);
            }
            if (filters.prodejna_id) params.append('prodejna_id', filters.prodejna_id);

            const json = await analyticsGet('zasilkovna-konverze/', params);
            if (!json.success) throw new Error(json.error || 'Chyba načítání');
            setData(json);
        } catch (e) {
            setError(e.message);
            setData(null);
        } finally {
            setLoading(false);
        }
    }, [filters]);

    useEffect(() => {
        if ((filters.period === 'custom' && filters.start_date && filters.end_date)
            || (filters.period === 'monthly_select' && filters.selected_month)) {
            loadData();
        }
    }, [filters, loadData]);

    const applyDateRange = ({ start_date, end_date, preset }) => {
        setDateError('');
        setFilters((prev) => ({ ...prev, period: 'custom', start_date, end_date }));
        setQuickKey(preset || detectQuickRangePreset(start_date, end_date));
    };

    const handlePeriodChange = ({ type, month }) => {
        if (type === 'custom') {
            setFilters((prev) => ({ ...prev, period: 'custom' }));
            setQuickKey('custom');
        } else if (type === 'month') {
            setFilters((prev) => ({
                ...prev,
                period: 'monthly_select',
                selected_month: month,
                start_date: '',
                end_date: '',
            }));
            setDateError('');
        }
    };

    const handleQuickPreset = (id) => {
        const range = computeQuickRange(id);
        if (!range) return;
        applyDateRange({ ...range, preset: id });
    };

    const summary = data?.summary || {};

    return (
        <AnalyticsSectionWrapper>
            <AnalyticsPeriodFilterPanel
                className="zk-filters"
                filters={filters}
                quickKey={quickKey}
                onPeriodChange={handlePeriodChange}
                onDateApply={(range) => applyDateRange({ ...range, preset: 'custom' })}
                onQuickPreset={handleQuickPreset}
                onRefresh={loadData}
                onDateErrorChange={setDateError}
                loading={loading}
                dateError={dateError}
            >
                <div className="filter-group">
                    <label>Prodejna:</label>
                    <select
                        value={filters.prodejna_id}
                        onChange={(e) => setFilters((f) => ({ ...f, prodejna_id: e.target.value }))}
                    >
                        <option value="">Všechny</option>
                        {stores.map((s) => (
                            <option key={s.id} value={s.id}>{s.nazev}</option>
                        ))}
                    </select>
                </div>
            </AnalyticsPeriodFilterPanel>

            {loading && <div className="zk-loading">Načítám…</div>}
            {error && <div className="zk-error">{error}</div>}

            {!loading && !error && data && (
                <>
                    <div className="zk-kpi-grid">
                        <div className="zk-kpi">
                            <span className="zk-kpi-label">Návštěvy balíků</span>
                            <strong>{fmtNum(summary.navstevy_baliku)}</strong>
                            <small>
                                vydané {fmtNum(summary.navstevy_vydane)}
                                · příjem {fmtNum(summary.navstevy_podani)}
                                · C2C {fmtNum(summary.navstevy_c2c)}
                            </small>
                        </div>
                        <div className="zk-kpi">
                            <span className="zk-kpi-label">Prodeje Zásilkovna</span>
                            <strong>{fmtNum(summary.prodeje_z_cislem)}</strong>
                            <small>
                                Z+číslo v poznámce (sleva není nutná)
                                · Packeta: {fmtNum(summary.prodeje_propojene)}
                                · jen Z: {fmtNum(summary.prodeje_z_bez_cisla)}
                                · sleva bez balíku: {fmtNum(summary.prodeje_sleva_fallback)}
                            </small>
                        </div>
                        <div className="zk-kpi">
                            <span className="zk-kpi-label">Konverze balík → nákup</span>
                            <strong>{fmtPct(summary.konverze_pct)}</strong>
                            <small>
                                Packeta stejný den: {fmtPct(summary.konverze_packeta_pct)}
                                · běžní zákazníci: {fmtNum(summary.navstevy_bezni)} účtenek
                            </small>
                        </div>
                        <div className="zk-kpi">
                            <span className="zk-kpi-label">Bez potvrzení Packeta</span>
                            <strong>{fmtNum(summary.neplatne_z)}</strong>
                            <small>Z+číslo v poznámce, balík v provizi stejný den nenalezen</small>
                        </div>
                    </div>

                    <div className="zk-panels">
                        <div className="zk-panels-col zk-panels-col--side">
                            <section className="zk-panel">
                                <h3>Konverze podle typu zásilky</h3>
                            <table className="zk-table">
                                <thead>
                                    <tr>
                                        <th>Typ balíku</th>
                                        <th>Skupina</th>
                                        <th>Návštěvy</th>
                                        <th>Prodeje</th>
                                        <th>Konverze</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(data.po_typu || []).map((row) => (
                                        <tr key={row.typ_provize}>
                                            <td>{row.typ_baliku || row.typ_provize}</td>
                                            <td>
                                                {row.typ_kategorie === 'vydane_dobirka'
                                                    ? 'vydané (dobírka)'
                                                    : row.typ_skupina === 'vydane'
                                                        ? 'vydané'
                                                        : row.typ_skupina === 'prijate_c2c'
                                                            ? 'C2C'
                                                            : row.typ_skupina === 'prijate'
                                                                ? 'příjem'
                                                                : '—'}
                                            </td>
                                            <td>{fmtNum(row.navstevy)}</td>
                                            <td>{fmtNum(row.prodeje)}</td>
                                            <td>{fmtPct(row.konverze_pct)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </section>

                            <section className="zk-panel">
                                <h3>Prodejny</h3>
                            <table className="zk-table">
                                <thead>
                                    <tr>
                                        <th>Prodejna</th>
                                        <th>Balíky</th>
                                        <th>Prodeje</th>
                                        <th>Konverze</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(data.po_prodejne || []).map((row) => (
                                        <tr key={row.id_prodejny}>
                                            <td>{row.prodejna}</td>
                                            <td>{fmtNum(row.navstevy)}</td>
                                            <td>{fmtNum(row.prodeje)}</td>
                                            <td>{fmtPct(row.konverze_pct)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </section>
                        </div>

                        <section className="zk-panel zk-panel--prodejci">
                            <h3>Prodejci</h3>
                            <table className="zk-table">
                                <thead>
                                    <tr>
                                        <th>Prodejce</th>
                                        <th>Balíky zprac.</th>
                                        <th>Prodeje</th>
                                        <th>Konverze</th>
                                        <th>Z bez čísla</th>
                                        <th>Sleva bez balíku</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(data.prodejci || []).length === 0 && (
                                        <tr><td colSpan={6}>Zatím žádná data – import Packeta + směny prodejce</td></tr>
                                    )}
                                    {(data.prodejci || []).map((row) => (
                                        <tr key={row.id_prodejce}>
                                            <td>{row.prodejce}</td>
                                            <td>{fmtNum(row.zasilkovna_baliku)}</td>
                                            <td>{fmtNum(row.zasilkovna_prodeje)}</td>
                                            <td>{fmtPct(row.zasilkovna_konverze_pct)}</td>
                                            <td>{fmtNum(row.zasilkovna_z_bez_cisla)}</td>
                                            <td>{fmtNum(row.zasilkovna_sleva_bez_baliku)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </section>
                    </div>

                    <section className="zk-panel zk-panel--wide">
                        <h3>Prodeje Zásilkovna (Z+číslo v poznámce)</h3>
                        {(data.detail || []).length === 0 ? (
                            <p className="zk-empty">
                                Žádný doklad se Z+číslem v poznámce.
                                {summary.prodeje_sleva_fallback > 0 && (
                                    <> Dokladů se slevou zasilkovna20 (bez čísla balíku): {fmtNum(summary.prodeje_sleva_fallback)}.</>
                                )}
                            </p>
                        ) : (
                            <table className="zk-table zk-table--compact">
                                <thead>
                                    <tr>
                                        <th>Datum</th>
                                        <th>Prodejce</th>
                                        <th>Doklad</th>
                                        <th>Zásilka</th>
                                        <th>Typ balíku</th>
                                        <th>Packeta</th>
                                        <th>Zdroj</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.detail.map((row) => (
                                        <tr key={`${row.doklad}-${row.zasilka}`}>
                                            <td>{row.datum_prodeje}</td>
                                            <td>{row.prodejce || '—'}</td>
                                            <td>{row.doklad}</td>
                                            <td>{row.zasilka}</td>
                                            <td>
                                                {row.typ_baliku || '—'}
                                                {row.typ_inferovano ? ' (odhad)' : ''}
                                            </td>
                                            <td>{row.packeta_nalezeno ? 'ano' : 'ne'}</td>
                                            <td>{row.match_source === 'poznamka' ? 'Z v poznámce' : row.match_source}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </section>

                    {(data.chybi_propojeni || []).length > 0 && (
                        <section className="zk-panel zk-panel--wide">
                            <h3>Z bez párování na balík</h3>
                            <p className="zk-hint">Jen „Z“ v poznámce bez čísla – nepočítá se jako prodej, dokud není párování na zásilku.</p>
                            <table className="zk-table zk-table--compact">
                                <thead>
                                    <tr>
                                        <th>Datum</th>
                                        <th>Prodejce</th>
                                        <th>Doklad</th>
                                        <th>Typ</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.chybi_propojeni.map((row) => (
                                        <tr key={row.doklad}>
                                            <td>{row.datum_prodeje}</td>
                                            <td>{row.prodejce || '—'}</td>
                                            <td>{row.doklad}</td>
                                            <td>{row.z_marker ? 'Z bez čísla' : (row.zasilka || '—')}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </section>
                    )}

                    {(data.sleva_bez_baliku || []).length > 0 && (
                        <section className="zk-panel zk-panel--wide">
                            <h3>Sleva Zásilkovna bez balíku</h3>
                            <p className="zk-hint">Řádek SLEVA „ZASILKOVNA ZASILKOVNA20“ bez Z / čísla balíku v poznámce – proti pravidlům.</p>
                            <table className="zk-table zk-table--compact">
                                <thead>
                                    <tr>
                                        <th>Datum</th>
                                        <th>Prodejce</th>
                                        <th>Doklad</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.sleva_bez_baliku.map((row) => (
                                        <tr key={row.doklad}>
                                            <td>{row.datum_prodeje}</td>
                                            <td>{row.prodejce || '—'}</td>
                                            <td>{row.doklad}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </section>
                    )}
                </>
            )}
        </AnalyticsSectionWrapper>
    );
};

export default ZasilkovnaKonverzeView;
