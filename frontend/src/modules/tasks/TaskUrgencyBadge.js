import React from 'react';
import { urgencyForTask, urgencyLabel, urgencyClassName } from '../../utils/taskUrgency';

const TaskUrgencyBadge = ({ task }) => {
    const urgency = urgencyForTask(task);
    const label = urgencyLabel(urgency);
    if (!label) return null;
    return (
        <span className={urgencyClassName(urgency)} title={label}>
            {label}
        </span>
    );
};

export default TaskUrgencyBadge;
