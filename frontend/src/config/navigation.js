/**
 * Jediný zdroj pravdy pro hlavní navigaci (sidebar, drawer, Clarity).
 */

export const NAV_GROUPS = [
    {
        id: 'overview',
        label: 'Přehled',
        items: [
            { sectionKey: 'main', label: 'Domů', path: '/', icon: 'fa-home' },
        ],
    },
    {
        id: 'content',
        label: 'Obsah',
        items: [
            { sectionKey: 'news', label: 'Novinky', path: '/news', icon: 'fa-newspaper' },
        ],
    },
    {
        id: 'commerce',
        label: 'Obchod',
        items: [
            { sectionKey: 'analytics', label: 'Analytika', path: '/analytics', adminOnly: true, icon: 'fa-chart-bar' },
            { sectionKey: 'plans', label: 'Plány', path: '/plans', adminOnly: true, icon: 'fa-tasks' },
            { sectionKey: 'orders', label: 'Objednávky', path: '/orders', icon: 'fa-shopping-cart' },
            { sectionKey: 'leaderboard', label: 'Žebříček', path: '/leaderboard', icon: 'fa-trophy' },
        ],
    },
    {
        id: 'operations',
        label: 'Operativa',
        items: [
            { sectionKey: 'shifts', label: 'Směny', path: '/shifts', icon: 'fa-calendar-alt' },
            { sectionKey: 'tasks', label: 'Úkoly', path: '/tasks', managerOnly: true, icon: 'fa-clipboard-list' },
            { sectionKey: 'coaching', label: 'Výkony', path: '/coaching', coachingOnly: true, icon: 'fa-user-check' },
        ],
    },
    {
        id: 'tools',
        label: 'Nástroje',
        items: [
            { sectionKey: 'access', label: 'Přístupy', path: '/access', icon: 'fa-key' },
            { sectionKey: 'tickets', label: 'Tickety', path: '/my-tickets', icon: 'fa-ticket-alt' },
        ],
    },
];

export const ADMIN_NAV_GROUP = {
    id: 'admin',
    label: 'Správa',
    adminOnly: true,
    items: [
        { sectionKey: 'users', label: 'Uživatelé', path: '/users', adminOnly: true, icon: 'fa-users' },
        { sectionKey: 'categories', label: 'Kategorie', path: '/categories', adminOnly: true, icon: 'fa-tags' },
        { sectionKey: 'stores', label: 'Prodejny', path: '/stores', adminOnly: true, icon: 'fa-store' },
    ],
};

/** Plochý seznam pro zpětnou kompatibilitu (DockNavbar, testy). */
export const NAV_ITEMS = NAV_GROUPS.flatMap((g) => g.items);

export const ALL_NAV_ITEMS = [
    ...NAV_ITEMS,
    ...ADMIN_NAV_GROUP.items,
];

export const isNavActive = (path, locationPath) => {
    if (path === '/') return locationPath === '/';
    if (path === '/coaching') {
        return locationPath === '/coaching' || locationPath.startsWith('/coaching/');
    }
    if (path === '/analytics') {
        return locationPath === '/analytics' || locationPath.startsWith('/analytics/');
    }
    return locationPath === path || locationPath.startsWith(`${path}/`);
};

export const isNavItemVisible = (item, { isAdmin, canManageTasks, canAccessCoaching }) => {
    if (item.adminOnly && !isAdmin()) return false;
    if (item.managerOnly && !canManageTasks()) return false;
    if (item.coachingOnly && !canAccessCoaching()) return false;
    return true;
};

export const getVisibleNavGroups = (auth) => {
    const groups = NAV_GROUPS.map((group) => ({
        ...group,
        items: group.items.filter((item) => isNavItemVisible(item, auth)),
    })).filter((group) => group.items.length > 0);

    if (auth.isAdmin() && ADMIN_NAV_GROUP.items.length > 0) {
        groups.push({
            ...ADMIN_NAV_GROUP,
            items: ADMIN_NAV_GROUP.items.filter((item) => isNavItemVisible(item, auth)),
        });
    }

    return groups;
};

export const getRouteLabel = (pathname) => {
    if (!pathname || pathname === '/') {
        return ALL_NAV_ITEMS.find((i) => i.path === '/')?.label || 'Domů';
    }
    const match = ALL_NAV_ITEMS.find((item) => isNavActive(item.path, pathname));
    return match?.label || pathname.replace(/^\//, '');
};
