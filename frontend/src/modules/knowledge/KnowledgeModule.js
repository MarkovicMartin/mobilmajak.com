import React, { useCallback, useEffect, useState } from 'react';
import api from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { PageHeader } from '../../components/ui';
import KnowledgeChat from './KnowledgeChat';
import './KnowledgeModule.css';

const emptyForm = { nazev: '', popis: '', soubor: null };

const errorText = (err, fallback) => {
    const data = err.response?.data;
    if (!data) return fallback;
    if (typeof data.detail === 'string') return data.detail;
    if (typeof data === 'object') {
        const first = Object.values(data)[0];
        if (Array.isArray(first) && first[0]) return String(first[0]);
        if (typeof first === 'string') return first;
    }
    return fallback;
};

const KnowledgeModule = () => {
    const { isAdmin } = useAuth();
    const admin = isAdmin();
    const [tab, setTab] = useState('docs');
    const [docs, setDocs] = useState([]);
    const [query, setQuery] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [form, setForm] = useState(emptyForm);
    const [editing, setEditing] = useState(null);
    const [saving, setSaving] = useState(false);

    const load = useCallback(async (q) => {
        setLoading(true);
        setError(null);
        try {
            const res = await api.get('/knowledge/documents/', { params: q ? { q } : {} });
            setDocs(Array.isArray(res.data) ? res.data : []);
        } catch (err) {
            setError(errorText(err, 'Dokumenty se nepodařilo načíst.'));
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        load('');
    }, [load]);

    const upload = async (event) => {
        event.preventDefault();
        if (!form.soubor) {
            setError('Vyberte soubor.');
            return;
        }
        setSaving(true);
        setError(null);
        try {
            const body = new FormData();
            body.append('nazev', form.nazev);
            body.append('popis', form.popis);
            body.append('soubor', form.soubor);
            await api.post('/knowledge/documents/', body);
            setForm(emptyForm);
            await load(query);
        } catch (err) {
            setError(errorText(err, 'Nahrání se nezdařilo.'));
        } finally {
            setSaving(false);
        }
    };

    const saveEdit = async (event) => {
        event.preventDefault();
        setSaving(true);
        setError(null);
        try {
            await api.patch(`/knowledge/documents/${editing.id}/`, {
                nazev: editing.nazev,
                popis: editing.popis,
                aktivni: editing.aktivni,
            });
            setEditing(null);
            await load(query);
        } catch (err) {
            setError(errorText(err, 'Úprava se nezdařila.'));
        } finally {
            setSaving(false);
        }
    };

    const remove = async (doc) => {
        if (!window.confirm(`Smazat „${doc.nazev}“?`)) return;
        try {
            await api.delete(`/knowledge/documents/${doc.id}/`);
            await load(query);
        } catch (err) {
            setError(errorText(err, 'Smazání se nezdařilo.'));
        }
    };

    return (
        <div className="knowledge-module">
            <PageHeader
                title="Znalostní báze"
                subtitle="Dokumenty pro celý tým. Nahrávat může jen administrátor."
            />
            <div className="knowledge-tabs" role="tablist">
                <button type="button" className={tab === 'docs' ? 'is-active' : ''} onClick={() => setTab('docs')}>
                    Dokumenty
                </button>
                <button type="button" className={tab === 'ask' ? 'is-active' : ''} onClick={() => setTab('ask')}>
                    Dotaz
                </button>
            </div>

            {error && <div className="alert alert-warning">{error}</div>}

            {tab === 'ask' ? (
                <KnowledgeChat />
            ) : (
                <>
                    <form
                        className="knowledge-filter"
                        onSubmit={(event) => {
                            event.preventDefault();
                            load(query);
                        }}
                    >
                        <span>Hledat v názvu a popisu</span>
                        <input
                            value={query}
                            onChange={(event) => setQuery(event.target.value)}
                            placeholder="Název dokumentu"
                        />
                        <button type="submit" className="btn btn--secondary">Hledat</button>
                    </form>

                    {admin && (
                        <form className="knowledge-form" onSubmit={upload}>
                            <strong>Nahrát dokument</strong>
                            <label>
                                Název
                                <input
                                    value={form.nazev}
                                    onChange={(event) => setForm({ ...form, nazev: event.target.value })}
                                    placeholder="Když nevyplníte, použije se jméno souboru"
                                />
                            </label>
                            <label>
                                Popis
                                <textarea
                                    rows={2}
                                    value={form.popis}
                                    onChange={(event) => setForm({ ...form, popis: event.target.value })}
                                />
                            </label>
                            <label>
                                Soubor (PDF, DOCX, TXT nebo obrázek)
                                <input
                                    type="file"
                                    accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.gif,.webp"
                                    onChange={(event) => setForm({ ...form, soubor: event.target.files?.[0] || null })}
                                />
                            </label>
                            <div className="knowledge-form__actions">
                                <button type="submit" className="btn btn--primary" disabled={saving}>
                                    {saving ? 'Nahrávám…' : 'Nahrát'}
                                </button>
                            </div>
                        </form>
                    )}

                    {editing && (
                        <form className="knowledge-form" onSubmit={saveEdit}>
                            <strong>Upravit dokument</strong>
                            <label>
                                Název
                                <input
                                    value={editing.nazev}
                                    onChange={(event) => setEditing({ ...editing, nazev: event.target.value })}
                                    required
                                />
                            </label>
                            <label>
                                Popis
                                <textarea
                                    rows={2}
                                    value={editing.popis}
                                    onChange={(event) => setEditing({ ...editing, popis: event.target.value })}
                                />
                            </label>
                            <label>
                                <span>
                                    <input
                                        type="checkbox"
                                        checked={editing.aktivni}
                                        onChange={(event) => setEditing({ ...editing, aktivni: event.target.checked })}
                                    />
                                    {' '}Aktivní
                                </span>
                            </label>
                            <div className="knowledge-form__actions">
                                <button type="submit" className="btn btn--primary" disabled={saving}>Uložit</button>
                                <button type="button" className="btn btn--secondary" onClick={() => setEditing(null)}>Zrušit</button>
                            </div>
                        </form>
                    )}

                    {loading && <p>Načítám…</p>}
                    {!loading && docs.length === 0 && (
                        <p className="knowledge-empty">Zatím tu nejsou žádné dokumenty.</p>
                    )}
                    <div className="knowledge-list">
                        {docs.map((doc) => (
                            <article key={doc.id} className="knowledge-card">
                                <div className="knowledge-card__title">{doc.nazev}</div>
                                <div className="knowledge-card__meta">
                                    {doc.original_filename}
                                    {doc.nahral_jmeno ? ` · ${doc.nahral_jmeno}` : ''}
                                    {doc.has_text ? ' · text k vyhledání' : ' · jen ke stažení'}
                                    {admin && !doc.aktivni ? ' · skrytý' : ''}
                                </div>
                                {doc.popis && <p>{doc.popis}</p>}
                                <div className="knowledge-card__actions">
                                    <a className="btn btn--secondary" href={doc.download_path}>Stáhnout</a>
                                    {admin && (
                                        <>
                                            <button type="button" className="btn btn--secondary" onClick={() => setEditing({
                                                id: doc.id,
                                                nazev: doc.nazev,
                                                popis: doc.popis || '',
                                                aktivni: doc.aktivni,
                                            })}
                                            >
                                                Upravit
                                            </button>
                                            <button type="button" className="btn btn--secondary" onClick={() => remove(doc)}>
                                                Smazat
                                            </button>
                                        </>
                                    )}
                                </div>
                            </article>
                        ))}
                    </div>
                </>
            )}
        </div>
    );
};

export default KnowledgeModule;
