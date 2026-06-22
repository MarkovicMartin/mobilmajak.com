/** Cesty a deep-linky pro modul úkolů (zaměstnanec vs. vedoucí). */

export const MY_TASKS_PATH = '/my-tasks';
export const MANAGE_TASKS_PATH = '/tasks';

export const tasksModulePath = (canManageTasks) => (
    canManageTasks?.() ? MANAGE_TASKS_PATH : MY_TASKS_PATH
);

export const parseTaskId = (searchParams, locationState) => {
    const fromQuery = searchParams?.get('id');
    if (fromQuery) {
        const n = Number(fromQuery);
        if (Number.isFinite(n) && n > 0) return n;
    }
    const fromState = locationState?.taskId;
    if (typeof fromState === 'number' && fromState > 0) return fromState;
    return null;
};

export const openTask = (navigate, taskId, { replace = false } = {}) => {
    if (!taskId) return;
    navigate(`${MY_TASKS_PATH}?id=${taskId}`, { replace, state: { taskId } });
};
