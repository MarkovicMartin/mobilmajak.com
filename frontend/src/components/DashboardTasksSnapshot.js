import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { TASKS_PATH } from '../utils/taskNavigation';
import { taskAPI } from '../services/api';

const PRIORITY_LABEL = { vysoka: 'Vysoká', stredni: 'Střední', nizka: 'Nízká' };

function formatDeadline(task) {
    if (!task.deadline) return '';
    const [y, m, d] = task.deadline.split('-');
    const date = `${d}.${m}.`;
    if (task.deadline_cas) return `${date} ${task.deadline_cas}`;
    return date;
}

export default function DashboardTasksSnapshot() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const json = await taskAPI.getDashboardSnapshot();
                if (!cancelled) setData(json);
            } catch {
                if (!cancelled) setData({ today: [], week_preview: [] });
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => { cancelled = true; };
    }, []);

    const today = data?.today || [];
    const week = data?.week_preview || [];

    return (
        <section className="dashboard-tasks-section card" aria-labelledby="dashboard-tasks-heading">
            <div className="card-header dashboard-tasks-header">
                <div className="card-title" id="dashboard-tasks-heading">
                    Úkoly k dokončení
                </div>
                <Link to={`${TASKS_PATH}/manage`} className="dashboard-tasks-link">Úkoly →</Link>
            </div>

            {loading ? (
                <p className="muted dashboard-tasks-empty">Načítám úkoly…</p>
            ) : today.length === 0 ? (
                <p className="dashboard-tasks-note">
                    Dnes žádné úkoly s termínem dokončení.
                </p>
            ) : (
                <ul className="dashboard-tasks-list">
                    {today.map((task) => (
                        <li key={task.id} className={`dashboard-task-item urgency-${task.urgency}`}>
                            <Link to={`${TASKS_PATH}/manage?id=${task.id}`} className="dashboard-task-link">
                                <span className="dashboard-task-title">{task.ukol}</span>
                                <span className="dashboard-task-meta">
                                    {task.assignee && <span>{task.assignee}</span>}
                                    {task.deadline_cas && <span>{task.deadline_cas}</span>}
                                    <span>{PRIORITY_LABEL[task.priorita] || task.priorita}</span>
                                </span>
                            </Link>
                        </li>
                    ))}
                </ul>
            )}

            {!loading && week.length > 0 && (
                <div className="dashboard-tasks-week">
                    <h4 className="dashboard-tasks-week-title">Příštích 7 dní</h4>
                    <ul className="dashboard-tasks-week-list">
                        {week.map((task) => (
                            <li key={task.id} className="dashboard-task-week-item">
                                <span className="dashboard-task-week-date">{formatDeadline(task)}</span>
                                <span className="dashboard-task-week-title">{task.ukol}</span>
                                {task.assignee && (
                                    <span className="dashboard-task-week-assignee">{task.assignee}</span>
                                )}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </section>
    );
}
