import { reklamaceAPI, taskAPI } from './api';
import { TASKS_MINE_PATH } from '../utils/taskNavigation';

const REKLAMACE_PATH = '/reklamace';

function normalizeReklamace(row) {
    const read = Boolean(row.read_at);
    return {
        id: `reklamace:${row.id}`,
        source: 'reklamace',
        sourceLabel: 'Reklamace',
        title: row.nase_znacka || 'Reklamace',
        message: row.message,
        createdAt: row.created_at,
        read,
        link: REKLAMACE_PATH,
        markRead: async () => {
            await reklamaceAPI.markNotificationsRead([row.id]);
        },
    };
}

function normalizeTaskUnread(task) {
    const label = task.vysledek || task.ukol || 'Úkol';
    return {
        id: `task-unread:${task.id}`,
        source: 'tasks',
        sourceLabel: 'Úkoly',
        title: label,
        message: 'Nový přiřazený úkol k vyřízení',
        createdAt: task.vytvoreno,
        read: false,
        link: `${TASKS_MINE_PATH}?id=${task.id}`,
        markRead: async () => {
            await taskAPI.markRead(task.id);
        },
    };
}

function normalizeTaskOverdue(task) {
    const label = task.vysledek || task.ukol || 'Úkol';
    return {
        id: `task-overdue:${task.id}`,
        source: 'tasks',
        sourceLabel: 'Úkoly',
        title: label,
        message: 'Úkol po termínu',
        createdAt: task.deadline || task.vytvoreno,
        read: false,
        link: `${TASKS_MINE_PATH}?id=${task.id}`,
        markRead: async () => {
            await taskAPI.markRead(task.id);
        },
    };
}

function normalizeTaskRead(task) {
    const label = task.vysledek || task.ukol || 'Úkol';
    return {
        id: `task-read:${task.id}`,
        source: 'tasks',
        sourceLabel: 'Úkoly',
        title: label,
        message: 'Přečtený úkol',
        createdAt: task.precteno_v || task.vytvoreno,
        read: true,
        link: `${TASKS_MINE_PATH}?id=${task.id}`,
        markRead: null,
    };
}

function sortByDateDesc(items) {
    return [...items].sort((a, b) => {
        const ta = a.createdAt ? new Date(a.createdAt).getTime() : 0;
        const tb = b.createdAt ? new Date(b.createdAt).getTime() : 0;
        return tb - ta;
    });
}

export async function fetchUnreadNotifications() {
    const [reklamaceRows, tasks, summary] = await Promise.all([
        reklamaceAPI.listUnreadNotifications(),
        taskAPI.list({ scope: 'mine', stav: 'vse', limit: 200 }),
        taskAPI.getNotificationsSummary(),
    ]);

    const items = [];
    const seenTaskIds = new Set();

    if (Array.isArray(reklamaceRows)) {
        reklamaceRows.forEach((row) => items.push(normalizeReklamace(row)));
    }

    if (Array.isArray(tasks)) {
        tasks.forEach((task) => {
            if (task.typ === 'prirazeny' && task.is_unread) {
                items.push(normalizeTaskUnread(task));
                seenTaskIds.add(task.id);
            }
        });
        if (summary?.success) {
            tasks.forEach((task) => {
                if (task.urgency === 'overdue' && !seenTaskIds.has(task.id)) {
                    items.push(normalizeTaskOverdue(task));
                }
            });
        }
    }

    return sortByDateDesc(items);
}

export async function fetchReadNotifications() {
    const [reklamaceRows, tasks] = await Promise.all([
        reklamaceAPI.listNotifications({ unread: false }),
        taskAPI.list({ scope: 'mine', stav: 'vse', limit: 100 }),
    ]);

    const items = [];

    if (Array.isArray(reklamaceRows)) {
        reklamaceRows.forEach((row) => items.push(normalizeReklamace(row)));
    }

    if (Array.isArray(tasks)) {
        tasks.forEach((task) => {
            if (task.typ === 'prirazeny' && task.precteno_v && !task.is_unread) {
                items.push(normalizeTaskRead(task));
            }
        });
    }

    return sortByDateDesc(items);
}

export async function fetchUnreadCount() {
    const [reklamaceRows, summary] = await Promise.all([
        reklamaceAPI.listUnreadNotifications(),
        taskAPI.getNotificationsSummary(),
    ]);
    const reklamaceCount = Array.isArray(reklamaceRows) ? reklamaceRows.length : 0;
    let taskCount = 0;
    if (summary?.success) {
        taskCount = (summary.tasks_unread || 0) + (summary.overdue_count || 0);
    }
    return reklamaceCount + taskCount;
}

export function dispatchNotificationsRefresh() {
    window.dispatchEvent(new Event('notifications-refresh'));
    window.dispatchEvent(new Event('tasks-notifications-refresh'));
    window.dispatchEvent(new Event('reklamace-notifications-refresh'));
}
