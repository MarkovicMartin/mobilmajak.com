import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { taskAPI, storeAPI } from '../../services/api';
import { PageHeader, Select, DatePicker } from '../../components/ui';
import Modal from '../../components/Modal';
import { useTasks } from '../../hooks/useTasks';
import TaskDetailPanel from './TaskDetailPanel';
import TaskEditForm from './TaskEditForm';
import TaskKanbanBoard from './TaskKanbanBoard';
import { parseTaskId, sameTaskId, TASKS_MANAGE_PATH } from '../../utils/taskNavigation';
import './TasksModule.css';

const PRIORITA_OPTIONS = [
    { value: 'nizka', label: 'Nízká' },
    { value: 'stredni', label: 'Střední' },
    { value: 'vysoka', label: 'Vysoká' },
];

const emptyDodRow = () => ({ text: '', splneno: false });

const TasksManageModule = ({ embedded = false }) => {
    const { user, isAdmin, canManageTasks } = useAuth();
    const location = useLocation();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const taskIdFromNav = parseTaskId(searchParams, location.state);
    const deepLinkTried = useRef(null);
    const [stores, setStores] = useState([]);
    const [formAssignees, setFormAssignees] = useState([]);
    const [filterStore, setFilterStore] = useState('');
    const [filterAssignee, setFilterAssignee] = useState('');
    const [selected, setSelected] = useState(null);
    const [editing, setEditing] = useState(false);
    const [createOpen, setCreateOpen] = useState(false);
    const [creating, setCreating] = useState(false);
    const [formError, setFormError] = useState('');
    const [wipWarning, setWipWarning] = useState('');
    const [form, setForm] = useState({
        vysledek: '',
        popis: '',
        dod_polozky: [emptyDodRow(), emptyDodRow()],
        priorita: 'stredni',
        termin_zadani: '',
        deadline: '',
        deadline_cas: '',
        id_prodejny: '',
        id_prodejce_ukol: '',
        assigneeIds: [],
        vyzaduje_schvaleni: false,
        typ: 'prirazeny',
        bezPobocky: false,
    });

    const listParams = useMemo(() => {
        const p = { stav: 'vse', typ: 'prirazeny' };
        if (filterStore) p.prodejna_id = filterStore;
        return p;
    }, [filterStore]);

    const { tasks, loading, load, create, update, setTasks } = useTasks({
        autoLoad: false,
        listParams,
    });

    const displayedTasks = useMemo(() => {
        if (!filterAssignee) return tasks;
        return tasks.filter((t) => String(t.id_prodejce_ukol) === String(filterAssignee));
    }, [tasks, filterAssignee]);

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

    /** Filtr zaměstnanců: jen lidé, kteří mají alespoň jeden úkol v aktuálním výběru pobočky. */
    const assigneeFilterOptions = useMemo(() => {
        const byId = new Map();
        for (const t of tasks) {
            const id = t.id_prodejce_ukol;
            if (!id) continue;
            if (!byId.has(id)) {
                byId.set(id, t.assignee?.jmeno_plne || `#${id}`);
            }
        }
        return [
            { value: '', label: 'Všichni zaměstnanci' },
            ...[...byId.entries()]
                .map(([id, name]) => ({ value: String(id), label: name }))
                .sort((a, b) => a.label.localeCompare(b.label, 'cs')),
        ];
    }, [tasks]);

    const fetchAssigneesForStore = useCallback(async (storeId) => {
        if (!storeId) return [];
        try {
            const res = await taskAPI.getAssignees(storeId);
            return res.assignees || [];
        } catch {
            return [];
        }
    }, []);

    const fetchAssigneesStoreless = useCallback(async () => {
        try {
            const res = await taskAPI.getAssignees(null, { storeless: true });
            return res.assignees || [];
        } catch {
            return [];
        }
    }, []);

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
        }
        if (vedouciStores.length === 1 && !filterStore) {
            setFilterStore(String(vedouciStores[0].id));
        }
    }, [vedouciStores, form.id_prodejny, filterStore]);

    useEffect(() => {
        load(listParams);
    }, [load, listParams]);

    // Assignees for create form
    useEffect(() => {
        let cancelled = false;
        (async () => {
            if (form.bezPobocky && user?.role === 'ADMIN') {
                const list = await fetchAssigneesStoreless();
                if (!cancelled) setFormAssignees(list);
                return;
            }
            if (!form.id_prodejny) {
                if (!cancelled) setFormAssignees([]);
                return;
            }
            const list = await fetchAssigneesForStore(form.id_prodejny);
            if (!cancelled) setFormAssignees(list);
        })();
        return () => { cancelled = true; };
    }, [form.id_prodejny, form.bezPobocky, user?.role, fetchAssigneesForStore, fetchAssigneesStoreless]);

    // Drop assignee filter when selected person no longer has tasks in current store view
    useEffect(() => {
        if (!filterAssignee) return;
        const stillPresent = tasks.some(
            (t) => String(t.id_prodejce_ukol) === String(filterAssignee),
        );
        if (!stillPresent) setFilterAssignee('');
    }, [tasks, filterAssignee]);

    const selectTask = useCallback((task) => {
        setSelected(task);
        setEditing(false);
        if (task?.id) {
            navigate(`${TASKS_MANAGE_PATH}?id=${task.id}`, {
                replace: true,
                state: { taskId: task.id },
            });
        }
    }, [navigate]);

    const toggleTask = useCallback((task) => {
        if (selected && sameTaskId(selected.id, task.id)) {
            setSelected(null);
            setEditing(false);
            deepLinkTried.current = null;
            navigate(TASKS_MANAGE_PATH, { replace: true });
            return;
        }
        selectTask(task);
    }, [navigate, selectTask, selected]);

    useEffect(() => {
        if (!taskIdFromNav) {
            deepLinkTried.current = null;
            return undefined;
        }
        if (loading) return undefined;
        if (selected && sameTaskId(selected.id, taskIdFromNav)) return undefined;

        const match = tasks.find((t) => sameTaskId(t.id, taskIdFromNav));
        if (match) {
            setSelected(match);
            setEditing(false);
            return undefined;
        }

        if (deepLinkTried.current === taskIdFromNav) return undefined;
        deepLinkTried.current = taskIdFromNav;

        let cancelled = false;
        (async () => {
            try {
                const task = await taskAPI.get(taskIdFromNav);
                if (cancelled || !task?.id) return;
                // Reset filtrů, ať je úkol vidět v seznamu
                setFilterStav('vse');
                setFilterSpecial('');
                setFilterStore('');
                setFilterAssignee('');
                setTasks((list) => (
                    list.some((t) => sameTaskId(t.id, task.id)) ? list : [task, ...list]
                ));
                setSelected(task);
                setEditing(false);
            } catch {
                /* úkol neexistuje / bez oprávnění */
            }
        })();
        return () => { cancelled = true; };
    }, [taskIdFromNav, tasks, loading, selected, setTasks]);

    const updateDod = (index, text) => {
        setForm((f) => {
            const dod = [...f.dod_polozky];
            dod[index] = { ...dod[index], text };
            return { ...f, dod_polozky: dod };
        });
    };

    const addDodRow = () => {
        setForm((f) => ({ ...f, dod_polozky: [...f.dod_polozky, emptyDodRow()] }));
    };

    const removeDodRow = (index) => {
        setForm((f) => ({
            ...f,
            dod_polozky: f.dod_polozky.filter((_, i) => i !== index),
        }));
    };

    const handleCreate = async (e) => {
        e.preventDefault();
        if (creating) return;
        setFormError('');
        setWipWarning('');
        const dod = form.dod_polozky
            .map((p) => ({ text: p.text.trim(), splneno: false }))
            .filter((p) => p.text);
        const assigneeIds = (form.assigneeIds || []).map((id) => Number(id)).filter(Boolean);
        if (!form.vysledek.trim() || assigneeIds.length < 1 || !form.deadline) {
            setFormError('Vyplňte výsledek, aspoň jednoho zaměstnance a termín dokončení.');
            return;
        }
        if (!form.bezPobocky && !form.id_prodejny) {
            setFormError('Vyberte pobočku nebo zapněte „Bez pobočky“.');
            return;
        }
        if (dod.length < 1) {
            setFormError('Přidejte alespoň jednu položku Definition of Done.');
            return;
        }
        setCreating(true);
        try {
            const created = await create({
                vysledek: form.vysledek.trim(),
                ukol: form.vysledek.trim().split('\n')[0].slice(0, 255),
                popis: form.popis.trim(),
                dod_polozky: dod,
                priorita: form.priorita,
                termin_zadani: form.termin_zadani || null,
                deadline: form.deadline,
                deadline_cas: form.deadline_cas || null,
                typ: 'prirazeny',
                id_prodejny: form.bezPobocky ? null : Number(form.id_prodejny),
                id_prodejce_ukol: assigneeIds[0],
                assignee_ids: assigneeIds,
                vyzaduje_schvaleni: form.vyzaduje_schvaleni,
            });
            if (created?.wip_warning) {
                window.alert(created.wip_warning);
            }
            setForm((f) => ({
                ...f,
                vysledek: '',
                popis: '',
                dod_polozky: [emptyDodRow(), emptyDodRow()],
                termin_zadani: '',
                deadline: '',
                deadline_cas: '',
                assigneeIds: [],
                vyzaduje_schvaleni: false,
            }));
            setFormError('');
            setWipWarning('');
            setCreateOpen(false);
            setSelected(created);
            navigate(`${TASKS_MANAGE_PATH}?id=${created.id}`, {
                replace: true,
                state: { taskId: created.id },
            });
            await load(listParams);
        } catch (err) {
            setFormError(err?.response?.data?.error || 'Vytvoření se nezdařilo.');
        } finally {
            setCreating(false);
        }
    };

    const handleDelete = async () => {
        if (!selected || !window.confirm('Smazat tento úkol?')) return;
        try {
            await taskAPI.delete(selected.id);
            setSelected(null);
            deepLinkTried.current = null;
            navigate(TASKS_MANAGE_PATH, { replace: true });
            await load(listParams);
        } catch (err) {
            window.alert(err?.response?.data?.error || 'Smazání se nezdařilo.');
        }
    };

    const handleStatusChange = useCallback(async (taskId, newStav, extra = {}) => {
        try {
            const updated = await taskAPI.update(taskId, { stav: newStav, ...extra });
            setTasks((list) => list.map((t) => (t.id === updated.id ? updated : t)));
            if (selected && sameTaskId(selected.id, updated.id)) {
                setSelected(updated);
                setEditing(false);
            }
            return { success: true, task: updated };
        } catch (err) {
            return {
                success: false,
                error: err?.response?.data?.error || err?.response?.data || err?.message,
            };
        }
    }, [selected, setTasks]);

    const storeLocked = user?.role === 'VEDOUCI' && vedouciStores.length <= 1;
    const showFilterStore = isAdmin() || vedouciStores.length > 1;

    const handleAssigneeFilterChange = (v) => {
        setFilterAssignee((prev) => (
            prev && String(prev) === String(v) && v !== '' ? '' : v
        ));
    };

    const filterBar = (
        <div className="tasks-filters">
            {showFilterStore && (
                <Select
                    options={filterStoreOptions}
                    value={filterStore}
                    onChange={(v) => {
                        setFilterStore(v);
                        setFilterAssignee('');
                    }}
                    aria-label="Filtr pobočky"
                />
            )}
            <Select
                options={assigneeFilterOptions}
                value={filterAssignee}
                onChange={handleAssigneeFilterChange}
                searchable
                aria-label="Filtr zaměstnance"
            />
            {canManageTasks() && (
                <button
                    type="button"
                    className="btn btn--primary tasks-filters__new"
                    onClick={() => {
                        setFormError('');
                        setWipWarning('');
                        setCreateOpen(true);
                    }}
                >
                    Nový úkol
                </button>
            )}
        </div>
    );

    const closeCreateModal = () => {
        setCreateOpen(false);
        setFormError('');
        setWipWarning('');
    };

    return (
        <div className={`tasks-module${embedded ? ' tasks-module--embedded' : ''}`}>
            {!embedded ? (
                <PageHeader title="Správa úkolů" actions={filterBar} />
            ) : (
                filterBar
            )}

            {createOpen && (
                <Modal
                    title="Nový úkol"
                    size="lg"
                    onClose={closeCreateModal}
                    onSubmit={handleCreate}
                    contentClassName="task-create-modal"
                    bodyClassName="task-create-modal__body"
                    footer={(
                        <>
                            <button type="button" className="btn btn--ghost" onClick={closeCreateModal} disabled={creating}>
                                Zrušit
                            </button>
                            <button type="submit" className="btn btn--primary" disabled={creating}>
                                {creating
                                ? 'Vytvářím…'
                                : ((form.assigneeIds || []).length > 1
                                    ? `Vytvořit společný úkol (${(form.assigneeIds || []).length})`
                                    : 'Vytvořit úkol')}
                            </button>
                        </>
                    )}
                >
                    <div className="task-form-grid">
                        <div className="task-form-section">
                            <span className="task-form-section__label">Výsledek</span>
                            <label className="task-form-label">
                                Outcome *
                                <textarea
                                    className="task-control task-control--text"
                                    rows={2}
                                    placeholder="Co má být na konci hotovo?"
                                    value={form.vysledek}
                                    onChange={(e) => setForm({ ...form, vysledek: e.target.value })}
                                />
                            </label>
                        </div>
                        <label className="task-form-label">
                            Popis / kontext
                            <textarea
                                className="task-control task-control--text"
                                rows={2}
                                placeholder="Volitelný kontext…"
                                value={form.popis}
                                onChange={(e) => setForm({ ...form, popis: e.target.value })}
                            />
                        </label>
                        <div className="task-dod-editor">
                            <p className="task-dod-editor__title">Definition of Done *</p>
                            <p className="task-dod-editor__hint">Alespoň jedna měřitelná položka</p>
                            {form.dod_polozky.map((row, i) => (
                                <div key={i} className="task-dod-editor-row">
                                    <span className="task-dod-editor-row__num">{i + 1}</span>
                                    <input
                                        className="task-control task-control--text"
                                        placeholder={`Položka ${i + 1}`}
                                        value={row.text}
                                        onChange={(e) => updateDod(i, e.target.value)}
                                    />
                                    {form.dod_polozky.length > 1 && (
                                        <button
                                            type="button"
                                            className="btn btn--ghost task-dod-remove"
                                            onClick={() => removeDodRow(i)}
                                            aria-label="Odebrat položku"
                                        >
                                            ×
                                        </button>
                                    )}
                                </div>
                            ))}
                            <button type="button" className="btn btn--ghost task-dod-add-btn" onClick={addDodRow}>
                                + Přidat položku
                            </button>
                        </div>
                        {isAdmin() && (
                            <div className="task-toggle-row">
                                <label className="task-toggle" htmlFor="bez-pobocky">
                                    <input
                                        id="bez-pobocky"
                                        type="checkbox"
                                        checked={form.bezPobocky}
                                        onChange={(e) => setForm({
                                            ...form,
                                            bezPobocky: e.target.checked,
                                            id_prodejny: e.target.checked ? '' : form.id_prodejny,
                                            id_prodejce_ukol: '',
                                            assigneeIds: [],
                                        })}
                                    />
                                    <span className="task-toggle__track" />
                                    <span className="task-toggle__thumb" />
                                </label>
                                <div>
                                    <label className="task-toggle-label" htmlFor="bez-pobocky">
                                        Bez pobočky
                                    </label>
                                    <p className="task-toggle-hint">Pro admin / backoffice účty</p>
                                </div>
                            </div>
                        )}
                        <div className={`task-form-row task-form-row--pair${form.bezPobocky ? ' task-form-row--bez-pobocky' : ''}`}>
                            {form.bezPobocky ? (
                                <Select
                                    options={[{ value: '', label: 'Bez pobočky' }]}
                                    value=""
                                    disabled
                                    aria-label="Pobočka"
                                />
                            ) : (
                                <Select
                                    options={formStoreOptions}
                                    value={form.id_prodejny}
                                    disabled={storeLocked}
                                    onChange={(v) => setForm({
                                        ...form,
                                        id_prodejny: v,
                                        id_prodejce_ukol: '',
                                        assigneeIds: [],
                                    })}
                                    aria-label="Pobočka"
                                />
                            )}
                            <Select
                                className="task-select--prio"
                                options={PRIORITA_OPTIONS}
                                value={form.priorita}
                                onChange={(v) => setForm({ ...form, priorita: v })}
                                aria-label="Priorita"
                            />
                        </div>
                        <div className="task-assignee-multi">
                            <div className="task-assignee-multi__head">
                                <span className="task-form-section__label">Zaměstnanci</span>
                                <button
                                    type="button"
                                    className="btn btn--ghost btn--sm"
                                    disabled={!formAssignees.length}
                                    onClick={() => {
                                        const all = formAssignees.map((a) => String(a.id));
                                        const selected = form.assigneeIds || [];
                                        const every = all.length > 0 && all.every((id) => selected.includes(id));
                                        setForm({
                                            ...form,
                                            assigneeIds: every ? [] : all,
                                            id_prodejce_ukol: every ? '' : all[0],
                                        });
                                    }}
                                >
                                    {(form.assigneeIds || []).length === formAssignees.length && formAssignees.length
                                        ? 'Zrušit výběr'
                                        : 'Všichni'}
                                </button>
                            </div>
                            {!formAssignees.length && (
                                <p className="task-toggle-hint">
                                    {form.bezPobocky || form.id_prodejny
                                        ? 'Nikdo k přiřazení.'
                                        : 'Nejdřív vyberte pobočku.'}
                                </p>
                            )}
                            <div className="task-assignee-multi__list">
                                {formAssignees.map((person) => {
                                    const id = String(person.id);
                                    const checked = (form.assigneeIds || []).includes(id);
                                    return (
                                        <label key={id} className="task-assignee-multi__item">
                                            <input
                                                type="checkbox"
                                                checked={checked}
                                                onChange={() => {
                                                    const current = form.assigneeIds || [];
                                                    const next = checked
                                                        ? current.filter((value) => value !== id)
                                                        : [...current, id];
                                                    setForm({
                                                        ...form,
                                                        assigneeIds: next,
                                                        id_prodejce_ukol: next[0] || '',
                                                    });
                                                }}
                                            />
                                            <span>{person.jmeno_plne || person.jmeno}</span>
                                        </label>
                                    );
                                })}
                            </div>
                            <p className="task-toggle-hint">
                                Více lidí = jeden úkol. Krok, který odškrtne jeden, už ostatní neřeší.
                            </p>
                        </div>
                        <div className="task-form-row task-form-row--deadlines">
                            <label className="task-form-label">
                                Termín zadání
                                <div className="task-date-field">
                                    <DatePicker
                                        value={form.termin_zadani}
                                        onApply={(termin_zadani) => setForm((f) => ({ ...f, termin_zadani }))}
                                        showError={false}
                                        wrapperClassName="task-date-field"
                                    />
                                </div>
                            </label>
                            <label className="task-form-label">
                                Termín dokončení
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
                                        aria-label="Čas dokončení"
                                    />
                                </div>
                            </label>
                        </div>
                        <label className="task-checkbox-label">
                            <input
                                type="checkbox"
                                checked={form.vyzaduje_schvaleni}
                                onChange={(e) => setForm({
                                    ...form,
                                    vyzaduje_schvaleni: e.target.checked,
                                })}
                            />
                            Vyžaduje schválení
                        </label>
                        {formError && <p className="task-edit-error">{formError}</p>}
                        {wipWarning && <p className="task-wip-warning">{wipWarning}</p>}
                    </div>
                </Modal>
            )}

            <div className="tasks-list-section">
                <TaskKanbanBoard
                    tasks={displayedTasks}
                    loading={loading}
                    variant="manage"
                    expandedId={selected?.id ?? null}
                    onToggle={toggleTask}
                    onStatusChange={handleStatusChange}
                    emptyMessage="Žádné úkoly"
                    renderDetail={(task) => (
                        editing && sameTaskId(selected?.id, task.id) && canManageTasks() ? (
                            <TaskEditForm
                                task={task}
                                storeOptions={isAdmin() ? stores : vedouciStores}
                                storeLocked={storeLocked}
                                isAdmin={isAdmin()}
                                onSaved={(u) => {
                                    setSelected(u);
                                    setEditing(false);
                                    update(u.id, u, { merge: true });
                                    load(listParams);
                                }}
                                onCancel={() => setEditing(false)}
                            />
                        ) : (
                            <>
                                <TaskDetailPanel
                                    task={task}
                                    layout="expand"
                                    hideHeaderTitle
                                    canEdit
                                    isManager
                                    showMarkRead={false}
                                    onUpdate={(u) => {
                                        setSelected(u);
                                        setTasks((list) => list.map((t) => (t.id === u.id ? u : t)));
                                    }}
                                />
                                <div className="task-row-detail-actions">
                                    {canManageTasks() && (
                                        <button
                                            type="button"
                                            className="btn btn--secondary"
                                            onClick={() => setEditing(true)}
                                        >
                                            Upravit úkol
                                        </button>
                                    )}
                                    {canManageTasks() && (
                                        <button
                                            type="button"
                                            className="btn btn--secondary"
                                            onClick={handleDelete}
                                        >
                                            Smazat úkol
                                        </button>
                                    )}
                                </div>
                            </>
                        )
                    )}
                />
            </div>
        </div>
    );
};

export default TasksManageModule;
