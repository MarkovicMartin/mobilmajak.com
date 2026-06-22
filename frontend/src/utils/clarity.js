/**
 * Microsoft Clarity – REACT_APP_CLARITY_PROJECT_ID (frontend/.env.production).
 * SPA: identify + tagy route/screen + titulek stránky kvůli správným nahrávkám a heatmapám.
 */

import { getAnalyticsSection } from '../modules/analytics/analyticsSections';
import { PLANS_SECTIONS } from '../modules/plans/plansSections';

const PROJECT_ID = (process.env.REACT_APP_CLARITY_PROJECT_ID || '').trim();
const VISITOR_KEY = 'mm_clarity_vid';

const ROUTE_SCREEN = {
    '/': 'home',
    '/orders': 'orders',
    '/shifts': 'shifts',
    '/news': 'news',
    '/access': 'access',
    '/plans': 'plans',
    '/analytics': 'analytics',
    '/coaching': 'coaching',
    '/leaderboard': 'leaderboard',
    '/profile': 'profile',
    '/my-tasks': 'my-tasks',
    '/tasks': 'tasks',
    '/my-tickets': 'my-tickets',
    '/users': 'users',
    '/categories': 'categories',
    '/stores': 'stores',
    '/tickets': 'tickets',
};

const ROUTE_LABEL = {
    '/': 'Domů',
    '/orders': 'Objednávky',
    '/shifts': 'Směny',
    '/news': 'Novinky',
    '/access': 'Přístupy',
    '/plans': 'Plány',
    '/analytics': 'Analytika',
    '/coaching': 'Výkony',
    '/leaderboard': 'Žebříček',
    '/profile': 'Profil',
    '/my-tasks': 'Moje úkoly',
    '/tasks': 'Správa úkolů',
    '/my-tickets': 'Tickety',
    '/users': 'Uživatelé',
    '/categories': 'Kategorie',
    '/stores': 'Prodejny',
    '/tickets': 'Tickety',
};

let initStarted = false;

export function getClarityProjectId() {
    return PROJECT_ID;
}

export function isClarityEnabled() {
    return Boolean(PROJECT_ID);
}

function getOrCreateVisitorId() {
    try {
        let id = sessionStorage.getItem(VISITOR_KEY);
        if (!id) {
            id = `v_${Math.random().toString(36).slice(2, 11)}`;
            sessionStorage.setItem(VISITOR_KEY, id);
        }
        return id;
    } catch {
        return 'anonymous';
    }
}

export function initClarity() {
    if (!PROJECT_ID || initStarted || typeof document === 'undefined') {
        return false;
    }
    initStarted = true;

    (function (c, l, a, r, i, t, y) {
        c[a] = c[a] || function () {
            (c[a].q = c[a].q || []).push(arguments);
        };
        t = l.createElement(r);
        t.async = 1;
        t.src = 'https://www.clarity.ms/tag/' + i;
        y = l.getElementsByTagName(r)[0];
        y.parentNode.insertBefore(t, y);
    })(window, document, 'clarity', 'script', PROJECT_ID);

    clarityCall('consentv2', {
        ad_Storage: 'granted',
        analytics_Storage: 'granted',
    });

    return true;
}

export function routeToScreen(pathname) {
    if (!pathname || pathname === '/') {
        return ROUTE_SCREEN['/'];
    }
    if (pathname.startsWith('/analytics')) {
        const section = pathname.replace(/^\/analytics\/?/, '').split('/')[0];
        return section ? `analytics:${section}` : 'analytics';
    }
    if (pathname.startsWith('/coaching')) {
        const section = pathname.replace(/^\/coaching\/?/, '').split('/')[0];
        return section ? `coaching:${section}` : 'coaching';
    }
    const base = pathname.split('/').filter(Boolean)[0];
    return ROUTE_SCREEN[`/${base}`] || base || 'unknown';
}

export function routeToLabel(pathname) {
    if (!pathname || pathname === '/') {
        return ROUTE_LABEL['/'];
    }
    if (pathname.startsWith('/analytics')) {
        const section = pathname.replace(/^\/analytics\/?/, '').split('/')[0];
        const meta = section ? getAnalyticsSection(section) : null;
        return meta?.label || (section ? `Analytika – ${section}` : 'Analytika');
    }
    if (pathname.startsWith('/coaching')) {
        return ROUTE_LABEL['/coaching'];
    }
    if (pathname.startsWith('/plans')) {
        const segment = pathname.replace(/^\/plans\/?/, '').split('/')[0];
        const section = PLANS_SECTIONS.find((s) => s.path === segment);
        return section ? `Plány – ${section.tabLabel}` : ROUTE_LABEL['/plans'];
    }
    const base = `/${pathname.split('/').filter(Boolean)[0]}`;
    return ROUTE_LABEL[base] || base.replace(/^\//, '');
}

export function clarityCall(...args) {
    if (typeof window !== 'undefined' && typeof window.clarity === 'function') {
        window.clarity(...args);
    } else if (typeof window !== 'undefined') {
        window.clarity = window.clarity || function () {
            (window.clarity.q = window.clarity.q || []).push(arguments);
        };
        window.clarity(...args);
    }
}

export function trackClarityUser(user) {
    if (!PROJECT_ID) {
        return;
    }
    if (user?.username) {
        clarityCall('set', 'user', user.username);
        clarityCall('set', 'role', user.role || 'unknown');
    } else {
        clarityCall('set', 'user', 'guest');
        clarityCall('set', 'role', 'guest');
    }
}

/** Virtual page – Clarity pak správně filtruje nahrávky a heatmapy po obrazovce. */
export function trackClarityPage(pathname, user) {
    if (!PROJECT_ID) {
        return;
    }

    let screen = routeToScreen(pathname);
    let label = routeToLabel(pathname);
    if (!user && (pathname === '/' || !pathname)) {
        screen = 'login';
        label = 'Přihlášení';
    }

    const visitorId = user?.username || getOrCreateVisitorId();

    document.title = `${label} | Mobilmajak`;

    clarityCall('set', 'route', pathname);
    clarityCall('set', 'screen', screen);
    clarityCall('set', 'page_label', label);
    clarityCall('identify', visitorId, '', pathname, label);
    clarityCall('event', 'spa_pageview');
}

export function trackClarityEvent(name) {
    if (name && PROJECT_ID) {
        clarityCall('event', name);
    }
}
