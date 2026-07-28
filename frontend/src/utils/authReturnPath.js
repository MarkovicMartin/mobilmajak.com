/** Zachování cílové URL přes přihlášení (Slack deep-link / nový tab). */

const KEY = 'mm-post-login-path';

export function rememberReturnPath(pathname, search = '') {
    if (typeof window === 'undefined') return;
    const path = `${pathname || ''}${search || ''}`;
    if (!path || path === '/' || path.startsWith('/login')) return;
    // Jen interní cesty aplikace
    if (!path.startsWith('/')) return;
    try {
        sessionStorage.setItem(KEY, path);
    } catch {
        /* ignore */
    }
}

export function consumeReturnPath() {
    if (typeof window === 'undefined') return null;
    try {
        const path = sessionStorage.getItem(KEY);
        sessionStorage.removeItem(KEY);
        if (!path || !path.startsWith('/') || path.startsWith('//')) return null;
        return path;
    } catch {
        return null;
    }
}

export function peekReturnPath() {
    if (typeof window === 'undefined') return null;
    try {
        return sessionStorage.getItem(KEY);
    } catch {
        return null;
    }
}
