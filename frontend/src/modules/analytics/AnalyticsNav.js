import React, { useCallback, useEffect, useState } from 'react';
import { analyticsAPI } from '../../services/api';
import ModuleSubnav from '../../components/ModuleSubnav';
import { ANALYTICS_SECTIONS } from './analyticsSections';
import './AnalyticsNav.css';

const pickLastIso = (data) =>
    data?.web_prodeje_all_latest ||
    data?.last_daily_backup ||
    data?.last_monthly_backup ||
    data?.web_prodeje_latest ||
    data?.last_daily_import ||
    data?.last_monthly_import ||
    null;

const AnalyticsNav = () => {
    const [actorStatus, setActorStatus] = useState({
        level: 'loading',
        text: 'Načítám stav…',
    });

    const fetchActorStatus = useCallback(async () => {
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

            const absDiff = Math.abs(diffMin);
            const rel =
                absDiff < 1
                    ? 'před méně než minutou'
                    : absDiff < 60
                      ? `před ${absDiff} min`
                      : `před ${Math.round(absDiff / 60)} h`;

            const timeLabel = last.toLocaleString('cs-CZ', {
                hour: '2-digit',
                minute: '2-digit',
                day: '2-digit',
                month: '2-digit',
                timeZoneName: 'short',
            });
            const sourceLabel = data?.data_source ? ` • zdroj ${data.data_source}` : '';
            setActorStatus({
                level,
                text: `Actor: ${label} • ${rel}${sourceLabel}`,
                title: `Naposledy ${timeLabel}`,
            });
        } catch {
            setActorStatus({ level: 'error', text: 'Actor: chyba při načítání' });
        }
    }, []);

    useEffect(() => {
        fetchActorStatus();
        const intervalId = window.setInterval(fetchActorStatus, 60 * 1000);
        return () => window.clearInterval(intervalId);
    }, [fetchActorStatus]);

    const tabs = ANALYTICS_SECTIONS.map((section) => ({
        id: section.id,
        label: section.tabLabel,
        icon: section.icon,
        to: `/analytics/${section.id}`,
    }));

    const meta = (
        <>
            <div
                className={`actor-status actor-${actorStatus.level}`}
                title={actorStatus.title || 'Stav automatického importu'}
            >
                <span className="actor-dot" />
                <span className="actor-text">{actorStatus.text}</span>
            </div>
            <button
                type="button"
                className="analytics-nav-refresh"
                onClick={fetchActorStatus}
                title="Obnovit stav importu"
            >
                🔄
            </button>
        </>
    );

    return (
        <ModuleSubnav
            tabs={tabs}
            meta={meta}
            accent="pink"
            ariaLabel="Navigace analytiky"
            className="analytics-nav"
        />
    );
};

export default AnalyticsNav;
