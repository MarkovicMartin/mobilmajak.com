import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { getVisibleNavGroups, isNavActive } from '../../config/navigation';

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
    const groups = getVisibleNavGroups({ isAdmin, canManageTasks, canAccessCoaching });

    const go = (path) => {
        navigate(path);
        onClose();
    };

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
                    {groups.map((group) => (
                        <div key={group.id} className="app-drawer__group">
                            <span className="app-drawer__group-label">{group.label}</span>
                            {group.items.map((item) => {
                                const active = isNavActive(item.path, location.pathname);
                                return (
                                    <button
                                        key={item.sectionKey}
                                        type="button"
                                        className={`app-drawer__link ${active ? 'app-drawer__link--active' : ''}`}
                                        onClick={() => go(item.path)}
                                    >
                                        <i className={`fas ${item.icon}`} aria-hidden="true" />
                                        {item.label}
                                    </button>
                                );
                            })}
                        </div>
                    ))}
                </div>

                <div className="app-drawer__footer">
                    <button
                        type="button"
                        className={`app-drawer__link ${location.pathname === '/profile' ? 'app-drawer__link--active' : ''}`}
                        onClick={() => go('/profile')}
                    >
                        <i className="fas fa-user" aria-hidden="true" />
                        Můj profil
                        {profileTaskBadge > 0 && (
                            <span className="badge app-drawer__profile-badge">
                                {profileTaskBadge > 99 ? '99+' : profileTaskBadge}
                            </span>
                        )}
                    </button>
                    <button
                        type="button"
                        className="app-drawer__link"
                        onClick={() => {
                            toggleTheme();
                        }}
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
