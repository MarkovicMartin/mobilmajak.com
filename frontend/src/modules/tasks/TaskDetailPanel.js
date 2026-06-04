import React, { useEffect } from 'react';
import { format } from 'date-fns';
import { cs } from 'date-fns/locale';
import { taskAPI } from '../../services/api';
import TaskUrgencyBadge from './TaskUrgencyBadge';
import TaskComments from './TaskComments';

const STAV_LABELS = {
    novy: 'Nový',
    v_procesu: 'V procesu',
    hotovo: 'Hotovo',
};

const TaskDetailPanel = ({
    task,
    onUpdate,
    onClose,
    canEdit = true,
    showMarkRead = true,
}) => {
    useEffect(() => {
        if (!task || !showMarkRead) return;
        if (task.typ === 'prirazeny' && !task.precteno_v) {
            taskAPI.markRead(task.id).then((updated) => {
                onUpdate?.({ ...task, precteno_v: updated.precteno_v });
            }).catch(() => {});
        }
    }, [task?.id]); // eslint-disable-line react-hooks/exhaustive-deps

    if (!task) {
        return (
            <div className="task-detail-panel task-detail-panel--empty">
                <p className="muted">Vyberte úkol ze seznamu</p>
            </div>
        );
    }

    const setStav = async (stav) => {
        if (!canEdit) return;
        try {
            const updated = await taskAPI.update(task.id, { stav });
            onUpdate?.(updated);
        } catch {
            /* tiché */
        }
    };

    const deadlineStr = task.deadline
        ? format(new Date(task.deadline), 'd. M. yyyy', { locale: cs })
        : null;
    const timeStr = task.deadline_cas ? String(task.deadline_cas).slice(0, 5) : null;

    return (
        <div className="task-detail-panel">
            <div className="task-detail-header">
                <h3>{task.ukol}</h3>
                {onClose && (
                    <button type="button" className="btn-icon" onClick={onClose} aria-label="Zavřít detail">
                        <i className="fas fa-times" />
                    </button>
                )}
            </div>
            <div className="task-detail-meta">
                <TaskUrgencyBadge task={task} />
                <span>Priorita: {task.priorita}</span>
                {deadlineStr && (
                    <span>
                        Termín: {deadlineStr}
                        {timeStr ? ` ${timeStr}` : ''}
                    </span>
                )}
                {task.typ === 'prirazeny' && task.zadavatel && (
                    <span>Od: {task.zadavatel.jmeno_plne || task.zadavatel.jmeno}</span>
                )}
                {task.prodejna && <span>Pobočka: {task.prodejna.nazev}</span>}
                {task.assignee && task.typ === 'prirazeny' && (
                    <span>Přiřazeno: {task.assignee.jmeno_plne}</span>
                )}
                <span>Stav: {STAV_LABELS[task.stav] || task.stav}</span>
            </div>
            {canEdit && task.stav !== 'hotovo' && (
                <div className="task-detail-actions">
                    {task.stav === 'novy' && (
                        <button type="button" className="btn-outline" onClick={() => setStav('v_procesu')}>
                            Začít řešit
                        </button>
                    )}
                    <button type="button" className="btn-primary" onClick={() => setStav('hotovo')}>
                        Označit hotovo
                    </button>
                </div>
            )}
            <TaskComments taskId={task.id} />
        </div>
    );
};

export default TaskDetailPanel;
