import React, { useState } from 'react';
import Modal from '../../components/Modal';
import { format, parse } from 'date-fns';
import { cs } from 'date-fns/locale';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { taskAPI } from '../../services/api';
import TaskUrgencyBadge from '../tasks/TaskUrgencyBadge';
import { openTask } from '../../utils/taskNavigation';
import { shiftRoleLabel } from '../shifts/shiftRoleLabels';
import { userMayEditShiftOnDate } from '../shifts/shiftEditPolicy';

const formatShiftTime = (t) => (t || '').substring(0, 5);

const canEditShift = (shift, user, dateStr) => {
    if (!user) return false;
    if (user.role === 'ADMIN') return true;
    if (shift.user_id !== user.id && user.role !== 'VEDOUCI') return false;
    return userMayEditShiftOnDate(user, dateStr);
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
    const { user, canManageTasks } = useAuth();
    const navigate = useNavigate();
    const [newUkol, setNewUkol] = useState('');
    const [saving, setSaving] = useState(false);

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

    const openTaskInModule = (task) => {
        openTask(navigate, task, { user, canManageTasks: canManageTasks() });
        onClose();
    };

    return (
        <Modal
            title={dateLabel}
            titleId="profile-day-title"
            onClose={onClose}
            size="sm"
            bodyClassName="profile-day-body"
        >
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
                                            {s.typ_smeny === 'dovolena' || s.typ_smeny === 'nemoc' ? (
                                                <>
                                                    <span className="profile-day-shift-type">
                                                        {s.typ_smeny === 'dovolena' ? '🏖️' : '🏥'}{' '}
                                                        {shiftRoleLabel(s)}
                                                    </span>
                                                </>
                                            ) : (
                                                <>
                                                    <span className="profile-day-shift-time">
                                                        {formatShiftTime(s.cas_od)}–{formatShiftTime(s.cas_do)}
                                                    </span>
                                                    {s.prodejna_nazev && (
                                                        <span className="profile-day-shift-store">{s.prodejna_nazev}</span>
                                                    )}
                                                    <span className="profile-day-shift-type">
                                                        {shiftRoleLabel(s)}
                                                    </span>
                                                </>
                                            )}
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
                                            className={`profile-day-task-btn${focusTaskId === t.id ? ' focus' : ''}`}
                                            onClick={() => openTaskInModule(t)}
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
        </Modal>
    );
};

export default ProfileDayPanel;
