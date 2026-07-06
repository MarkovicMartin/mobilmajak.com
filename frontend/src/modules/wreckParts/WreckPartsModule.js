import React, { useState, useEffect, useCallback, useMemo } from 'react';
import api from '../../services/api';
import { PageHeader, Select } from '../../components/ui';
import { useAuth } from '../../context/AuthContext';
import WreckPartForm from './WreckPartForm';
import './WreckPartsModule.css';

const WreckPartsModule = () => {
    const { user } = useAuth();
    const [parts, setParts] = useState([]);
    const [stores, setStores] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showForm, setShowForm] = useState(false);
    const [editing, setEditing] = useState(null);
    const [filters, setFilters] = useState({ store: '', search: '' });

    const loadData = useCallback(async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams();
            if (filters.store) params.append('store', filters.store);
            if (filters.search) params.append('search', filters.search);

            const [partsRes, summaryRes] = await Promise.all([
                api.get(`/wreck-parts/parts/?${params}`),
                api.get('/wreck-parts/store-summary/'),
            ]);
            setParts(partsRes.data);
            setStores(summaryRes.data.stores || []);
            setError(null);
        } catch (err) {
            setError('Nepodařilo se načíst díly z vraků');
            setParts([]);
        } finally {
            setLoading(false);
        }
    }, [filters]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    useEffect(() => {
        if (user?.prodejna && !filters.store) {
            setFilters((prev) => ({ ...prev, store: user.prodejna }));
        }
    }, [user, filters.store]);

    const grouped = useMemo(() => {
        const map = {};
        parts.forEach((p) => {
            const key = p.store || 'Neuvedeno';
            if (!map[key]) map[key] = [];
            map[key].push(p);
        });
        return Object.entries(map).sort(([a], [b]) => a.localeCompare(b, 'cs'));
    }, [parts]);

    const storeOptions = useMemo(() => [
        { value: '', label: 'Všechny prodejny' },
        ...stores.map((s) => ({ value: s.store, label: `${s.store} (${s.count})` })),
    ], [stores]);

    const handleSave = async (data) => {
        if (editing) {
            await api.put(`/wreck-parts/parts/${editing.id}/`, data);
        } else {
            await api.post('/wreck-parts/parts/', data);
        }
        setShowForm(false);
        setEditing(null);
        loadData();
    };

    const handleDelete = async (id) => {
        if (!window.confirm('Skrýt tento záznam?')) return;
        await api.delete(`/wreck-parts/parts/${id}/`);
        loadData();
    };

    return (
        <div className="wreck-parts-module">
            <PageHeader
                title="Díly z vraků"
                actions={(
                    <button type="button" className="btn btn-primary" onClick={() => { setEditing(null); setShowForm(true); }}>
                        <i className="fas fa-plus" /> Přidat
                    </button>
                )}
            />

            <div className="wreck-parts-filters">
                <Select
                    label="Prodejna"
                    value={filters.store}
                    onChange={(e) => setFilters((p) => ({ ...p, store: e.target.value }))}
                    options={storeOptions}
                />
                <input
                    type="search"
                    className="form-control"
                    placeholder="Hledat model, typ dílu…"
                    value={filters.search}
                    onChange={(e) => setFilters((p) => ({ ...p, search: e.target.value }))}
                />
            </div>

            {error && <div className="alert alert-danger">{error}</div>}
            {loading && <p className="wreck-parts-loading">Načítám…</p>}

            {!loading && grouped.length === 0 && (
                <p className="wreck-parts-empty">Žádné záznamy.</p>
            )}

            {grouped.map(([store, items]) => (
                <section key={store} className="wreck-parts-store">
                    <h2 className="wreck-parts-store__title">
                        {store}
                        <span className="wreck-parts-store__count">{items.length}</span>
                    </h2>
                    <div className="wreck-parts-table-wrap">
                        <table className="wreck-parts-table">
                            <thead>
                                <tr>
                                    <th>Model</th>
                                    <th>Typ dílu</th>
                                    <th>Počet</th>
                                    <th>Poznámka</th>
                                    <th />
                                </tr>
                            </thead>
                            <tbody>
                                {items.map((p) => (
                                    <tr key={p.id}>
                                        <td>{p.model_name}</td>
                                        <td>{p.part_type}</td>
                                        <td>{p.quantity}</td>
                                        <td className="wreck-parts-notes">{p.notes || '—'}</td>
                                        <td className="wreck-parts-actions">
                                            <button type="button" className="btn btn-sm btn-outline" onClick={() => { setEditing(p); setShowForm(true); }}>Upravit</button>
                                            <button type="button" className="btn btn-sm btn-outline-danger" onClick={() => handleDelete(p.id)}>Smazat</button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </section>
            ))}

            {showForm && (
                <WreckPartForm
                    initial={editing}
                    onSave={handleSave}
                    onCancel={() => { setShowForm(false); setEditing(null); }}
                />
            )}
        </div>
    );
};

export default WreckPartsModule;
