import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { format } from 'date-fns';
import { useAuth } from '../../context/AuthContext';
import { taskAPI, storeAPI } from '../../services/api';
import { PageHeader, Select, DatePicker } from '../../components/ui';
import { useTasks } from '../../hooks/useTasks';
import TaskDetailPanel from './TaskDetailPanel';
import TaskEditForm from './TaskEditForm';
import TaskUrgencyBadge from './TaskUrgencyBadge';
import TaskStatusIcon from '../../components/TaskStatusIcon';
import { buildAssigneeSelectOptions } from './TaskAssigneeOptions';
import TasksWorkloadSection from './TasksWorkloadSection';
import './TasksModule.css';

const STAV_OPTIONS = [
    { value: 'vse', label: 'Všechny stavy' },
    { value: 'novy', label: 'Nové' },
    { value: 'v_procesu', label: 'V procesu' },
    { value: 'hotovo', label: 'Hotové' },
];

const PRIORITA_OPTIONS = [
    { value: 'nizka', label: 'Nízká' },
    { value: 'stredni', label: 'Střední' },
    { value: 'vysoka', label: 'Vysoká' },
];

const TasksManageModule = () => {
    const { user, isAdmin, canManageTasks } = useAuth();
    const [adminTab, setAdminTab] = useState('manage');
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

    const storeOptionsForForm = useMemo(
        () => (isAdmin() ? stores : vedouciStores),
        [isAdmin, stores, vedouciStores],
    );

    const filterStoreOptions = useMemo(() => {
        const list = isAdmin() ? stores : vedouciStores;
        const placeholder = isAdmin() ? 'Všechny pobočky' : 'Všechny moje pobočky';
        return [
            { value: '', label: placeholder },
            ...list.map((s) => ({
                value: String(s.id),
                label: s.nazev_kratkiy || s.nazev,
            })),
        ];
    }, [isAdmin, stores, vedouciStores]);

    const formStoreOptions = useMemo(
        () => [
            { value: '', label: 'Pobočka…' },
            ...storeOptionsForForm.map((s) => ({
                value: String(s.id),
                label: s.nazev_kratkiy || s.nazev,
            })),
        ],
        [storeOptionsForForm],
    );

    const assigneeFilterOptions = useMemo(
        () => buildAssigneeSelectOptions(assignees, 'Všichni zaměstnanci'),
        [assignees],
    );

    const assigneeFormOptions = useMemo(
        () => buildAssigneeSelectOptions(assignees, 'Přiřadit…'),
        [assignees],
    );

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
    const showFilterStore = isAdmin() || vedouciStores.length > 1;
    const showWorkloadTab = isAdmin();

    return (
        <div className="tasks-module">
            <PageHeader
                title={showWorkloadTab && adminTab === 'workload' ? 'Úkoly – vytížení' : 'Správa úkolů'}
                actions={(!showWorkloadTab || adminTab === 'manage') ? (
                    <div className="tasks-filters">
                        <Select
                            options={STAV_OPTIONS}
                            value={filterStav}
                            onChange={setFilterStav}
                            aria-label="Filtr stavu"
                        />
                        {showFilterStore && (
                            <Select
                                options={filterStoreOptions}
                                value={filterStore}
                                onChange={setFilterStore}
                                aria-label="Filtr pobočky"
                            />
                        )}
                        <Select
                            options={assigneeFilterOptions}
                            value={filterAssignee}
                            onChange={setFilterAssignee}
                            aria-label="Filtr zaměstnance"
                        />
                    </div>
                ) : undefined}
            />

            {showWorkloadTab && (
                <div className="tasks-admin-tabs" role="tablist" aria-label="Sekce úkolů">
                    <button
                        type="button"
                        role="tab"
                        aria-selected={adminTab === 'manage'}
                        className={`tasks-admin-tabs__btn${adminTab === 'manage' ? ' is-active' : ''}`}
                        onClick={() => setAdminTab('manage')}
                    >
                        Správa úkolů
                    </button>
                    <button
                        type="button"
                        role="tab"
                        aria-selected={adminTab === 'workload'}
                        className={`tasks-admin-tabs__btn${adminTab === 'workload' ? ' is-active' : ''}`}
                        onClick={() => setAdminTab('workload')}
                    >
                        Vytížení
                    </button>
                </div>
            )}

            {adminTab === 'workload' && showWorkloadTab ? (
                <TasksWorkloadSection />
            ) : (
                <>
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
                        <Select
                            options={formStoreOptions}
                            value={form.id_prodejny}
                            disabled={storeLocked}
                            onChange={(v) => setForm({ ...form, id_prodejny: v, id_prodejce_ukol: '' })}
                            aria-label="Pobočka"
                        />
                        <Select
                            options={assigneeFormOptions}
                            value={form.id_prodejce_ukol}
                            onChange={(v) => setForm({ ...form, id_prodejce_ukol: v })}
                            disabled={!form.id_prodejny}
                            aria-label="Přiřadit zaměstnance"
                        />
                        <Select
                            className="task-select--prio"
                            options={PRIORITA_OPTIONS}
                            value={form.priorita}
                            onChange={(v) => setForm({ ...form, priorita: v })}
                            aria-label="Priorita"
                        />
                    </div>
                    <div className="task-form-row task-form-row--deadline">
                        <div className="task-date-field">
                            <DatePicker
                                value={form.deadline}
                                onApply={(deadline) => setForm((f) => ({ ...f, deadline }))}
                                showError={false}
                                wrapperClassName="task-date-field"
                            />
                        </div>
                        <input
                            type="time"
                            className="task-control task-control--time"
                            value={form.deadline_cas}
                            onChange={(e) => setForm({ ...form, deadline_cas: e.target.value })}
                        />
                        <button type="submit" className="btn btn--primary task-submit-btn">
                            Vytvořit úkol
                        </button>
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
                            className="btn btn--secondary tasks-action-btn"
                            onClick={() => setEditing(true)}
                        >
                            Upravit úkol
                        </button>
                    )}
                    {selected && !editing && (
                        <button
                            type="button"
                            className="btn btn--secondary tasks-action-btn"
                            onClick={handleDelete}
                        >
                            Smazat úkol
                        </button>
                    )}
                </div>
            </div>
                </>
            )}
        </div>
    );
};

export default TasksManageModule;
