import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import ShellNavLinks, { ShellProfileLinks } from './ShellNavLinks';

const AppSidebar = ({
    isAdmin,
    canManageTasks,
    canAccessCoaching,
    logout,
    isDarkMode,
    toggleTheme,
    profileTaskBadge,
    collapsed,
    onToggleCollapse,
}) => {
    const navigate = useNavigate();
    const location = useLocation();
    const auth = { isAdmin, canManageTasks, canAccessCoaching };

    return (
        <aside
            className={`app-sidebar ${collapsed ? 'app-sidebar--collapsed' : ''}`}
            aria-label="Hlavní navigace"
        >
            <div className="app-sidebar__brand">
                <div className="app-sidebar__logo" aria-hidden="true">
                    MM
                </div>
                {!collapsed && <h1 className="app-sidebar__title">MOBIL MAJÁK</h1>}
                <button
                    type="button"
                    className="app-sidebar__collapse-btn"
                    onClick={onToggleCollapse}
                    title={collapsed ? 'Rozbalit menu' : 'Sbalit menu'}
                    aria-label={collapsed ? 'Rozbalit menu' : 'Sbalit menu'}
                >
                    <i className={`fas fa-chevron-${collapsed ? 'right' : 'left'}`} />
                </button>
            </div>

            <nav className="app-sidebar__nav">
                <ShellNavLinks
                    auth={auth}
                    location={location}
                    navigate={navigate}
                    collapsed={collapsed}
                    profileTaskBadge={profileTaskBadge}
                    linkClass="app-sidebar__link"
                    activeClass="app-sidebar__link--active"
                    childClass="app-sidebar__link--child"
                    groupClass="app-sidebar__group"
                    groupLabelClass="app-sidebar__group-label"
                />
            </nav>

            <div className="app-sidebar__footer">
                <div className="app-sidebar__footer-row">
                    <div className="app-sidebar__profile-wrap">
                        <ShellProfileLinks
                            location={location}
                            navigate={navigate}
                            collapsed={collapsed}
                            linkClass="app-sidebar__link"
                            activeClass="app-sidebar__link--active"
                        />
                    </div>
                    <button
                        type="button"
                        className="app-sidebar__icon-btn"
                        onClick={toggleTheme}
                        title={isDarkMode ? 'Světlý režim' : 'Tmavý režim'}
                    >
                        <i className={`fas ${isDarkMode ? 'fa-sun' : 'fa-moon'}`} />
                    </button>
                </div>
                <div className="app-sidebar__footer-row">
                    <button
                        type="button"
                        className="app-sidebar__link app-sidebar__link--logout"
                        onClick={logout}
                        title={collapsed ? 'Odhlásit' : undefined}
                    >
                        <i className="fas fa-sign-out-alt" aria-hidden="true" />
                        {!collapsed && <span className="shell-nav__label">Odhlásit</span>}
                    </button>
                </div>
            </div>
        </aside>
    );
};

export default AppSidebar;
