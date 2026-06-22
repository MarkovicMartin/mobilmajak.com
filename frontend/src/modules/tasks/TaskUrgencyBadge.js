import React from 'react';
import { urgencyForTask, urgencyLabel, urgencyClassName } from '../../utils/taskUrgency';

const TaskUrgencyBadge = ({ task }) => {
    const urgency = urgencyForTask(task);
    const label = urgencyLabel(urgency, task);
    if (!label) return null;
    const cls = task?.at_risk ? 'task-urgency task-urgency--at-risk' : urgencyClassName(urgency);
    return (
        <span className={cls} title={label}>
            {label}
        </span>
    );
};

export default TaskUrgencyBadge;
