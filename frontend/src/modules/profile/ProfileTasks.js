import React, { useState, useMemo, useEffect } from 'react';
import { format } from 'date-fns';
import { useLocation } from 'react-router-dom';
import { useTasks } from '../../hooks/useTasks';
import TaskDetailPanel from '../tasks/TaskDetailPanel';
import TaskUrgencyBadge from '../tasks/TaskUrgencyBadge';
import TaskStatusIcon from '../../components/TaskStatusIcon';
import { urgencyForTask, URGENCY_OVERDUE } from '../../utils/taskUrgency';
import '../tasks/TasksModule.css';

const ProfileTasks = ({ initialTaskId }) => {
    const location = useLocation();
    const taskIdFromNav = initialTaskId ?? location.state?.taskId;
    const [filter, setFilter] = useState('aktivni');
    const [selected, setSelected] = useState(null);
    const [newUkol, setNewUkol] = useState('');

    const listParams = useMemo(() => {
        const p = { scope: 'mine' };
        if (filter === 'hotove') p.stav = 'hotovo';
        else if (filter === 'aktivni') p.stav = 'vse';
        return p;
    }, [filter]);

    const { tasks, loading, load, update, create } = useTasks({ listParams });

    useEffect(() => {
        if (!taskIdFromNav || loading) return;
        const match = tasks.find((t) => t.id === taskIdFromNav);
        if (match) setSelected(match);
    }, [taskIdFromNav, tasks, loading]);

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
        if (filter === 'aktivni') {
            return tasks.filter((t) => t.stav !== 'hotovo');
        }
        return tasks;
    }, [tasks, filter]);

    return (
        <div className="profile-tasks">
            <form className="task-form-grid" style={{ marginBottom: '1rem' }} onSubmit={addPersonalTask}>
                <input
                    className="input"
                    placeholder="Vlastní úkol…"
                    value={newUkol}
                    onChange={(e) => setNewUkol(e.target.value)}
                />
                <button type="submit" className="btn-primary">Přidat osobní úkol</button>
            </form>
            <div className="profile-tasks-filters">
                <button
                    type="button"
                    className={filter === 'aktivni' ? 'active' : ''}
                    onClick={() => setFilter('aktivni')}
                >
                    Aktivní
                </button>
                <button
                    type="button"
                    className={filter === 'hotove' ? 'active' : ''}
                    onClick={() => setFilter('hotove')}
                >
                    Hotové
                </button>
                <button
                    type="button"
                    className={filter === 'po_terminu' ? 'active' : ''}
                    onClick={() => setFilter('po_terminu')}
                >
                    Po termínu
                </button>
                <button type="button" className="btn-link" onClick={() => load(listParams)}>
                    Obnovit
                </button>
            </div>

            <div className="tasks-layout">
                <div className="tasks-list-panel">
                    {loading && <p className="muted">Načítám…</p>}
                    {!loading && displayed.length === 0 && (
                        <p className="muted">Žádné úkoly v tomto filtru</p>
                    )}
                    {displayed.map((t) => (
                        <div
                            key={t.id}
                            className={`tasks-list-item ${selected?.id === t.id ? 'selected' : ''}`}
                            onClick={() => setSelected(t)}
                            role="button"
                            tabIndex={0}
                            onKeyDown={(e) => e.key === 'Enter' && setSelected(t)}
                        >
                            <TaskStatusIcon task={t} size="sm" />
                            <div className="tasks-list-item-body">
                                <div className="task-title">{t.ukol}</div>
                                <div className="metric-sub">
                                    {t.typ === 'prirazeny' ? 'Od vedoucího' : 'Osobní'}
                                    {t.deadline
                                        ? ` · ${format(new Date(t.deadline), 'd. M. yyyy')}`
                                        : ''}
                                </div>
                            </div>
                            <div className="tasks-list-item-badges">
                                <TaskUrgencyBadge task={t} />
                            </div>
                        </div>
                    ))}
                </div>
                <TaskDetailPanel
                    task={selected}
                    onUpdate={(u) => {
                        setSelected(u);
                        update(u.id, u, { merge: true });
                        window.dispatchEvent(new Event('tasks-notifications-refresh'));
                    }}
                />
            </div>
        </div>
    );
};

export default ProfileTasks;
