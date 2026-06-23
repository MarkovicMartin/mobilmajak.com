export const TASKS_SECTIONS = [
    { id: 'mine', path: 'mine', tabLabel: 'Moje úkoly', icon: 'fa-clipboard-list' },
    { id: 'manage', path: 'manage', tabLabel: 'Správa úkolů', icon: 'fa-tasks', managerOnly: true },
    { id: 'workload', path: 'workload', tabLabel: 'Vytížení', icon: 'fa-chart-bar', adminOnly: true },
];

export const DEFAULT_TASKS_SECTION = TASKS_SECTIONS[0].id;

export const tasksIdFromPath = (pathname) => {
    const segment = (pathname || '').replace(/^\/tasks\/?/, '').split('/')[0] || '';
    const section = TASKS_SECTIONS.find((s) => s.path === segment);
    return section?.id || DEFAULT_TASKS_SECTION;
};

export const tasksPathForId = (id) => {
    const section = TASKS_SECTIONS.find((s) => s.id === id);
    return section ? `/tasks/${section.path}` : '/tasks/mine';
};

export function getVisibleTasksSections({ isAdmin, canManageTasks }) {
    return TASKS_SECTIONS.filter((section) => {
        if (section.adminOnly && !isAdmin()) return false;
        if (section.managerOnly && !canManageTasks()) return false;
        return true;
    });
}
