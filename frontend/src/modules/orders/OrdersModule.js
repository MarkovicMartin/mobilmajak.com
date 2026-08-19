import React, { useState, useEffect, useCallback } from 'react';
import api from '../../services/api';
import { PageHeader, Select } from '../../components/ui';
import KanbanBoard from './KanbanBoard';
import OrderForm from './OrderForm';
import OrderDetail from './OrderDetail';
import { FILTER_STATUS_OPTIONS, statusLabel } from './orderHelpers';
import { normalizeApiError, apiErrorAlertText, withGatewayRetry } from '../../utils/apiErrorMessage';
import './OrdersModule.css';

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

function findOrderColumn(data, orderId) {
    for (const [status, col] of Object.entries(data || {})) {
        const orders = col?.orders || [];
        const idx = orders.findIndex((o) => o.id === orderId);
        if (idx >= 0) return { status, idx, order: orders[idx] };
    }
    return null;
}

function moveOrderInKanban(data, orderId, newStatus, patch = {}) {
    const found = findOrderColumn(data, orderId);
    if (!found) return data;
    if (found.status === newStatus && Object.keys(patch).length === 0) {
        return data;
    }

    const next = cloneKanban(data);
    if (!next[newStatus]) {
        next[newStatus] = { orders: [], count: 0, label: statusLabel(newStatus) };
    }

    next[found.status].orders = next[found.status].orders.filter((o) => o.id !== orderId);
    next[found.status].count = next[found.status].orders.length;

    const moved = {
        ...found.order,
        ...patch,
        status: newStatus,
        status_display: statusLabel(newStatus),
    };
    next[newStatus].orders = [moved, ...next[newStatus].orders.filter((o) => o.id !== orderId)];
    next[newStatus].count = next[newStatus].orders.length;
    return next;
}

function removeOrderFromKanban(data, orderId) {
    const found = findOrderColumn(data, orderId);
    if (!found) return data;
    const next = cloneKanban(data);
    next[found.status].orders = next[found.status].orders.filter((o) => o.id !== orderId);
    next[found.status].count = next[found.status].orders.length;
    return next;
}

