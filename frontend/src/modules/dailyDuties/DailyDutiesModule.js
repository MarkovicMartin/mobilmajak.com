import React, { useCallback, useEffect, useState } from 'react';
import api, { storeAPI, userAPI } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { PageHeader } from '../../components/ui';
import './DailyDutiesModule.css';

const todayIso = () => {
    const now = new Date();
    const pad = (value) => String(value).padStart(2, '0');
    return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
};

const emptyForm = {
    title: '',
    description: '',
    periodicity: 'daily',
    target: 'prodejna',
    prodejna: '',
    uzivatel: '',
    is_active: true,
};

const errorText = (err, fallback) => {
    const data = err.response?.data;
    if (!data) return fallback;
    if (typeof data.detail === 'string') return data.detail;
    if (typeof data === 'string') return data;
    if (Array.isArray(data) && data[0]) return String(data[0]);
    if (typeof data === 'object') {
        const first = Object.values(data)[0];
        if (Array.isArray(first) && first[0]) return String(first[0]);
        if (typeof first === 'string') return first;
    }
    return fallback;
};

const DailyDutiesModule = () => {
    const { isAdmin } = useAuth();
    const admin = isAdmin();
    const [tab, setTab] = useState('mine');
    const [date, setDate] = useState(todayIso);
    const [items, setItems] = useState([]);
    const [statusItems, setStatusItems] = useState([]);
    const [templates, setTemplates] = useState([]);
    const [stores, setStores] = useState([]);
    const [users, setUsers] = useState([]);
    const [form, setForm] = useState(emptyForm);
    const [editingId, setEditingId] = useState(null);
    const [notes, setNotes] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [saving, setSaving] = useState(false);

    const loadMine = useCallback(async (day) => {
        setLoading(true);
        setError(null);
        try {
            const res = await api.get('/daily-duties/mine/', { params: { date: day } });
            setItems(res.data.items || []);
        } catch (err) {
            setError(errorText(err, 'Povinnosti se nepodařilo načíst.'));
        } finally {
            setLoading(false);
        }
    }, []);

    const loadStatus = useCallback(async (day) => {
        setError(null);
        try {
            const res = await api.get('/daily-duties/status/', { params: { date: day } });
            setStatusItems(res.data.items || []);
        } catch (err) {
            setError(errorText(err, 'Stav se nepodařilo načíst.'));
        }
    }, []);

    const loadTemplates = useCallback(async () => {
        setError(null);
        try {
            const [tpl, storeRes, userRes] = await Promise.all([
                api.get('/daily-duties/templates/'),
                storeAPI.getStores({ aktivni: 'true' }),
                userAPI.getUsers({ aktivni: true }),
            ]);
            setTemplates(Array.isArray(tpl.data) ? tpl.data : []);
            setStores(storeRes.stores || []);
            setUsers(userRes.users || []);
        } catch (err) {
            setError(errorText(err, 'Šablony se nepodařilo načíst.'));
        }
    }, []);

    useEffect(() => {
        loadMine(date);
    }, [date, loadMine]);

    useEffect(() => {
        if (tab === 'status' && admin) loadStatus(date);
        if (tab === 'templates' && admin) loadTemplates();
    }, [tab, date, admin, loadStatus, loadTemplates]);

    const complete = async (item) => {
        setSaving(true);
        setError(null);
        try {
            await api.post(`/daily-duties/mine/${item.id}/complete/`, {
                date,
                note: notes[item.id] || '',
            });
            await loadMine(date);
        } catch (err) {
            setError(errorText(err, 'Položku se nepodařilo odškrtnout.'));
        } finally {
            setSaving(false);
        }
    };

    const submitTemplate = async (event) => {
        event.preventDefault();
        setSaving(true);
        setError(null);
        const body = {
            title: form.title.trim(),
            description: form.description,
            periodicity: form.periodicity,
            is_active: form.is_active,
            prodejna: form.target === 'prodejna' ? Number(form.prodejna) : null,
            uzivatel: form.target === 'uzivatel' ? Number(form.uzivatel) : null,
        };
        try {
            if (editingId) {
                await api.patch(`/daily-duties/templates/${editingId}/`, body);
            } else {
                await api.post('/daily-duties/templates/', body);
            }
            setForm(emptyForm);
            setEditingId(null);
            await loadTemplates();
        } catch (err) {
            setError(errorText(err, 'Šablonu se nepodařilo uložit.'));
        } finally {
            setSaving(false);
        }
    };

    const editTemplate = (template) => {
        setEditingId(template.id);
        setForm({
            title: template.title,
            description: template.description || '',
            periodicity: template.periodicity,
            target: template.uzivatel ? 'uzivatel' : 'prodejna',
            prodejna: template.prodejna ? String(template.prodejna) : '',
            uzivatel: template.uzivatel ? String(template.uzivatel) : '',
            is_active: template.is_active,
        });
    };

    const removeTemplate = async (template) => {
        if (!window.confirm(`Smazat šablonu „${template.title}“?`)) return;
        try {
            await api.delete(`/daily-duties/templates/${template.id}/`);
            await loadTemplates();
        } catch (err) {
            setError(errorText(err, 'Šablonu se nepodařilo smazat.'));
        }
    };

    const renderItem = (item, { checkable }) => (
        <article
            key={`${item.id}-${item.period_start}`}
            className={`daily-duties-card${item.completed ? ' daily-duties-card--done' : ''}`}
        >
            <div className="daily-duties-card__title">{item.title}</div>
            <div className="daily-duties-card__meta">
                <span className="daily-duties-badge">{item.periodicity_display}</span>
                {item.target_label}
                {item.period_label ? ` · ${item.period_label}` : ''}
            </div>
            {item.description && <p className="daily-duties-card__desc">{item.description}</p>}
            {item.completed && item.completion && (
                <p className="daily-duties-card__meta">
                    Splněno
                    {item.completion.completed_by_name ? ` · ${item.completion.completed_by_name}` : ''}
                    {item.completion.note ? ` · ${item.completion.note}` : ''}
                </p>
            )}
            {checkable && (
                <div className="daily-duties-card__actions">
                    {item.completed ? (
                        <span>Hotovo v tomto období</span>
                    ) : (
                        <>
                            <input
                                value={notes[item.id] || ''}
                                onChange={(event) => setNotes({ ...notes, [item.id]: event.target.value })}
                                placeholder="Poznámka (volitelně)"
                                aria-label={`Poznámka k ${item.title}`}
                            />
                            <button
                                type="button"
                                className="btn btn--primary"
                                disabled={saving || !item.can_complete}
                                onClick={() => complete(item)}
                            >
                                Splnit
                            </button>
                        </>
                    )}
                </div>
            )}
        </article>
    );

    return (
        <div className="daily-duties-module">
            <PageHeader
                title="Denní povinnosti"
                subtitle="Denní, týdenní a měsíční položky pro prodejnu nebo konkrétního člověka."
            />

            <div className="daily-duties-tabs" role="tablist">
                <button type="button" className={tab === 'mine' ? 'is-active' : ''} onClick={() => setTab('mine')}>
                    Moje
                </button>
                {admin && (
                    <>
                        <button type="button" className={tab === 'status' ? 'is-active' : ''} onClick={() => setTab('status')}>
                            Stav
                        </button>
                        <button type="button" className={tab === 'templates' ? 'is-active' : ''} onClick={() => setTab('templates')}>
                            Šablony
                        </button>
                    </>
                )}
            </div>

            {tab !== 'templates' && (
                <label className="daily-duties-date">
                    Den (u týdenních a měsíčních se bere období, do kterého den spadá)
                    <input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
                </label>
            )}

            {error && <div className="alert alert-warning">{error}</div>}

            {tab === 'mine' && (
                <>
                    {loading && <p>Načítám…</p>}
                    {!loading && items.length === 0 && (
                        <p className="daily-duties-empty">Pro tento den nemáte žádné povinnosti.</p>
                    )}
                    <div className="daily-duties-list">
                        {items.map((item) => renderItem(item, { checkable: true }))}
                    </div>
                </>
            )}

            {tab === 'status' && admin && (
                <div className="daily-duties-list">
                    {statusItems.length === 0 && <p className="daily-duties-empty">Žádné aktivní šablony.</p>}
                    {statusItems.map((item) => renderItem(item, { checkable: false }))}
                </div>
            )}

            {tab === 'templates' && admin && (
                <>
                    <form className="daily-duties-form" onSubmit={submitTemplate}>
                        <strong>{editingId ? 'Upravit šablonu' : 'Nová šablona'}</strong>
                        <label>
                            Název
                            <input
                                value={form.title}
                                onChange={(event) => setForm({ ...form, title: event.target.value })}
                                required
                            />
                        </label>
                        <label>
                            Popis
                            <textarea
                                rows={2}
                                value={form.description}
                                onChange={(event) => setForm({ ...form, description: event.target.value })}
                            />
                        </label>
                        <label>
                            Periodicita
                            <select
                                value={form.periodicity}
                                onChange={(event) => setForm({ ...form, periodicity: event.target.value })}
                            >
                                <option value="daily">Denně</option>
                                <option value="weekly">Týdně (jednou za ISO týden)</option>
                                <option value="monthly">Měsíčně (jednou za kalendářní měsíc)</option>
                            </select>
                        </label>
                        <label>
                            Komu
                            <select
                                value={form.target}
                                onChange={(event) => setForm({ ...form, target: event.target.value })}
                            >
                                <option value="prodejna">Prodejna</option>
                                <option value="uzivatel">Konkrétní člověk</option>
                            </select>
                        </label>
                        {form.target === 'prodejna' ? (
                            <label>
                                Prodejna
                                <select
                                    value={form.prodejna}
                                    onChange={(event) => setForm({ ...form, prodejna: event.target.value })}
                                    required
                                >
                                    <option value="">Vyberte prodejnu</option>
                                    {stores.map((store) => (
                                        <option key={store.id} value={store.id}>{store.nazev}</option>
                                    ))}
                                </select>
                            </label>
                        ) : (
                            <label>
                                Uživatel
                                <select
                                    value={form.uzivatel}
                                    onChange={(event) => setForm({ ...form, uzivatel: event.target.value })}
                                    required
                                >
                                    <option value="">Vyberte uživatele</option>
                                    {users.map((person) => (
                                        <option key={person.id} value={person.id}>
                                            {person.jmeno} {person.prijmeni} ({person.role})
                                        </option>
                                    ))}
                                </select>
                            </label>
                        )}
                        <label>
                            <span>
                                <input
                                    type="checkbox"
                                    checked={form.is_active}
                                    onChange={(event) => setForm({ ...form, is_active: event.target.checked })}
                                />
                                {' '}Aktivní
                            </span>
                        </label>
                        <div className="daily-duties-form__actions">
                            <button type="submit" className="btn btn--primary" disabled={saving}>
                                {editingId ? 'Uložit' : 'Založit'}
                            </button>
                            {editingId && (
                                <button
                                    type="button"
                                    className="btn btn--secondary"
                                    onClick={() => {
                                        setEditingId(null);
                                        setForm(emptyForm);
                                    }}
                                >
                                    Zrušit
                                </button>
                            )}
                        </div>
                    </form>
                    <div className="daily-duties-list">
                        {templates.map((template) => (
                            <article key={template.id} className="daily-duties-card">
                                <div className="daily-duties-card__title">{template.title}</div>
                                <div className="daily-duties-card__meta">
                                    <span className="daily-duties-badge">{template.periodicity_display}</span>
                                    {template.prodejna_nazev || template.uzivatel_jmeno}
                                    {template.is_active ? '' : ' · neaktivní'}
                                </div>
                                <div className="daily-duties-card__actions">
                                    <button type="button" className="btn btn--secondary" onClick={() => editTemplate(template)}>
                                        Upravit
                                    </button>
                                    <button type="button" className="btn btn--secondary" onClick={() => removeTemplate(template)}>
                                        Smazat
                                    </button>
                                </div>
                            </article>
                        ))}
                    </div>
                </>
            )}
        </div>
    );
};

export default DailyDutiesModule;
