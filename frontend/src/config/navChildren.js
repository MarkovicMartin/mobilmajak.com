import { ANALYTICS_SECTIONS } from '../modules/analytics/analyticsSections';
import { PLANS_SECTIONS } from '../modules/plans/plansSections';
import { COACHING_SECTIONS } from '../modules/coaching/coachingSections';
import { SHIFTS_SECTIONS } from '../modules/shifts/shiftsSections';

const PROFILE_NAV_CHILDREN = [
    { id: 'calendar', label: 'Můj kalendář', icon: 'fa-calendar' },
    { id: 'shifts', label: 'Směny', path: '/shifts', icon: 'fa-calendar-alt' },
    { id: 'analytics', label: 'Moje výsledky', icon: 'fa-chart-line' },
    { id: 'info', label: 'Osobní údaje', icon: 'fa-id-card' },
];

/** Podpoložky modulů pro sidebar (desktop) a ploché menu (mobil). */
export function getNavChildren(parentItem, auth) {
    if (!parentItem?.sectionKey) return [];

    switch (parentItem.sectionKey) {
        case 'analytics':
            return ANALYTICS_SECTIONS.map((s) => ({
                sectionKey: `analytics-${s.id}`,
                label: s.tabLabel,
                path: `/analytics/${s.id}`,
                icon: s.icon,
                isChild: true,
            }));

        case 'plans':
            return PLANS_SECTIONS.map((s) => ({
                sectionKey: `plans-${s.id}`,
                label: s.tabLabel,
                path: `/plans/${s.path}`,
                icon: s.icon,
                isChild: true,
            }));

        case 'coaching':
            return COACHING_SECTIONS.map((s) => ({
                sectionKey: `coaching-${s.id}`,
                label: s.tabLabel,
                path: s.path ? `/coaching/${s.path}` : '/coaching',
                icon: s.icon,
                isChild: true,
            }));

        case 'shifts':
            return SHIFTS_SECTIONS.filter(
                (s) => !s.adminOnly || auth.isAdmin(),
            ).map((s) => ({
                sectionKey: `shifts-${s.id}`,
                label: s.tabLabel,
                path: '/shifts',
                navState: { view: s.id },
                icon: s.icon,
                isChild: true,
            }));

        case 'profile':
            return PROFILE_NAV_CHILDREN.map((s) => ({
                sectionKey: `profile-${s.id}`,
                label: s.label,
                path: s.path || '/profile',
                navState: s.path ? undefined : { profileTab: s.id },
                icon: s.icon,
                isChild: true,
            }));

        default:
            return [];
    }
}

export const PARENTS_WITH_CHILDREN = new Set([
    'analytics',
    'plans',
    'coaching',
    'shifts',
]);
