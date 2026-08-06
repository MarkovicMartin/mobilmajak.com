/** Detekce vypršené session (ne „nedostatečná oprávnění“). */

const AUTH_DETAIL_RE = /credentials|authentication|not authenticated|nepřihlášen/i;

export function isAuthFailureResponse(status, body) {
    if (status === 401) return true;
    if (status !== 403) return false;
    const detail = body && typeof body === 'object' ? body.detail : null;
    if (typeof detail === 'string' && AUTH_DETAIL_RE.test(detail)) return true;
    if (Array.isArray(detail)) {
        return detail.some((item) => typeof item === 'string' && AUTH_DETAIL_RE.test(item));
    }
    return false;
}

const listeners = new Set();

export function onSessionExpired(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
}

export function notifySessionExpired() {
    listeners.forEach((fn) => {
        try {
            fn();
        } catch {
            /* ignore */
        }
    });
}

/** Pro raw fetch() mimo axios. */
export async function handleFetchAuthFailure(response) {
    if (!response || response.ok) return false;
    if (response.status !== 401 && response.status !== 403) return false;
    let body = null;
    try {
        body = await response.clone().json();
    } catch {
        body = null;
    }
    if (!isAuthFailureResponse(response.status, body)) return false;
    notifySessionExpired();
    return true;
}
