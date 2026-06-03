import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { ticketAPI } from '../../services/api';
import TicketCommentRow from './TicketCommentRow';
import './TicketsModule.css';
import './MyTickets.css';

const STAVY = [
    { value: 'novy', label: 'Nový', color: '#e74c3c' },
    { value: 'makam', label: 'Makám na tom', color: '#f39c12' },
    { value: 'opraveno', label: 'Opraveno', color: '#27ae60' },
];

const FILTER_ROZPRACOVANE = 'rozpracovane';
const OPEN_STAVY = ['novy', 'makam'];

const FILTER_OPTIONS = [
    { value: FILTER_ROZPRACOVANE, label: 'Rozpracované' },
    { value: 'novy', label: 'Nový' },
    { value: 'makam', label: 'Makám na tom' },
    { value: 'opraveno', label: 'Hotové' },
    { value: 'vse', label: 'Všechny' },
];

const matchesFilter = (ticket, filterStav) => {
    if (filterStav === 'vse') return true;
    if (filterStav === FILTER_ROZPRACOVANE) return OPEN_STAVY.includes(ticket.stav);
    return ticket.stav === filterStav;
};

const formatDuration = (ms) => {
    const totalMinutes = Math.floor(ms / 60000);
    const days = Math.floor(totalMinutes / 1440);
    const hours = Math.floor((totalMinutes % 1440) / 60);
    const minutes = totalMinutes % 60;
    if (days > 0) return `${days}d ${hours}h ${minutes}min`;
    if (hours > 0) return `${hours}h ${minutes}min`;
    return `${minutes}min`;
};

const getResolutionMs = (ticket) => {
    if (ticket.stav !== 'opraveno' || !ticket.opraveno_at) return null;
    return new Date(ticket.opraveno_at) - new Date(ticket.vytvoreno);
};

const StatusBadge = ({ stav }) => {
    const s = STAVY.find(x => x.value === stav) || STAVY[0];
    return (
        <span className="ticket-badge" style={{ backgroundColor: s.color }}>
            {s.label}
        </span>
    );
};

