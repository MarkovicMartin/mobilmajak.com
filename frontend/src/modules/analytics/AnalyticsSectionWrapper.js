import React from 'react';
import './AnalyticsSectionWrapper.css';

/** Obal sekce – navigace je v AnalyticsNav (záložky nahoře). */
const AnalyticsSectionWrapper = ({ children }) => (
    <div className="analytics-section-wrapper">
        <div className="section-content">{children}</div>
    </div>
);

export default AnalyticsSectionWrapper;

