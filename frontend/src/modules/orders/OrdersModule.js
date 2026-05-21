import React, { useState, useEffect, useCallback } from 'react';
import api from '../../services/api';
import KanbanBoard from './KanbanBoard';
import OrderForm from './OrderForm';
import OrderDetail from './OrderDetail';
import AnalyticsDateRange from '../../components/AnalyticsDateRange';
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

    const applyOrderDateRange = ({ start_date, end_date }) => {
        setFilters(prev => ({ ...prev, date_from: start_date, date_to: end_date }));
    };

    // Načtení dat pro kanban board
    const loadKanbanData = useCallback(async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams();
            
            Object.keys(filters).forEach(key => {
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
            setKanbanData({}); // Fallback na prázdný objekt
        } finally {
            setLoading(false);
        }
    }, [filters]);

    // Načtení statistik pro dashboard
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

    // Periodické obnovování dat každé 2 minuty
    useEffect(() => {
        const interval = setInterval(() => {
            loadKanbanData();
            loadDashboardStats();
        }, 120000);

        return () => clearInterval(interval);
    }, [filters, loadKanbanData, loadDashboardStats]);

    // Zpracování změny stavu objednávky (drag & drop)
    const handleStatusChange = async (orderId, newStatus, poznamka = '') => {
        try {
            await api.patch(`/orders/orders/${orderId}/update_status/`, {
                novy_status: newStatus,
                poznamka: poznamka
            });
            
            // Obnovíme data
            await loadKanbanData();
            await loadDashboardStats();
            
            return { success: true };
        } catch (err) {
            console.error('Chyba při změně stavu:', err);
            return { 
                success: false, 
                error: err.response?.data?.error || 'Nepodařilo se změnit stav objednávky' 
            };
        }
    };

    // Vytvoření nové objednávky
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
                error: err.response?.data || 'Nepodařilo se vytvořit objednávku' 
            };
        }
    };

    // Smazání objednávky
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

    // Změna filtrů
    const handleFilterChange = (key, value) => {
        setFilters(prev => ({
            ...prev,
            [key]: value
        }));
    };

    // Vymazání filtrů
    const clearFilters = () => {
        setFilters({
            search: '',
            status: '',
            date_from: '',
            date_to: ''
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
            {/* Header s tlačítky a statistikami */}
            <div className="orders-header">
                <div className="header-left">
                    <h1>📦 Objednávky</h1>
                    <div className="stats-summary">
                        <span className="stat">
                            📊 Celkem: <strong>{dashboardStats.total_orders || 0}</strong>
                        </span>
                        <span className="stat">
                            🆕 Dnes: <strong>{dashboardStats.today_orders || 0}</strong>
                        </span>
                        <span className="stat">
                            📅 Týden: <strong>{dashboardStats.week_orders || 0}</strong>
                        </span>
                    </div>
                </div>
                
                <div className="header-right">
                    <button 
                        className="btn btn-primary"
                        onClick={() => setShowForm(true)}
                    >
                        ➕ Nová objednávka
                    </button>
                    <button 
                        className="btn btn-secondary"
                        onClick={() => {
                            loadKanbanData();
                            loadDashboardStats();
                        }}
                        disabled={loading}
                    >
                        🔄 Obnovit
                    </button>
                </div>
            </div>

            {/* Filtry */}
            <div className="filters-section">
                <div className="filters">
                    <input
                        type="text"
                        placeholder="🔍 Hledat podle jména, telefonu, telefonu..."
                        value={filters.search}
                        onChange={(e) => handleFilterChange('search', e.target.value)}
                        className="filter-input"
                    />
                    
                    <select
                        value={filters.status}
                        onChange={(e) => handleFilterChange('status', e.target.value)}
                        className="filter-select"
                    >
                        <option value="">Všechny stavy</option>
                        <option value="nove">Nové</option>
                        <option value="objednano">Objednáno</option>
                        <option value="v_kosiku">V košíku</option>
                        <option value="predobjednano">Předobjednáno</option>
                        <option value="neni_skladem">Není skladem</option>
                        <option value="storno">Storno</option>
                        <option value="dorazilo_ceka">Dorazilo čeká na zákazníka</option>
                        <option value="hotovo">Hotovo</option>
                    </select>
                    
                    <AnalyticsDateRange
                        variant="bare"
                        startDate={filters.date_from}
                        endDate={filters.date_to}
                        onApply={applyOrderDateRange}
                        inputClassName="filter-input"
                        showError={false}
                    />
                    
                    <button 
                        className="btn btn-clear"
                        onClick={clearFilters}
                    >
                        ✨ Vymazat filtry
                    </button>
                </div>
            </div>

            {/* Chybová hláška */}
            {error && (
                <div className="error-message">
                    ❌ {error}
                </div>
            )}

            {/* Kanban board */}
            <KanbanBoard 
                kanbanData={kanbanData}
                onStatusChange={handleStatusChange}
                onOrderClick={setSelectedOrder}
                onDeleteOrder={handleDeleteOrder}
                loading={loading}
            />

            {/* Modální okna */}
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