import React from 'react';
import { getDataSourceName, getDataSourceDescription, isApifyEnabled } from '../config/apiConfig';
import './DataSourceInfo.css';

const DataSourceInfo = ({ showDetails = false }) => {
    const sourceName = getDataSourceName();
    const sourceDescription = getDataSourceDescription();
    const isApify = isApifyEnabled();
    
    if (!showDetails) {
        return (
            <div className={`data-source-badge ${isApify ? 'apify' : 'google-sheets'}`}>
                <span className="data-source-icon">
                    {isApify ? '🤖' : '📊'}
                </span>
                <span className="data-source-name">{sourceName}</span>
            </div>
        );
    }
    
    return (
        <div className={`data-source-info ${isApify ? 'apify' : 'google-sheets'}`}>
            <div className="data-source-header">
                <span className="data-source-icon">
                    {isApify ? '🤖' : '📊'}
                </span>
                <div className="data-source-details">
                    <h4 className="data-source-title">Zdroj dat: {sourceName}</h4>
                    <p className="data-source-description">{sourceDescription}</p>
                </div>
            </div>
            
            {isApify && (
                <div className="data-source-features">
                    <div className="feature">
                        <span className="feature-icon">✅</span>
                        <span>Automatické extrakce z eshopu</span>
                    </div>
                    <div className="feature">
                        <span className="feature-icon">⚡</span>
                        <span>Real-time aktualizace</span>
                    </div>
                    <div className="feature">
                        <span className="feature-icon">🛡️</span>
                        <span>Spolehlivé ukládání do databáze</span>
                    </div>
                </div>
            )}
            
            {!isApify && (
                <div className="data-source-warning">
                    <div className="warning">
                        <span className="warning-icon">⚠️</span>
                        <span>Tato implementace je zastaralá a bude v budoucnu odstraněna</span>
                    </div>
                </div>
            )}
        </div>
    );
};

export default DataSourceInfo; 