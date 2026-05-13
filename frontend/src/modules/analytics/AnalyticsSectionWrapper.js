import React from 'react';
import { useNavigate } from 'react-router-dom';
import './AnalyticsSectionWrapper.css';

const AnalyticsSectionWrapper = ({ title, icon, children }) => {
    const navigate = useNavigate();

    return (
        <div className="analytics-section-wrapper">
            <div className="section-header">
                <button 
                    className="back-btn"
                    onClick={() => navigate('/analytics')}
                    title="Zpět na přehled sekcí"
                >
                    ← Zpět na přehled
                </button>
                <h3 className="section-title">
                    <span className="section-icon">{icon}</span>
                    {title}
                </h3>
            </div>
            <div className="section-content">
                {children}
            </div>
        </div>
    );
};

export default AnalyticsSectionWrapper;

