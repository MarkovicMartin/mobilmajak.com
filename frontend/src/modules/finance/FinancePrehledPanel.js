import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { financeAPI } from '../../services/api';
import FinanceZdrojFilter from './FinanceZdrojFilter';
import { movementLabel, zdrojMeta } from './financeUtils';

const formatCurrency = (value) => {
    const n = Number(value) || 0;
    return new Intl.NumberFormat('cs-CZ', {
        style: 'currency',
        currency: 'CZK',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(Math.round(n));
};

const STAV_FILTERS = [
    { id: 'vse', label: 'Vše' },
    { id: 'nezarazeno', label: 'Chybí zařazení' },
    { id: 'auto', label: 'Auto ✓' },
    { id: 'rucne', label: 'Ručně' },
    { id: 'ignorovat', label: 'Ignorovat' },
];

const stavBadge = (p) => {
    if (p.stav === 'ignorovat') return { cls: 'finance-badge--muted', text: 'ignorovat' };
    if (p.stav === 'nezarazeno') return { cls: 'finance-badge--warn', text: 'chybí' };
    if (p.zarazeno_automaticky) {
        return { cls: 'finance-badge--ok', text: p.auto_pravidlo || 'auto' };
    }
    if (p.stav === 'rucne') return { cls: 'finance-badge--manual', text: 'ručně' };
    return { cls: '', text: p.stav };
};

const FinancePrehledPanel = () => {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [stavFilter, setStavFilter] = useState('vse');
    const [filterZdroj, setFilterZdroj] = useState('');

    const load = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const rows = await financeAPI.getPrehled({
                stav: stavFilter,
                ...(filterZdroj ? { zdroj: filterZdroj } : {}),
            });
            setItems(Array.isArray(rows) ? rows : []);
        } catch (e) {
            setError(e.response?.data?.error || e.message || 'Chyba načítání');
        } finally {
            setLoading(false);
        }
    }, [stavFilter, filterZdroj]);

    useEffect(() => {
        load();
    }, [load]);

    const counts = useMemo(() => ({
        all: items.length,
        fio: items.filter((p) => p.zdroj === 'fio').length,
        kasa: items.filter((p) => p.zdroj === 'symplio_pokladna').length,
    }), [items]);

    return (
        <section className="finance-panel">
            <p className="finance-panel__intro">
                Přehled zařazení: <strong>Auto ✓</strong> = pravidlo + kategorie,
                <strong> chybí</strong> = bez kategorie, <strong>ignorovat</strong> = převody / vklad na účet.
                Sloupec Pravidlo ukazuje, které pravidlo položku zařadilo.
            </p>
            <div className="finance-filters" role="group" aria-label="Filtr stavu">
                {STAV_FILTERS.map((f) => (
                    <button
                        key={f.id}
                        type="button"
                        className={`finance-filter-chip${stavFilter === f.id ? ' active' : ''}`}
                        onClick={() => setStavFilter(f.id)}
                    >
                        {f.label}
                    </button>
                ))}
            </div>
            <FinanceZdrojFilter
                value={filterZdroj}
                onChange={setFilterZdroj}
                items={items}
            />
            {loading && <p>Načítám…</p>}
            {error && <p className="finance-error">{error}</p>}
            {!loading && items.length === 0 && (
                <p className="finance-empty">Žádné položky pro filtr.</p>
            )}
            {!loading && items.length > 0 && (
                <p className="finance-prehled-meta">
                    Zobrazeno {items.length} položek
                    {filterZdroj ? '' : ` (Fio ${counts.fio}, pokladna ${counts.kasa})`}
                </p>
            )}
            {!loading && items.length > 0 && (
                <div className="finance-table-wrap">
                    <table className="finance-table">
                        <thead>
                            <tr>
                                <th>Datum</th>
                                <th>Účet</th>
                                <th>Částka</th>
                                <th>Stav</th>
                                <th>Pravidlo</th>
                                <th>Kategorie</th>
                                <th>Prodejna</th>
                                <th>Popis</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items.map((p) => {
                                const src = zdrojMeta(p.zdroj);
                                const badge = stavBadge(p);
                                return (
                                    <tr key={p.id} className={src.rowClass}>
                                        <td>{p.datum}</td>
                                        <td>
                                            <span className={`finance-badge ${src.badgeClass}`}>{src.short}</span>
                                        </td>
                                        <td>{formatCurrency(p.castka)}</td>
                                        <td>
                                            <span className={`finance-badge ${badge.cls}`}>{badge.text}</span>
                                        </td>
                                        <td className="finance-cell-pravidlo">{p.auto_pravidlo || '–'}</td>
                                        <td>{p.kategorie_nazev || '–'}</td>
                                        <td>{p.prodejna_nazev || '–'}</td>
                                        <td className="finance-cell-zprava">{movementLabel(p)}</td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </section>
    );
};

export default FinancePrehledPanel;
