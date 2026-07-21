import React, { useState, useEffect, useCallback, useMemo } from 'react';
import api from '../../services/api';
import { PageHeader, Select, DateRangePicker } from '../../components/ui';
import KanbanBoard from './KanbanBoard';
import OrderForm from './OrderForm';
import OrderDetail from './OrderDetail';
import { FILTER_STATUS_OPTIONS, statusLabel } from './orderHelpers';
import './OrdersModule.css';

const OrdersModule = () => {
    const [kanbanData, setKanbanData] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showForm, setShowForm] = useState(false);
    const [selectedOrder, setSelectedOrder] = useState(null);
    const [filters, setFilters] = useState({
        search: '',
        status: '',
        date_from: '',
        date_to: ''
    });
    const [dashboardStats, setDashboardStats] = useState({});

    const applyOrderDateRange = useCallback(({ start_date, end_date }) => {
        setFilters((prev) => ({ ...prev, date_from: start_date, date_to: end_date }));
    }, []);

    const statsSummary = useMemo(() => (
        <div className="orders-stats-summary">
            <span className="orders-stat">
                Celkem: <strong>{dashboardStats.total_orders || 0}</strong>
            </span>
            <span className="orders-stat">
                Dnes: <strong>{dashboardStats.today_orders || 0}</strong>
            </span>
            <span className="orders-stat">
                Týden: <strong>{dashboardStats.week_orders || 0}</strong>
            </span>
        </div>
    ), [dashboardStats]);

    const loadKanbanData = useCallback(async () => {
        try {
            setLoading(true);
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
            setError('Nepodařilo se načíst objednávky');
            setKanbanData({});
        } finally {
            setLoading(false);
        }
    }, [filters]);

    const loadDashboardStats = useCallback(async () => {
        try {
            const response = await api.get('/orders/dashboard-stats/');
            setDashboardStats(response.data);
        } catch (err) {
            console.error('Chyba při načítání statistik:', err);
        }
    }, []);

    useEffect(() => {
        loadKanbanData();
        loadDashboardStats();
    }, [filters, loadKanbanData, loadDashboardStats]);

    useEffect(() => {
        const interval = setInterval(() => {
            loadKanbanData();
            loadDashboardStats();
        }, 120000);
        return () => clearInterval(interval);
    }, [filters, loadKanbanData, loadDashboardStats]);

    const handleStatusChange = async (orderId, newStatus, poznamka = '', dodavatel = null) => {
        try {
            const body = {
                novy_status: newStatus,
                poznamka: poznamka,
            };
            if (dodavatel != null) {
                body.dodavatel = dodavatel;
            }
            await api.patch(`/orders/orders/${orderId}/update_status/`, body);

            await loadKanbanData();
            await loadDashboardStats();

            setSelectedOrder((prev) => {
                if (!prev || prev.id !== orderId) return prev;
                return {
                    ...prev,
                    status: newStatus,
                    status_display: statusLabel(newStatus),
                    ...(dodavatel != null ? { dodavatel } : {}),
                };
            });

            return { success: true };
        } catch (err) {
            console.error('Chyba při změně stavu:', err);
            return {
                success: false,
                error: err.response?.data || 'Nepodařilo se změnit stav objednávky',
            };
        }
    };

    const handleCreateOrder = async (orderData) => {
        try {
            await api.post('/orders/orders/', orderData);
            setShowForm(false);
            await loadKanbanData();
            await loadDashboardStats();
            return { success: true };
        } catch (err) {
            console.error('Chyba při vytváření objednávky:', err);
            return {
                success: false,
                error: err.response?.data || 'Nepodařilo se vytvořit objednávku',
            };
        }
    };

    const handleDeleteOrder = async (orderId) => {
        if (!window.confirm('Opravdu chcete smazat tuto objednávku?')) {
            return;
        }

        try {
            await api.delete(`/orders/orders/${orderId}/`);
            await loadKanbanData();
            await loadDashboardStats();
            setSelectedOrder(null);
        } catch (err) {
            console.error('Chyba při mazání objednávky:', err);
            alert('Nepodařilo se smazat objednávku');
        }
    };

    const handleFilterChange = (key, value) => {
        setFilters((prev) => ({
            ...prev,
            [key]: value,
        }));
    };

    const clearFilters = () => {
        setFilters({
            search: '',
            status: '',
            date_from: '',
            date_to: '',
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
                                loadDashboardStats();
                            }}
                            disabled={loading}
                        >
                            Obnovit
                        </button>
                    </>
                )}
            />

            {statsSummary}

            <div className="filters-section">
                <div className="filters">
                    <input
                        type="text"
                        placeholder="Hledat podle jména, telefonu, modelu…"
                        value={filters.search}
                        onChange={(e) => handleFilterChange('search', e.target.value)}
                        className="filter-input input"
                    />

                    <Select
                        options={FILTER_STATUS_OPTIONS}
                        value={filters.status}
                        onChange={(v) => handleFilterChange('status', v)}
                        aria-label="Filtr stavu objednávky"
                    />

                    <DateRangePicker
                        variant="inline"
                        startDate={filters.date_from}
                        endDate={filters.date_to}
                        onApply={applyOrderDateRange}
                        showError={false}
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
                />
            )}
        </div>
    );
};

export default OrdersModule;
