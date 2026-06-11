import React from 'react';
import { NavLink } from 'react-router-dom';
import './Tabs.css';

const accentClass = (accent, legacy) => {
    if (!legacy) return '';
    if (accent === 'blue') return 'module-subnav--accent-blue';
    if (accent === 'pink') return 'module-subnav--accent-pink';
    return 'module-subnav--accent-default';
};

/**
 * Modulové záložky – URL (NavLink) nebo stav (tlačítka).
 * legacy=true používá třídy module-subnav pro zpětnou kompatibilitu.
 */
const Tabs = ({
    tabs,
    activeId,
    onTabChange,
    meta,
    accent = 'pink',
    ariaLabel = 'Navigace modulu',
    className = '',
    legacy = false,
}) => {
    const rootClass = legacy
        ? `module-subnav ${accentClass(accent, true)} ${className}`.trim()
        : `ui-tabs ${className}`.trim();
    const listClass = legacy ? 'module-subnav-tabs' : 'ui-tabs__list';
    const tabBase = legacy ? 'module-subnav-tab' : 'ui-tabs__tab';
    const tabActive = legacy ? ' module-subnav-tab--active' : ' ui-tabs__tab--active';
    const iconClass = legacy ? 'module-subnav-tab-icon' : 'ui-tabs__icon';
    const labelClass = legacy ? 'module-subnav-tab-label' : 'ui-tabs__label';
    const metaClass = legacy ? 'module-subnav-meta' : 'ui-tabs__meta';

    return (
        <header className={rootClass} aria-label={ariaLabel}>
            <div className={listClass} role="tablist">
                {tabs.map((tab) => {
                    const content = (
                        <>
                            {tab.icon != null && (
                                <span className={iconClass} aria-hidden="true">
                                    {tab.icon}
                                </span>
                            )}
                            <span className={labelClass}>{tab.label}</span>
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
                                    `${tabBase}${isActive ? tabActive : ''}`
                                }
                            >
                                {content}
                            </NavLink>
                        );
                    }

                    const isActive = activeId === tab.id;
                    return (
                        <button
                            key={tab.id}
                            type="button"
                            role="tab"
                            aria-selected={isActive}
                            className={`${tabBase}${isActive ? tabActive : ''}`}
                            onClick={() => onTabChange?.(tab.id)}
                        >
                            {content}
                        </button>
                    );
                })}
            </div>
            {meta ? <div className={metaClass}>{meta}</div> : null}
        </header>
    );
};

export default Tabs;