const TicketsModule = () => {
    const { user, canManageTickets } = useAuth();
    const isTicketManager = canManageTickets();
    const [tickets, setTickets] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expanded, setExpanded] = useState(null);
    const [commentTexts, setCommentTexts] = useState({});
    const [submittingComment, setSubmittingComment] = useState(null);
    const [statusChanging, setStatusChanging] = useState(null);
    const [filterStav, setFilterStav] = useState(FILTER_ROZPRACOVANE);
    const [editingCommentId, setEditingCommentId] = useState(null);
    const [editCommentText, setEditCommentText] = useState('');
    const [savingCommentId, setSavingCommentId] = useState(null);
    const [deletingCommentId, setDeletingCommentId] = useState(null);

    useEffect(() => {
        loadTickets();
    }, []);

    useEffect(() => {
        if (!isTicketManager) return undefined;
        ticketAPI.markAllRead()
            .then(() => window.dispatchEvent(new CustomEvent('tickets-unread-refresh')))
            .catch(() => {});
        return undefined;
    }, [isTicketManager]);

    const loadTickets = async () => {
        try {
            setLoading(true);
            const response = await ticketAPI.getAll();
            if (response.success) {
                setTickets(response.tickets);
            } else {
                setError('Chyba při načítání ticketů.');
            }
        } catch (e) {
            setError('Chyba při načítání ticketů.');
        } finally {
            setLoading(false);
        }
    };

    const handleStatusChange = async (ticketId, stav) => {
        setStatusChanging(ticketId);
        try {
            const response = await ticketAPI.updateStatus(ticketId, stav);
            if (response.success) {
                setTickets(prev => prev.map(t => t.id === ticketId ? { ...t, stav, stav_display: response.ticket.stav_display } : t));
                if (stav === 'opraveno') {
                    window.dispatchEvent(new CustomEvent('tickets-unread-refresh'));
                }
                if (expanded === ticketId) {
                    setExpanded(null);
                    setTimeout(() => setExpanded(ticketId), 50);
                }
            }
        } catch (e) {
            alert('Chyba při změně stavu.');
        } finally {
            setStatusChanging(null);
        }
    };

    const handleAddComment = async (ticketId) => {
        const text = (commentTexts[ticketId] || '').trim();
        if (!text) return;
        setSubmittingComment(ticketId);
        try {
            const response = await ticketAPI.addComment(ticketId, text);
            if (response.success) {
                setTickets(prev => prev.map(t => {
                    if (t.id !== ticketId) return t;
                    return { ...t, comments: [...(t.comments || []), response.comment] };
                }));
                setCommentTexts(prev => ({ ...prev, [ticketId]: '' }));
            }
        } catch (e) {
            alert('Chyba při odesílání komentáře.');
        } finally {
            setSubmittingComment(null);
        }
    };

    const handleDelete = async (ticketId) => {
        if (!window.confirm('Opravdu smazat tento ticket?')) return;
        try {
            await ticketAPI.deleteTicket(ticketId);
            setTickets(prev => prev.filter(t => t.id !== ticketId));
            if (expanded === ticketId) setExpanded(null);
        } catch (e) {
            alert('Chyba při mazání ticketu.');
        }
    };

    const handleStartEditComment = (c) => {
        setEditingCommentId(c.id);
        setEditCommentText(c.text || '');
    };

    const handleSaveComment = async (ticketId, commentId) => {
        const text = editCommentText.trim();
        if (!text) return;
        setSavingCommentId(commentId);
        try {
            const res = await ticketAPI.updateComment(ticketId, commentId, text);
            if (res.success && res.comment) {
                setTickets(prev => prev.map(t => {
                    if (t.id !== ticketId) return t;
                    return {
                        ...t,
                        comments: (t.comments || []).map((cm) => (cm.id === commentId ? res.comment : cm)),
                    };
                }));
                setEditingCommentId(null);
                setEditCommentText('');
            }
        } catch (e) {
            alert('Chyba při úpravě komentáře.');
        } finally {
            setSavingCommentId(null);
        }
    };

    const handleDeleteComment = async (ticketId, commentId) => {
        if (!window.confirm('Opravdu smazat tento komentář?')) return;
        setDeletingCommentId(commentId);
        try {
            await ticketAPI.deleteComment(ticketId, commentId);
            setTickets(prev => prev.map(t => {
                if (t.id !== ticketId) return t;
                return { ...t, comments: (t.comments || []).filter((cm) => cm.id !== commentId) };
            }));
        } catch (e) {
            alert(e.response?.data?.error || 'Chyba při mazání komentáře.');
        } finally {
            setDeletingCommentId(null);
        }
    };

    const toggleExpand = async (ticketId) => {
        if (expanded === ticketId) {
            setExpanded(null);
            return;
        }
        // Načteme detail s komentáři
        try {
            const response = await ticketAPI.getDetail(ticketId);
            if (response.success) {
                setTickets(prev => prev.map(t => t.id === ticketId ? { ...t, ...response.ticket } : t));
            }
        } catch (e) {}
        setExpanded(ticketId);
        try {
            const mr = await ticketAPI.markRead(ticketId);
            if (mr.success) {
                window.dispatchEvent(new CustomEvent('tickets-unread-refresh'));
            }
        } catch {
            /* ignore */
        }
    };

    const filtered = tickets.filter((t) => matchesFilter(t, filterStav));
    const countForFilter = (value) => tickets.filter((t) => matchesFilter(t, value)).length;

    const resolvedMs = tickets
        .map(t => getResolutionMs(t))
        .filter(ms => ms !== null);
    const avgMs = resolvedMs.length > 0
        ? resolvedMs.reduce((a, b) => a + b, 0) / resolvedMs.length
        : null;

    if (loading) return <div className="tickets-loading">Načítám tickety...</div>;
    if (error) return <div className="tickets-error">{error}</div>;

    const filterEmptyLabel = FILTER_OPTIONS.find((o) => o.value === filterStav)?.label?.toLowerCase() || '';

    return (
        <div className={`tickets-module${isTicketManager ? '' : ' my-tickets'}`}>
            <div className="tickets-header">
                <h2>{isTicketManager ? '🎫 Správa ticketů' : '🐛 Moje tickety'}</h2>
                {isTicketManager && avgMs !== null && (
                    <div className="tickets-avg">
                        ⏱ Průměrná doba vyřešení: <strong>{formatDuration(avgMs)}</strong>
                        <span className="tickets-avg-count">({resolvedMs.length} {resolvedMs.length === 1 ? 'ticket' : resolvedMs.length < 5 ? 'tickety' : 'ticketů'})</span>
                    </div>
                )}
            <div className="tickets-filter">
                    <label>Filtr:</label>
                    <select value={filterStav} onChange={e => setFilterStav(e.target.value)}>
                        {FILTER_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                                {opt.label} ({countForFilter(opt.value)})
                            </option>
                        ))}
                    </select>
                    <button className="btn-refresh" onClick={loadTickets}>↻ Obnovit</button>
                </div>
            </div>

            {filtered.length === 0 && (
                <div className="tickets-empty">
                    {tickets.length === 0
                        ? (isTicketManager
                            ? 'Žádné tickety.'
                            : 'Zatím žádné tickety. Klikni na „Nový bug“ v menu Tikety a nahlaste problém nebo nápad.')
                        : `Žádné tickety${filterEmptyLabel ? ` (${filterEmptyLabel})` : ''}.`}
                </div>
            )}

            <div className="tickets-list">
                {filtered.map(ticket => (
                    <div key={ticket.id} className={`ticket-card stav-${ticket.stav}`}>
                        <div className="ticket-card-header" onClick={() => toggleExpand(ticket.id)}>
                            <div className="ticket-card-left">
                                <span className="ticket-id">#{ticket.id}</span>
                                <div className="ticket-card-info">
                                    <span className="ticket-nazev">{ticket.nazev}</span>
                                    <span className="ticket-meta">
                                        {isTicketManager && ticket.autor_jmeno && (
                                            <>{ticket.autor_jmeno} · </>
                                        )}
                                        {new Date(ticket.vytvoreno).toLocaleDateString('cs-CZ')}
                                        {ticket.images && ticket.images.length > 0 && (
                                            <span className="ticket-img-count"> · 📎 {ticket.images.length}</span>
                                        )}
                                        {isTicketManager && getResolutionMs(ticket) !== null && (
                                            <span className="ticket-resolved-time"> · ✅ {formatDuration(getResolutionMs(ticket))}</span>
                                        )}
                                        {isTicketManager && ticket.stav !== 'opraveno' && (
                                            <span className="ticket-open-time"> · 🕐 {formatDuration(Date.now() - new Date(ticket.vytvoreno))}</span>
                                        )}
                                    </span>
                                </div>
                            </div>
                            <div className="ticket-card-right">
                                <StatusBadge stav={ticket.stav} />
                                <span className="ticket-expand">{expanded === ticket.id ? '▲' : '▼'}</span>
                            </div>
                        </div>

                        {expanded === ticket.id && (
                            <div className="ticket-card-body">
                                {ticket.url && (
                                    <div className="ticket-url">
                                        <span>📍 Stránka:</span>
                                        <a href={ticket.url} target="_blank" rel="noreferrer">{ticket.url}</a>
                                    </div>
                                )}
                                <p className="ticket-popis">{ticket.popis}</p>

                                {ticket.images && ticket.images.length > 0 && (
                                    <div className="ticket-images">
                                        {ticket.images.map(img => (
                                            <a key={img.id} href={img.obrazek} target="_blank" rel="noreferrer">
                                                <img src={img.obrazek} alt="příloha" className="ticket-thumb" />
                                            </a>
                                        ))}
                                    </div>
                                )}

                                {isTicketManager && (
                                    <div className="ticket-actions">
                                        <label>Změnit stav:</label>
                                        <div className="stav-buttons">
                                            {STAVY.map(s => (
                                                <button
                                                    key={s.value}
                                                    className={`btn-stav ${ticket.stav === s.value ? 'active' : ''}`}
                                                    style={{ '--stav-color': s.color }}
                                                    onClick={() => handleStatusChange(ticket.id, s.value)}
                                                    disabled={statusChanging === ticket.id || ticket.stav === s.value}
                                                >
                                                    {s.label}
                                                </button>
                                            ))}
                                        </div>
                                        <button
                                            className="btn-delete"
                                            onClick={() => handleDelete(ticket.id)}
                                        >
                                            🗑 Smazat
                                        </button>
                                    </div>
                                )}

                                <div className="ticket-comments">
                                    <h4>Komentáře ({(ticket.comments || []).length})</h4>
                                    {(ticket.comments || []).map(c => (
                                        <TicketCommentRow
                                            key={c.id}
                                            comment={c}
                                            ticketId={ticket.id}
                                            currentUserId={user?.id}
                                            isAdmin={isTicketManager}
                                            editingCommentId={editingCommentId}
                                            editCommentText={editCommentText}
                                            onStartEdit={handleStartEditComment}
                                            onEditTextChange={setEditCommentText}
                                            onSaveEdit={handleSaveComment}
                                            onCancelEdit={() => {
                                                setEditingCommentId(null);
                                                setEditCommentText('');
                                            }}
                                            savingCommentId={savingCommentId}
                                            deletingCommentId={deletingCommentId}
                                            onDeleteComment={handleDeleteComment}
                                        />
                                    ))}
                                    <div className="comment-form">
                                        <textarea
                                            placeholder={isTicketManager ? 'Napište komentář...' : 'Doplňující informace nebo dotaz...'}
                                            value={commentTexts[ticket.id] || ''}
                                            onChange={e => setCommentTexts(prev => ({ ...prev, [ticket.id]: e.target.value }))}
                                            rows={2}
                                        />
                                        <button
                                            onClick={() => handleAddComment(ticket.id)}
                                            disabled={submittingComment === ticket.id || !(commentTexts[ticket.id] || '').trim()}
                                        >
                                            {submittingComment === ticket.id ? 'Odesílám...' : 'Odeslat komentář'}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
};

export default TicketsModule;
