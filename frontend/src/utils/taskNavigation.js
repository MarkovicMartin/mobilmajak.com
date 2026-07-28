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
    const fromStateNum = Number(fromState);
    if (Number.isFinite(fromStateNum) && fromStateNum > 0) return fromStateNum;
    return null;
};

export const sameTaskId = (a, b) => {
    if (a == null || b == null) return false;
    return Number(a) === Number(b);
};

/**
 * Kam otevřít úkol podle přiřazení.
 * Moje / osobní → /tasks/mine, cizí přiřazený (pro manažera) → /tasks/manage.
 */
export const pathForTask = (task, user, { canManageTasks = false } = {}) => {
    if (!task || !user) return TASKS_MINE_PATH;
    const uid = Number(user.id);
    const assigneeId = Number(task.id_prodejce_ukol);
    const creatorId = Number(task.id_prodejce_zadal);
    const isMine =
        (Number.isFinite(assigneeId) && assigneeId === uid)
        || (task.typ === 'osobni' && Number.isFinite(creatorId) && creatorId === uid)
        || (task.typ === 'osobni' && !Number.isFinite(assigneeId));
    if (isMine) return TASKS_MINE_PATH;
    if (canManageTasks) return TASKS_MANAGE_PATH;
    return TASKS_MINE_PATH;
};

/**
 * @param {Function} navigate
 * @param {number|object} taskOrId – id nebo objekt úkolu (ideálně s id_prodejce_ukol)
 * @param {{ replace?: boolean, path?: string, user?: object, canManageTasks?: boolean }} [options]
 */
export const openTask = (navigate, taskOrId, options = {}) => {
    const { replace = false, path, user, canManageTasks = false } = options;
    const task = taskOrId && typeof taskOrId === 'object' ? taskOrId : null;
    const taskId = task ? task.id : taskOrId;
    if (!taskId) return;
    const resolved = path || (task ? pathForTask(task, user, { canManageTasks }) : TASKS_MINE_PATH);
    const id = Number(taskId);
    navigate(`${resolved}?id=${id}`, { replace, state: { taskId: id } });
};
