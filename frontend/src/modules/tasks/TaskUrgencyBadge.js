import React from 'react';
import { urgencyForTask, urgencyLabel, urgencyClassName } from '../../utils/taskUrgency';

const TaskUrgencyBadge = ({ task }) => {
    const urgency = urgencyForTask(task);
    const label = urgencyLabel(urgency, task);
    const cls = task?.at_risk && urgency !== 'overdue'
        ? 'task-urgency task-urgency--at-risk'
        : urgencyClassName(urgency);
    return (
        <span className={cls} title={label === '—' ? 'Bez blížícího se termínu' : label}>
            {label}
        </span>
    );
};

export default TaskUrgencyBadge;
