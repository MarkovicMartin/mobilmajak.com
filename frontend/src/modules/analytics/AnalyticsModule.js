import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import AnalyticsNav from './AnalyticsNav';
import { DEFAULT_ANALYTICS_SECTION } from './analyticsSections';
import ProdejnyPolozky from './sections/ProdejnyPolozky';
import ProdejnyTraffic from './sections/ProdejnyTraffic';
import Servis from './sections/Servis';
import Eshop from './sections/Eshop';
import CelkovaCisla from './sections/CelkovaCisla';
import ProdejniAnalytika from './sections/ProdejniAnalytika';
import './AnalyticsModule.css';
import './AnalyticsDensity.css';

const AnalyticsModule = ({ currentUser }) => {
    return (
        <div className="analytics-module">
            <AnalyticsNav />
            <div className="analytics-content">
                <Routes>
                    <Route
                        index
                        element={<Navigate to={`/analytics/${DEFAULT_ANALYTICS_SECTION}`} replace />}
                    />
                    <Route path="prodejny-polozky" element={<ProdejnyPolozky currentUser={currentUser} />} />
                    <Route path="prodejny-traffic" element={<ProdejnyTraffic currentUser={currentUser} />} />
                    <Route path="servis" element={<Servis currentUser={currentUser} />} />
                    <Route path="eshop" element={<Eshop currentUser={currentUser} />} />
                    <Route path="celkova-cisla" element={<CelkovaCisla currentUser={currentUser} />} />
                    <Route path="prodejni-analytika" element={<ProdejniAnalytika currentUser={currentUser} />} />
                    <Route path="*" element={<Navigate to={`/analytics/${DEFAULT_ANALYTICS_SECTION}`} replace />} />
                </Routes>
            </div>
        </div>
    );
};

export default AnalyticsModule; 