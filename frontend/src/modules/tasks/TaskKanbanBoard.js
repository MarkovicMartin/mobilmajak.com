import React, { useMemo, useState } from 'react';
import {
    DndContext,
    DragOverlay,
    PointerSensor,
    TouchSensor,
    useSensor,
    useSensors,
} from '@dnd-kit/core';
import TaskKanbanColumn from './TaskKanbanColumn';
import { TaskRow } from './TaskRow';
import { STAV_LABELS } from '../../utils/taskDisplay';
import './TaskKanban.css';

export const TASK_STATUS_COLUMNS = [
    { key: 'novy', label: 'Nové', color: '#1d4ed8', textColor: '#fff' },
    { key: 'v_procesu', label: 'V procesu', color: '#b45309', textColor: '#fff' },
    { key: 'blokovany', label: 'Blokované', color: '#b91c1c', textColor: '#fff' },
    { key: 'ceka_schvaleni', label: 'Čeká schválení', color: '#7c3aed', textColor: '#fff' },
    { key: 'hotovo', label: 'Hotové', color: '#047857', textColor: '#fff' },
];

const TaskKanbanBoard = ({
    tasks,
    loading = false,
    variant = 'manage',
    statusFilter = '',
    columnKeys = null,
    expandedId = null,
    onToggle,
    renderDetail,
    onStatusChange,
    dragEnabled = true,
    emptyMessage = 'Žádné úkoly',
}) => {
    const [activeTask, setActiveTask] = useState(null);
    const [dragOverColumn, setDragOverColumn] = useState(null);

    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: { distance: 8 },
        }),
        useSensor(TouchSensor, {
            activationConstraint: { delay: 250, tolerance: 8 },
        }),
    );

    const visibleColumns = useMemo(() => {
        if (statusFilter && statusFilter !== 'vse') {
            const col = TASK_STATUS_COLUMNS.find((c) => c.key === statusFilter);
            if (col) return [col];
            return [{
                key: statusFilter,
                label: STAV_LABELS[statusFilter] || statusFilter,
                color: '#64748b',
                textColor: '#fff',
            }];
        }
        if (columnKeys?.length) {
            const set = new Set(columnKeys);
            return TASK_STATUS_COLUMNS.filter((c) => set.has(c.key));
        }
        return TASK_STATUS_COLUMNS;
    }, [statusFilter, columnKeys]);

    const tasksByStatus = useMemo(() => {
        const map = Object.fromEntries(visibleColumns.map((c) => [c.key, []]));
        tasks.forEach((task) => {
            const key = task.stav;
            if (map[key]) map[key].push(task);
            else if (visibleColumns.length === 1) map[visibleColumns[0].key].push(task);
        });
        return map;
    }, [tasks, visibleColumns]);

    const totalVisible = useMemo(
        () => Object.values(tasksByStatus).reduce((n, list) => n + list.length, 0),
        [tasksByStatus],
    );

    const handleDragStart = (event) => {
        const found = tasks.find((t) => String(t.id) === String(event.active.id));
        setActiveTask(found || event.active.data.current?.task || null);
    };

    const handleDragOver = (event) => {
        const { over } = event;
        if (over?.id && String(over.id).startsWith('column-')) {
            setDragOverColumn(String(over.id).replace('column-', ''));
        } else {
            setDragOverColumn(null);
        }
    };

    const handleDragEnd = async (event) => {
        const { active, over } = event;
        const dragged = activeTask;
        setActiveTask(null);
        setDragOverColumn(null);
        if (!over || !dragged || !onStatusChange) return;

        let newStatus = null;
        if (String(over.id).startsWith('column-')) {
            newStatus = String(over.id).replace('column-', '');
        } else {
            const overTask = tasks.find((t) => String(t.id) === String(over.id));
            if (overTask) newStatus = overTask.stav;
        }

        if (!newStatus || dragged.stav === newStatus) return;
        if (!visibleColumns.some((c) => c.key === newStatus)) return;

        let extra = {};
        if (newStatus === 'blokovany') {
            const reason = window.prompt('Důvod blokace (povinný):');
            if (!reason || !reason.trim()) {
                window.alert('Pro přesun do Blokované je povinný důvod.');
                return;
            }
            extra = { blokovano_duvod: reason.trim() };
        }

        const result = await onStatusChange(dragged.id, newStatus, extra);
        if (result && result.success === false) {
            const err = result.error;
            const msg = typeof err === 'object'
                ? (err.error || err.detail || JSON.stringify(err))
                : (typeof err === 'string' ? err : 'Nepodařilo se změnit stav');
            window.alert(msg);
        }
    };

    if (loading) {
        return (
            <div className="task-kanban-board">
                <div className="task-kanban-loading">
                    <div className="task-kanban-spinner" />
                    <p>Načítám úkoly…</p>
                </div>
            </div>
        );
    }

    if (!totalVisible) {
        return <p className="muted">{emptyMessage}</p>;
    }

    return (
        <DndContext
            sensors={sensors}
            onDragStart={handleDragStart}
            onDragOver={handleDragOver}
            onDragEnd={handleDragEnd}
        >
            <div className="task-kanban-board">
                <div className="task-kanban-columns">
                    {visibleColumns.map((col) => (
                        <TaskKanbanColumn
                            key={col.key}
                            id={col.key}
                            title={col.label}
                            color={col.color}
                            textColor={col.textColor}
                            tasks={tasksByStatus[col.key] || []}
                            variant={variant}
                            isDropTarget={dragOverColumn === col.key}
                            expandedId={expandedId}
                            onToggle={onToggle}
                            renderDetail={renderDetail}
                            dragEnabled={dragEnabled}
                        />
                    ))}
                </div>
            </div>

            <DragOverlay>
                {activeTask ? (
                    <TaskRow
                        task={activeTask}
                        variant={variant}
                        isDraggingOverlay
                        dragEnabled={false}
                    />
                ) : null}
            </DragOverlay>
        </DndContext>
    );
};

export default TaskKanbanBoard;
