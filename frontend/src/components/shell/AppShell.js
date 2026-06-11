import React, { useState, useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import AppSidebar from './AppSidebar';
import AppMobileDrawer from './AppMobileDrawer';
import AppTopBar from './AppTopBar';
import { showAppToast } from '../AppToast';
import { taskAPI } from '../../services/api';
import { useUnreadPoll } from '../../hooks/useUnreadPoll';
import './AppShell.css';

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
        if (drawerOpen) {
            document.body.style.overflow = 'hidden';
            const handleEscape = (e) => {
                if (e.key === 'Escape') setDrawerOpen(false);
            };
            document.addEventListener('keydown', handleEscape);
            return () => {
                document.body.style.overflow = '';
                document.removeEventListener('keydown', handleEscape);
            };
        }
        document.body.style.overflow = '';
    }, [drawerOpen]);

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
            <AppSidebar {...shellProps} />
            <AppMobileDrawer
                {...shellProps}
                open={drawerOpen}
                onClose={() => setDrawerOpen(false)}
            />
            <div className="app-shell__body">
                <AppTopBar
                    user={user}
                    isDarkMode={isDarkMode}
                    toggleTheme={toggleTheme}
                    onMenuClick={() => setDrawerOpen(true)}
                />
                <main className="app-main">{children}</main>
            </div>
        </div>
    );
};

export default AppShell;
