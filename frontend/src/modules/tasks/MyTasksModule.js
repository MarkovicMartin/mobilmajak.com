import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { format } from 'date-fns';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { PageHeader } from '../../components/ui';
import { useTasks } from '../../hooks/useTasks';
import TaskDetailPanel from './TaskDetailPanel';
import TaskUrgencyBadge from './TaskUrgencyBadge';
import TaskStatusIcon from '../../components/TaskStatusIcon';
import { urgencyForTask, URGENCY_OVERDUE } from '../../utils/taskUrgency';
import { parseTaskId, TASKS_MINE_PATH } from '../../utils/taskNavigation';
import {
    taskDisplayTitle,
    isPrirazenySop,
    isActiveTask,
    ACTIVE_TASK_STAVY,
} from '../../utils/taskDisplay';
import './TasksModule.css';

const WIP_LIMIT = 3;

const MyTasksModule = ({ embedded = false }) => {
    const location = useLocation();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const taskIdFromNav = parseTaskId(searchParams, location.state);
    const [filter, setFilter] = useState('aktivni');
    const [selected, setSelected] = useState(null);
    const [newUkol, setNewUkol] = useState('');
    const [mobileDetail, setMobileDetail] = useState(false);

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
        setMobileDetail(true);
        if (task?.id) {
            navigate(`${TASKS_MINE_PATH}?id=${task.id}`, { replace: true, state: { taskId: task.id } });
        }
    }, [navigate]);

    const clearSelection = useCallback(() => {
        setSelected(null);
        setMobileDetail(false);
        navigate(TASKS_MINE_PATH, { replace: true });
    }, [navigate]);

    useEffect(() => {
        if (!taskIdFromNav || loading) return;
        const match = tasks.find((t) => t.id === taskIdFromNav);
        if (match) {
            setSelected(match);
            setMobileDetail(true);
        }
    }, [taskIdFromNav, tasks, loading]);

    const activePrirazeny = useMemo(
        () => tasks.filter((t) => isPrirazenySop(t) && isActiveTask(t)),
        [tasks],
    );

    const wipCount = activePrirazeny.length;

    const addPersonalTask = async (e) => {
        e.preventDefault();
        if (!newUkol.trim()) return;
        try {
            await create({
                ukol: newUkol.trim(),
                typ: 'osobni',
                priorita: 'stredni',
            });
            setNewUkol('');
        } catch {
            /* tiché */
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

    const showListOnMobile = !mobileDetail || !selected;

    return (
        <div className={`tasks-module my-tasks-module${embedded ? ' my-tasks-module--embedded' : ''}`}>
            {!embedded && <PageHeader title="Moje úkoly" />}

            {activePrirazeny.length > 0 && showListOnMobile && (
                <div className="profile-tasks-wip">
                    <strong>Moje aktivní přiřazené úkoly ({wipCount}/{WIP_LIMIT})</strong>
                    <div className="profile-tasks-wip-list">
                        {activePrirazeny.slice(0, WIP_LIMIT).map((t) => (
                            <button
                                key={t.id}
                                type="button"
                                className={`profile-tasks-wip-item${selected?.id === t.id ? ' selected' : ''}`}
                                onClick={() => selectTask(t)}
                            >
                                <span>{taskDisplayTitle(t)}</span>
                                <TaskUrgencyBadge task={t} />
                            </button>
                        ))}
                    </div>
                    {wipCount > WIP_LIMIT && (
                        <p className="task-wip-warning">
                            Máte {wipCount} aktivních úkolů – doporučený limit je {WIP_LIMIT}.
                        </p>
                    )}
                </div>
            )}

            {showListOnMobile && (
                <>
                    <form className="profile-tasks-personal-form" onSubmit={addPersonalTask}>
                        <input
                            className="task-control"
                            placeholder="Vlastní úkol…"
                            value={newUkol}
                            onChange={(e) => setNewUkol(e.target.value)}
                        />
                        <button type="submit" className="btn btn--primary task-submit-btn">
                            Přidat osobní úkol
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
                </>
            )}

            <div className={`tasks-layout${mobileDetail && selected ? ' tasks-layout--detail-open' : ''}`}>
                <div className={`tasks-list-panel${showListOnMobile ? '' : ' tasks-list-panel--hidden-mobile'}`}>
                    {loading && <p className="muted">Načítám…</p>}
                    {!loading && displayed.length === 0 && (
                        <p className="muted">Žádné úkoly v tomto filtru</p>
                    )}
                    {displayed.map((t) => (
                        <div
                            key={t.id}
                            className={`tasks-list-item ${selected?.id === t.id ? 'selected' : ''}`}
                            onClick={() => selectTask(t)}
                            role="button"
                            tabIndex={0}
                            onKeyDown={(e) => e.key === 'Enter' && selectTask(t)}
                        >
                            <TaskStatusIcon task={t} size="sm" />
                            <div className="tasks-list-item-body">
                                <div className="task-title">{taskDisplayTitle(t)}</div>
                                <div className="metric-sub">
                                    {t.typ === 'prirazeny' ? 'Od vedoucího' : 'Osobní'}
                                    {t.deadline
                                        ? ` · ${format(new Date(t.deadline), 'd. M. yyyy')}`
                                        : ''}
                                    {isPrirazenySop(t) && ACTIVE_TASK_STAVY.includes(t.stav)
                                        ? ` · ${t.stav}`
                                        : ''}
                                </div>
                            </div>
                            <div className="tasks-list-item-badges">
                                <TaskUrgencyBadge task={t} />
                            </div>
                        </div>
                    ))}
                </div>

                <div className={`tasks-detail-column${mobileDetail && selected ? ' tasks-detail-column--mobile-open' : ''}`}>
                    {mobileDetail && selected && (
                        <button
                            type="button"
                            className="tasks-mobile-back btn-link"
                            onClick={clearSelection}
                        >
                            ← Zpět na seznam
                        </button>
                    )}
                    <TaskDetailPanel
                        task={selected}
                        layout="page"
                        onClose={mobileDetail && selected ? clearSelection : undefined}
                        onUpdate={handleTaskUpdate}
                    />
                </div>
            </div>
        </div>
    );
};

export default MyTasksModule;
