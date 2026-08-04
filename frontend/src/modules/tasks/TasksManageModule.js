import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { format } from 'date-fns';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { taskAPI, storeAPI } from '../../services/api';
import { PageHeader, Select, DatePicker } from '../../components/ui';
import { useTasks } from '../../hooks/useTasks';
import TaskDetailPanel from './TaskDetailPanel';
import TaskEditForm from './TaskEditForm';
import TaskUrgencyBadge from './TaskUrgencyBadge';
import TaskStatusIcon from '../../components/TaskStatusIcon';
import { buildAssigneeSelectOptions } from './TaskAssigneeOptions';
import { taskDisplayTitle, ACTIVE_TASK_STAVY } from '../../utils/taskDisplay';
import { parseTaskId, sameTaskId, TASKS_MANAGE_PATH } from '../../utils/taskNavigation';
import './TasksModule.css';

const STAV_OPTIONS = [
    { value: 'vse', label: 'Všechny stavy' },
    { value: 'novy', label: 'Nové' },
    { value: 'v_procesu', label: 'V procesu' },
    { value: 'blokovany', label: 'Blokované' },
    { value: 'ceka_schvaleni', label: 'Čeká schválení' },
    { value: 'hotovo', label: 'Hotové' },
];

const FILTER_OPTIONS = [
    { value: '', label: 'Vše' },
    { value: 'at_risk', label: 'At risk' },
    { value: 'cekajici_schvaleni', label: 'Čeká schválení' },
];

const PRIORITA_OPTIONS = [
    { value: 'nizka', label: 'Nízká' },
    { value: 'stredni', label: 'Střední' },
    { value: 'vysoka', label: 'Vysoká' },
];

const WIP_LIMIT = 3;

const emptyDodRow = () => ({ text: '', splneno: false });

