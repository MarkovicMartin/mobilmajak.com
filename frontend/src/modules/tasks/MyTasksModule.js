import React, { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { PageHeader } from '../../components/ui';
import { useTasks } from '../../hooks/useTasks';
import { taskAPI } from '../../services/api';
import TaskDetailPanel from './TaskDetailPanel';
import TaskKanbanBoard from './TaskKanbanBoard';
import { urgencyForTask, URGENCY_OVERDUE } from '../../utils/taskUrgency';
import { parseTaskId, sameTaskId, TASKS_MINE_PATH } from '../../utils/taskNavigation';
import './TasksModule.css';

const MyTasksModule = ({ embedded = false }) => {
    const location = useLocation();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const taskIdFromNav = parseTaskId(searchParams, location.state);
    const [filter, setFilter] = useState('aktivni');
    const [selected, setSelected] = useState(null);
    const [newUkol, setNewUkol] = useState('');
    const [creating, setCreating] = useState(false);
    const deepLinkTried = useRef(null);

    const listParams = useMemo(() => {
        const p = { scope: 'mine' };
        if (filter === 'hotove') p.stav = 'hotovo';
        else if (filter === 'cekajici') p.stav = 'ceka_schvaleni';
        else if (filter === 'aktivni') p.stav = 'vse';
        return p;
    }, [filter]);

    const { tasks, loading, load, create, setTasks } = useTasks({ listParams });

    const selectTask = useCallback((task) => {
        setSelected(task);
        if (task?.id) {
            navigate(`${TASKS_MINE_PATH}?id=${task.id}`, { replace: true, state: { taskId: task.id } });
        }
    }, [navigate]);

    const toggleTask = useCallback((task) => {
        if (selected && sameTaskId(selected.id, task.id)) {
            setSelected(null);
            deepLinkTried.current = null;
            navigate(TASKS_MINE_PATH, { replace: true });
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
        if (selected && sameTaskId(selected.id, taskIdFromNav)) {
            return undefined;
        }

        const match = tasks.find((t) => sameTaskId(t.id, taskIdFromNav));
        if (match) {
            setSelected(match);
            if (filter === 'aktivni' && ['hotovo', 'ceka_schvaleni'].includes(match.stav)) {
                setFilter(match.stav === 'hotovo' ? 'hotove' : 'cekajici');
            }
            return undefined;
        }

        if (deepLinkTried.current === taskIdFromNav) return undefined;
        deepLinkTried.current = taskIdFromNav;

        let cancelled = false;
        (async () => {
            try {
                const task = await taskAPI.get(taskIdFromNav);
                if (cancelled || !task?.id) return;
                setTasks((list) => (
                    list.some((t) => sameTaskId(t.id, task.id)) ? list : [task, ...list]
                ));
                setSelected(task);
                if (task.stav === 'hotovo') setFilter('hotove');
                else if (task.stav === 'ceka_schvaleni') setFilter('cekajici');
                else setFilter('aktivni');
            } catch {
                /* úkol neexistuje / bez oprávnění – zůstane seznam */
            }
        })();
        return () => { cancelled = true; };
    }, [taskIdFromNav, tasks, loading, selected, filter, setTasks]);

    const addPersonalTask = async (e) => {
        e.preventDefault();
        if (creating || !newUkol.trim()) return;
        setCreating(true);
        try {
            const created = await create({
                ukol: newUkol.trim(),
                typ: 'osobni',
                priorita: 'stredni',
            });
            setNewUkol('');
            if (created?.id) selectTask(created);
        } catch {
            /* tiché */
        } finally {
            setCreating(false);
        }
    };

    const displayed = useMemo(() => {
        if (filter === 'po_terminu') {
            return tasks.filter((t) => t.stav !== 'hotovo' && urgencyForTask(t) === URGENCY_OVERDUE);
        }
        if (filter === 'at_risk') {
            return tasks.filter((t) => t.at_risk);
        }
        if (filter === 'aktivni') {
            return tasks.filter((t) => !['hotovo', 'ceka_schvaleni'].includes(t.stav));
        }
        return tasks;
    }, [tasks, filter]);

    const handleTaskUpdate = (u) => {
        setSelected(u);
        setTasks((list) => list.map((t) => (t.id === u.id ? u : t)));
        window.dispatchEvent(new Event('tasks-notifications-refresh'));
    };

    const handleStatusChange = useCallback(async (taskId, newStav, extra = {}) => {
        try {
            const updated = await taskAPI.update(taskId, { stav: newStav, ...extra });
            setTasks((list) => list.map((t) => (t.id === updated.id ? updated : t)));
            if (selected && sameTaskId(selected.id, updated.id)) {
                setSelected(updated);
            }
            window.dispatchEvent(new Event('tasks-notifications-refresh'));
            return { success: true, task: updated };
        } catch (err) {
            return {
                success: false,
                error: err?.response?.data?.error || err?.response?.data || err?.message,
            };
        }
    }, [selected, setTasks]);

    const mineColumnKeys = useMemo(() => {
        if (filter === 'hotove') return ['hotovo'];
        if (filter === 'cekajici') return ['ceka_schvaleni'];
        if (filter === 'aktivni') return ['novy', 'v_procesu', 'blokovany'];
        return null;
    }, [filter]);

    return (
        <div className={`tasks-module my-tasks-module${embedded ? ' my-tasks-module--embedded' : ''}`}>
            {!embedded && <PageHeader title="Moje úkoly" />}

            <form className="profile-tasks-personal-form" onSubmit={addPersonalTask}>
                <input
                    className="task-control"
                    placeholder="Vlastní úkol…"
                    value={newUkol}
                    onChange={(e) => setNewUkol(e.target.value)}
                />
                <button type="submit" className="btn btn--primary task-submit-btn" disabled={creating || !newUkol.trim()}>
                    {creating ? 'Přidávám…' : 'Přidat osobní úkol'}
                </button>
            </form>
            <div className="profile-tasks-filters tasks-filter-pills">
                <button
                    type="button"
                    className={`tasks-filter-pill${filter === 'aktivni' ? ' is-active' : ''}`}
                    onClick={() => setFilter('aktivni')}
                >
                    Aktivní
                </button>
                <button
                    type="button"
                    className={`tasks-filter-pill${filter === 'hotove' ? ' is-active' : ''}`}
                    onClick={() => setFilter('hotove')}
                >
                    Hotové
                </button>
                <button
                    type="button"
                    className={`tasks-filter-pill${filter === 'po_terminu' ? ' is-active' : ''}`}
                    onClick={() => setFilter('po_terminu')}
                >
                    Po termínu
                </button>
                <button
                    type="button"
                    className={`tasks-filter-pill${filter === 'at_risk' ? ' is-active' : ''}`}
                    onClick={() => setFilter('at_risk')}
                >
                    At risk
                </button>
                <button type="button" className="btn-link" onClick={() => load(listParams)}>
                    Obnovit
                </button>
            </div>

            <div className="tasks-list-section">
                <TaskKanbanBoard
                    tasks={displayed}
                    loading={loading}
                    variant="mine"
                    columnKeys={mineColumnKeys}
                    expandedId={selected?.id ?? null}
                    onToggle={toggleTask}
                    onStatusChange={handleStatusChange}
                    emptyMessage="Žádné úkoly v tomto filtru"
                    renderDetail={(task) => (
                        <TaskDetailPanel
                            task={task}
                            layout="expand"
                            hideHeaderTitle
                            onUpdate={handleTaskUpdate}
                        />
                    )}
                />
            </div>
        </div>
    );
};

export default MyTasksModule;
