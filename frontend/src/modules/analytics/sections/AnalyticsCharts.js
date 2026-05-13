import React, { useState, useEffect, useCallback } from 'react';
import { getApiEndpoints } from '../../../config/apiConfig';
import {
    ComposedChart,
    Bar,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer
} from 'recharts';
import ChartFilters from './ChartFilters';
import './AnalyticsCharts.css';

const AnalyticsCharts = ({ currentUser }) => {
    const [chartData, setChartData] = useState([]);
    const [aggregations, setAggregations] = useState({});
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [users, setUsers] = useState([]);
    
    // Výchozí filtry
    const [filters, setFilters] = useState({
        type: 'daily',
        start_date: '',
        end_date: '',
        prodejny: [],
        metriky: ['polozky_nad_100'],
        prodejce_id: ''
    });

    // Barvy pro metriky (podle ChartFilters)
    const metricColors = {
        'polozky_nad_100': '#8884d8',
        'sluzby_celkem': '#82ca9d',
        'prumer_polozek_uctu': '#ffc658',
        'ct300': '#ff7c7c',
        'ct600': '#8dd1e1',
        'ct1200': '#d084d0',
        'akt': '#87d068',
        'zah250': '#ffb347',
        'nap': '#ff6b6b',
        'zah500': '#4ecdc4',
        'kop250': '#ffe66d',
        'kop500': '#ff8b94',
        'pz1': '#95e1d3',
        'knz': '#fad390',
        'aligator': '#f8b500'
    };

    // Načtení uživatelů pro filtr prodejců
    const loadUsers = useCallback(async () => {
        try {
            const response = await fetch('/api/users/list/', {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                setUsers(data.users || []);
            }
        } catch (error) {
            console.error('Chyba při načítání uživatelů:', error);
        }
    }, []);

    // Načtení dat pro graf
    const loadChartData = useCallback(async () => {
        setLoading(true);
        setError(null);
        
        try {
            // Sestavení query parametrů
            const params = new URLSearchParams();
            params.append('type', filters.type);
            
            if (filters.start_date) params.append('start_date', filters.start_date);
            if (filters.end_date) params.append('end_date', filters.end_date);
            if (filters.prodejce_id) params.append('prodejce_id', filters.prodejce_id);
            
            // Přidání prodejen
            filters.prodejny.forEach(prodejna => {
                params.append('prodejny[]', prodejna);
            });
            
            // Přidání metrik
            filters.metriky.forEach(metrika => {
                params.append('metriky[]', metrika);
            });
            
            const endpoints = getApiEndpoints();
            const response = await fetch(`${endpoints.chartsData}?${params.toString()}`, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                
                if (data.success) {
                    setChartData(data.data || []);
                    setAggregations(data.aggregations || {});
                } else {
                    setError(data.error || 'Neznámá chyba při načítání dat');
                }
            } else {
                setError(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            setError(`Chyba při načítání dat: ${error.message}`);
        } finally {
            setLoading(false);
        }
    }, [filters]);

    // Načtení dat při změně filtrů (automaticky)
    useEffect(() => {
        loadChartData();
    }, [loadChartData]);

    // Načtení uživatelů při prvním načtení
    useEffect(() => {
        if (currentUser?.role === 'ADMIN') {
            loadUsers();
        }
    }, [currentUser, loadUsers]);

    // Kontrola, zda je uživatel admin
    if (currentUser?.role !== 'ADMIN') {
        return (
            <div className="analytics-charts-unauthorized">
                <h3>🔒 Nedostatečná oprávnění</h3>
                <p>Interaktivní grafy jsou dostupné pouze pro administrátory.</p>
            </div>
        );
    }

    // Custom tooltip pro graf
    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            return (
                <div className="custom-tooltip">
                    <h4>{label}</h4>
                    {payload.map((entry, index) => (
                        <div key={index} className="tooltip-item">
                            <span 
                                className="tooltip-color" 
                                style={{ backgroundColor: entry.color }}
                            ></span>
                            <span className="tooltip-label">{entry.dataKey}:</span>
                            <span className="tooltip-value">{entry.value}</span>
                        </div>
                    ))}
                </div>
            );
        }
        return null;
    };

    return (
        <div className="analytics-charts">
            <div className="charts-header">
                <h2>📊 Interaktivní analytika (verze 1.1)</h2>
                <p>Pokročilé grafy s možností filtrování a porovnávání dat</p>
            </div>

            {/* Filtry */}
            <ChartFilters 
                filters={filters}
                onFiltersChange={setFilters}
                users={users}
            />

            {/* Loading / Error */}
            {loading && (
                <div className="loading-container">
                    <div className="loading-spinner"></div>
                    <p>Načítám data...</p>
                </div>
            )}

            {error && (
                <div className="error-container">
                    <h4>❌ Chyba při načítání dat</h4>
                    <p>{error}</p>
                    <button onClick={loadChartData} className="retry-btn">
                        🔄 Zkusit znovu
                    </button>
                </div>
            )}

            {/* Agregace (souhrn) */}
            {!loading && !error && Object.keys(aggregations).length > 0 && (
                <div className="aggregations-container">
                    <h3>📈 Souhrn za období</h3>
                    <div className="aggregations-grid">
                        {Object.entries(aggregations).map(([metrika, agg]) => (
                            <div key={metrika} className="aggregation-card">
                                <div className="agg-header">
                                    <span 
                                        className="agg-color" 
                                        style={{ backgroundColor: metricColors[metrika] }}
                                    ></span>
                                    <h4>{metrika.replace(/_/g, ' ').toUpperCase()}</h4>
                                </div>
                                <div className="agg-stats">
                                    <div className="agg-item">
                                        <span className="agg-label">Celkem:</span>
                                        <span className="agg-value">{agg.sum}</span>
                                    </div>
                                    <div className="agg-item">
                                        <span className="agg-label">Průměr:</span>
                                        <span className="agg-value">{agg.average}</span>
                                    </div>
                                    <div className="agg-item">
                                        <span className="agg-label">Min/Max:</span>
                                        <span className="agg-value">{agg.min} / {agg.max}</span>
                                    </div>
                                    <div className="agg-item">
                                        <span className="agg-label">Trend:</span>
                                        <span className={`agg-value ${agg.trend >= 0 ? 'positive' : 'negative'}`}>
                                            {agg.trend >= 0 ? '↗' : '↘'} {Math.abs(agg.trend)}%
                                        </span>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Graf */}
            {!loading && !error && chartData.length > 0 && (
                <div className="chart-container">
                    <h3>📊 Graf prodejních dat</h3>
                    <div className="chart-wrapper">
                        <ResponsiveContainer width="100%" height={400}>
                            <ComposedChart
                                data={chartData}
                                margin={{
                                    top: 20,
                                    right: 30,
                                    left: 20,
                                    bottom: 5,
                                }}
                            >
                                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                                <XAxis 
                                    dataKey="displayDate" 
                                    tick={{ fontSize: 12 }}
                                    interval={0}
                                    angle={-45}
                                    textAnchor="end"
                                    height={80}
                                />
                                <YAxis tick={{ fontSize: 12 }} />
                                <Tooltip content={<CustomTooltip />} />
                                <Legend />
                                
                                {/* Vykreslení sloupců pro každou metriku */}
                                {filters.metriky.map((metrika, index) => {
                                    // Rozhodnutí, zda použít sloupec nebo čáru
                                    const isLineMetric = metrika === 'prumer_polozek_uctu';
                                    
                                    if (isLineMetric) {
                                        return (
                                            <Line 
                                                key={metrika}
                                                type="monotone"
                                                dataKey={metrika}
                                                stroke={metricColors[metrika]}
                                                strokeWidth={3}
                                                dot={{ r: 4 }}
                                                name={metrika.replace(/_/g, ' ').toUpperCase()}
                                            />
                                        );
                                    } else {
                                        return (
                                            <Bar 
                                                key={metrika}
                                                dataKey={metrika}
                                                fill={metricColors[metrika]}
                                                name={metrika.replace(/_/g, ' ').toUpperCase()}
                                                fillOpacity={0.8}
                                            />
                                        );
                                    }
                                })}
                            </ComposedChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            )}

            {/* Žádná data */}
            {!loading && !error && chartData.length === 0 && (
                <div className="no-data-container">
                    <h3>📭 Žádná data k zobrazení</h3>
                    <p>Zkuste upravit filtry nebo počkejte na načtení více dat do systému.</p>
                </div>
            )}

            {/* Debug info */}
            {process.env.NODE_ENV === 'development' && (
                <div className="debug-info">
                    <details>
                        <summary>🔧 Debug informace</summary>
                        <pre>{JSON.stringify({ filters, chartDataLength: chartData.length, aggregations }, null, 2)}</pre>
                    </details>
                </div>
            )}
        </div>
    );
};

export default AnalyticsCharts; 