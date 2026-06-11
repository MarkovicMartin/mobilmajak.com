import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getVisibleNavGroups } from '../config/navigation';
import './DashboardModuleHub.css';

/**
 * Rychlé odkazy na moduly podle role – jediný zdroj z navigation.js.
 */
export default function DashboardModuleHub({ excludePaths = ['/'] }) {
    const navigate = useNavigate();
    const auth = useAuth();
    const exclude = useMemo(() => new Set(excludePaths), [excludePaths]);

    const items = useMemo(() => {
        const groups = getVisibleNavGroups({
            isAdmin: auth.isAdmin,
            canManageTasks: auth.canManageTasks,
            canAccessCoaching: auth.canAccessCoaching,
        });
        return groups.flatMap((g) => g.items).filter((item) => !exclude.has(item.path));
    }, [auth, exclude]);

    if (items.length === 0) return null;

    const activate = (path) => (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            navigate(path);
        }
    };

    return (
        <section className="dashboard-module-hub" aria-label="Moduly aplikace">
            <h2 className="dashboard-module-hub__title">Moduly</h2>
            <div className="dashboard-module-hub__grid">
                {items.map((item) => (
                    <button
                        key={item.sectionKey}
                        type="button"
                        className="dashboard-module-hub__card"
                        onClick={() => navigate(item.path)}
                        onKeyDown={activate(item.path)}
                    >
                        <i className={`fas ${item.icon} dashboard-module-hub__icon`} aria-hidden="true" />
                        <span className="dashboard-module-hub__label">{item.label}</span>
                    </button>
                ))}
            </div>
        </section>
    );
}
