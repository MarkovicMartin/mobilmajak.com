/**
 * Jediný zdroj pravdy pro hlavní navigaci (sidebar, drawer, Clarity).
 */
import { getNavChildren, PARENTS_WITH_CHILDREN } from './navChildren';
import { getAnalyticsSection } from '../modules/analytics/analyticsSections';
import { plansIdFromPath, PLANS_SECTIONS } from '../modules/plans/plansSections';
import { TASKS_SECTIONS } from '../modules/tasks/tasksSections';
import { FINANCE_MODULE_ENABLED } from './featureFlags';

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
            ...(FINANCE_MODULE_ENABLED
                ? [{ sectionKey: 'finance', label: 'Finance', path: '/finance', adminOnly: true, icon: 'fa-coins' }]
                : []),
            { sectionKey: 'orders', label: 'Objednávky', path: '/orders', icon: 'fa-shopping-cart' },
            { sectionKey: 'leaderboard', label: 'Žebříček', path: '/leaderboard', icon: 'fa-trophy' },
        ],
    },
    {
        id: 'operations',
        label: 'Operativa',
        items: [
            { sectionKey: 'shifts', label: 'Směny', path: '/shifts', icon: 'fa-calendar-alt' },
            { sectionKey: 'tasks', label: 'Úkoly', path: '/tasks', icon: 'fa-clipboard-list' },
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
    if (path === '/finance') {
        return locationPath === '/finance' || locationPath.startsWith('/finance/');
    }
    return locationPath === path || locationPath.startsWith(`${path}/`);
};

export const isNavItemVisible = (item, { isAdmin, canManageTasks, canAccessCoaching }) => {
    if (item.adminOnly && !isAdmin()) return false;
    if (item.managerOnly && !canManageTasks()) return false;
    if (item.coachingOnly && !canAccessCoaching()) return false;
    return true;
};

const attachChildren = (item, auth) => {
    if (!PARENTS_WITH_CHILDREN.has(item.sectionKey)) {
        return { ...item, children: [] };
    }
    const children = isNavItemVisible(item, auth) ? getNavChildren(item, auth) : [];
    return { ...item, children };
};

const flattenItemsForMobile = (items, auth) =>
    items.flatMap((item) => {
        if (!isNavItemVisible(item, auth)) return [];
        const children = getNavChildren(item, auth);
        if (children.length > 0) return children;
        return [item];
    });

export const getVisibleNavGroups = (auth, { mobile = false } = {}) => {
    const groups = NAV_GROUPS.map((group) => {
        const visible = group.items.filter((item) => isNavItemVisible(item, auth));
        const items = mobile
            ? flattenItemsForMobile(visible, auth)
            : visible.map((item) => attachChildren(item, auth));
        return { ...group, items };
    }).filter((group) => group.items.length > 0);

    if (auth.isAdmin() && ADMIN_NAV_GROUP.items.length > 0) {
        groups.push({
            ...ADMIN_NAV_GROUP,
            items: ADMIN_NAV_GROUP.items.filter((item) => isNavItemVisible(item, auth)),
        });
    }

    return groups;
};

/** Položky profilu pro mobilní drawer (místo záložek v modulu). */
export const getProfileNavChildren = (auth) => getNavChildren({ sectionKey: 'profile' }, auth);

export const getRouteLabel = (pathname) => {
    if (!pathname || pathname === '/') {
        return ALL_NAV_ITEMS.find((i) => i.path === '/')?.label || 'Domů';
    }
    if (pathname.startsWith('/analytics/')) {
        const id = pathname.replace('/analytics/', '').split('/')[0];
        return getAnalyticsSection(id)?.tabLabel || 'Analytika';
    }
    if (pathname.startsWith('/plans/')) {
        const section = PLANS_SECTIONS.find((s) => s.id === plansIdFromPath(pathname));
        return section?.tabLabel || 'Plány';
    }
    if (pathname.startsWith('/finance')) {
        return 'Finance';
    }
    if (pathname.startsWith('/tasks/')) {
        const section = TASKS_SECTIONS.find((s) => s.path === pathname.replace(/^\/tasks\/?/, '').split('/')[0]);
        return section ? `Úkoly – ${section.tabLabel}` : 'Úkoly';
    }
    if (pathname === '/tasks' || pathname === '/my-tasks') {
        return 'Úkoly';
    }
    if (pathname.startsWith('/coaching')) {
        if (pathname.includes('/compare')) return 'Analýza výkonu';
        if (pathname.includes('/seller/')) return 'Výkony';
        return 'Přehled týmu';
    }
    const match = ALL_NAV_ITEMS.find((item) => isNavActive(item.path, pathname));
    return match?.label || pathname.replace(/^\//, '');
};

export const navigateNavItem = (navigate, item) => {
    if (item.navState) {
        navigate(item.path, { state: item.navState });
    } else {
        navigate(item.path);
    }
};

export const isNavItemLinkActive = (item, pathname, locationState) => {
    if (item.navState?.view) {
        const view = locationState?.view || 'calendar';
        return pathname === '/shifts' && view === item.navState.view;
    }
    if (item.navState?.profileTab) {
        const tab = locationState?.profileTab || 'calendar';
        return pathname === '/profile' && tab === item.navState.profileTab;
    }
    if (item.isChild && item.path) {
        return pathname === item.path || pathname.startsWith(`${item.path}/`);
    }
    return isNavActive(item.path, pathname);
};
