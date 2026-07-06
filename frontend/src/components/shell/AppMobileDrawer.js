import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import ShellBrand from '../brand/ShellBrand';
import ShellNavLinks, { ShellProfileLinks } from './ShellNavLinks';
import NotificationCenter from './NotificationCenter';

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
    reklamaceNotifBadge,
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
                        <ShellBrand />
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
                        reklamaceNotifBadge={reklamaceNotifBadge}
                        onNavigate={onClose}
                        linkClass="app-drawer__link"
                        activeClass="app-drawer__link--active"
                        childClass="app-drawer__link--child"
                        groupClass="app-drawer__group"
                        groupLabelClass="app-drawer__group-label"
                    />
                </div>

                <div className="app-drawer__footer">
                    <div className="app-drawer__footer-row">
                        <ShellProfileLinks
                            location={location}
                            navigate={navigate}
                            onNavigate={onClose}
                            linkClass="app-drawer__link"
                            activeClass="app-drawer__link--active"
                            childClass="app-drawer__link--child"
                        />
                        <NotificationCenter />
                    </div>
                    <div className="app-drawer__footer-row app-drawer__footer-row--logout">
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
                        <button
                            type="button"
                            className="app-sidebar__icon-btn"
                            onClick={() => toggleTheme()}
                            title={isDarkMode ? 'Světlý režim' : 'Tmavý režim'}
                        >
                            <i className={`fas ${isDarkMode ? 'fa-sun' : 'fa-moon'}`} aria-hidden="true" />
                        </button>
                    </div>
                </div>
            </nav>
        </>
    );
};

export default AppMobileDrawer;
