import React from 'react';
import { NavLink } from 'react-router-dom';
import '../styles/ModuleSubnav.css';

const accentClass = (accent) => {
    if (accent === 'blue') return 'module-subnav--accent-blue';
    if (accent === 'pink') return 'module-subnav--accent-pink';
    return 'module-subnav--accent-default';
};

const ModuleSubnav = ({
    tabs,
    activeId,
    onTabChange,
    meta,
    accent = 'pink',
    ariaLabel = 'Navigace modulu',
    className = '',
}) => (
    <header
        className={`module-subnav ${accentClass(accent)} ${className}`.trim()}
        aria-label={ariaLabel}
    >
        <div className="module-subnav-tabs" role="tablist">
            {tabs.map((tab) => {
                const content = (
                    <>
                        {tab.icon != null && (
                            <span className="module-subnav-tab-icon" aria-hidden="true">
                                {tab.icon}
                            </span>
                        )}
                        <span className="module-subnav-tab-label">{tab.label}</span>
                    </>
                );

                if (tab.to) {
                    return (
                        <NavLink
                            key={tab.id}
                            to={tab.to}
                            end={tab.end}
                            role="tab"
                            className={({ isActive }) =>
                                `module-subnav-tab${isActive ? ' module-subnav-tab--active' : ''}`
                            }
                        >
                            {content}
                        </NavLink>
                    );
                }

                return (
                    <button
                        key={tab.id}
                        type="button"
                        role="tab"
                        aria-selected={activeId === tab.id}
                        className={`module-subnav-tab${activeId === tab.id ? ' module-subnav-tab--active' : ''}`}
                        onClick={() => onTabChange?.(tab.id)}
                    >
                        {content}
                    </button>
                );
            })}
        </div>
        {meta ? <div className="module-subnav-meta">{meta}</div> : null}
    </header>
);

export default ModuleSubnav;
