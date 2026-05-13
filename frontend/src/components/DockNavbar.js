import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion, LayoutGroup } from 'framer-motion';
import AdminDropdown from './AdminDropdown';
import BugButton from './BugButton';
import './DockNavbar.css';

export const NAV_ITEMS = [
    { sectionKey: 'main', label: 'Domů', path: '/', adminOnly: false, icon: 'fa-home' },
    { sectionKey: 'news', label: 'Novinky', path: '/news', adminOnly: false, icon: 'fa-newspaper' },
    { sectionKey: 'analytics', label: 'Analytika', path: '/analytics', adminOnly: true, icon: 'fa-chart-bar' },
    { sectionKey: 'plans', label: 'Plány', path: '/plans', adminOnly: true, icon: 'fa-tasks' },
    { sectionKey: 'shifts', label: 'Směny', path: '/shifts', adminOnly: false, icon: 'fa-calendar-alt' },
    { sectionKey: 'leaderboard', label: 'Žebříček', path: '/leaderboard', adminOnly: false, icon: 'fa-trophy' },
    { sectionKey: 'access', label: 'Přístupy', path: '/access', adminOnly: false, icon: 'fa-key' },
];

export const isNavActive = (path, locationPath) => {
    if (path === '/') return locationPath === '/';
    return locationPath === path || locationPath.startsWith(path + '/');
};

const springHover = { type: 'spring', stiffness: 300, damping: 22 };

