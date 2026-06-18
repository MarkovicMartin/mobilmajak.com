import React, { useEffect, useState } from 'react';
import { analyticsGet } from '../../../utils/analyticsRequest';

/**
 * @param {'collapsible' | 'page'} variant – page = vždy otevřené (modul Úkoly admin)
 */
const PolozkyTasksPanel = ({
    filters,
    defaultOpen = false,
    variant = 'collapsible',
    onLoadingChange,
}) => {
    const isPage = variant === 'page';
    const [open, setOpen] = useState(isPage || defaultOpen);
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const active = isPage || open;

    useEffect(() => {
        if (!active) return undefined;
        let cancelled = false;
        const load = async () => {
            setLoading(true);
            onLoadingChange?.(true);
            setError(null);
            try {
                const p = new URLSearchParams();
                Object.keys(filters || {}).forEach((k) => {
                    if (filters[k] != null && filters[k] !== '') p.append(k, filters[k]);
                });
                const json = await analyticsGet('web-prodeje/polozky/tasks-workload/', p);
                if (!json.success) throw new Error(json.error || 'Chyba');
                if (!cancelled) setData(json);
            } catch (e) {
                if (!cancelled) {
                    setError(e.message);
                    setData(null);
                }
            } finally {
                if (!cancelled) {
                    setLoading(false);
                    onLoadingChange?.(false);
                }
            }
        };
        load();
        return () => { cancelled = true; };
    }, [active, JSON.stringify(filters), onLoadingChange]);

    const body = (
        <div className={isPage ? 'polozky-tasks-panel__body polozky-tasks-panel__body--page' : 'polozky-tasks-panel__body'}>
            {loading && <p>Načítám…</p>}
            {error && <p className="celkova-cisla-error">{error}</p>}
            {data && !loading && (
                <>
                    <p className="polozky-tasks-hint" title={data.poznamka_proxy}>
                        {data.poznamka_proxy}
                    </p>
                    <div className="polozky-tasks-sla">
                        <span>Hotovo: {data.sla?.pocet_hotovo ?? 0}</span>
                        <span>Průměr do hotovo: {data.sla?.prumer_hodin_do_hotovo ?? '—'} h</span>
                        <span>
                            Včas:{' '}
                            {data.sla?.podil_vcas != null
                                ? `${Math.round(data.sla.podil_vcas * 100)} %`
                                : '—'}
                        </span>
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
    );

    if (isPage) {
        return (
            <div className="polozky-tasks-panel polozky-tasks-panel--page">
                <h2 className="polozky-tasks-panel__title">Vytížení při úkolech</h2>
                {body}
            </div>
        );
    }

    return (
        <div className="polozky-tasks-panel">
            <button
                type="button"
                className="polozky-tasks-panel__toggle"
                onClick={() => setOpen((v) => !v)}
            >
                {open ? '▼' : '▶'} Úkoly a vytížení
            </button>
            {open && body}
        </div>
    );
};

export default PolozkyTasksPanel;