const OrdersModule = () => {
    const [kanbanData, setKanbanData] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showForm, setShowForm] = useState(false);
    const [selectedOrder, setSelectedOrder] = useState(null);
    const [searchInput, setSearchInput] = useState('');
    const [filters, setFilters] = useState({
        search: '',
        status: '',
        // date range filtr je pryč (zůstává jen search + status)
    });

    // Debounce: API search až ~300 ms po posledním stisku klávesy
    useEffect(() => {
        const timer = window.setTimeout(() => {
            setFilters((prev) => {
                const next = searchInput.trim();
                if (prev.search === next) return prev;
                return { ...prev, search: next };
            });
        }, 300);
        return () => window.clearTimeout(timer);
    }, [searchInput]);

    const loadKanbanData = useCallback(async ({ silent = false } = {}) => {
        try {
            if (!silent) setLoading(true);
            const params = new URLSearchParams();

            Object.keys(filters).forEach((key) => {
                if (filters[key]) {
                    params.append(key, filters[key]);
                }
            });

            const response = await api.get(`/orders/orders/?${params.toString()}`);
            setKanbanData(response.data.kanban_data);
            setError(null);
        } catch (err) {
            console.error('Chyba při načítání objednávek:', err);
            if (!silent) {
                setError('Nepodařilo se načíst objednávky');
                setKanbanData({});
            }
        } finally {
            if (!silent) setLoading(false);
        }
    }, [filters]);

    useEffect(() => {
        loadKanbanData();
    }, [filters, loadKanbanData]);

    useEffect(() => {
        const interval = setInterval(() => {
            loadKanbanData({ silent: true });
        }, 120000);
        return () => clearInterval(interval);
    }, [filters, loadKanbanData]);

    // Po návratu na kartu / okno – tiché obnovení (bez čekání na 2min poll)
    useEffect(() => {
        const onVisible = () => {
            if (document.visibilityState !== 'visible') return;
            loadKanbanData({ silent: true });
        };
        document.addEventListener('visibilitychange', onVisible);
        return () => document.removeEventListener('visibilitychange', onVisible);
    }, [loadKanbanData]);
    const handleStatusChange = async (orderId, newStatus, poznamka = '', dodavatel = null) => {
        const snapshot = kanbanData;
        const patch = dodavatel != null ? { dodavatel } : {};
        setKanbanData((prev) => moveOrderInKanban(prev, orderId, newStatus, patch));
        setSelectedOrder((prev) => {
            if (!prev || prev.id !== orderId) return prev;
            return {
                ...prev,
                status: newStatus,
                status_display: statusLabel(newStatus),
                ...patch,
            };
        });

        try {
            const body = {
                novy_status: newStatus,
                poznamka: poznamka,
            };
            if (dodavatel != null) {
                body.dodavatel = dodavatel;
            }
            await withGatewayRetry(() =>
                api.patch(`/orders/orders/${orderId}/update_status/`, body)
            );
            loadKanbanData({ silent: true });
            loadDashboardStats();
            return { success: true };
        } catch (err) {
            console.error('Chyba při změně stavu:', err);
            setKanbanData(snapshot);
            setSelectedOrder((prev) => {
                if (!prev || prev.id !== orderId) return prev;
                const restored = findOrderColumn(snapshot, orderId)?.order;
                return restored ? { ...prev, ...restored } : prev;
            });
            return {
                success: false,
                error: normalizeApiError(err, 'Nepodařilo se změnit stav objednávky'),
            };
        }
    };

    const handleCreateOrder = async (orderData) => {
        try {
            await withGatewayRetry(() => api.post('/orders/orders/', orderData));
            setShowForm(false);
            await loadKanbanData();
            await loadDashboardStats();
            return { success: true };
        } catch (err) {
            console.error('Chyba při vytváření objednávky:', err);
            return {
                success: false,
                error: normalizeApiError(err, 'Nepodařilo se vytvořit objednávku'),
            };
        }
    };

    const handleUpdateOrder = async (orderId, patch) => {
        try {
            const response = await withGatewayRetry(() =>
                api.patch(`/orders/orders/${orderId}/`, patch)
            );
            const updated = response.data;
            await loadKanbanData();
            setSelectedOrder((prev) => {
                if (!prev || prev.id !== orderId) return prev;
                return { ...prev, ...updated };
            });
            return { success: true, data: updated };
        } catch (err) {
            console.error('Chyba při úpravě objednávky:', err);
            return {
                success: false,
                error: normalizeApiError(err, 'Nepodařilo se uložit změny'),
            };
        }
    };

    const handleDeleteOrder = async (orderId) => {
        if (!window.confirm('Opravdu chcete smazat tuto objednávku?')) {
            return;
        }

        const snapshot = kanbanData;
        const hadSelected = selectedOrder?.id === orderId;
        setKanbanData((prev) => removeOrderFromKanban(prev, orderId));
        if (hadSelected) setSelectedOrder(null);

        try {
            await withGatewayRetry(() => api.delete(`/orders/orders/${orderId}/`));
            loadKanbanData({ silent: true });
            loadDashboardStats();
        } catch (err) {
            console.error('Chyba při mazání objednávky:', err);
            setKanbanData(snapshot);
            if (hadSelected) {
                const restored = findOrderColumn(snapshot, orderId)?.order;
                if (restored) setSelectedOrder(restored);
            }
            alert(apiErrorAlertText(err, 'Nepodařilo se smazat objednávku'));
        }
    };

    const handleFilterChange = (key, value) => {
        setFilters((prev) => ({
            ...prev,
            [key]: value,
        }));
    };

    const clearFilters = () => {
        setSearchInput('');
        setFilters({
            search: '',
            status: '',
        });
    };

    if (loading && (!kanbanData || Object.keys(kanbanData).length === 0)) {
        return (
            <div className="orders-module">
                <div className="loading">
                    <div className="spinner"></div>
                    <p>Načítám objednávky...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="orders-module">
            <PageHeader
                title="Objednávky"
                actions={(
                    <>
                        <button
                            type="button"
                            className="btn btn--primary"
                            onClick={() => setShowForm(true)}
                        >
                            Nová objednávka
                        </button>
                        <button
                            type="button"
                            className="btn btn--secondary"
                            onClick={() => {
                                loadKanbanData();
                            }}
                            disabled={loading}
                        >
                            Obnovit
                        </button>
                    </>
                )}
            />

            <div className="filters-section">
                <div className="filters">
                    <input
                        type="text"
                        placeholder="Hledat podle jména, telefonu, modelu…"
                        value={searchInput}
                        onChange={(e) => setSearchInput(e.target.value)}
                        className="filter-input filter-input--search input"
                    />

                    <Select
                        options={FILTER_STATUS_OPTIONS}
                        value={filters.status}
                        onChange={(v) => handleFilterChange('status', v)}
                        aria-label="Filtr stavu objednávky"
                        className="filter-select filter-select--status"
                    />

                    <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        onClick={clearFilters}
                    >
                        Vymazat filtry
                    </button>
                </div>
            </div>

            {error && (
                <div className="error-message">
                    {error}
                </div>
            )}

            <KanbanBoard
                kanbanData={kanbanData}
                onStatusChange={handleStatusChange}
                onOrderClick={setSelectedOrder}
                onDeleteOrder={handleDeleteOrder}
                loading={loading}
                statusFilter={filters.status}
                searchActive={Boolean((filters.search || '').trim())}
            />

            {showForm && (
                <OrderForm
                    onClose={() => setShowForm(false)}
                    onSubmit={handleCreateOrder}
                />
            )}

            {selectedOrder && (
                <OrderDetail
                    order={selectedOrder}
                    onClose={() => setSelectedOrder(null)}
                    onDelete={handleDeleteOrder}
                    onStatusChange={handleStatusChange}
                    onUpdate={handleUpdateOrder}
                />
            )}
        </div>
    );
};

export default OrdersModule;
