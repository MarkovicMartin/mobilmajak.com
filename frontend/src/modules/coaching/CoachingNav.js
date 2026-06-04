import React from 'react';
import { NavLink } from 'react-router-dom';
import { COACHING_SECTIONS } from './coachingSections';
import '../analytics/AnalyticsNav.css';
import './CoachingNav.css';

const CoachingNav = ({
    monthValue,
    monthOptions,
    onMonthChange,
    prodejnaId,
    prodejny,
    onProdejnaChange,
}) => (
    <header className="analytics-nav coaching-nav" aria-label="Navigace výkonů">
        <div className="analytics-nav-tabs" role="tablist">
            {COACHING_SECTIONS.map((section) => (
                <NavLink
                    key={section.id}
                    to={section.path ? `/coaching/${section.path}` : '/coaching'}
                    end={!section.path}
                    role="tab"
                    className={({ isActive }) =>
                        `analytics-nav-tab${isActive ? ' analytics-nav-tab--active' : ''}`
                    }
                >
                    <span className="analytics-nav-tab-icon" aria-hidden="true">{section.icon}</span>
                    <span className="analytics-nav-tab-label">{section.tabLabel}</span>
                </NavLink>
            ))}
        </div>
        <div className="analytics-nav-meta coaching-nav-meta">
            {prodejny?.length > 1 && (
                <label className="coaching-nav-filter">
                    <span className="coaching-nav-filter-label">Prodejna</span>
                    <select
                        className="coaching-nav-select"
                        value={prodejnaId}
                        onChange={(e) => onProdejnaChange(e.target.value)}
                    >
                        <option value="">Vše</option>
                        {prodejny.map((p) => (
                            <option key={p.id} value={p.id}>{p.nazev}</option>
                        ))}
                    </select>
                </label>
            )}
            <label className="coaching-nav-filter">
                <span className="coaching-nav-filter-label">Měsíc</span>
                <select
                    className="coaching-nav-select"
                    value={monthValue}
                    onChange={(e) => onMonthChange(e.target.value)}
                >
                    {monthOptions.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                </select>
            </label>
        </div>
    </header>
);

export default CoachingNav;
