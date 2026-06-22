import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { storeAPI } from '../../services/api';
import { computeQuickRange, detectQuickRangePreset } from '../../utils/analyticsQuickRange';
import AnalyticsPeriodFilterPanel from '../../components/analytics/AnalyticsPeriodFilterPanel';
import PolozkyTasksPanel from '../analytics/components/PolozkyTasksPanel';
import {
    buildInitialPolozkyFilters,
    mergePolozkyScope,
    pickPolozkyScope,
} from '../analytics/sections/polozkyFilters';
import '../analytics/sections/Polozky.css';

const TasksWorkloadSection = () => {
    const [filters, setFilters] = useState(buildInitialPolozkyFilters);
    const [scopeFilters, setScopeFilters] = useState(() => pickPolozkyScope(buildInitialPolozkyFilters()));
    const [stores, setStores] = useState([]);
    const [loading, setLoading] = useState(false);
    const [refreshKey, setRefreshKey] = useState(0);
    const [quickKey, setQuickKey] = useState(() =>
        detectQuickRangePreset(
            buildInitialPolozkyFilters().start_date,
            buildInitialPolozkyFilters().end_date,
        ),
    );

    const workloadFilters = useMemo(
        () => mergePolozkyScope(filters, scopeFilters),
        [filters, scopeFilters],
    );

    useEffect(() => {
        storeAPI.getStoreChoices().then((data) => {
            const list = Array.isArray(data) ? data : data?.stores || data?.results || [];
            setStores(list);
        }).catch(() => setStores([]));
    }, []);

    const applyDateRange = useCallback(({ start_date, end_date, preset }) => {
        setFilters((f) => ({
            ...f,
            period: 'custom',
            start_date,
            end_date,
        }));
        setQuickKey(preset || detectQuickRangePreset(start_date, end_date));
    }, []);

    const handlePeriodChange = useCallback(({ type, month }) => {
        if (type === 'custom') {
            setFilters((f) => ({ ...f, period: 'custom' }));
            setQuickKey('custom');
            return;
        }
        if (type === 'month' && month) {
            setFilters((f) => ({
                ...f,
                period: 'monthly_select',
                selected_month: month,
                start_date: '',
                end_date: '',
            }));
            setQuickKey('custom');
        }
    }, []);

    const handleDateApply = useCallback(({ startDate, endDate }) => {
        applyDateRange({
            start_date: startDate,
            end_date: endDate,
            preset: detectQuickRangePreset(startDate, endDate),
        });
    }, [applyDateRange]);

    const handleQuickPreset = useCallback((id) => {
        const range = computeQuickRange(id);
        if (!range) return;
        applyDateRange({ ...range, preset: id });
    }, [applyDateRange]);

    const updateScope = useCallback((patch) => {
        setScopeFilters((prev) => ({ ...prev, ...patch }));
    }, []);

    return (
        <div className="tasks-workload-section">
            <p className="tasks-workload-intro">
                Přehled dokončených úkolů a proxy indexu vytížení prodejců v zvoleném období.
                Nejde o skutečný počet zákazníků.
            </p>

            <AnalyticsPeriodFilterPanel
                filters={filters}
                quickKey={quickKey}
                onPeriodChange={handlePeriodChange}
                onDateApply={handleDateApply}
                onQuickPreset={handleQuickPreset}
                onRefresh={() => setRefreshKey((k) => k + 1)}
                loading={loading}
                className="tasks-workload-filters"
            >
                <div className="filter-group">
                    <label>Kanál:</label>
                    <select
                        value={scopeFilters.kanal}
                        onChange={(e) => updateScope({ kanal: e.target.value })}
                    >
                        <option value="all">Všechny kanály</option>
                        <option value="prodejna">Prodejna</option>
                        <option value="eshop">E-shop</option>
                        <option value="allegro">ALLEGRO</option>
                        <option value="servis">Servis</option>
                    </select>
                </div>
                <div className="filter-group">
                    <label>Prodejna:</label>
                    <select
                        value={scopeFilters.prodejna_id || ''}
                        onChange={(e) => updateScope({ prodejna_id: e.target.value })}
                    >
                        <option value="">Všechny</option>
                        {stores.map((s) => (
                            <option key={s.id || s.value} value={s.id || s.value}>
                                {s.nazev || s.label || s.nazev_kratkiy}
                            </option>
                        ))}
                    </select>
                </div>
            </AnalyticsPeriodFilterPanel>

            <PolozkyTasksPanel
                filters={workloadFilters}
                variant="page"
                onLoadingChange={setLoading}
                refreshKey={refreshKey}
            />
        </div>
    );
};

export default TasksWorkloadSection;
