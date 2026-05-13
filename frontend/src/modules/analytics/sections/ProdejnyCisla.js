import React, { useState } from 'react';
import './SectionStyles.css';

const ProdejnyCisla = () => {
    const [selectedPeriod, setSelectedPeriod] = useState('month');
    const [selectedMetric, setSelectedMetric] = useState('revenue');

    // Mock data pro ukázku
    const storeData = [
        { 
            name: 'Prodejna Praha 1', 
            revenue: 1250000, 
            customers: 342, 
            avgOrder: 3655,
            growth: 15.2 
        },
        { 
            name: 'Prodejna Brno', 
            revenue: 980000, 
            customers: 267, 
            avgOrder: 3670,
            growth: 8.7 
        },
        { 
            name: 'Prodejna Ostrava', 
            revenue: 664000, 
            customers: 189, 
            avgOrder: 3513,
            growth: -2.1 
        },
    ];

    const totalRevenue = storeData.reduce((sum, store) => sum + store.revenue, 0);
    const totalCustomers = storeData.reduce((sum, store) => sum + store.customers, 0);
    const avgOrderValue = totalRevenue / totalCustomers;

    return (
        <div className="analytics-section">
            <div className="section-filters">
                <div className="filter-group">
                    <label>Období:</label>
                    <select 
                        value={selectedPeriod} 
                        onChange={(e) => setSelectedPeriod(e.target.value)}
                    >
                        <option value="day">Dnes</option>
                        <option value="week">Tento týden</option>
                        <option value="month">Tento měsíc</option>
                        <option value="quarter">Toto čtvrtletí</option>
                        <option value="year">Tento rok</option>
                    </select>
                </div>
                <div className="filter-group">
                    <label>Metrika:</label>
                    <select 
                        value={selectedMetric} 
                        onChange={(e) => setSelectedMetric(e.target.value)}
                    >
                        <option value="revenue">Obrat</option>
                        <option value="customers">Zákazníci</option>
                        <option value="avgOrder">Průměrná objednávka</option>
                        <option value="growth">Růst</option>
                    </select>
                </div>
            </div>

            <div className="section-content">
                <div className="stats-cards">
                    <div className="stat-card">
                        <h4>Celkový obrat</h4>
                        <div className="stat-value">{totalRevenue.toLocaleString()} Kč</div>
                        <div className="stat-change positive">+11.2% oproti minulému období</div>
                    </div>
                    <div className="stat-card">
                        <h4>Celkem zákazníků</h4>
                        <div className="stat-value">{totalCustomers}</div>
                        <div className="stat-change positive">+156 nových zákazníků</div>
                    </div>
                    <div className="stat-card">
                        <h4>Průměrná objednávka</h4>
                        <div className="stat-value">{Math.round(avgOrderValue).toLocaleString()} Kč</div>
                        <div className="stat-change negative">-2.3% oproti minulému období</div>
                    </div>
                    <div className="stat-card">
                        <h4>Nejlepší prodejna</h4>
                        <div className="stat-value">Praha 1</div>
                        <div className="stat-change">Růst +15.2%</div>
                    </div>
                </div>

                <div className="data-table">
                    <h4>Přehled prodejen</h4>
                    <table>
                        <thead>
                            <tr>
                                <th>Prodejna</th>
                                <th>Obrat</th>
                                <th>Zákazníci</th>
                                <th>Průměrná objednávka</th>
                                <th>Růst (%)</th>
                                <th>Výkonnost</th>
                            </tr>
                        </thead>
                        <tbody>
                            {storeData.map((store, index) => (
                                <tr key={index}>
                                    <td>
                                        <strong>{store.name}</strong>
                                    </td>
                                    <td>{store.revenue.toLocaleString()} Kč</td>
                                    <td>{store.customers}</td>
                                    <td>{store.avgOrder.toLocaleString()} Kč</td>
                                    <td>
                                        <span className={`growth-indicator ${store.growth > 0 ? 'positive' : 'negative'}`}>
                                            {store.growth > 0 ? '+' : ''}{store.growth}%
                                        </span>
                                    </td>
                                    <td>
                                        <div className="performance-bar">
                                            <div 
                                                className="performance-fill" 
                                                style={{ 
                                                    width: `${(store.revenue / Math.max(...storeData.map(s => s.revenue))) * 100}%` 
                                                }}
                                            ></div>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                <div className="metrics-comparison">
                    <h4>Porovnání klíčových metrik</h4>
                    <div className="comparison-grid">
                        <div className="metric-item">
                            <h5>Konverzní poměr</h5>
                            <div className="metric-value">3.2%</div>
                            <div className="metric-trend positive">↗ +0.5%</div>
                        </div>
                        <div className="metric-item">
                            <h5>Návštěvnost za den</h5>
                            <div className="metric-value">127</div>
                            <div className="metric-trend positive">↗ +12</div>
                        </div>
                        <div className="metric-item">
                            <h5>Průměrná doba návštěvy</h5>
                            <div className="metric-value">24 min</div>
                            <div className="metric-trend negative">↘ -3 min</div>
                        </div>
                        <div className="metric-item">
                            <h5>Opakovaní zákazníci</h5>
                            <div className="metric-value">67%</div>
                            <div className="metric-trend positive">↗ +4%</div>
                        </div>
                    </div>
                </div>

                <div className="charts-section">
                    <div className="chart-placeholder large">
                        <h4>Trend prodeje za posledních 30 dní</h4>
                        <div className="placeholder-content">
                            📈 Interaktivní graf trendu bude implementován v další fázi
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ProdejnyCisla; 