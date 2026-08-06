import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { taskAPI } from '../services/api';
import { taskDisplayTitle, STAV_LABELS } from '../utils/taskDisplay';
import { urgencyForTask, URGENCY_OVERDUE } from '../utils/taskUrgency';
import { openTask, TASKS_MINE_PATH } from '../utils/taskNavigation';
import TaskUrgencyBadge from '../modules/tasks/TaskUrgencyBadge';
import '../modules/tasks/TasksModule.css';
import './MyTasksPreview.css';

const PREVIEW_LIMIT = 6;
const OPEN_STAVY = new Set(['novy', 'v_procesu', 'blokovany', 'ceka_schvaleni']);

const URGENCY_RANK = {
    overdue: 0,
    urgent: 1,
    warn: 2,
    neutral: 3,
};

function formatDeadline(task) {
    if (!task.deadline) return '';
    const [, m, d] = task.deadline.split('-');
    const date = `${d}.${m}.`;
    if (task.deadline_cas) return `${date} ${String(task.deadline_cas).slice(0, 5)}`;
    return date;
}

function sortOpenTasks(a, b) {
    const ua = urgencyForTask(a);
    const ub = urgencyForTask(b);
    const ra = URGENCY_RANK[ua] ?? 9;
    const rb = URGENCY_RANK[ub] ?? 9;
    if (ra !== rb) return ra - rb;
    const da = a.deadline || '9999-99-99';
    const db = b.deadline || '9999-99-99';
    if (da !== db) return da.localeCompare(db);
    return (a.id || 0) - (b.id || 0);
}

export default function MyTasksPreview() {
    const navigate = useNavigate();
    const { user, canManageTasks } = useAuth();
    const [tasks, setTasks] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const data = await taskAPI.list({ scope: 'mine', stav: 'vse', limit: 50 });
                if (!cancelled) setTasks(Array.isArray(data) ? data : []);
            } catch {
                if (!cancelled) setTasks([]);
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => { cancelled = true; };
    }, []);

    const openTasks = useMemo(
        () => tasks.filter((t) => OPEN_STAVY.has(t.stav)).sort(sortOpenTasks),
        [tasks],
    );

    const preview = openTasks.slice(0, PREVIEW_LIMIT);
    const remaining = openTasks.length - preview.length;

    const handleOpen = (task) => {
        openTask(navigate, task, {
            user,
            canManageTasks: typeof canManageTasks === 'function' ? canManageTasks() : !!canManageTasks,
        });
    };

    return (
        <section className="my-tasks-preview card" aria-labelledby="my-tasks-preview-heading">
            <div className="my-tasks-preview__header">
                <h3 className="my-tasks-preview__title" id="my-tasks-preview-heading">
                    Moje úkoly
                    {!loading && openTasks.length > 0 ? (
                        <span className="my-tasks-preview__count">{openTasks.length}</span>
                    ) : null}
                </h3>
                <Link to={TASKS_MINE_PATH} className="my-tasks-preview__link">
                    Všechny →
                </Link>
            </div>

            {loading ? (
                <p className="my-tasks-preview__empty">Načítám úkoly…</p>
            ) : preview.length === 0 ? (
                <p className="my-tasks-preview__empty">Nemáte otevřené úkoly.</p>
            ) : (
                <ul className="my-tasks-preview__list">
                    {preview.map((task) => {
                        const overdue = urgencyForTask(task) === URGENCY_OVERDUE;
                        return (
                            <li key={task.id}>
                                <button
                                    type="button"
                                    className={`my-tasks-preview__item${overdue ? ' my-tasks-preview__item--overdue' : ''}${task.is_unread ? ' my-tasks-preview__item--unread' : ''}`}
                                    onClick={() => handleOpen(task)}
                                >
                                    <span className="my-tasks-preview__item-main">
                                        <span className="my-tasks-preview__item-title">
                                            {task.typ === 'prirazeny' ? '📋 ' : ''}
                                            {taskDisplayTitle(task)}
                                        </span>
                                        <span className="my-tasks-preview__item-meta">
                                            <span>{STAV_LABELS[task.stav] || task.stav}</span>
                                            {formatDeadline(task) ? (
                                                <span>do {formatDeadline(task)}</span>
                                            ) : null}
                                        </span>
                                    </span>
                                    <TaskUrgencyBadge task={task} />
                                </button>
                            </li>
                        );
                    })}
                </ul>
            )}

            {!loading && remaining > 0 ? (
                <Link to={TASKS_MINE_PATH} className="my-tasks-preview__more">
                    +{remaining} další{remaining === 1 ? '' : remaining < 5 ? ' úkoly' : ' úkolů'}
                </Link>
            ) : null}
        </section>
    );
}
