import React, { useState, useEffect, useCallback, useMemo } from 'react';
import api from '../../services/api';
import { dispatchNotificationsRefresh } from '../../services/notificationsService';
import { PageHeader, Select } from '../../components/ui';
import { useAuth } from '../../context/AuthContext';
import ReklamaceForm from './ReklamaceForm';
import ReklamaceBoard from './ReklamaceBoard';
import ReklamaceDetail from './ReklamaceDetail';
import {
    groupByStatus,
    statusLabel,
    FILTER_STATUS_OPTIONS,
    canTransition,
    REKLAMACE_STATUS,
} from './reklamaceHelpers';
import './ReklamaceModule.css';

function cloneKanban(data) {
    const next = {};
    Object.keys(data || {}).forEach((key) => {
        const col = data[key] || {};
        next[key] = {
            ...col,
            orders: [...(col.orders || [])],
        };
    });
    return next;
}

function findItemColumn(data, itemId) {
    for (const [status, col] of Object.entries(data || {})) {
        const orders = col?.orders || [];
        const idx = orders.findIndex((o) => o.id === itemId);
        if (idx >= 0) return { status, idx, item: orders[idx] };
    }
    return null;
}

function moveItemInKanban(data, itemId, newStatus, patch = {}) {
    const found = findItemColumn(data, itemId);
    if (!found) return data;
    const next = cloneKanban(data);
    if (!next[newStatus]) {
        next[newStatus] = { orders: [], count: 0, label: statusLabel(newStatus) };
    }
    next[found.status].orders = next[found.status].orders.filter((o) => o.id !== itemId);
    next[found.status].count = next[found.status].orders.length;
    const moved = {
        ...found.item,
        ...patch,
        status: newStatus,
        status_label: statusLabel(newStatus),
        is_overdue: newStatus === REKLAMACE_STATUS.NEZPRACOVANE ? found.item.is_overdue : false,
    };
    next[newStatus].orders = [moved, ...next[newStatus].orders.filter((o) => o.id !== itemId)];
    next[newStatus].count = next[newStatus].orders.length;
    return next;
}

function removeItemFromKanban(data, itemId) {
    const found = findItemColumn(data, itemId);
    if (!found) return data;
    const next = cloneKanban(data);
    next[found.status].orders = next[found.status].orders.filter((o) => o.id !== itemId);
    next[found.status].count = next[found.status].orders.length;
    return next;
}

