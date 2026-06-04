import React, { useState, useEffect, useCallback } from 'react';
import { format } from 'date-fns';
import { cs } from 'date-fns/locale';
import { taskAPI } from '../../services/api';

const TaskComments = ({ taskId, onCommentAdded }) => {
    const [comments, setComments] = useState([]);
    const [text, setText] = useState('');
    const [loading, setLoading] = useState(false);
    const [sending, setSending] = useState(false);

    const load = useCallback(async () => {
        if (!taskId) return;
        setLoading(true);
        try {
            const data = await taskAPI.listComments(taskId);
            setComments(Array.isArray(data) ? data : []);
        } catch {
            setComments([]);
        } finally {
            setLoading(false);
        }
    }, [taskId]);

    useEffect(() => {
        load();
    }, [load]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!text.trim() || !taskId) return;
        setSending(true);
        try {
            await taskAPI.addComment(taskId, text.trim());
            setText('');
            await load();
            onCommentAdded?.();
        } catch {
            /* tiché */
        } finally {
            setSending(false);
        }
    };

    return (
        <div className="task-comments">
            <h4 className="task-comments-title">Komentáře</h4>
            {loading && <p className="muted">Načítám…</p>}
            <ul className="task-comments-list">
                {comments.map((c) => (
                    <li key={c.id} className="task-comment-item">
                        <div className="task-comment-meta">
                            <strong>{c.autor_jmeno || `Uživatel #${c.autor_id}`}</strong>
                            <span>
                                {format(new Date(c.vytvoreno), 'd. M. yyyy HH:mm', { locale: cs })}
                            </span>
                        </div>
                        <p>{c.text}</p>
                    </li>
                ))}
                {!loading && comments.length === 0 && (
                    <li className="muted">Zatím žádné komentáře</li>
                )}
            </ul>
            <form className="task-comments-form" onSubmit={handleSubmit}>
                <textarea
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Napsat komentář…"
                    rows={2}
                />
                <button type="submit" className="btn-primary" disabled={sending || !text.trim()}>
                    Odeslat
                </button>
            </form>
        </div>
    );
};

export default TaskComments;