const DockNavbar = ({
    user,
    isAdmin,
    logout,
    isDarkMode,
    toggleTheme,
}) => {
    const navigate = useNavigate();
    const location = useLocation();
    const [mobileNavOpen, setMobileNavOpen] = useState(false);

    const closeMobileNav = () => setMobileNavOpen(false);

    useEffect(() => {
        closeMobileNav();
    }, [location.pathname]);

    useEffect(() => {
        const mq = window.matchMedia('(max-width: 768px)');
        const handleChange = () => {
            if (!mq.matches) closeMobileNav();
        };
        mq.addEventListener('change', handleChange);
        return () => mq.removeEventListener('change', handleChange);
    }, []);

    useEffect(() => {
        if (mobileNavOpen) {
            document.body.style.overflow = 'hidden';
            const handleEscape = (e) => {
                if (e.key === 'Escape') closeMobileNav();
            };
            document.addEventListener('keydown', handleEscape);
            return () => {
                document.body.style.overflow = '';
                document.removeEventListener('keydown', handleEscape);
            };
        }
        document.body.style.overflow = '';
    }, [mobileNavOpen]);

    const visibleNavItems = NAV_ITEMS.filter((item) => !item.adminOnly || isAdmin());

    const handleLogout = () => {
        logout();
    };

    return (
        <>
            <header className="dock-navbar" role="banner">
                {/* Mobilní horní lišta */}
                <div className="dock-navbar-mobile">
                    <div className="dock-mobile-wrap">
                        <div className="dock-mobile-bar">
                            <button
                                className="dock-mobile-toggle"
                                onClick={() => setMobileNavOpen((o) => !o)}
                                aria-expanded={mobileNavOpen}
                                aria-controls="mobile-nav-drawer"
                                aria-label={mobileNavOpen ? 'Zavřít menu' : 'Otevřít menu'}
                                type="button"
                            >
                                <span className="dock-hamburger-line" />
                                <span className="dock-hamburger-line" />
                                <span className="dock-hamburger-line" />
                            </button>
                            <div className="dock-mobile-actions">
                                <button
                                    type="button"
                                    className="dock-icon-btn dock-icon-btn--compact"
                                    onClick={toggleTheme}
                                    title={isDarkMode ? 'Světlý režim' : 'Tmavý režim'}
                                >
                                    <i className={`fas ${isDarkMode ? 'fa-sun' : 'fa-moon'}`} />
                                </button>
                                {isAdmin() && <AdminDropdown onOpen={() => setMobileNavOpen(false)} />}
                                <BugButton user={user} onOpen={() => setMobileNavOpen(false)} />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Desktop dock */}
                <div className="dock-navbar-desktop">
                    <motion.div
                        className="dock-glass"
                        animate={{ y: [0, -3, 0] }}
                        transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
                    >
                        <LayoutGroup>
                            <nav className="dock-nav-icons" aria-label="Hlavní navigace">
                                {visibleNavItems.map((item) => {
                                    const active = isNavActive(item.path, location.pathname);
                                    return (
                                        <motion.div
                                            key={item.sectionKey}
                                            className="dock-nav-item-wrap"
                                            whileHover={{ scale: 1.12, rotate: -4 }}
                                            transition={springHover}
                                        >
                                            <button
                                                type="button"
                                                className={`dock-icon-btn ${active ? 'dock-icon-btn--active' : ''}`}
                                                onClick={() => navigate(item.path)}
                                                data-tooltip={item.label}
                                                title={item.label}
                                            >
                                                <i className={`fas ${item.icon}`} />
                                                {active && (
                                                    <motion.span
                                                        layoutId="dock-active-dot"
                                                        className="dock-active-dot"
                                                        transition={springHover}
                                                    />
                                                )}
                                            </button>
                                        </motion.div>
                                    );
                                })}
                            </nav>
                        </LayoutGroup>

                        <div className="dock-sep" aria-hidden="true" />

                        <div className="dock-actions">
                            <motion.div whileHover={{ scale: 1.12, rotate: -4 }} transition={springHover}>
                                <button
                                    type="button"
                                    className="dock-icon-btn"
                                    onClick={toggleTheme}
                                    data-tooltip={isDarkMode ? 'Světlý režim' : 'Tmavý režim'}
                                    title={isDarkMode ? 'Světlý režim' : 'Tmavý režim'}
                                >
                                    <i className={`fas ${isDarkMode ? 'fa-sun' : 'fa-moon'}`} />
                                </button>
                            </motion.div>

                            {isAdmin() && (
                                <motion.div whileHover={{ scale: 1.08 }} transition={springHover} className="dock-slot">
                                    <AdminDropdown onOpen={() => setMobileNavOpen(false)} />
                                </motion.div>
                            )}
                            <motion.div whileHover={{ scale: 1.08 }} transition={springHover} className="dock-slot">
                                <BugButton user={user} onOpen={() => setMobileNavOpen(false)} />
                            </motion.div>

                            <motion.div whileHover={{ scale: 1.12, rotate: -4 }} transition={springHover}>
                                <button
                                    type="button"
                                    className={`dock-icon-btn ${location.pathname === '/profile' ? 'dock-icon-btn--active' : ''}`}
                                    onClick={() => navigate('/profile')}
                                    data-tooltip="Můj profil"
                                    title="Můj profil"
                                >
                                    <i className="fas fa-user" />
                                    {location.pathname === '/profile' && (
                                        <motion.span
                                            layoutId="dock-active-dot-profile"
                                            className="dock-active-dot"
                                            transition={springHover}
                                        />
                                    )}
                                </button>
                            </motion.div>

                            <motion.div whileHover={{ scale: 1.12, rotate: -4 }} transition={springHover}>
                                <button
                                    type="button"
                                    className="dock-icon-btn dock-icon-btn--logout"
                                    onClick={handleLogout}
                                    data-tooltip="Odhlásit"
                                    title="Odhlásit"
                                >
                                    <i className="fas fa-sign-out-alt" />
                                </button>
                            </motion.div>
                        </div>
                    </motion.div>
                </div>
            </header>

            <div
                className={`mobile-nav-backdrop ${mobileNavOpen ? 'open' : ''}`}
                onClick={closeMobileNav}
                aria-hidden="true"
            />
            <nav
                id="mobile-nav-drawer"
                className={`mobile-nav-drawer ${mobileNavOpen ? 'open' : ''}`}
                aria-label="Mobilní navigace"
            >
                <button
                    className="mobile-nav-close"
                    onClick={closeMobileNav}
                    aria-label="Zavřít menu"
                    type="button"
                >
                    ×
                </button>
                {user?.jmeno && (
                    <div className="mobile-nav-user-banner">{user.jmeno}</div>
                )}
                <ul
                    className={`mobile-nav-list ${user?.jmeno ? 'mobile-nav-list--with-user' : ''}`}
                >
                    {visibleNavItems.map((item) => (
                        <li key={item.sectionKey}>
                            <button
                                className={`mobile-nav-link ${isNavActive(item.path, location.pathname) ? 'active' : ''}`}
                                onClick={() => {
                                    navigate(item.path);
                                    closeMobileNav();
                                }}
                                type="button"
                            >
                                <i className={`fas ${item.icon}`} />
                                {item.label}
                            </button>
                        </li>
                    ))}
                    <li>
                        <button
                            className={`mobile-nav-link ${location.pathname === '/profile' ? 'active' : ''}`}
                            onClick={() => {
                                navigate('/profile');
                                closeMobileNav();
                            }}
                            type="button"
                        >
                            <i className="fas fa-user" /> Můj profil
                        </button>
                    </li>
                    <li>
                        <button
                            className="mobile-nav-link mobile-nav-link--logout"
                            onClick={() => {
                                handleLogout();
                                closeMobileNav();
                            }}
                            type="button"
                        >
                            <i className="fas fa-sign-out-alt" /> Odhlásit
                        </button>
                    </li>
                </ul>
            </nav>
        </>
    );
};

export default DockNavbar;
