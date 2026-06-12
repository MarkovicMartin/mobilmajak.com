import React, { useState, useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import AppSidebar from './AppSidebar';
import AppMobileDrawer from './AppMobileDrawer';
import AppTopBar from './AppTopBar';
import { showAppToast } from '../AppToast';
import { taskAPI } from '../../services/api';
import { useUnreadPoll } from '../../hooks/useUnreadPoll';
import './AppShell.css';

const SIDEBAR_COLLAPSED_KEY = 'mm-sidebar-collapsed';

const readSidebarCollapsed = () => {
    try {
        return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === '1';
    } catch {
        return false;
    }
};

const AppShell = ({
    children,
    user,
    isAdmin,
    canManageTasks,
    canAccessCoaching,
    logout,
    isDarkMode,
    toggleTheme,
}) => {
    const location = useLocation();
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [sidebarCollapsed, setSidebarCollapsed] = useState(readSidebarCollapsed);

    const toggleSidebarCollapse = useCallback(() => {
        setSidebarCollapsed((prev) => {
            const next = !prev;
            try {
                localStorage.setItem(SIDEBAR_COLLAPSED_KEY, next ? '1' : '0');
            } catch {
                /* ignore */
            }
            return next;
        });
    }, []);

    useEffect(() => {
        document.documentElement.classList.toggle('sidebar-collapsed', sidebarCollapsed);
    }, [sidebarCollapsed]);

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

    useEffect(() => {
        setDrawerOpen(false);
    }, [location.pathname]);

    useEffect(() => {
        const mq = window.matchMedia('(min-width: 769px)');
        const handleChange = () => {
            if (mq.matches) setDrawerOpen(false);
        };
        mq.addEventListener('change', handleChange);
        return () => mq.removeEventListener('change', handleChange);
    }, []);

    useEffect(() => {
        document.body.classList.toggle('app-drawer-open', drawerOpen);
        if (!drawerOpen) return undefined;
        const handleEscape = (e) => {
            if (e.key === 'Escape') setDrawerOpen(false);
        };
        document.addEventListener('keydown', handleEscape);
        return () => {
            document.removeEventListener('keydown', handleEscape);
        };
    }, [drawerOpen]);

    useEffect(() => () => {
        document.body.classList.remove('app-drawer-open');
    }, []);

    const shellProps = {
        user,
        isAdmin,
        canManageTasks,
        canAccessCoaching,
        logout,
        isDarkMode,
        toggleTheme,
        profileTaskBadge,
    };

    return (
        <div className="app-shell">
            <AppSidebar
                {...shellProps}
                collapsed={sidebarCollapsed}
                onToggleCollapse={toggleSidebarCollapse}
            />
            <AppMobileDrawer
                {...shellProps}
                open={drawerOpen}
                onClose={() => setDrawerOpen(false)}
            />
            <div className="app-shell__body">
                <AppTopBar
                    isDarkMode={isDarkMode}
                    toggleTheme={toggleTheme}
                    drawerOpen={drawerOpen}
                    onMenuClick={() => setDrawerOpen(true)}
                    onDrawerClose={() => setDrawerOpen(false)}
                />
                <main className="app-main">{children}</main>
            </div>
        </div>
    );
};

export default AppShell;
