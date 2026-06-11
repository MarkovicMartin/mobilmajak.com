import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { format } from 'date-fns';
import { useAuth } from '../../context/AuthContext';
import { taskAPI, storeAPI } from '../../services/api';
import { AnalyticsDateInput } from '../../components/AnalyticsDateRange';
import { useTasks } from '../../hooks/useTasks';
import TaskDetailPanel from './TaskDetailPanel';
import TaskEditForm from './TaskEditForm';
import TaskUrgencyBadge from './TaskUrgencyBadge';
import TaskStatusIcon from '../../components/TaskStatusIcon';
import { TaskAssigneeOptions } from './TaskAssigneeOptions';
import './TasksModule.css';

const TasksManageModule = () => {
    const { user, isAdmin, canManageTasks } = useAuth();
    const [stores, setStores] = useState([]);
    const [assignees, setAssignees] = useState([]);
    const [filterStav, setFilterStav] = useState('vse');
    const [filterStore, setFilterStore] = useState('');
    const [filterAssignee, setFilterAssignee] = useState('');
    const [selected, setSelected] = useState(null);
    const [editing, setEditing] = useState(false);
    const [form, setForm] = useState({
        ukol: '',
        priorita: 'stredni',
        deadline: '',
        deadline_cas: '',
        id_prodejny: '',
        id_prodejce_ukol: '',
        typ: 'prirazeny',
    });

    const listParams = useMemo(() => {
        const p = { stav: filterStav, typ: 'prirazeny' };
        if (filterStore) p.prodejna_id = filterStore;
        if (filterAssignee) p.prodejce_id = filterAssignee;
        return p;
    }, [filterStav, filterStore, filterAssignee]);

    const { tasks, loading, load, create, update } = useTasks({
        autoLoad: false,
        listParams,
    });

    const vedouciStores = useMemo(() => {
        if (isAdmin()) return stores;
        if (user?.role === 'VEDOUCI') {
            return stores.filter((s) => s.vedouci_user_id === user.id);
        }
        return [];
    }, [stores, user, isAdmin]);

    useEffect(() => {
        const fetchStores = async () => {
            try {
                const data = await storeAPI.getStores({ aktivni: true });
                const list = data?.success
                    ? (data.stores || [])
                    : (Array.isArray(data) ? data : data?.stores || data?.prodejny || []);
                setStores(list.filter((s) => s.aktivni !== false));
            } catch {
                setStores([]);
            }
        };
        fetchStores();
    }, []);

    useEffect(() => {
        if (vedouciStores.length === 1 && !form.id_prodejny) {
            setForm((f) => ({ ...f, id_prodejny: String(vedouciStores[0].id) }));
            setFilterStore(String(vedouciStores[0].id));
        }
    }, [vedouciStores, form.id_prodejny]);

    useEffect(() => {
        load(listParams);
    }, [load, listParams]);

    const loadAssignees = useCallback(async (storeId) => {
        if (!storeId) {
            setAssignees([]);
            return;
        }
        try {
            const res = await taskAPI.getAssignees(storeId);
            setAssignees(res.assignees || []);
        } catch {
            setAssignees([]);
        }
    }, []);

    useEffect(() => {
        loadAssignees(form.id_prodejny);
    }, [form.id_prodejny, loadAssignees]);

    const handleCreate = async (e) => {
        e.preventDefault();
        if (!form.ukol || !form.id_prodejny || !form.id_prodejce_ukol) return;
        try {
            const created = await create({
                ukol: form.ukol,
                priorita: form.priorita,
                deadline: form.deadline || null,
                deadline_cas: form.deadline_cas || null,
                typ: 'prirazeny',
                id_prodejny: Number(form.id_prodejny),
                id_prodejce_ukol: Number(form.id_prodejce_ukol),
            });
            setForm((f) => ({
                ...f,
                ukol: '',
                deadline: '',
                deadline_cas: '',
            }));
            setSelected(created);
            await load(listParams);
        } catch {
            /* tiché */
        }
    };

    const handleDelete = async () => {
        if (!selected || !window.confirm('Smazat tento úkol?')) return;
        try {
            await taskAPI.delete(selected.id);
            setSelected(null);
            await load(listParams);
        } catch {
            /* tiché */
        }
    };

    const storeLocked = user?.role === 'VEDOUCI' && vedouciStores.length <= 1;

    return (
        <div className="tasks-module">
            <div className="tasks-module-header">
                <h2>Správa úkolů</h2>
                <div className="tasks-filters">
                    <select className="task-select" value={filterStav} onChange={(e) => setFilterStav(e.target.value)}>
                        <option value="vse">Všechny stavy</option>
                        <option value="novy">Nové</option>
                        <option value="v_procesu">V procesu</option>
                        <option value="hotovo">Hotové</option>
                    </select>
                    {isAdmin() && (
                        <select
                            className="task-select"
                            value={filterStore}
                            onChange={(e) => setFilterStore(e.target.value)}
                        >
                            <option value="">Všechny pobočky</option>
                            {stores.map((s) => (
                                <option key={s.id} value={s.id}>
                                    {s.nazev_kratkiy || s.nazev}
                                </option>
                            ))}
                        </select>
                    )}
                    {!isAdmin() && vedouciStores.length > 1 && (
                        <select
                            className="task-select"
                            value={filterStore}
                            onChange={(e) => setFilterStore(e.target.value)}
                        >
                            <option value="">Všechny moje pobočky</option>
                            {vedouciStores.map((s) => (
                                <option key={s.id} value={s.id}>
                                    {s.nazev_kratkiy || s.nazev}
                                </option>
                            ))}
                        </select>
                    )}
                    <select
                        className="task-select"
                        value={filterAssignee}
                        onChange={(e) => setFilterAssignee(e.target.value)}
                    >
                        <TaskAssigneeOptions assignees={assignees} placeholder="Všichni zaměstnanci" />
                    </select>
                </div>
            </div>

            <div className="task-form-card">
                <h3>Nový úkol</h3>
                <form className="task-form-grid" onSubmit={handleCreate}>
                    <input
                        className="task-control task-control--text"
                        placeholder="Text úkolu…"
                        value={form.ukol}
                        onChange={(e) => setForm({ ...form, ukol: e.target.value })}
                    />
                    <div className="task-form-row task-form-row--meta">
                        <select
                            className="task-select"
                            value={form.id_prodejny}
                            disabled={storeLocked}
                            onChange={(e) => setForm({ ...form, id_prodejny: e.target.value, id_prodejce_ukol: '' })}
                        >
                            <option value="">Pobočka…</option>
                            {(isAdmin() ? stores : vedouciStores).map((s) => (
                                <option key={s.id} value={s.id}>
                                    {s.nazev_kratkiy || s.nazev}
                                </option>
                            ))}
                        </select>
                        <select
                            className="task-select"
                            value={form.id_prodejce_ukol}
                            onChange={(e) => setForm({ ...form, id_prodejce_ukol: e.target.value })}
                            disabled={!form.id_prodejny}
                        >
                            <TaskAssigneeOptions assignees={assignees} placeholder="Přiřadit…" />
                        </select>
                        <select
                            className="task-select task-select--prio"
                            value={form.priorita}
                            onChange={(e) => setForm({ ...form, priorita: e.target.value })}
                        >
                            <option value="nizka">Nízká</option>
                            <option value="stredni">Střední</option>
                            <option value="vysoka">Vysoká</option>
                        </select>
                    </div>
                    <div className="task-form-row task-form-row--deadline">
                        <div className="task-date-field">
                            <AnalyticsDateInput
                                value={form.deadline}
                                onApply={(deadline) => setForm((f) => ({ ...f, deadline }))}
                                showError={false}
                                inputClassName="task-control task-control--date"
                            />
                        </div>
                        <input
                            type="time"
                            className="task-control task-control--time"
                            value={form.deadline_cas}
                            onChange={(e) => setForm({ ...form, deadline_cas: e.target.value })}
                        />
                        <button type="submit" className="task-submit-btn">Vytvořit úkol</button>
                    </div>
                </form>
            </div>

            <div className="tasks-layout">
                <div className="tasks-list-panel">
                    {loading && <p className="muted">Načítám…</p>}
                    {!loading && tasks.length === 0 && <p className="muted">Žádné úkoly</p>}
                    {tasks.map((t) => (
                        <div
                            key={t.id}
                            className={`tasks-list-item ${selected?.id === t.id ? 'selected' : ''}`}
                            onClick={() => { setSelected(t); setEditing(false); }}
                            onKeyDown={(e) => e.key === 'Enter' && (setSelected(t), setEditing(false))}
                            role="button"
                            tabIndex={0}
                        >
                            <TaskStatusIcon task={t} size="sm" />
                            <div className="tasks-list-item-body">
                                <div className="task-title">{t.ukol}</div>
                                <div className="metric-sub">
                                    {t.assignee?.jmeno_plne || '—'}
                                    {t.prodejna?.nazev ? ` · ${t.prodejna.nazev}` : ''}
                                    {t.deadline
                                        ? ` · ${format(new Date(t.deadline), 'd. M.')}`
                                        : ''}
                                </div>
                            </div>
                            <div className="tasks-list-item-badges">
                                <TaskUrgencyBadge task={t} />
                            </div>
                        </div>
                    ))}
                </div>
                <div>
                    {selected && editing && canManageTasks() ? (
                        <TaskEditForm
                            task={selected}
                            storeOptions={isAdmin() ? stores : vedouciStores}
                            storeLocked={storeLocked}
                            onSaved={(u) => {
                                setSelected(u);
                                setEditing(false);
                                update(u.id, u, { merge: true });
                                load(listParams);
                            }}
                            onCancel={() => setEditing(false)}
                        />
                    ) : (
                        <TaskDetailPanel
                            task={selected}
                            canEdit
                            showMarkRead={false}
                            onUpdate={(u) => {
                                setSelected(u);
                                update(u.id, u, { merge: true });
                            }}
                        />
                    )}
                    {selected && canManageTasks() && !editing && (
                        <button
                            type="button"
                            className="btn-outline"
                            style={{ marginTop: '0.75rem', marginRight: '0.5rem' }}
                            onClick={() => setEditing(true)}
                        >
                            Upravit úkol
                        </button>
                    )}
                    {selected && !editing && (
                        <button
                            type="button"
                            className="btn-outline"
                            style={{ marginTop: '0.75rem' }}
                            onClick={handleDelete}
                        >
                            Smazat úkol
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default TasksManageModule;
