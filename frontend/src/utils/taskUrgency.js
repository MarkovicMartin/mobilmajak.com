import { differenceInHours, differenceInDays, isPast, parseISO } from 'date-fns';

export const URGENCY_NEUTRAL = 'neutral';
export const URGENCY_WARN = 'warn';
export const URGENCY_URGENT = 'urgent';
export const URGENCY_OVERDUE = 'overdue';

export function taskDeadlineDate(task) {
    if (!task?.deadline) return null;
    const base = typeof task.deadline === 'string' ? parseISO(task.deadline) : new Date(task.deadline);
    if (task.deadline_cas) {
        const [h, m] = String(task.deadline_cas).split(':').map(Number);
        base.setHours(h || 23, m || 59, 59, 999);
    } else {
        base.setHours(23, 59, 59, 999);
    }
    return base;
}

export function urgencyForTask(task, now = new Date()) {
    if (task?.urgency) return task.urgency;
    const deadline = taskDeadlineDate(task);
    if (!deadline) return URGENCY_NEUTRAL;
    if (isPast(deadline)) return URGENCY_OVERDUE;
    const hours = differenceInHours(deadline, now);
    if (hours <= 24) return URGENCY_URGENT;
    const days = differenceInDays(deadline, now);
    if (days <= 7) return URGENCY_WARN;
    return URGENCY_NEUTRAL;
}

export function urgencyLabel(urgency) {
    switch (urgency) {
        case URGENCY_OVERDUE:
            return 'Po termínu';
        case URGENCY_URGENT:
            return 'Do 24 h';
        case URGENCY_WARN:
            return 'Blíží se termín';
        default:
            return '';
    }
}

export function urgencyClassName(urgency) {
    return `task-urgency task-urgency--${urgency || URGENCY_NEUTRAL}`;
}
