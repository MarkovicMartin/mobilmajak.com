import React from 'react';
import { Link } from 'react-router-dom';
import './PageHeader.css';

/**
 * Jednotná hlavička stránky – nadpis, podtitul, akce, volitelné breadcrumbs.
 */
const PageHeader = ({
    title,
    subtitle,
    actions,
    breadcrumbs,
    className = '',
    titleAs: TitleTag = 'h1',
}) => (
    <header className={`page-header ui-page-header ${className}`.trim()}>
        <div className="page-header__titles ui-page-header__main">
            {breadcrumbs != null && breadcrumbs !== false && (
                <nav className="ui-page-header__breadcrumbs" aria-label="Drobečková navigace">
                    {Array.isArray(breadcrumbs) ? (
                        <ol className="ui-page-header__breadcrumb-list">
                            {breadcrumbs.map((crumb, index) => {
                                const isLast = index === breadcrumbs.length - 1;
                                const key = crumb.id || crumb.to || crumb.label || index;
                                return (
                                    <li key={key} className="ui-page-header__breadcrumb-item">
                                        {crumb.to && !isLast ? (
                                            <Link to={crumb.to} className="ui-page-header__breadcrumb-link">
                                                {crumb.label}
                                            </Link>
                                        ) : (
                                            <span
                                                className="ui-page-header__breadcrumb-current"
                                                aria-current={isLast ? 'page' : undefined}
                                            >
                                                {crumb.label}
                                            </span>
                                        )}
                                    </li>
                                );
                            })}
                        </ol>
                    ) : (
                        breadcrumbs
                    )}
                </nav>
            )}
            {title != null && title !== false && (
                <TitleTag className="page-header__title ui-page-header__title">{title}</TitleTag>
            )}
            {subtitle != null && subtitle !== false && (
                <p className="page-header__subtitle ui-page-header__subtitle">{subtitle}</p>
            )}
        </div>
        {actions != null && actions !== false && (
            <div className="page-header__actions ui-page-header__actions">{actions}</div>
        )}
    </header>
);

export default PageHeader;
