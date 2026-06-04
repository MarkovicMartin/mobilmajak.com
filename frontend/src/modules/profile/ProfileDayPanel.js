import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { format, parse } from 'date-fns';
import { cs } from 'date-fns/locale';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { taskAPI } from '../../services/api';
import TaskDetailPanel from '../tasks/TaskDetailPanel';
import TaskUrgencyBadge from '../tasks/TaskUrgencyBadge';

const SHIFT_TYPE_LABELS = {
    prace: 'Práce',
    dovolena: 'Dovolená',
    nemoc: 'Nemoc',
};

const formatShiftTime = (t) => (t || '').substring(0, 5);

const canEditShift = (shift, user, dateStr) => {
    if (!user) return false;
    if (['ADMIN', 'VEDOUCI'].includes(user.role)) return true;
    if (shift.user_id !== user.id) return false;
    const [y, m] = dateStr.split('-').map(Number);
    const shiftMonth = new Date(y, m - 1, 1);
    const now = new Date();
    const currentMonth = new Date(now.getFullYear(), now.getMonth(), 1);
    return shiftMonth >= currentMonth;
};

const ProfileDayPanel = ({
    dateStr,
    shifts = [],
    tasks = [],
    focusShiftId,
    focusTaskId,
    onClose,
    onRefresh,
}) => {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [newUkol, setNewUkol] = useState('');
    const [saving, setSaving] = useState(false);
    const [selectedTask, setSelectedTask] = useState(null);
    const [taskDetail, setTaskDetail] = useState(null);

    useEffect(() => {
        if (focusTaskId) {
            const match = tasks.find((t) => t.id === focusTaskId);
            if (match) {
                setSelectedTask(match);
                setTaskDetail(match);
            }
        }
    }, [focusTaskId, tasks]);

    if (!dateStr) return null;

    const dateLabel = format(parse(dateStr, 'yyyy-MM-dd', new Date()), 'EEEE d. MMMM yyyy', { locale: cs });
    const month = dateStr.slice(0, 7);

    const openShiftsModule = (openForm = false) => {
        navigate('/shifts', {
            state: { month, datum: dateStr, openForm },
        });
        onClose();
    };

    const addPersonalTask = async (e) => {
        e.preventDefault();
        if (!newUkol.trim() || saving) return;
        setSaving(true);
        try {
            await taskAPI.create({
                ukol: newUkol.trim(),
                typ: 'osobni',
                priorita: 'stredni',
                deadline: dateStr,
            });
            setNewUkol('');
            onRefresh?.();
            window.dispatchEvent(new Event('tasks-notifications-refresh'));
        } catch {
            /* tiché */
        } finally {
            setSaving(false);
        }
    };

    const openTaskInProfile = (task) => {
        navigate('/profile', { state: { profileTab: 'tasks', taskId: task.id } });
        onClose();
    };

    const handleTaskSelect = async (task) => {
        setSelectedTask(task);
        setTaskDetail(task);
    };

    const handleTaskUpdate = (updated) => {
        setTaskDetail(updated);
        setSelectedTask(updated);
        onRefresh?.();
    };

    return createPortal(
        <div className="modal-overlay profile-day-overlay" onClick={onClose}>
            <div
                className="modal-content profile-day-panel"
                onClick={(e) => e.stopPropagation()}
                role="dialog"
                aria-labelledby="profile-day-title"
            >
                <div className="modal-header">
                    <h2 id="profile-day-title">{dateLabel}</h2>
                    <button type="button" className="modal-close" onClick={onClose} aria-label="Zavřít">
                        ×
                    </button>
                </div>
                <div className="modal-body profile-day-body">
                    <section className="profile-day-section">
                        <h3>Směny</h3>
                        {shifts.length === 0 ? (
                            <p className="muted">Žádná směna</p>
                        ) : (
                            <ul className="profile-day-shift-list">
                                {shifts.map((s) => (
                                    <li
                                        key={s.id}
                                        className={`profile-day-shift-card${focusShiftId === s.id ? ' profile-day-shift-card--focus' : ''}`}
                                    >
                                        <div className="profile-day-shift-main">
                                            <span className="profile-day-shift-time">
                                                {formatShiftTime(s.cas_od)}–{formatShiftTime(s.cas_do)}
                                            </span>
                                            {s.prodejna_nazev && (
                                                <span className="profile-day-shift-store">{s.prodejna_nazev}</span>
                                            )}
                                            <span className="profile-day-shift-type">
                                                {SHIFT_TYPE_LABELS[s.typ_smeny] || s.typ_smeny}
                                            </span>
                                        </div>
                                        {s.poznamka && (
                                            <p className="profile-day-shift-note">{s.poznamka}</p>
                                        )}
                                        {canEditShift(s, user, dateStr) && (
                                            <button
                                                type="button"
                                                className="btn-link profile-day-shift-edit"
                                                onClick={() => openShiftsModule(true)}
                                            >
                                                Upravit v modulu Směny
                                            </button>
                                        )}
                                    </li>
                                ))}
                            </ul>
                        )}
                        {canEditShift({ user_id: user?.id }, user, dateStr) && shifts.length === 0 && (
                            <button
                                type="button"
                                className="btn-outline profile-day-add-shift"
                                onClick={() => openShiftsModule(true)}
                            >
                                Přidat směnu
                            </button>
                        )}
                    </section>

                    <section className="profile-day-section">
                        <h3>Úkoly</h3>
                        {tasks.length === 0 ? (
                            <p className="muted">Žádný úkol na tento den</p>
                        ) : (
                            <ul className="profile-day-task-list">
                                {tasks.map((t) => (
                                    <li key={t.id}>
                                        <button
                                            type="button"
                                            className={`profile-day-task-btn${selectedTask?.id === t.id ? ' selected' : ''}${focusTaskId === t.id ? ' focus' : ''}`}
                                            onClick={() => handleTaskSelect(t)}
                                        >
                                            <span className="profile-day-task-title">
                                                {t.typ === 'prirazeny' ? '📋 ' : ''}
                                                {t.ukol}
                                            </span>
                                            <TaskUrgencyBadge task={t} />
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        )}
                        {selectedTask && (
                            <div className="profile-day-task-detail">
                                <TaskDetailPanel
                                    task={taskDetail}
                                    onUpdate={handleTaskUpdate}
                                    onClose={() => {
                                        setSelectedTask(null);
                                        setTaskDetail(null);
                                    }}
                                />
                                <button
                                    type="button"
                                    className="btn-link"
                                    onClick={() => openTaskInProfile(selectedTask)}
                                >
                                    Otevřít v Moje úkoly
                                </button>
                            </div>
                        )}
                    </section>

                    <section className="profile-day-section">
                        <h3>Osobní úkol / poznámka</h3>
                        <form className="profile-day-quick-add" onSubmit={addPersonalTask}>
                            <input
                                className="input"
                                placeholder="Co máte na tento den v plánu?"
                                value={newUkol}
                                onChange={(e) => setNewUkol(e.target.value)}
                            />
                            <button type="submit" className="btn-primary" disabled={saving || !newUkol.trim()}>
                                {saving ? 'Ukládám…' : 'Přidat'}
                            </button>
                        </form>
                    </section>
                </div>
            </div>
        </div>,
        document.body,
    );
};

export default ProfileDayPanel;
