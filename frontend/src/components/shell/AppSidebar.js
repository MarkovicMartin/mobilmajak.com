import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import BugButton from '../BugButton';
import { getVisibleNavGroups, isNavActive } from '../../config/navigation';

const AppSidebar = ({
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

    const go = (path) => navigate(path);

    return (
        <aside className="app-sidebar" aria-label="Hlavní navigace">
            <div className="app-sidebar__brand">
                <div className="app-sidebar__logo" aria-hidden="true">MM</div>
                <h1 className="app-sidebar__title">MOBIL MAJÁK</h1>
            </div>

            <nav className="app-sidebar__nav">
                {groups.map((group) => (
                    <div key={group.id} className="app-sidebar__group">
                        <span className="app-sidebar__group-label">{group.label}</span>
                        {group.items.map((item) => {
                            const active = isNavActive(item.path, location.pathname);
                            return (
                                <button
                                    key={item.sectionKey}
                                    type="button"
                                    className={`app-sidebar__link ${active ? 'app-sidebar__link--active' : ''}`}
                                    onClick={() => go(item.path)}
                                    aria-current={active ? 'page' : undefined}
                                >
                                    <i className={`fas ${item.icon}`} aria-hidden="true" />
                                    {item.label}
                                </button>
                            );
                        })}
                    </div>
                ))}
            </nav>

            <div className="app-sidebar__footer">
                <div className="app-sidebar__footer-row">
                    <div className="app-sidebar__profile-wrap">
                        <button
                            type="button"
                            className={`app-sidebar__link ${location.pathname === '/profile' ? 'app-sidebar__link--active' : ''}`}
                            onClick={() => go('/profile')}
                        >
                            <i className="fas fa-user" aria-hidden="true" />
                            Můj profil
                        </button>
                        {profileTaskBadge > 0 && (
                            <span className="app-sidebar__badge" aria-label={`${profileTaskBadge} upozornění`}>
                                {profileTaskBadge > 99 ? '99+' : profileTaskBadge}
                            </span>
                        )}
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
                    <BugButton user={user} />
                    <button
                        type="button"
                        className="app-sidebar__link app-sidebar__link--logout"
                        onClick={logout}
                    >
                        <i className="fas fa-sign-out-alt" aria-hidden="true" />
                        Odhlásit
                    </button>
                </div>
            </div>
        </aside>
    );
};

export default AppSidebar;