const ReklamaceModule = () => {
    const { user } = useAuth();
    const [items, setItems] = useState([]);
    const [kanbanData, setKanbanData] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showForm, setShowForm] = useState(false);
    const [selectedItem, setSelectedItem] = useState(null);
    const [filters, setFilters] = useState({
        prodejna: '',
        search: '',
        dodavatel: '',
        status: '',
    });
    const [notifications, setNotifications] = useState([]);

    const loadNotifications = useCallback(async () => {
        try {
            const res = await api.get('/reklamace/notifikace/');
            setNotifications(res.data);
        } catch {
            setNotifications([]);
        }
    }, []);

    const loadData = useCallback(async ({ silent = false } = {}) => {
        try {
            if (!silent) setLoading(true);
            const params = new URLSearchParams();
            if (filters.prodejna) params.append('prodejna', filters.prodejna);
            if (filters.search) params.append('search', filters.search);
            if (filters.dodavatel) params.append('dodavatel', filters.dodavatel);
            params.append('include_resolved', '1');
            const res = await api.get(`/reklamace/polozky/?${params}`);
            const list = res.data || [];
            setItems(list);
            setKanbanData(groupByStatus(list));
            setError(null);
        } catch (err) {
            console.error(err);
            if (!silent) {
                setError('Nepodařilo se načíst reklamace');
                setItems([]);
                setKanbanData({});
            }
        } finally {
            if (!silent) setLoading(false);
        }
    }, [filters.prodejna, filters.search, filters.dodavatel]);

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

    const overdueCount = useMemo(
        () => items.filter((i) => i.is_overdue).length,
        [items],
    );

    const totalCount = useMemo(
        () => Object.values(kanbanData).reduce((sum, col) => sum + (col?.count || 0), 0),
        [kanbanData],
    );

    const handleCreate = async (data) => {
        await api.post('/reklamace/polozky/', data);
        setShowForm(false);
        await loadData({ silent: true });
    };

    const handleUpdate = async (id, patch) => {
        try {
            const response = await api.patch(`/reklamace/polozky/${id}/`, patch);
            const updated = response.data;
            setItems((prev) => prev.map((i) => (i.id === id ? { ...i, ...updated } : i)));
            setKanbanData((prev) => {
                const found = findItemColumn(prev, id);
                if (!found) return groupByStatus(
                    Object.values(prev).flatMap((c) => c.orders || []),
                );
                const next = cloneKanban(prev);
                next[found.status].orders = next[found.status].orders.map((o) => (
                    o.id === id ? { ...o, ...updated } : o
                ));
                return next;
            });
            setSelectedItem((prev) => (prev?.id === id ? { ...prev, ...updated } : prev));
            return { success: true, data: updated };
        } catch (err) {
            return {
                success: false,
                error: err.response?.data || 'Nepodařilo se uložit změny',
            };
        }
    };

    const handleStatusChange = async (itemId, newStatus, extra = {}) => {
        const found = findItemColumn(kanbanData, itemId);
        if (!found) {
            return { success: false, error: 'Položka nenalezena' };
        }
        if (!canTransition(found.item.status, newStatus)) {
            return { success: false, error: 'Nepovolený přechod stavu' };
        }

        const snapshot = kanbanData;
        const patch = {
            ...(extra.zpusob_vyrizeni ? { zpusob_vyrizeni: extra.zpusob_vyrizeni } : {}),
        };
        setKanbanData((prev) => moveItemInKanban(prev, itemId, newStatus, patch));
        setSelectedItem((prev) => {
            if (!prev || prev.id !== itemId) return prev;
            return {
                ...prev,
                ...patch,
                status: newStatus,
                status_label: statusLabel(newStatus),
                is_overdue: false,
            };
        });

        try {
            if (newStatus === REKLAMACE_STATUS.ODESLANE) {
                await api.post(`/reklamace/polozky/${itemId}/odeslat_dodavateli/`);
            } else if (newStatus === REKLAMACE_STATUS.VRIZENE) {
                await api.post(`/reklamace/polozky/${itemId}/potvrdit_zpracovani/`, {
                    zpusob_vyrizeni: extra.zpusob_vyrizeni,
                });
            } else {
                throw new Error('Nepodporovaný stav');
            }
            loadData({ silent: true });
            return { success: true };
        } catch (err) {
            console.error(err);
            setKanbanData(snapshot);
            setSelectedItem((prev) => {
                if (!prev || prev.id !== itemId) return prev;
                return findItemColumn(snapshot, itemId)?.item || prev;
            });
            return {
                success: false,
                error: err.response?.data || err.message || 'Nepodařilo se změnit stav',
            };
        }
    };

    const handleDelete = async (id) => {
        if (!window.confirm('Skrýt tuto reklamaci?')) return;

        const snapshot = kanbanData;
        const hadSelected = selectedItem?.id === id;
        setKanbanData((prev) => removeItemFromKanban(prev, id));
        if (hadSelected) setSelectedItem(null);

        try {
            await api.delete(`/reklamace/polozky/${id}/`);
            loadData({ silent: true });
        } catch (err) {
            console.error(err);
            setKanbanData(snapshot);
            if (hadSelected) {
                const restored = findItemColumn(snapshot, id)?.item;
                if (restored) setSelectedItem(restored);
            }
            alert('Nepodařilo se smazat reklamaci');
        }
    };

    return (
        <div className="reklamace-module">
            <PageHeader
                title="Reklamace"
                actions={(
                    <>
                        <button
                            type="button"
                            className="btn btn--primary"
                            onClick={() => setShowForm(true)}
                        >
                            Nová reklamace
                        </button>
                        <button
                            type="button"
                            className="btn btn--secondary"
                            onClick={() => {
                                loadData();
                                loadNotifications();
                            }}
                            disabled={loading}
                        >
                            Obnovit
                        </button>
                    </>
                )}
            />

            <div className="reklamace-stats-summary">
                <span className="reklamace-stat">
                    Celkem: <strong>{totalCount}</strong>
                </span>
                {overdueCount > 0 && (
                    <span className="reklamace-stat reklamace-stat--overdue">
                        Po termínu: <strong>{overdueCount}</strong>
                    </span>
                )}
            </div>

            <div className="reklamace-filters-section">
                <div className="reklamace-filters">
                    <input
                        type="search"
                        className="reklamace-filter-input input"
                        placeholder="Hledat značku, název, EAN, zásilku…"
                        value={filters.search}
                        onChange={(e) => setFilters((p) => ({ ...p, search: e.target.value }))}
                    />
                    <Select
                        options={prodejnaOptions}
                        value={filters.prodejna}
                        onChange={(v) => setFilters((p) => ({ ...p, prodejna: v }))}
                        aria-label="Filtr prodejny"
                    />
                    <input
                        type="search"
                        className="reklamace-filter-input reklamace-filter-dodavatel input"
                        placeholder="Dodavatel"
                        value={filters.dodavatel}
                        onChange={(e) => setFilters((p) => ({ ...p, dodavatel: e.target.value }))}
                    />
                    <Select
                        options={FILTER_STATUS_OPTIONS}
                        value={filters.status}
                        onChange={(v) => setFilters((p) => ({ ...p, status: v }))}
                        aria-label="Filtr stavu"
                    />
                    <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        onClick={() => setFilters({
                            prodejna: '',
                            search: '',
                            dodavatel: '',
                            status: '',
                        })}
                    >
                        Vymazat filtry
                    </button>
                </div>
            </div>

            {notifications.length > 0 && (
                <div className="reklamace-notifications" role="status">
                    <strong>Připomínky</strong>
                    <ul>
                        {notifications.map((n) => (
                            <li key={n.id}>{n.message}</li>
                        ))}
                    </ul>
                    <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        onClick={dismissNotifications}
                    >
                        Označit jako přečtené
                    </button>
                </div>
            )}

            {error && <div className="reklamace-error">{error}</div>}

            <ReklamaceBoard
                kanbanData={kanbanData}
                onStatusChange={handleStatusChange}
                onItemClick={setSelectedItem}
                onDeleteItem={handleDelete}
                loading={loading}
                statusFilter={filters.status}
            />

            {showForm && (
                <ReklamaceForm
                    defaultProdejna={user?.prodejna || ''}
                    onSave={handleCreate}
                    onCancel={() => setShowForm(false)}
                />
            )}

            {selectedItem && (
                <ReklamaceDetail
                    item={selectedItem}
                    onClose={() => setSelectedItem(null)}
                    onDelete={handleDelete}
                    onStatusChange={handleStatusChange}
                    onUpdate={handleUpdate}
                />
            )}
        </div>
    );
};

export default ReklamaceModule;
