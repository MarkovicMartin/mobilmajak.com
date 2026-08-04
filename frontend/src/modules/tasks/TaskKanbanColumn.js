import React from 'react';
import { useDroppable } from '@dnd-kit/core';
import { TaskListHeader, TaskRowGroup } from './TaskRow';
import './TaskKanban.css';

const TaskKanbanColumn = ({
    id,
    title,
    color,
    textColor,
    tasks,
    variant = 'manage',
    isDropTarget,
    expandedId,
    onToggle,
    renderDetail,
    dragEnabled = true,
}) => {
    const { setNodeRef, isOver } = useDroppable({
        id: `column-${id}`,
    });

    const openId = expandedId != null ? String(expandedId) : null;

    return (
        <div
            ref={setNodeRef}
            className={`task-kanban-column${isOver || isDropTarget ? ' is-drop-target' : ''}`}
        >
            <div
                className="task-kanban-column__header"
                style={{ backgroundColor: color, color: textColor }}
            >
                <span className="task-kanban-column__title">{title}</span>
                <span className="task-kanban-column__count">({tasks.length})</span>
            </div>

            <div className="task-kanban-column__body">
                <TaskListHeader variant={variant} />
                {tasks.length === 0 ? (
                    <div className="task-kanban-column__empty">Žádné úkoly</div>
                ) : (
                    tasks.map((task) => (
                        <TaskRowGroup
                            key={task.id}
                            task={task}
                            variant={variant}
                            isOpen={openId === String(task.id)}
                            onToggle={onToggle}
                            renderDetail={renderDetail}
                            dragEnabled={dragEnabled}
                        />
                    ))
                )}
            </div>
        </div>
    );
};

export default TaskKanbanColumn;
