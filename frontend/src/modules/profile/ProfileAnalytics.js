import React, { useState, useEffect } from 'react';
import { getApiEndpoints } from '../../config/apiConfig';
import './ProfileAnalytics.css';

const ProfileAnalytics = ({ userId }) => {
    const [dataType, setDataType] = useState('daily'); // daily/monthly/points
    const [selectedDate, setSelectedDate] = useState('');
    const [todayData, setTodayData] = useState(null);
    const [monthlyData, setMonthlyData] = useState(null);
    const [todayPoints, setTodayPoints] = useState(null);
    const [monthlyPoints, setMonthlyPoints] = useState(null);
    const [historicalData, setHistoricalData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        loadTodayData();
        loadMonthlyData();
        loadTodayPoints();
        loadMonthlyPoints();
    }, [userId]);

    useEffect(() => {
        if (selectedDate) {
            loadHistoricalData();
        }
    }, [selectedDate, dataType, userId]);

    const loadTodayData = async () => {
        setLoading(true);
        try {
            const endpoints = getApiEndpoints();
            const response = await fetch(`${endpoints.salespersonToday}?user_id=${userId}`, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                setTodayData(data);
            } else {
                setError('Chyba při načítání dnešních dat');
            }
        } catch (error) {
            setError('Chyba při komunikaci se serverem');
        } finally {
            setLoading(false);
        }
    };

    const loadMonthlyData = async () => {
        setLoading(true);
        try {
            const endpoints = getApiEndpoints();
            const response = await fetch(`${endpoints.salespersonMonthly}?user_id=${userId}`, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                setMonthlyData(data);
            } else {
                setError('Chyba při načítání měsíčních dat');
            }
        } catch (error) {
            setError('Chyba při komunikaci se serverem');
        } finally {
            setLoading(false);
        }
    };

    const loadTodayPoints = async () => {
        setLoading(true);
        try {
            const endpoints = getApiEndpoints();
            const response = await fetch(`${endpoints.salespersonPointsToday}?user_id=${userId}`, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                setTodayPoints(data);
            } else {
                setError('Chyba při načítání dnešních bodů');
            }
        } catch (error) {
            setError('Chyba při komunikaci se serverem');
        } finally {
            setLoading(false);
        }
    };

    const loadMonthlyPoints = async () => {
        setLoading(true);
        try {
            const endpoints = getApiEndpoints();
            const response = await fetch(`${endpoints.salespersonPointsMonthly}?user_id=${userId}`, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                setMonthlyPoints(data);
            } else {
                setError('Chyba při načítání měsíčních bodů');
            }
        } catch (error) {
            setError('Chyba při komunikaci se serverem');
        } finally {
            setLoading(false);
        }
    };

    const loadHistoricalData = async () => {
        setLoading(true);
        try {
            const response = await fetch(`/api/analytics/salesperson/analytics/?user_id=${userId}&type=${dataType}&date=${selectedDate}`, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                setHistoricalData(data.data || []);
            } else {
                setError('Chyba při načítání historických dat');
            }
        } catch (error) {
            setError('Chyba při komunikaci se serverem');
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('cs-CZ');
    };

    const formatCurrency = (amount) => {
        if (amount === null || amount === undefined) return '0 Kč';
        return new Intl.NumberFormat('cs-CZ', {
            style: 'currency',
            currency: 'CZK',
            minimumFractionDigits: 0,
            maximumFractionDigits: 2,
        }).format(amount);
    };

    const formatNumber = (num) => {
        if (num === null || num === undefined) return '0';
        return new Intl.NumberFormat('cs-CZ').format(Math.round(num));
    };

    const renderServisMarzeRow = (payload) => {
        const marze = payload?.servisni_prace?.marze ?? 0;
        return (
            <div className="servis-marze-row">
                <span className="label">Servis marže celkem:</span>
                <span className="value">{formatNumber(marze)}</span>
            </div>
        );
    };

    const renderPointsCard = (title, pointsData) => {
        if (!pointsData || pointsData.source === 'none') {
            return (
                <div className="data-card no-data body-card">
                    <h3>{title}</h3>
                    <p>Pro toto období nejsou k dispozici žádná data</p>
                </div>
            );
        }

        if (pointsData.source === 'error') {
            return (
                <div className="data-card error body-card">
                    <h3>{title}</h3>
                    <p>{pointsData.message}</p>
                </div>
            );
        }

        return (
            <div className="data-card body-card">
                <div className="card-header">
                    <h3>{title}</h3>
                    <div className="points-badge large">
                        <i className="fas fa-star"></i>
                        {pointsData.total_points || 0} bodů
                    </div>
                </div>

                <div className="card-content">
                    <div className="body-info">
                        <p>Celkový bodový zisk za dané období</p>
                    </div>

                    {pointsData.breakdown && (
                        <div className="data-grid">
                            <div className="data-item">
                                <span className="label">Položky nad 100 Kč (15b):</span>
                                <span className="value">
                                    {pointsData.breakdown.polozky_nad_100.count}× = {pointsData.breakdown.polozky_nad_100.points}b
                                </span>
                            </div>
                            <div className="data-item">
                                <span className="label">CT300 (15b):</span>
                                <span className="value">
                                    {pointsData.breakdown.ct300.count}× = {pointsData.breakdown.ct300.points}b
                                </span>
                            </div>
                            <div className="data-item">
                                <span className="label">CT600 (50b):</span>
                                <span className="value">
                                    {pointsData.breakdown.ct600.count}× = {pointsData.breakdown.ct600.points}b
                                </span>
                            </div>
                            <div className="data-item">
                                <span className="label">CT1200 (100b):</span>
                                <span className="value">
                                    {pointsData.breakdown.ct1200.count}× = {pointsData.breakdown.ct1200.points}b
                                </span>
                            </div>
                            <div className="data-item">
                                <span className="label">AKT (30b):</span>
                                <span className="value">
                                    {pointsData.breakdown.akt.count}× = {pointsData.breakdown.akt.points}b
                                </span>
                            </div>
                            <div className="data-item">
                                <span className="label">ZAH250 (30b):</span>
                                <span className="value">
                                    {pointsData.breakdown.zah250.count}× = {pointsData.breakdown.zah250.points}b
                                </span>
                            </div>
                            <div className="data-item">
                                <span className="label">ZAH500 (50b):</span>
                                <span className="value">
                                    {pointsData.breakdown.zah500.count}× = {pointsData.breakdown.zah500.points}b
                                </span>
                            </div>
                            <div className="data-item">
                                <span className="label">KOP250 (30b):</span>
                                <span className="value">
                                    {pointsData.breakdown.kop250.count}× = {pointsData.breakdown.kop250.points}b
                                </span>
                            </div>
                            <div className="data-item">
                                <span className="label">NAP (50b):</span>
                                <span className="value">
                                    {pointsData.breakdown.nap.count}× = {pointsData.breakdown.nap.points}b
                                </span>
                            </div>
                            <div className="data-item">
                                <span className="label">PZ1 (100b):</span>
                                <span className="value">
                                    {pointsData.breakdown.pz1.count}× = {pointsData.breakdown.pz1.points}b
                                </span>
                            </div>
                            <div className="data-item">
                                <span className="label">KNZ (30b):</span>
                                <span className="value">
                                    {pointsData.breakdown.knz.count}× = {pointsData.breakdown.knz.points}b
                                </span>
                            </div>
                            <div className="data-item">
                                <span className="label">ALIGATOR (0b):</span>
                                <span className="value">
                                    {pointsData.breakdown.aligator.count}× = {pointsData.breakdown.aligator.points}b
                                </span>
                            </div>
                            {pointsData.breakdown.servis_marze && (
                                <div className="data-item servis-marze-points">
                                    <span className="label">
                                        Servis marže ({pointsData.breakdown.servis_marze.odmena_sazba ?? 10} %):
                                    </span>
                                    <span className="value">
                                        {formatNumber(pointsData.breakdown.servis_marze.marze)} → {formatNumber(pointsData.breakdown.servis_marze.points)}b
                                    </span>
                                </div>
                            )}

                        </div>
                    )}
                </div>

                <div className="data-source">
                    <small>Zdroj: {pointsData.source === 'database' ? 'Databáze' : 'Google Sheets'}</small>
                </div>
            </div>
        );
    };

    const renderDataCard = (title, data) => {
        if (!data || data.source === 'none') {
            return (
                <div className="data-card no-data">
                    <h3>{title}</h3>
                    <p>Pro toto období nejsou k dispozici žádná data</p>
                </div>
            );
        }

        return (
            <div className="data-card">
                <div className="card-header">
                    <h3>{title}</h3>
                    <div className="card-date">
                        {formatDate(data.date || new Date())}
                    </div>
                </div>

                <div className="card-content">
                    <div className="metrics-summary">
                        <div className="metric-item">
                            <div className="metric-value">{data.polozky_nad_100 || 0}</div>
                            <div className="metric-label">Položky nad 100 Kč</div>
                        </div>
                        <div className="metric-item">
                            <div className="metric-value">{data.sluzby_celkem || 0}</div>
                            <div className="metric-label">Služby celkem</div>
                        </div>
                        <div className="metric-item">
                            <div className="metric-value">{(data.prumer_polozek_uctu || 0).toFixed(2)}</div>
                            <div className="metric-label">Průměr pol./účtu</div>
                        </div>
                    </div>

                    {renderServisMarzeRow(data)}

                    <div className="products-grid">
                        <div className="product-item">
                            <span>CT300:</span>
                            <span>{data.ct300 || 0}</span>
                        </div>
                        <div className="product-item">
                            <span>CT600:</span>
                            <span>{data.ct600 || 0}</span>
                        </div>
                        <div className="product-item">
                            <span>CT1200:</span>
                            <span>{data.ct1200 || 0}</span>
                        </div>
                        <div className="product-item">
                            <span>AKT:</span>
                            <span>{data.akt || 0}</span>
                        </div>
                        <div className="product-item">
                            <span>ZAH250:</span>
                            <span>{data.zah250 || 0}</span>
                        </div>
                        <div className="product-item">
                            <span>NAP:</span>
                            <span>{data.nap || 0}</span>
                        </div>
                        <div className="product-item">
                            <span>ZAH500:</span>
                            <span>{data.zah500 || 0}</span>
                        </div>
                        <div className="product-item">
                            <span>KOP250:</span>
                            <span>{data.kop250 || 0}</span>
                        </div>
                        <div className="product-item">
                            <span>KOP500:</span>
                            <span>{data.kop500 || 0}</span>
                        </div>
                        <div className="product-item">
                            <span>PZ1:</span>
                            <span>{data.pz1 || 0}</span>
                        </div>
                        <div className="product-item">
                            <span>KNZ:</span>
                            <span>{data.knz || 0}</span>
                        </div>
                        <div className="product-item">
                            <span>ALIGATOR:</span>
                            <span>{data.aligator || 0}</span>
                        </div>
                    </div>
                </div>

                <div className="data-source">
                    <small>Zdroj: {data.source === 'database' ? 'Databáze' : 'Google Sheets'}</small>
                </div>
            </div>
        );
    };

    return (
        <div className="profile-analytics">
            <div className="analytics-header">
                <h2>Moje výsledky</h2>
                <p>Přehled vašich prodejních výsledků a bodového hodnocení</p>
            </div>

            {error && (
                <div className="error-message">
                    {error}
                </div>
            )}

            <div className="analytics-controls">
                <div className="data-type-toggle">
                    <button 
                        className={dataType === 'daily' ? 'active' : ''}
                        onClick={() => setDataType('daily')}
                    >
                        📅 Denní data
                    </button>
                    <button 
                        className={dataType === 'monthly' ? 'active' : ''}
                        onClick={() => setDataType('monthly')}
                    >
                        📊 Měsíční data
                    </button>
                    <button 
                        className={dataType === 'points' ? 'active' : ''}
                        onClick={() => setDataType('points')}
                    >
                        ⭐ Moje body
                    </button>
                </div>

                <div className="date-picker">
                    <label htmlFor="date-select">Vyberte datum:</label>
                    <input
                        type="date"
                        id="date-select"
                        value={selectedDate}
                        onChange={(e) => setSelectedDate(e.target.value)}
                    />
                </div>
            </div>

            <div className="analytics-grid">
                {dataType === 'points' ? (
                    <>
                        {renderPointsCard('Dnešní body', todayPoints)}
                        {renderPointsCard('Měsíční body', monthlyPoints)}
                    </>
                ) : (
                    <>
                        {renderDataCard('Dnešní výsledky', todayData)}
                        {renderDataCard('Měsíční výsledky', monthlyData)}                    </>
                )}
            </div>

            {selectedDate && dataType !== 'points' && (
                <div className="historical-data">
                    <h3>Výsledky za {formatDate(selectedDate)}</h3>
                    
                    {loading && <div className="loading">Načítání...</div>}
                    
                    {historicalData.length > 0 ? (
                        <div className="historical-cards">
                            {historicalData.map((data, index) => (
                                <div key={index} className="historical-card">
                                    {renderDataCard(`${dataType === 'daily' ? 'Denní' : 'Měsíční'} výsledky`, data)}
                                </div>
                            ))}
                        </div>
                    ) : (
                        !loading && <p>Žádná data nejsou k dispozici pro vybrané datum.</p>
                    )}
                </div>
            )}
        </div>
    );
};

export default ProfileAnalytics; 