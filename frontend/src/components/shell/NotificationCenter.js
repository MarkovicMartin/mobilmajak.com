import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { cs } from 'date-fns/locale';
import { useUnreadPoll } from '../../hooks/useUnreadPoll';
import {
    fetchUnreadNotifications,
    fetchReadNotifications,
    fetchUnreadCount,
    dispatchNotificationsRefresh,
} from '../../services/notificationsService';
import './NotificationCenter.css';

const formatWhen = (iso) => {
    if (!iso) return '';
    try {
        return formatDistanceToNow(new Date(iso), { addSuffix: true, locale: cs });
    } catch {
        return '';
    }
};

const NotificationCenter = ({ collapsed = false }) => {
    const [open, setOpen] = useState(false);
    const [tab, setTab] = useState('unread');
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(false);
    const rootRef = useRef(null);
    const navigate = useNavigate();
    const location = useLocation();

    const { count: unreadCount, refresh: refreshCount } = useUnreadPoll({
        enabled: true,
        fetchCount: fetchUnreadCount,
        refreshEventName: 'notifications-refresh',
    });

    const loadItems = useCallback(async (activeTab) => {
        setLoading(true);
        try {
            const data = activeTab === 'read'
                ? await fetchReadNotifications()
                : await fetchUnreadNotifications();
            setItems(data);
        } catch {
            setItems([]);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (!open) return undefined;
        loadItems(tab);
        const onRefresh = () => loadItems(tab);
        window.addEventListener('notifications-refresh', onRefresh);
        return () => window.removeEventListener('notifications-refresh', onRefresh);
    }, [open, tab, loadItems]);

    useEffect(() => {
        setOpen(false);
    }, [location.pathname]);

    useEffect(() => {
        if (!open) return undefined;
        const handleClickOutside = (event) => {
            if (rootRef.current?.contains(event.target)) return;
            setOpen(false);
        };
        const handleEscape = (event) => {
            if (event.key === 'Escape') setOpen(false);
        };
        document.addEventListener('mousedown', handleClickOutside);
        document.addEventListener('keydown', handleEscape);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
            document.removeEventListener('keydown', handleEscape);
        };
    }, [open]);

    const handleToggle = () => {
        setOpen((prev) => {
            if (!prev) {
                setTab('unread');
                refreshCount();
            }
            return !prev;
        });
    };

    const handleItemClick = async (item) => {
        if (!item.read && item.markRead) {
            try {
                await item.markRead();
                dispatchNotificationsRefresh();
            } catch {
                /* navigate anyway */
            }
        }
        setOpen(false);
        navigate(item.link);
    };

    const handleMarkAllRead = async () => {
        const unread = items.filter((i) => !i.read && i.markRead);
        await Promise.all(unread.map((i) => i.markRead().catch(() => null)));
        dispatchNotificationsRefresh();
        loadItems('unread');
    };

    const displayCount = tab === 'unread' ? unreadCount : items.length;

    return (
        <div className="notification-center" ref={rootRef}>
            <button
                type="button"
                className="app-sidebar__icon-btn notification-center__toggle"
                onClick={handleToggle}
                aria-expanded={open}
                aria-haspopup="true"
                title="Upozornění"
                aria-label={displayCount > 0 ? `Upozornění, ${displayCount} nepřečtených` : 'Upozornění'}
            >
                <i className="fas fa-bell" aria-hidden="true" />
                {unreadCount > 0 && (
                    <span className="notification-center__badge" aria-hidden="true">
                        {unreadCount > 99 ? '99+' : unreadCount}
                    </span>
                )}
            </button>

            {open && (
                <div className="notification-center__panel" role="dialog" aria-label="Centrum upozornění">
                    <div className="notification-center__header">
                        <span className="notification-center__title">Upozornění</span>
                        {tab === 'unread' && unreadCount > 0 && (
                            <button
                                type="button"
                                className="notification-center__mark-all"
                                onClick={handleMarkAllRead}
                            >
                                Označit vše
                            </button>
                        )}
                    </div>

                    <div className="notification-center__tabs" role="tablist">
                        <button
                            type="button"
                            role="tab"
                            aria-selected={tab === 'unread'}
                            className={`notification-center__tab ${tab === 'unread' ? 'notification-center__tab--active' : ''}`}
                            onClick={() => setTab('unread')}
                        >
                            Nepřečtené
                        </button>
                        <button
                            type="button"
                            role="tab"
                            aria-selected={tab === 'read'}
                            className={`notification-center__tab ${tab === 'read' ? 'notification-center__tab--active' : ''}`}
                            onClick={() => setTab('read')}
                        >
                            Přečtené
                        </button>
                    </div>

                    <div className="notification-center__list" role="tabpanel">
                        {loading && (
                            <p className="notification-center__empty">Načítám…</p>
                        )}
                        {!loading && items.length === 0 && (
                            <p className="notification-center__empty">
                                {tab === 'unread' ? 'Žádná nepřečtená upozornění' : 'Žádná přečtená upozornění'}
                            </p>
                        )}
                        {!loading && items.map((item) => (
                            <button
                                key={item.id}
                                type="button"
                                className={`notification-center__item ${item.read ? 'notification-center__item--read' : ''}`}
                                onClick={() => handleItemClick(item)}
                            >
                                <div className="notification-center__item-head">
                                    <span className="notification-center__source">{item.sourceLabel}</span>
                                    <span className="notification-center__when">{formatWhen(item.createdAt)}</span>
                                </div>
                                <span className="notification-center__item-title">{item.title}</span>
                                <span className="notification-center__item-msg">{item.message}</span>
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default NotificationCenter;
