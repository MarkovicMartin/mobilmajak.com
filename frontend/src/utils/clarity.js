/**
 * Bezpečné volání Microsoft Clarity (skript v public/index.html).
 * Tagy „route“ a „screen“ umožní ve filtrech oddělit SPA obrazovky.
 */

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
    '/tickets': 'tickets',
};

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

/** Virtual page + filtry po obrazovce (React Router pathname). */
export function trackClarityPage(pathname) {
    const screen = routeToScreen(pathname);
    clarityCall('set', 'route', pathname);
    clarityCall('set', 'screen', screen);
    clarityCall('event', 'spa_pageview');
}

/** Vlastní událost (např. chyba formuláře) – zobrazí se v Clarity Events. */
export function trackClarityEvent(name) {
    if (name) {
        clarityCall('event', name);
    }
}
