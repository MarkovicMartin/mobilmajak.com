import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import AnalyticsDashboard from './AnalyticsDashboard';
import ProdejnyPolozky from './sections/ProdejnyPolozky';
import ProdejnyTraffic from './sections/ProdejnyTraffic';
import Servis from './sections/Servis';
import Eshop from './sections/Eshop';
import CelkovaCisla from './sections/CelkovaCisla';
import ProdejniAnalytika from './sections/ProdejniAnalytika';
import './AnalyticsModule.css';

const AnalyticsModule = ({ currentUser }) => {
    return (
        <div className="analytics-module">
            <div className="analytics-header">
                <h2>📊 Analytika</h2>
                <p>Přehled statistik a analýz prodeje</p>
            </div>

            <div className="analytics-content">
                <Routes>
                    <Route index element={<AnalyticsDashboard currentUser={currentUser} />} />
                    <Route path="prodejny-polozky" element={<ProdejnyPolozky currentUser={currentUser} />} />
                    <Route path="prodejny-traffic" element={<ProdejnyTraffic currentUser={currentUser} />} />
                    <Route path="servis" element={<Servis currentUser={currentUser} />} />
                    <Route path="eshop" element={<Eshop currentUser={currentUser} />} />
                    <Route path="celkova-cisla" element={<CelkovaCisla currentUser={currentUser} />} />
                    <Route path="prodejni-analytika" element={<ProdejniAnalytika currentUser={currentUser} />} />
                    <Route path="*" element={<Navigate to="/analytics" replace />} />
                </Routes>
            </div>
        </div>
    );
};

export default AnalyticsModule; 