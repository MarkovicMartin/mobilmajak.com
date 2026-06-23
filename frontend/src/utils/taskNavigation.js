/** Cesty a deep-linky pro modul úkolů. */

export const TASKS_PATH = '/tasks';
export const TASKS_MINE_PATH = '/tasks/mine';
export const TASKS_MANAGE_PATH = '/tasks/manage';
export const TASKS_WORKLOAD_PATH = '/tasks/workload';

/** @deprecated použij TASKS_MINE_PATH */
export const MY_TASKS_PATH = TASKS_MINE_PATH;
/** @deprecated použij TASKS_MANAGE_PATH */
export const MANAGE_TASKS_PATH = TASKS_MANAGE_PATH;

export const tasksModulePath = () => TASKS_PATH;

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
    navigate(`${TASKS_MINE_PATH}?id=${taskId}`, { replace, state: { taskId } });
};
