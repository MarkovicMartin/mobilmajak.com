import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import ShellNavLinks, { ShellProfileLinks } from './ShellNavLinks';

const AppMobileDrawer = ({
    open,
    onClose,
    user,
    isAdmin,
    canManageTasks,
    canAccessCoaching,
    logout,
    isDarkMode,
    toggleTheme,
    profileTaskBadge,
}) => {
    const navigate = useNavigate();
    const location = useLocation();
    const auth = { isAdmin, canManageTasks, canAccessCoaching };

    return (
        <>
            <div
                className={`app-drawer-backdrop ${open ? 'app-drawer-backdrop--open' : ''}`}
                onClick={onClose}
                aria-hidden="true"
            />
            <nav
                id="app-mobile-drawer"
                className={`app-drawer ${open ? 'app-drawer--open' : ''}`}
                aria-label="Mobilní navigace"
                aria-hidden={!open}
            >
                <div className="app-drawer__header">
                    {user?.jmeno ? (
                        <span className="app-drawer__user">{user.jmeno}</span>
                    ) : (
                        <span className="app-drawer__user">MOBIL MAJÁK</span>
                    )}
                    <button
                        type="button"
                        className="app-drawer__close"
                        onClick={onClose}
                        aria-label="Zavřít menu"
                    >
                        ×
                    </button>
                </div>

                <div className="app-drawer__nav">
                    <ShellNavLinks
                        auth={auth}
                        location={location}
                        navigate={navigate}
                        mobile
                        profileTaskBadge={profileTaskBadge}
                        onNavigate={onClose}
                        linkClass="app-drawer__link"
                        activeClass="app-drawer__link--active"
                        childClass="app-drawer__link--child"
                        groupClass="app-drawer__group"
                        groupLabelClass="app-drawer__group-label"
                    />
                </div>

                <div className="app-drawer__footer">
                    <ShellProfileLinks
                        location={location}
                        navigate={navigate}
                        onNavigate={onClose}
                        linkClass="app-drawer__link"
                        activeClass="app-drawer__link--active"
                    />
                    <button
                        type="button"
                        className="app-drawer__link"
                        onClick={() => toggleTheme()}
                    >
                        <i className={`fas ${isDarkMode ? 'fa-sun' : 'fa-moon'}`} aria-hidden="true" />
                        {isDarkMode ? 'Světlý režim' : 'Tmavý režim'}
                    </button>
                    <button
                        type="button"
                        className="app-drawer__link app-drawer__link--logout"
                        onClick={() => {
                            logout();
                            onClose();
                        }}
                    >
                        <i className="fas fa-sign-out-alt" aria-hidden="true" />
                        Odhlásit
                    </button>
                </div>
            </nav>
        </>
    );
};

export default AppMobileDrawer;
