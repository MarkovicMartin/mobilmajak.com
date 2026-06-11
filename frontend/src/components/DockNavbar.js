import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion, LayoutGroup } from 'framer-motion';
import AdminDropdown from './AdminDropdown';
import BugButton from './BugButton';
import { showAppToast } from './AppToast';
import { taskAPI } from '../services/api';
import { useUnreadPoll } from '../hooks/useUnreadPoll';
import { springHover } from '../constants/motion';
import './DockNavbar.css';

import { NAV_ITEMS, isNavActive } from '../config/navigation';

/** @deprecated Použij config/navigation.js – ponecháno pro zpětnou kompatibilitu. */
export { NAV_ITEMS, isNavActive };

const DockNavbar = ({
    user,
    isAdmin,
    canManageTasks,
    logout,
    isDarkMode,
    toggleTheme,
}) => {
    const navigate = useNavigate();
    const location = useLocation();
    const [mobileNavOpen, setMobileNavOpen] = useState(false);

    const fetchTaskNotifications = useCallback(async () => {
        if (!user) return 0;
        const res = await taskAPI.getNotificationsSummary();
        if (!res.success) return 0;
        return (res.tasks_unread || 0) + (res.overdue_count || 0);
    }, [user]);

    const notifyTasks = useCallback((delta) => {
        const word = delta === 1 ? 'nový úkol' : `${delta} nových úkolů`;
        showAppToast(`📋 Máte ${word} k vyřízení`);
    }, []);

    const { count: profileTaskBadge } = useUnreadPoll({
        enabled: !!user,
        fetchCount: fetchTaskNotifications,
        onNotify: notifyTasks,
        refreshEventName: 'tasks-notifications-refresh',
    });

    const closeMobileNav = () => setMobileNavOpen(false);

    useEffect(() => {
        closeMobileNav();
    }, [location.pathname]);

    useEffect(() => {
        const root = document.documentElement;
        const header = document.querySelector('.dock-navbar');
        const mq = window.matchMedia('(min-width: 769px)');

        const syncDockClearance = () => {
            if (!header || !mq.matches) {
                root.style.removeProperty('--dock-clearance');
                root.style.removeProperty('--dock-clearance-compact');
                root.style.removeProperty('--subnav-sticky-top');
                return;
            }
            const { bottom } = header.getBoundingClientRect();
            const gap = 16;
            const clearance = Math.ceil(bottom + gap);
            root.style.setProperty('--dock-clearance', `${clearance}px`);
            root.style.setProperty('--dock-clearance-compact', `${Math.max(clearance - 14, 68)}px`);
            root.style.setProperty('--subnav-sticky-top', `${clearance}px`);
        };

        const scheduleSync = () => {
            requestAnimationFrame(() => {
                requestAnimationFrame(syncDockClearance);
            });
        };

        const onScroll = () => {
            root.classList.toggle('dock-scrolled', window.scrollY > 20);
            scheduleSync();
        };

        scheduleSync();
        onScroll();

        const ro = header ? new ResizeObserver(scheduleSync) : null;
        ro?.observe(header);
        const glass = document.querySelector('.dock-glass');
        if (glass && ro) ro.observe(glass);

        window.addEventListener('scroll', onScroll, { passive: true });
        window.addEventListener('resize', scheduleSync);
        mq.addEventListener('change', scheduleSync);

        return () => {
            window.removeEventListener('scroll', onScroll);
            window.removeEventListener('resize', scheduleSync);
            mq.removeEventListener('change', scheduleSync);
            ro?.disconnect();
            root.classList.remove('dock-scrolled');
            root.style.removeProperty('--dock-clearance');
            root.style.removeProperty('--dock-clearance-compact');
            root.style.removeProperty('--subnav-sticky-top');
        };
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

    const visibleNavItems = NAV_ITEMS.filter((item) => {
        if (item.adminOnly && !isAdmin()) return false;
        if (item.managerOnly && !(canManageTasks?.() ?? false)) return false;
        return true;
    });

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
                                {isAdmin() && (
                                    <AdminDropdown onOpen={() => setMobileNavOpen(false)} />
                                )}
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
                                    const showExpandedLabel = active;
                                    return (
                                        <motion.div
                                            key={item.sectionKey}
                                            className={`dock-nav-item-wrap ${showExpandedLabel ? 'dock-nav-item-wrap--expanded' : ''}`}
                                            whileHover={showExpandedLabel ? { scale: 1.04 } : { scale: 1.12, rotate: -4 }}
                                            transition={springHover}
                                        >
                                            <motion.button
                                                type="button"
                                                layout
                                                className={`dock-icon-btn ${active ? 'dock-icon-btn--active' : ''} ${showExpandedLabel ? 'dock-icon-btn--with-label' : ''}`}
                                                onClick={() => navigate(item.path)}
                                                data-tooltip={showExpandedLabel ? undefined : item.label}
                                                title={item.label}
                                                transition={springHover}
                                            >
                                                <i className={`fas ${item.icon}`} />
                                                {showExpandedLabel && (
                                                    <motion.span
                                                        className="dock-nav-label"
                                                        initial={{ opacity: 0, maxWidth: 0 }}
                                                        animate={{ opacity: 1, maxWidth: 160 }}
                                                        transition={{ duration: 0.22, ease: 'easeOut' }}
                                                    >
                                                        {item.label}
                                                    </motion.span>
                                                )}
                                                {active && (
                                                    <motion.span
                                                        layoutId="dock-active-dot"
                                                        className="dock-active-dot"
                                                        transition={springHover}
                                                    />
                                                )}
                                            </motion.button>
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

                            <motion.div
                                className={`dock-profile-btn-wrap ${location.pathname === '/profile' ? 'dock-nav-item-wrap--expanded' : ''}`}
                                whileHover={
                                    location.pathname === '/profile'
                                        ? { scale: 1.04 }
                                        : { scale: 1.12, rotate: -4 }
                                }
                                transition={springHover}
                            >
                                <motion.button
                                    type="button"
                                    layout
                                    className={`dock-icon-btn ${location.pathname === '/profile' ? 'dock-icon-btn--active dock-icon-btn--with-label' : ''}`}
                                    onClick={() => navigate('/profile')}
                                    data-tooltip={location.pathname === '/profile' ? undefined : 'Můj profil'}
                                    title="Můj profil"
                                    transition={springHover}
                                >
                                    <i className="fas fa-user" />
                                    {profileTaskBadge > 0 && (
                                        <span className="dock-profile-badge" aria-label={`${profileTaskBadge} upozornění`}>
                                            {profileTaskBadge > 99 ? '99+' : profileTaskBadge}
                                        </span>
                                    )}
                                    {location.pathname === '/profile' && (
                                        <motion.span
                                            className="dock-nav-label"
                                            initial={{ opacity: 0, maxWidth: 0 }}
                                            animate={{ opacity: 1, maxWidth: 160 }}
                                            transition={{ duration: 0.22, ease: 'easeOut' }}
                                        >
                                            Můj profil
                                        </motion.span>
                                    )}
                                    {location.pathname === '/profile' && (
                                        <motion.span
                                            layoutId="dock-active-dot-profile"
                                            className="dock-active-dot"
                                            transition={springHover}
                                        />
                                    )}
                                </motion.button>
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
