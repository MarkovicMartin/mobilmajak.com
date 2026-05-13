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

const StatusBadge = ({ stav }) => {
    const s = STAVY.find(x => x.value === stav) || STAVY[0];
    return (
        <span className="ticket-badge" style={{ backgroundColor: s.color }}>
            {s.label}
        </span>
    );
};

const MyTickets = ({ onNewTicket }) => {
    const { user, isAdmin } = useAuth();
    const [tickets, setTickets] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expanded, setExpanded] = useState(null);
    const [commentTexts, setCommentTexts] = useState({});
    const [submittingComment, setSubmittingComment] = useState(null);
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
            const response = await ticketAPI.getMy();
            if (response.success) {
                setTickets(response.tickets);
            } else {
                setError('Chyba při načítání.');
            }
        } catch (e) {
            setError('Chyba při načítání.');
        } finally {
            setLoading(false);
        }
    };

    const toggleExpand = async (ticketId) => {
        if (expanded === ticketId) {
            setExpanded(null);
            return;
        }
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
        } catch (e) {
            /* ignore */
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

    if (loading) return <div className="tickets-loading">Načítám tickety...</div>;
    if (error) return <div className="tickets-error">{error}</div>;

    return (
        <div className="tickets-module my-tickets">
            <div className="tickets-header">
                <h2>🐛 Moje tickety</h2>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button className="btn-refresh" onClick={loadTickets}>↻ Obnovit</button>
                    {onNewTicket && (
                        <button className="btn-new-ticket" onClick={onNewTicket}>
                            + Nový ticket
                        </button>
                    )}
                </div>
            </div>

            {tickets.length === 0 && (
                <div className="tickets-empty">
                    Zatím žádné tickety. Klikni na „+ Nový ticket" a nahlaste nám problém nebo nápad.
                </div>
            )}

            <div className="tickets-list">
                {tickets.map(ticket => (
                    <div key={ticket.id} className={`ticket-card stav-${ticket.stav}`}>
                        <div className="ticket-card-header" onClick={() => toggleExpand(ticket.id)}>
                            <div className="ticket-card-left">
                                <span className="ticket-id">#{ticket.id}</span>
                                <div className="ticket-card-info">
                                    <span className="ticket-nazev">{ticket.nazev}</span>
                                    <span className="ticket-meta">
                                        {new Date(ticket.vytvoreno).toLocaleDateString('cs-CZ')}
                                        {ticket.images && ticket.images.length > 0 && (
                                            <span className="ticket-img-count"> · 📎 {ticket.images.length}</span>
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
                                            placeholder="Doplňující informace nebo dotaz..."
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

export default MyTickets;
