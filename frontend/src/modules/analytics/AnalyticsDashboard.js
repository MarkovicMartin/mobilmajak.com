import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './AnalyticsDashboard.css';
import { analyticsAPI } from '../../services/api';

const AnalyticsDashboard = ({ currentUser }) => {
    const navigate = useNavigate();

    const [actorStatus, setActorStatus] = useState({
        level: 'loading',
        text: 'Načítám stav…',
    });

    const pickLastIso = (data) => {
        return (
            data?.web_prodeje_all_latest ||
            data?.last_daily_backup ||
            data?.last_monthly_backup ||
            data?.web_prodeje_latest ||
            data?.last_daily_import ||
            data?.last_monthly_import ||
            null
        );
    };

    const fetchActorStatus = async () => {
        try {
            const data = await analyticsAPI.getActorStatus();
            const lastIso = pickLastIso(data);
            if (!lastIso) {
                setActorStatus({ level: 'error', text: 'Actor: žádná data' });
                return;
            }
            const last = new Date(lastIso);
            const now = new Date();
            const diffMin = Math.round((now.getTime() - last.getTime()) / 60000);

            let level = 'ok';
            let label = 'běží';
            if (diffMin > 10 && diffMin <= 30) {
                level = 'warn';
                label = `zpožděn ~${diffMin} min`;
            } else if (diffMin > 30) {
                level = 'error';
                label = `neaktivní (${diffMin} min)`;
            }

            // Relativní čas
            const absDiff = Math.abs(diffMin);
            const rel = absDiff < 1
                ? 'před méně než minutou'
                : absDiff < 60
                    ? `před ${absDiff} min`
                    : `před ${Math.round(absDiff / 60)} h`;

            const timeLabel = last.toLocaleString('cs-CZ', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit', timeZoneName: 'short' });
            const sourceLabel = data?.data_source ? ` • zdroj ${data.data_source}` : '';
            setActorStatus({ level, text: `Actor: ${label} • ${rel}${sourceLabel}`, title: `Naposledy ${timeLabel}` });
        } catch (err) {
            setActorStatus({ level: 'error', text: 'Actor: chyba při načítání stavu' });
        }
    };

    useEffect(() => {
        fetchActorStatus();
        const intervalId = setInterval(fetchActorStatus, 60 * 1000);
        return () => clearInterval(intervalId);
    }, []);

    const sections = [
        {
            id: 'prodejny-polozky',
            name: 'Prodejny - Položky',
            icon: '📱',
            description: 'Analýza prodaných položek v prodejnách'
        },
        {
            id: 'prodejny-traffic',
            name: 'Prodejny & Zákazníci',
            icon: '🧑‍🤝‍🧑',
            description: 'Počet zákazníků podle unikátních dokladů'
        },
        {
            id: 'servis',
            name: 'Servis',
            icon: '🔧',
            description: 'Analýza servisních služeb'
        },
        {
            id: 'eshop',
            name: 'E-shop',
            icon: '🛒',
            description: 'Statistiky online prodeje'
        },
        {
            id: 'celkova-cisla',
            name: 'Celková čísla',
            icon: '📈',
            description: 'Souhrnné statistiky všech kanálů'
        },
        {
            id: 'prodejni-analytika',
            name: 'Prodejní analytika',
            icon: '🎯',
            description: 'Pokročilé analýzy prodeje a trendů'
        }
    ];

    const renderOverview = () => {
        return (
            <div className="analytics-overview">
                <h3>Přehled analytických sekcí</h3>
                <p>Vyberte sekci, kterou chcete analyzovat:</p>

                <div className="sections-grid">
                    {sections.map((section) => (
                        <div
                            key={section.id}
                            className="section-card"
                            onClick={() => navigate(`/analytics/${section.id}`)}
                        >
                            <div className="section-icon">{section.icon}</div>
                            <h4>{section.name}</h4>
                            <p>{section.description}</p>
                            <button className="section-btn">Otevřít</button>
                        </div>
                    ))}
                </div>
            </div>
        );
    };

    return (
        <div className="analytics-dashboard">
            <div className="dashboard-header">
                <h2>Dashboard analytiky</h2>
                <div className="dashboard-controls">
                    <div className={`actor-status actor-${actorStatus.level}`} title={actorStatus.title || "Stav automatického importu"}>
                        <span className="actor-dot" />
                        <span className="actor-text">{actorStatus.text}</span>
                    </div>
                    <select className="time-range-select">
                        <option value="today">Dnes</option>
                        <option value="week">Tento týden</option>
                        <option value="month">Tento měsíc</option>
                        <option value="quarter">Toto čtvrtletí</option>
                        <option value="year">Tento rok</option>
                        <option value="custom">Vlastní období</option>
                    </select>
                    <button className="refresh-btn" onClick={fetchActorStatus}>🔄 Obnovit</button>
                </div>
            </div>

            <div className="dashboard-content">
                {renderOverview()}
            </div>
        </div>
    );
};

export default AnalyticsDashboard; 