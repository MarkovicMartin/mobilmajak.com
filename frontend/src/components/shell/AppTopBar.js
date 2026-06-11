import React from 'react';
import { useLocation } from 'react-router-dom';
import BugButton from '../BugButton';
import { routeToLabel } from '../../utils/clarity';

const AppTopBar = ({ onMenuClick, user, isDarkMode, toggleTheme }) => {
    const location = useLocation();
    const pageTitle = routeToLabel(location.pathname);

    return (
        <header className="app-topbar" role="banner">
            <button
                type="button"
                className="app-topbar__menu"
                onClick={onMenuClick}
                aria-expanded="false"
                aria-controls="app-mobile-drawer"
                aria-label="Otevřít menu"
            >
                <span className="app-topbar__hamburger" />
            </button>
            <h1 className="app-topbar__title">{pageTitle}</h1>
            <div className="app-topbar__actions">
                <button
                    type="button"
                    className="app-topbar__icon-btn"
                    onClick={toggleTheme}
                    title={isDarkMode ? 'Světlý režim' : 'Tmavý režim'}
                >
                    <i className={`fas ${isDarkMode ? 'fa-sun' : 'fa-moon'}`} />
                </button>
                <BugButton user={user} />
            </div>
        </header>
    );
};

export default AppTopBar;
