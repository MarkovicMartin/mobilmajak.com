import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { ticketAPI } from '../../services/api';
import TicketCommentRow from './TicketCommentRow';
import './TicketsModule.css';

const STAVY = [
    { value: 'novy', label: 'Nový', color: '#e74c3c' },
    { value: 'makam', label: 'Makám na tom', color: '#f39c12' },
    { value: 'opraveno', label: 'Opraveno', color: '#27ae60' },
];

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
    const { user, isAdmin } = useAuth();
    const [tickets, setTickets] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expanded, setExpanded] = useState(null);
    const [commentTexts, setCommentTexts] = useState({});
    const [submittingComment, setSubmittingComment] = useState(null);
    const [statusChanging, setStatusChanging] = useState(null);
    const [filterStav, setFilterStav] = useState('vse');
    const [editingCommentId, setEditingCommentId] = useState(null);
    const [editCommentText, setEditCommentText] = useState('');
    const [savingCommentId, setSavingCommentId] = useState(null);
    const [deletingCommentId, setDeletingCommentId] = useState(null);

    useEffect(() => {
        loadTickets();
    }, []);

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
    };

    const filtered = filterStav === 'vse' ? tickets : tickets.filter(t => t.stav === filterStav);

    const resolvedMs = tickets
        .map(t => getResolutionMs(t))
        .filter(ms => ms !== null);
    const avgMs = resolvedMs.length > 0
        ? resolvedMs.reduce((a, b) => a + b, 0) / resolvedMs.length
        : null;

    if (loading) return <div className="tickets-loading">Načítám tickety...</div>;
    if (error) return <div className="tickets-error">{error}</div>;

    return (
        <div className="tickets-module">
            <div className="tickets-header">
                <h2>🎫 Správa ticketů</h2>
                {avgMs !== null && (
                    <div className="tickets-avg">
                        ⏱ Průměrná doba vyřešení: <strong>{formatDuration(avgMs)}</strong>
                        <span className="tickets-avg-count">({resolvedMs.length} {resolvedMs.length === 1 ? 'ticket' : resolvedMs.length < 5 ? 'tickety' : 'ticketů'})</span>
                    </div>
                )}
            <div className="tickets-filter">
                    <label>Filtr:</label>
                    <select value={filterStav} onChange={e => setFilterStav(e.target.value)}>
                        <option value="vse">Všechny ({tickets.length})</option>
                        {STAVY.map(s => (
                            <option key={s.value} value={s.value}>
                                {s.label} ({tickets.filter(t => t.stav === s.value).length})
                            </option>
                        ))}
                    </select>
                    <button className="btn-refresh" onClick={loadTickets}>↻ Obnovit</button>
                </div>
            </div>

            {filtered.length === 0 && (
                <div className="tickets-empty">Žádné tickety{filterStav !== 'vse' ? ' v tomto stavu' : ''}.</div>
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
                                        {ticket.autor_jmeno} · {new Date(ticket.vytvoreno).toLocaleDateString('cs-CZ')}
                                        {ticket.images && ticket.images.length > 0 && (
                                            <span className="ticket-img-count"> · 📎 {ticket.images.length}</span>
                                        )}
                                        {getResolutionMs(ticket) !== null && (
                                            <span className="ticket-resolved-time"> · ✅ {formatDuration(getResolutionMs(ticket))}</span>
                                        )}
                                        {ticket.stav !== 'opraveno' && (
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

                                <div className="ticket-comments">
                                    <h4>Komentáře ({(ticket.comments || []).length})</h4>
                                    {(ticket.comments || []).map(c => (
                                        <TicketCommentRow
                                            key={c.id}
                                            comment={c}
                                            ticketId={ticket.id}
                                            currentUserId={user?.id}
                                            isAdmin={isAdmin()}
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
                                            placeholder="Napište komentář..."
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
