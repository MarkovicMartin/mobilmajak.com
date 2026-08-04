import React, { useMemo, useRef } from 'react';
import { format } from 'date-fns';
import { useDraggable } from '@dnd-kit/core';
import TaskUrgencyBadge from './TaskUrgencyBadge';
import { taskDisplayTitle } from '../../utils/taskDisplay';
import { urgencyForTask, URGENCY_OVERDUE } from '../../utils/taskUrgency';
import './TaskRow.css';

const CLICK_DRAG_THRESHOLD_PX = 8;

const PRIORITY_LABELS = {
    nizka: 'Nízká',
    stredni: 'Střední',
    vysoka: 'Vysoká',
};

export function formatTaskShortDate(value) {
    if (!value) return '—';
    return format(new Date(value), 'd. M.');
}

export function formatTaskDeadline(task) {
    if (!task?.deadline) return '—';
    const d = format(new Date(task.deadline), 'd. M.');
    const t = task.deadline_cas ? String(task.deadline_cas).slice(0, 5) : '';
    return t ? `${d} ${t}` : d;
}

export const TASK_ROW_HEADERS_MANAGE = [
    '', 'Úkol', 'Přiřazeno', 'Pobočka', 'Priorita', 'Zadání', 'Dokončení', 'Urgence',
];

export const TASK_ROW_HEADERS_MINE = [
    '', 'Úkol', 'Typ', 'Zadání', 'Dokončení', 'Urgence',
];

/**
 * Dense draggable task row (order-row style).
 */
const TaskRow = ({
    task,
    variant = 'manage',
    isOpen = false,
    onToggle,
    dragEnabled = true,
    isDraggingOverlay = false,
}) => {
    const pointerStart = useRef(null);
    const isManage = variant === 'manage';

    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        isDragging,
    } = useDraggable({
        id: task.id,
        disabled: !dragEnabled || isDraggingOverlay,
        data: { task },
    });

    const style = transform
        ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
        : undefined;

    const overdue = task.stav !== 'hotovo' && urgencyForTask(task) === URGENCY_OVERDUE;
    const urgencyClass = task.at_risk || overdue ? 'task-row--at-risk' : '';
    const prioClass = task.priorita === 'vysoka'
        ? 'task-row--prio-high'
        : task.priorita === 'nizka'
            ? 'task-row--prio-low'
            : '';

    const handlePointerDownCapture = (e) => {
        pointerStart.current = { x: e.clientX, y: e.clientY };
    };

    const handleRowClick = (e) => {
        if (e.target.closest('button, a, input, textarea, select, label')) return;
        if (isDragging) return;
        const start = pointerStart.current;
        if (start) {
            const dx = Math.abs(e.clientX - start.x);
            const dy = Math.abs(e.clientY - start.y);
            if (dx > CLICK_DRAG_THRESHOLD_PX || dy > CLICK_DRAG_THRESHOLD_PX) return;
        }
        onToggle?.(task);
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            className={[
                'task-row',
                `task-row--${variant}`,
                isOpen ? 'task-row--expanded' : '',
                isDragging ? 'task-row--placeholder' : '',
                isDraggingOverlay ? 'task-row--overlay' : '',
                prioClass,
                urgencyClass,
            ].filter(Boolean).join(' ')}
            onPointerDownCapture={handlePointerDownCapture}
            onClick={handleRowClick}
            onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onToggle?.(task);
                }
            }}
            role="button"
            tabIndex={0}
            aria-expanded={isOpen}
            {...(dragEnabled && !isDraggingOverlay ? listeners : {})}
            {...(dragEnabled && !isDraggingOverlay ? attributes : {})}
        >
            <div className="task-row__cell task-row__expand">
                <button
                    type="button"
                    className="task-expand-btn"
                    aria-expanded={isOpen}
                    aria-label={isOpen ? 'Sbalit úkol' : 'Rozbalit úkol'}
                    onClick={(e) => {
                        e.stopPropagation();
                        onToggle?.(task);
                    }}
                    onPointerDown={(e) => e.stopPropagation()}
                >
                    {isOpen ? '▼' : '▶'}
                </button>
            </div>
            <div
                className="task-row__cell task-row__title"
                title={taskDisplayTitle(task)}
            >
                {taskDisplayTitle(task)}
                {task.is_unread && <span className="task-row__unread" title="Nepřečteno" />}
            </div>
            {isManage ? (
                <>
                    <div className="task-row__cell" title={task.assignee?.jmeno_plne || ''}>
                        {task.assignee?.jmeno_plne || '—'}
                    </div>
                    <div
                        className="task-row__cell"
                        title={task.prodejna?.nazev || (task.typ === 'prirazeny' && !task.id_prodejny ? 'Bez pobočky' : '')}
                    >
                        {task.prodejna?.nazev
                            || (task.typ === 'prirazeny' && !task.id_prodejny ? 'Bez pobočky' : '—')}
                    </div>
                    <div className="task-row__cell task-row__prio">
                        {PRIORITY_LABELS[task.priorita] || task.priorita || '—'}
                    </div>
                </>
            ) : (
                <div className="task-row__cell">
                    {task.typ === 'prirazeny' ? 'Od vedoucího' : 'Osobní'}
                </div>
            )}
            <div className="task-row__cell task-row__date">
                {formatTaskShortDate(task.termin_zadani)}
            </div>
            <div className="task-row__cell task-row__date">
                {formatTaskDeadline(task)}
            </div>
            <div className="task-row__cell task-row__urgency">
                <TaskUrgencyBadge task={task} />
            </div>
        </div>
    );
};

export function TaskRowGroup({
    task,
    variant,
    isOpen,
    onToggle,
    renderDetail,
    dragEnabled,
}) {
    return (
        <div className={`task-row-group${isOpen ? ' is-open' : ''}`}>
            <TaskRow
                task={task}
                variant={variant}
                isOpen={isOpen}
                onToggle={onToggle}
                dragEnabled={dragEnabled}
            />
            {isOpen && (
                <div className="task-row-detail" onPointerDown={(e) => e.stopPropagation()}>
                    {renderDetail?.(task)}
                </div>
            )}
        </div>
    );
}

/** Flat list fallback (no columns) – kept for filtered single-status views without DnD need. */
export function TaskListHeader({ variant = 'manage' }) {
    const headers = variant === 'manage' ? TASK_ROW_HEADERS_MANAGE : TASK_ROW_HEADERS_MINE;
    return (
        <div className={`task-row-header task-row-header--${variant}`} aria-hidden="true">
            {headers.map((label, i) => (
                <span key={`${label}-${i}`}>{label}</span>
            ))}
        </div>
    );
}

const TaskList = ({
    tasks,
    loading = false,
    emptyMessage = 'Žádné úkoly',
    variant = 'manage',
    expandedId = null,
    onToggle,
    renderDetail,
    dragEnabled = false,
}) => {
    const openId = useMemo(
        () => (expandedId != null ? String(expandedId) : null),
        [expandedId],
    );

    if (loading) {
        return <p className="muted">Načítám…</p>;
    }

    if (!tasks.length) {
        return <p className="muted">{emptyMessage}</p>;
    }

    return (
        <div className={`task-table task-table--${variant}`}>
            <TaskListHeader variant={variant} />
            <div className="task-table__body">
                {tasks.map((task) => (
                    <TaskRowGroup
                        key={task.id}
                        task={task}
                        variant={variant}
                        isOpen={openId === String(task.id)}
                        onToggle={onToggle}
                        renderDetail={renderDetail}
                        dragEnabled={dragEnabled}
                    />
                ))}
            </div>
        </div>
    );
};

export default TaskList;
export { TaskRow };