const TasksManageModule = ({ embedded = false }) => {
    const { user, isAdmin, canManageTasks } = useAuth();
    const location = useLocation();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const taskIdFromNav = parseTaskId(searchParams, location.state);
    const deepLinkTried = useRef(null);
    const [stores, setStores] = useState([]);
    const [assignees, setAssignees] = useState([]);
    const [filterStav, setFilterStav] = useState('vse');
    const [filterSpecial, setFilterSpecial] = useState('');
    const [filterStore, setFilterStore] = useState('');
    const [filterAssignee, setFilterAssignee] = useState('');
    const [selected, setSelected] = useState(null);
    const [editing, setEditing] = useState(false);
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
        vyzaduje_schvaleni: false,
        typ: 'prirazeny',
        bezPobocky: false,
    });

    const listParams = useMemo(() => {
        const p = { stav: filterStav, typ: 'prirazeny' };
        if (filterStore) p.prodejna_id = filterStore;
        if (filterAssignee) p.prodejce_id = filterAssignee;
        if (filterSpecial) p.filter = filterSpecial;
        return p;
    }, [filterStav, filterStore, filterAssignee, filterSpecial]);

    const { tasks, loading, load, create, update, setTasks } = useTasks({
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

    const wipByAssignee = useMemo(() => {
        const counts = {};
        tasks.forEach((t) => {
            if (!ACTIVE_TASK_STAVY.includes(t.stav)) return;
            const id = t.id_prodejce_ukol;
            counts[id] = (counts[id] || 0) + 1;
        });
        return counts;
    }, [tasks]);

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

    const loadAssignees = useCallback(async (storeId, storeless = false) => {
        if (!storeless && !storeId) {
            setAssignees([]);
            return;
        }
        try {
            const res = storeless
                ? await taskAPI.getAssignees(null, { storeless: true })
                : await taskAPI.getAssignees(storeId);
            setAssignees(res.assignees || []);
        } catch {
            setAssignees([]);
        }
    }, []);

    useEffect(() => {
        const adminUser = user?.role === 'ADMIN';
        if (form.bezPobocky && adminUser) {
            loadAssignees(null, true);
        } else {
            loadAssignees(form.id_prodejny);
        }
    }, [form.id_prodejny, form.bezPobocky, user?.role, loadAssignees]);

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
        setFormError('');
        setWipWarning('');
        const dod = form.dod_polozky
            .map((p) => ({ text: p.text.trim(), splneno: false }))
            .filter((p) => p.text);
        if (!form.vysledek.trim() || !form.id_prodejce_ukol || !form.deadline) {
            setFormError('Vyplňte výsledek, zaměstnance a termín dokončení.');
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
                id_prodejce_ukol: Number(form.id_prodejce_ukol),
                vyzaduje_schvaleni: form.vyzaduje_schvaleni,
            });
            if (created?.wip_warning) setWipWarning(created.wip_warning);
            setForm((f) => ({
                ...f,
                vysledek: '',
                popis: '',
                dod_polozky: [emptyDodRow(), emptyDodRow()],
                termin_zadani: '',
                deadline: '',
                deadline_cas: '',
                vyzaduje_schvaleni: false,
            }));
            setSelected(created);
            navigate(`${TASKS_MANAGE_PATH}?id=${created.id}`, {
                replace: true,
                state: { taskId: created.id },
            });
            await load(listParams);
        } catch (err) {
            setFormError(err?.response?.data?.error || 'Vytvoření se nezdařilo.');
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

    const storeLocked = user?.role === 'VEDOUCI' && vedouciStores.length <= 1;
    const showFilterStore = isAdmin() || vedouciStores.length > 1;

    const selectedAssigneeWip = selected?.id_prodejce_ukol
        ? wipByAssignee[selected.id_prodejce_ukol] || 0
        : 0;

    const filterBar = (
        <div className="tasks-filters">
            <Select
                options={FILTER_OPTIONS}
                value={filterSpecial}
                onChange={(v) => {
                    setFilterSpecial(v);
                    if (v === 'cekajici_schvaleni') setFilterStav('vse');
                }}
                aria-label="Speciální filtr"
            />
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
    );

    return (
        <div className={`tasks-module${embedded ? ' tasks-module--embedded' : ''}`}>
            {!embedded ? (
                <PageHeader title="Správa úkolů" actions={filterBar} />
            ) : (
                filterBar
            )}
            {assignees.length > 0 && (
                <div className="tasks-wip-bar">
                    {assignees.map((a) => {
                        const count = wipByAssignee[a.id] || 0;
                        if (!count) return null;
                        const over = count >= WIP_LIMIT;
                        return (
                            <button
                                key={a.id}
                                type="button"
                                className={`tasks-wip-chip${over ? ' is-over' : ''}`}
                                onClick={() => setFilterAssignee(String(a.id))}
                            >
                                {a.jmeno_plne}: {count}/{WIP_LIMIT}
                            </button>
                        );
                    })}
                </div>
            )}

            <div className="task-form-card">
                <div className="task-form-card__header">
                    <h3>Nový úkol</h3>
                    <span className="task-form-card__badge">SOP</span>
                </div>
                <form className="task-form-grid" onSubmit={handleCreate}>
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
                    <div className={`task-form-row task-form-row--meta${form.bezPobocky ? ' task-form-row--bez-pobocky' : ''}`}>
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
                                onChange={(v) => setForm({ ...form, id_prodejny: v, id_prodejce_ukol: '' })}
                                aria-label="Pobočka"
                            />
                        )}
                        <Select
                            options={assigneeFormOptions}
                            value={form.id_prodejce_ukol}
                            onChange={(v) => setForm({ ...form, id_prodejce_ukol: v })}
                            disabled={!form.bezPobocky && !form.id_prodejny}
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
                    <div className="task-form-row task-form-row--actions task-form-row--actions-simple">
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
                        <button type="submit" className="btn btn--primary task-submit-btn">
                            Vytvořit úkol
                        </button>
                    </div>
                    {formError && <p className="task-edit-error">{formError}</p>}
                    {wipWarning && <p className="task-wip-warning">{wipWarning}</p>}
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
                            onClick={() => selectTask(t)}
                            onKeyDown={(e) => e.key === 'Enter' && selectTask(t)}
                            role="button"
                            tabIndex={0}
                        >
                            <TaskStatusIcon task={t} size="sm" />
                            <div className="tasks-list-item-body">
                                <div className="task-title">{taskDisplayTitle(t)}</div>
                                <div className="metric-sub">
                                    {t.assignee?.jmeno_plne || '—'}
                                    {t.prodejna?.nazev ? ` · ${t.prodejna.nazev}` : (t.typ === 'prirazeny' && !t.id_prodejny ? ' · Bez pobočky' : '')}
                                    {t.termin_zadani
                                        ? ` · zadání ${format(new Date(t.termin_zadani), 'd. M.')}`
                                        : ''}
                                    {t.deadline
                                        ? ` · dokončení ${format(new Date(t.deadline), 'd. M.')}`
                                        : ''}
                                </div>
                            </div>
                            <div className="tasks-list-item-badges">
                                <TaskUrgencyBadge task={t} />
                            </div>
                        </div>
                    ))}
                </div>
                <div className="tasks-detail-column">
                    {selected && editing && canManageTasks() ? (
                        <TaskEditForm
                            task={selected}
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
                        <TaskDetailPanel
                            task={selected}
                            canEdit
                            isManager
                            showMarkRead={false}
                            onUpdate={(u) => {
                                setSelected(u);
                                setTasks((list) => list.map((t) => (t.id === u.id ? u : t)));
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
                    {selected && selectedAssigneeWip > 0 && !editing && (
                        <p className="task-wip-indicator">
                            WIP: {selectedAssigneeWip}/{WIP_LIMIT} aktivních u {selected.assignee?.jmeno_plne}
                        </p>
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
        </div>
    );
};

export default TasksManageModule;
