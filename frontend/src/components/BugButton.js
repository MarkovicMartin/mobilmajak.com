import React, { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import TicketForm from '../modules/tickets/TicketForm';
import { useAuth } from '../context/AuthContext';
import { ticketAPI } from '../services/api';
import { useUnreadPoll } from '../hooks/useUnreadPoll';
import { showAppToast } from './AppToast';
import { springHover } from '../constants/motion';
import './BugButton.css';

const BugButton = ({ user, onOpen }) => {
    const { canManageTickets } = useAuth();
    const isTicketManager = canManageTickets();
    const [isOpen, setIsOpen] = useState(false);
    const [showForm, setShowForm] = useState(false);
    const [successMsg, setSuccessMsg] = useState(null);
    const dropdownRef = useRef(null);
    const mobileDrawerRef = useRef(null);
    const navigate = useNavigate();
    const location = useLocation();

    const fetchTicketUnread = useCallback(async () => {
        if (!user) return 0;
        const res = await ticketAPI.getUnreadSummary();
        if (!res.success || typeof res.unread_count !== 'number') return 0;
        return { count: res.unread_count, role: res.role };
    }, [user]);

    const notifyTickets = useCallback((delta, _next, meta) => {
        const msg = meta?.role === 'manager'
            ? (delta === 1 ? '🔔 Máte nový ticket' : `🔔 ${delta} nových ticketů`)
            : (delta === 1
                ? '🔔 Aktualizace u vašeho ticketu'
                : `🔔 ${delta} aktualizací u vašich ticketů`);
        showAppToast(msg);
    }, []);

    const { count: unreadCount, refresh: fetchUnread } = useUnreadPoll({
        enabled: !!user,
        fetchCount: fetchTicketUnread,
        onNotify: notifyTickets,
        refreshEventName: 'tickets-unread-refresh',
    });

    useEffect(() => {
        const handleClickOutside = (event) => {
            const inToggle = dropdownRef.current?.contains(event.target);
            const inDrawer = mobileDrawerRef.current?.contains(event.target);
            if (inToggle || inDrawer) return;
            setIsOpen(false);
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    useEffect(() => {
        setIsOpen(false);
    }, [location.pathname]);

    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden';
            const handleEscape = (e) => { if (e.key === 'Escape') setIsOpen(false); };
            document.addEventListener('keydown', handleEscape);
            return () => {
                document.body.style.overflow = '';
                document.removeEventListener('keydown', handleEscape);
            };
        }
        document.body.style.overflow = '';
    }, [isOpen]);

    const handleToggle = () => {
        if (!isOpen) {
            onOpen?.();
            fetchUnread();
        }
        setIsOpen((o) => !o);
    };

    const handleNewTicket = () => {
        setIsOpen(false);
        requestAnimationFrame(() => {
            setShowForm(true);
        });
    };

    const handleMyTickets = () => {
        setIsOpen(false);
        navigate('/my-tickets');
    };

    const handleFormSuccess = () => {
        setShowForm(false);
        setSuccessMsg('Ticket byl úspěšně odeslán!');
        setTimeout(() => setSuccessMsg(null), 3500);
    };

    const onTicketsPage = location.pathname === '/my-tickets';
    const showExpandedLabel = onTicketsPage;
    const expandedLabel = isTicketManager ? 'Správa tiketů' : 'Moje tikety';
    const ticketsMenuLabel = isTicketManager ? 'Správa tiketů' : 'Moje tikety';
    const ticketsMenuDesc = isTicketManager
        ? 'Přehled a řešení všech tiketů'
        : 'Zobrazit stav mých hlášení';

    const menuContent = (
        <>
            <div className="bug-dropdown-header">
                <span className="bug-title">Tikety</span>
                <span className="bug-subtitle">Nahlásit problém nebo nápad</span>
            </div>
            <div className="bug-options">
                <button className="bug-option" onClick={handleNewTicket} type="button">
                    <span className="bug-option-icon">✏️</span>
                    <div className="bug-option-content">
                        <span className="bug-option-name">Nový bug</span>
                        <span className="bug-option-desc">Nahlásit problém nebo nápad</span>
                    </div>
                </button>
                <button className="bug-option" onClick={handleMyTickets} type="button">
                    <span className="bug-option-icon">📋</span>
                    <div className="bug-option-content">
                        <span className="bug-option-name">{ticketsMenuLabel}</span>
                        <span className="bug-option-desc">{ticketsMenuDesc}</span>
                    </div>
                </button>
            </div>
        </>
    );

    const mobileMenuContent = (
        <ul className="mobile-nav-list">
            <li>
                <button
                    className="mobile-nav-link"
                    onClick={handleNewTicket}
                    type="button"
                >
                    <span>✏️</span>
                    Nový bug
                </button>
            </li>
            <li>
                <button
                    className={`mobile-nav-link ${onTicketsPage ? 'active' : ''}`}
                    onClick={handleMyTickets}
                    type="button"
                >
                    <span>📋</span>
                    {ticketsMenuLabel}
                </button>
            </li>
        </ul>
    );

    return (
        <>
            <div className="bug-dropdown" ref={dropdownRef}>
                <motion.div
                    className={`dock-nav-item-wrap ${showExpandedLabel ? 'dock-nav-item-wrap--expanded' : ''}`}
                    whileHover={showExpandedLabel ? { scale: 1.04 } : { scale: 1.08 }}
                    transition={springHover}
                >
                    <motion.button
                        type="button"
                        layout
                        className={`dock-icon-btn bug-toggle-dock ${isOpen ? 'bug-toggle-dock--open' : ''} ${showExpandedLabel ? 'dock-icon-btn--active dock-icon-btn--with-label' : ''} ${unreadCount > 0 && !onTicketsPage ? 'bug-toggle-has-unread' : ''}`}
                        onClick={handleToggle}
                        data-tooltip={showExpandedLabel ? undefined : 'Tikety'}
                        title="Tikety / nahlásit problém"
                        aria-label={unreadCount > 0 ? `Tikety, ${unreadCount} nepřečtených` : 'Tikety / nahlásit problém'}
                        transition={springHover}
                        aria-expanded={isOpen}
                    >
                        <i className="fas fa-bug" />
                        {showExpandedLabel && (
                            <motion.span
                                className="dock-nav-label"
                                initial={{ opacity: 0, maxWidth: 0 }}
                                animate={{ opacity: 1, maxWidth: 160 }}
                                transition={{ duration: 0.22, ease: 'easeOut' }}
                            >
                                {expandedLabel}
                            </motion.span>
                        )}
                        {showExpandedLabel && (
                            <motion.span
                                layoutId="dock-active-dot-bug"
                                className="dock-active-dot"
                                transition={springHover}
                            />
                        )}
                        {unreadCount > 0 && (
                            <span className="bug-unread-badge" aria-hidden="true" />
                        )}
                    </motion.button>
                </motion.div>

                {isOpen && (
                    <>
                        {createPortal(
                            <div className="bug-mobile-drawer-root" ref={mobileDrawerRef}>
                                <div
                                    className={`bug-drawer-backdrop bug-mobile-only ${isOpen ? 'open' : ''}`}
                                    onClick={() => setIsOpen(false)}
                                    aria-hidden="true"
                                />
                                <div className={`bug-drawer-panel bug-mobile-only ${isOpen ? 'open' : ''}`}>
                                    <button
                                        className="mobile-nav-close"
                                        onClick={() => setIsOpen(false)}
                                        aria-label="Zavřít menu"
                                        type="button"
                                    >
                                        ×
                                    </button>
                                    {mobileMenuContent}
                                </div>
                            </div>,
                            document.body
                        )}
                        <div className="bug-dropdown-menu bug-desktop-only">{menuContent}</div>
                    </>
                )}
            </div>

            {showForm && (
                <TicketForm
                    onSuccess={handleFormSuccess}
                    onCancel={() => setShowForm(false)}
                />
            )}

            {successMsg && (
                <div className="bug-success-toast">
                    ✅ {successMsg}
                </div>
            )}
        </>
    );
};

export default BugButton;
