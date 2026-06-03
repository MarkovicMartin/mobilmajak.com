/**
 * Microsoft Clarity – načtení podle REACT_APP_CLARITY_PROJECT_ID (viz frontend/.env.example).
 * Tagy route/screen pro filtry ve SPA.
 */

const PROJECT_ID = (process.env.REACT_APP_CLARITY_PROJECT_ID || '').trim();

const ROUTE_SCREEN = {
    '/': 'home',
    '/orders': 'orders',
    '/shifts': 'shifts',
    '/news': 'news',
    '/access': 'access',
    '/plans': 'plans',
    '/leaderboard': 'leaderboard',
    '/profile': 'profile',
    '/my-tickets': 'my-tickets',
    '/users': 'users',
    '/categories': 'categories',
    '/stores': 'stores',
    '/tickets': 'my-tickets',
};

let initStarted = false;

export function getClarityProjectId() {
    return PROJECT_ID;
}

export function isClarityEnabled() {
    return Boolean(PROJECT_ID);
}

/** Jednorázové vložení oficiálního Clarity tagu (stejný snippet jako dříve v index.html). */
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
    const base = pathname.split('/').filter(Boolean)[0];
    return ROUTE_SCREEN[`/${base}`] || base || 'unknown';
}

export function clarityCall(...args) {
    if (typeof window !== 'undefined' && typeof window.clarity === 'function') {
        window.clarity(...args);
    }
}

export function trackClarityPage(pathname) {
    if (!PROJECT_ID) {
        return;
    }
    const screen = routeToScreen(pathname);
    clarityCall('set', 'route', pathname);
    clarityCall('set', 'screen', screen);
    clarityCall('event', 'spa_pageview');
}

export function trackClarityEvent(name) {
    if (name && PROJECT_ID) {
        clarityCall('event', name);
    }
}
