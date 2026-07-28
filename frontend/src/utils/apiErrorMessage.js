const TRANSIENT_STATUSES = new Set([502, 503, 504]);

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Jedno opakování po krátké pauze při 502/503/504 nebo Network Error
 * (upstream reset bez HTTP odpovědi – typicky měsíční žebříček).
 * Delší client timeout nepomůže – nginx 502 vrátí hned.
 */
export async function withGatewayRetry(fn, { retries = 1, delayMs = 1000 } = {}) {
    let lastErr;
    for (let attempt = 0; attempt <= retries; attempt += 1) {
        try {
            return await fn();
        } catch (err) {
            lastErr = err;
            const status = err?.response?.status;
            const isGateway = TRANSIENT_STATUSES.has(status);
            const isNetwork = !err?.response && (
                err?.code === 'ERR_NETWORK'
                || /^network error$/i.test(err?.message || '')
            );
            if ((!isGateway && !isNetwork) || attempt >= retries) {
                throw err;
            }
            await sleep(delayMs);
        }
    }
    throw lastErr;
}

/**
 * Přeloží axios/DRF chybu na zprávu pro UI.
 * Nginx HTML (502/…) nikdy nevrací do alertu.
 * DRF field-error objekty nechává jako objekt (pro setErrors).
 */
export function normalizeApiError(err, fallback = 'Nepodařilo se dokončit požadavek') {
    const status = err?.response?.status;
    if (status === 502) {
        return 'Server dočasně neodpovídá. Zkuste to prosím znovu.';
    }
    if (status === 503) {
        return 'Server je dočasně nedostupný. Zkuste to prosím znovu.';
    }
    if (status === 504) {
        return 'Vypršel časový limit serveru. Zkuste to prosím znovu.';
    }

    const data = err?.response?.data;
    if (data == null) {
        return fallback;
    }

    if (typeof data === 'string') {
        const text = data.trim();
        if (!text) return fallback;
        if (looksLikeHtml(text)) {
            return fallback;
        }
        return text;
    }

    if (typeof data === 'object') {
        if (typeof data.detail === 'string') return data.detail;
        if (typeof data.error === 'string') return data.error;
        if (typeof data.message === 'string') return data.message;
        return data;
    }

    return fallback;
}

/** Pro alert / toast – vždy string. */
export function apiErrorAlertText(errOrData, fallback = 'Nepodařilo se dokončit požadavek') {
    const normalized = errOrData?.response
        ? normalizeApiError(errOrData, fallback)
        : sanitizeErrorPayload(errOrData, fallback);
    if (typeof normalized === 'string') return normalized;
    if (normalized && typeof normalized === 'object') {
        const first = Object.values(normalized).flat?.()?.[0]
            || Object.values(normalized)[0];
        if (typeof first === 'string') return first;
        if (Array.isArray(first) && typeof first[0] === 'string') return first[0];
        try {
            return JSON.stringify(normalized);
        } catch {
            return fallback;
        }
    }
    return fallback;
}

function sanitizeErrorPayload(data, fallback) {
    if (data == null) return fallback;
    if (typeof data === 'string') {
        const text = data.trim();
        if (!text || looksLikeHtml(text)) return fallback;
        return text;
    }
    return data;
}

function looksLikeHtml(text) {
    return text.startsWith('<') || /<\/?(html|head|body|title)\b/i.test(text);
}
