import React, { useState, useEffect, useCallback, useMemo } from 'react';
import api from '../../services/api';
import { dispatchNotificationsRefresh } from '../../services/notificationsService';
import { PageHeader, Select } from '../../components/ui';
import { useAuth } from '../../context/AuthContext';
import ReklamaceForm from './ReklamaceForm';
import ReklamaceRow from './ReklamaceRow';
import './ReklamaceModule.css';

const ReklamaceModule = () => {
    const { user } = useAuth();
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showForm, setShowForm] = useState(false);
    const [editing, setEditing] = useState(null);
    const [busyId, setBusyId] = useState(null);
    const [showResolved, setShowResolved] = useState(false);
    const [filters, setFilters] = useState({ prodejna: '', search: '', dodavatel: '' });
    const [notifications, setNotifications] = useState([]);

    const loadNotifications = useCallback(async () => {
        try {
            const res = await api.get('/reklamace/notifikace/');
            setNotifications(res.data);
        } catch {
            setNotifications([]);
        }
    }, []);

    const loadData = useCallback(async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams();
            if (filters.prodejna) params.append('prodejna', filters.prodejna);
            if (filters.search) params.append('search', filters.search);
            if (filters.dodavatel) params.append('dodavatel', filters.dodavatel);
            if (showResolved) params.append('include_resolved', '1');
            const res = await api.get(`/reklamace/polozky/?${params}`);
            setItems(res.data);
            setError(null);
        } catch (err) {
            setError('Nepodařilo se načíst reklamace');
            setItems([]);
        } finally {
            setLoading(false);
        }
    }, [filters, showResolved]);

    useEffect(() => {
        loadData();
        loadNotifications();
    }, [loadData, loadNotifications]);

    const dismissNotifications = async () => {
        try {
            await api.post('/reklamace/notifikace/mark-read/', { ids: notifications.map((n) => n.id) });
            setNotifications([]);
            dispatchNotificationsRefresh();
        } catch {
            /* ignore */
        }
    };

    const prodejny = useMemo(() => {
        const set = new Set(items.map((i) => i.prodejna).filter(Boolean));
        return [...set].sort((a, b) => a.localeCompare(b, 'cs'));
    }, [items]);

    const prodejnaOptions = useMemo(() => [
        { value: '', label: 'Všechny prodejny' },
        ...prodejny.map((p) => ({ value: p, label: p })),
    ], [prodejny]);

    const handleSave = async (data) => {
        if (editing) {
            await api.put(`/reklamace/polozky/${editing.id}/`, data);
        } else {
            await api.post('/reklamace/polozky/', data);
        }
        setShowForm(false);
        setEditing(null);
        loadData();
    };

    const handleDelete = async (id) => {
        if (!window.confirm('Skrýt tuto reklamaci?')) return;
        await api.delete(`/reklamace/polozky/${id}/`);
        loadData();
    };

    const handleOdeslat = async (id) => {
        try {
            setBusyId(id);
            await api.post(`/reklamace/polozky/${id}/odeslat_dodavateli/`);
            loadData();
        } catch (err) {
            setError('Nepodařilo se označit jako odeslané');
        } finally {
            setBusyId(null);
        }
    };

    const handlePotvrdit = async (id, payload) => {
        try {
            setBusyId(id);
            await api.post(`/reklamace/polozky/${id}/potvrdit_zpracovani/`, payload);
            loadData();
        } catch (err) {
            setError('Nepodařilo se potvrdit zpracování');
        } finally {
            setBusyId(null);
        }
    };

    const overdueCount = useMemo(
        () => items.filter((i) => i.is_overdue).length,
        [items],
    );

    return (
        <div className="reklamace-module">
            <PageHeader
                title="Reklamace evidence"
                subtitle="Co kam šlo – dodavatel, zásilka, faktura"
                actions={(
                    <button type="button" className="btn btn-primary" onClick={() => { setEditing(null); setShowForm(true); }}>
                        <i className="fas fa-plus" /> Nová
                    </button>
                )}
            />

            <div className="reklamace-filters">
                <Select
                    label="Prodejna"
                    value={filters.prodejna}
                    onChange={(e) => setFilters((p) => ({ ...p, prodejna: e.target.value }))}
                    options={prodejnaOptions}
                />
                <input
                    type="search"
                    className="form-control"
                    placeholder="Hledat značku, název, EAN, zásilku…"
                    value={filters.search}
                    onChange={(e) => setFilters((p) => ({ ...p, search: e.target.value }))}
                />
                <input
                    type="search"
                    className="form-control reklamace-filter-dodavatel"
                    placeholder="Dodavatel"
                    value={filters.dodavatel}
                    onChange={(e) => setFilters((p) => ({ ...p, dodavatel: e.target.value }))}
                />
                <label className="reklamace-toggle">
                    <input
                        type="checkbox"
                        checked={showResolved}
                        onChange={(e) => setShowResolved(e.target.checked)}
                    />
                    Zobrazit vyřízené
                </label>
            </div>

            {notifications.length > 0 && (
                <div className="reklamace-notifications" role="status">
                    <strong>Připomínky</strong>
                    <ul>
                        {notifications.map((n) => (
                            <li key={n.id}>{n.message}</li>
                        ))}
                    </ul>
                    <button type="button" className="btn btn-sm btn-outline reklamace-notifications__dismiss" onClick={dismissNotifications}>
                        Označit jako přečtené
                    </button>
                </div>
            )}

            <div className="reklamace-stats">
                Celkem: <strong>{items.length}</strong>
                {overdueCount > 0 && (
                    <span className="reklamace-stats__overdue">
                        · Po termínu: <strong>{overdueCount}</strong>
                    </span>
                )}
            </div>

            <div className="reklamace-legend">
                <span className="reklamace-legend__item reklamace-legend__item--nezpracovane">Nezpracované</span>
                <span className="reklamace-legend__item reklamace-legend__item--overdue">Po 24 h – odeslat</span>
                <span className="reklamace-legend__item reklamace-legend__item--odeslane">Odeslané</span>
                <span className="reklamace-legend__item reklamace-legend__item--vyrizene">Vyřízené</span>
            </div>

            {error && <div className="alert alert-danger">{error}</div>}
            {loading && <p>Načítám…</p>}

            <div className="reklamace-list">
                {!loading && items.length === 0 && <p className="reklamace-empty">Žádné záznamy.</p>}
                {items.map((item) => (
                    <ReklamaceRow
                        key={item.id}
                        item={item}
                        busy={busyId === item.id}
                        onEdit={() => { setEditing(item); setShowForm(true); }}
                        onDelete={() => handleDelete(item.id)}
                        onOdeslat={handleOdeslat}
                        onPotvrdit={handlePotvrdit}
                    />
                ))}
            </div>

            {showForm && (
                <ReklamaceForm
                    initial={editing}
                    defaultProdejna={user?.prodejna || ''}
                    onSave={handleSave}
                    onCancel={() => { setShowForm(false); setEditing(null); }}
                />
            )}
        </div>
    );
};

export default ReklamaceModule;
