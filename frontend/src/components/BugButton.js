import React, { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate, useLocation } from 'react-router-dom';
import TicketForm from '../modules/tickets/TicketForm';
import { ticketAPI } from '../services/api';
import './BugButton.css';

const POLL_MS = 90000;

const BugButton = ({ user, onOpen }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [unreadCount, setUnreadCount] = useState(0);
    const [showForm, setShowForm] = useState(false);
    const [successMsg, setSuccessMsg] = useState(null);
    const dropdownRef = useRef(null);
    const mobileDrawerRef = useRef(null);
    const navigate = useNavigate();
    const location = useLocation();

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

    const fetchUnread = useCallback(async () => {
        if (!user) {
            setUnreadCount(0);
            return;
        }
        try {
            const res = await ticketAPI.getUnreadSummary();
            if (res.success && typeof res.unread_count === 'number') {
                setUnreadCount(res.unread_count);
            }
        } catch {
            setUnreadCount(0);
        }
    }, [user]);

    useEffect(() => {
        fetchUnread();
    }, [fetchUnread]);

    useEffect(() => {
        if (!user) return undefined;
        const id = window.setInterval(fetchUnread, POLL_MS);
        const onFocus = () => fetchUnread();
        const onVis = () => {
            if (document.visibilityState === 'visible') fetchUnread();
        };
        const onRefresh = () => fetchUnread();
        window.addEventListener('focus', onFocus);
        document.addEventListener('visibilitychange', onVis);
        window.addEventListener('tickets-unread-refresh', onRefresh);
        return () => {
            clearInterval(id);
            window.removeEventListener('focus', onFocus);
            document.removeEventListener('visibilitychange', onVis);
            window.removeEventListener('tickets-unread-refresh', onRefresh);
        };
    }, [user, fetchUnread]);

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
                        <span className="bug-option-name">Moje tikety</span>
                        <span className="bug-option-desc">Zobrazit stav mých hlášení</span>
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
                    className={`mobile-nav-link ${location.pathname === '/my-tickets' ? 'active' : ''}`}
                    onClick={handleMyTickets}
                    type="button"
                >
                    <span>📋</span>
                    Moje tikety
                </button>
            </li>
        </ul>
    );

    return (
        <>
            <div className="bug-dropdown" ref={dropdownRef}>
                <button
                    className={`bug-toggle ${isOpen ? 'active' : ''} ${unreadCount > 0 ? 'bug-toggle-has-unread' : ''}`}
                    onClick={handleToggle}
                    title="Tikety / nahlásit problém"
                    type="button"
                    aria-label={unreadCount > 0 ? `Tikety, ${unreadCount} nepřečtených` : 'Tikety / nahlásit problém'}
                >
                    🐛
                </button>

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
