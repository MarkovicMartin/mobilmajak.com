import React, { useEffect, useState } from 'react';
import { analyticsGet } from '../../../utils/analyticsRequest';

const PolozkyTasksPanel = ({ filters, defaultOpen = false }) => {
    const [open, setOpen] = useState(defaultOpen);
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!open) return;
        const load = async () => {
            setLoading(true);
            setError(null);
            try {
                const p = new URLSearchParams();
                Object.keys(filters || {}).forEach((k) => {
                    if (filters[k] != null && filters[k] !== '') p.append(k, filters[k]);
                });
                const json = await analyticsGet('web-prodeje/polozky/tasks-workload/', p);
                if (!json.success) throw new Error(json.error || 'Chyba');
                setData(json);
            } catch (e) {
                setError(e.message);
                setData(null);
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [open, JSON.stringify(filters)]);

    return (
        <div className="polozky-tasks-panel">
            <button
                type="button"
                className="polozky-tasks-panel__toggle"
                onClick={() => setOpen((v) => !v)}
            >
                {open ? '▼' : '▶'} Úkoly a vytížení
            </button>
            {open && (
                <div className="polozky-tasks-panel__body">
                    {loading && <p>Načítám…</p>}
                    {error && <p className="celkova-cisla-error">{error}</p>}
                    {data && (
                        <>
                            <p className="polozky-tasks-hint" title={data.poznamka_proxy}>
                                {data.poznamka_proxy}
                            </p>
                            <div className="polozky-tasks-sla">
                                <span>Hotovo: {data.sla?.pocet_hotovo ?? 0}</span>
                                <span>Průměr do hotovo: {data.sla?.prumer_hodin_do_hotovo ?? '—'} h</span>
                                <span>Včas: {data.sla?.podil_vcas != null ? `${Math.round(data.sla.podil_vcas * 100)} %` : '—'}</span>
                            </div>
                            <table className="polozky-tasks-table">
                                <thead>
                                    <tr>
                                        <th>Prodejce</th>
                                        <th>Úkolů</th>
                                        <th>Doklady při úkolech</th>
                                        <th title="Proxy vs průměr prodejny">Index vytížení</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(data.prodejci || []).map((row) => (
                                        <tr key={row.id_prodejce}>
                                            <td>{row.prodejce}</td>
                                            <td>{row.pocet_ukolu_hotovo}</td>
                                            <td>{row.doklady_pri_ukolech}</td>
                                            <td>{row.index_vytizeni ?? '—'}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </>
                    )}
                </div>
            )}
        </div>
    );
};

export default PolozkyTasksPanel;
