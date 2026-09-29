import React, { useEffect, useState } from 'react';
import api from '../../services/api';

const STORAGE_KEY = 'kb-chat-v1';

const loadHistory = () => {
    try {
        const raw = sessionStorage.getItem(STORAGE_KEY);
        const parsed = raw ? JSON.parse(raw) : [];
        return Array.isArray(parsed) ? parsed : [];
    } catch (err) {
        return [];
    }
};

const KnowledgeChat = () => {
    const [messages, setMessages] = useState(loadHistory);
    const [question, setQuestion] = useState('');
    const [sending, setSending] = useState(false);

    useEffect(() => {
        try {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
        } catch (err) {
            // Historie zůstane jen v paměti karty.
        }
    }, [messages]);

    const ask = async (event) => {
        event.preventDefault();
        const text = question.trim();
        if (!text || sending) return;
        setQuestion('');
        setMessages((prev) => [...prev, { role: 'user', text }]);
        setSending(true);
        try {
            const res = await api.post('/knowledge/ask/', { question: text });
            setMessages((prev) => [...prev, {
                role: 'assistant',
                text: res.data.answer || '',
                sources: res.data.sources || [],
            }]);
        } catch (err) {
            const detail = err.response?.data?.detail;
            setMessages((prev) => [...prev, {
                role: 'assistant',
                text: typeof detail === 'string' ? detail : 'Dotaz se nepodařilo vyhledat.',
                sources: [],
            }]);
        } finally {
            setSending(false);
        }
    };

    return (
        <div className="kb-chat">
            <div className="kb-chat__log" aria-live="polite">
                {messages.length === 0 && (
                    <p className="knowledge-empty">
                        Zeptejte se na postup z nahraných dokumentů. Odpověď jsou úryvky z textu, bez generovaného modelu.
                    </p>
                )}
                {messages.map((message, index) => (
                    <div
                        key={`${message.role}-${index}`}
                        className={`kb-chat__bubble kb-chat__bubble--${message.role}`}
                    >
                        <div>{message.text}</div>
                        {message.sources?.length > 0 && (
                            <ul className="kb-chat__sources">
                                {message.sources.map((source) => (
                                    <li key={source.document_id}>
                                        <a href={source.download_path}>{source.title}</a>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>
                ))}
            </div>
            <form className="kb-chat__composer" onSubmit={ask}>
                <input
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    placeholder="Např. jak řešit reklamaci"
                    aria-label="Dotaz do znalostní báze"
                    maxLength={500}
                />
                <button type="submit" className="btn btn--primary" disabled={sending || !question.trim()}>
                    {sending ? 'Hledám…' : 'Zeptat se'}
                </button>
                {messages.length > 0 && (
                    <button
                        type="button"
                        className="btn btn--secondary"
                        onClick={() => setMessages([])}
                    >
                        Vymazat
                    </button>
                )}
            </form>
        </div>
    );
};

export default KnowledgeChat;
