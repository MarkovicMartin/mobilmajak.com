import React from 'react';
import { useLocation } from 'react-router-dom';
import BugButton from '../BugButton';
import { routeToLabel } from '../../utils/clarity';

const AppTopBar = ({ user, onMenuClick, isDarkMode, toggleTheme, drawerOpen = false, onDrawerClose }) => {
    const location = useLocation();
    const pageTitle = routeToLabel(location.pathname);

    return (
        <header className="app-topbar" role="banner">
            <button
                type="button"
                className="app-topbar__menu"
                onClick={drawerOpen ? onDrawerClose : onMenuClick}
                aria-expanded={drawerOpen}
                aria-controls="app-mobile-drawer"
                aria-label={drawerOpen ? 'Zavřít menu' : 'Otevřít menu'}
            >
                <span className="app-topbar__hamburger" />
            </button>
            <h1 className="app-topbar__title">{pageTitle}</h1>
            <div className="app-topbar__actions">
                {user && (
                    <BugButton user={user} variant="shell" />
                )}
                <button
                    type="button"
                    className="app-topbar__icon-btn"
                    onClick={toggleTheme}
                    title={isDarkMode ? 'Světlý režim' : 'Tmavý režim'}
                >
                    <i className={`fas ${isDarkMode ? 'fa-sun' : 'fa-moon'}`} />
                </button>
            </div>
        </header>
    );
};

export default AppTopBar;
