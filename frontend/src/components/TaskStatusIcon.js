import React from 'react';
import { taskStatusIconVariant, TASK_STATUS_ICON_LABELS } from '../utils/taskStatusIcon';
import './TaskStatusIcon.css';

const ICONS = {
    hotovo: `${process.env.PUBLIC_URL}/assets/prodejce/hotovo.png`,
    neutral: `${process.env.PUBLIC_URL}/assets/prodejce/neutral.png`,
    activity: `${process.env.PUBLIC_URL}/assets/prodejce/activity.png`,
};

export default function TaskStatusIcon({ task, size = 'md', className = '' }) {
    const variant = taskStatusIconVariant(task);
    const src = ICONS[variant] || ICONS.neutral;

    return (
        <img
            src={src}
            alt=""
            className={`task-status-icon task-status-icon--${size} task-status-icon--${variant} ${className}`.trim()}
            title={TASK_STATUS_ICON_LABELS[variant]}
            aria-hidden="true"
        />
    );
}
