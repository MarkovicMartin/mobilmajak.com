/**
 * Detekce UX záseků a automatické vytvoření ticketu (POST /api/tickets/ux-friction/).
 */

import api from '../services/api';
import { routeToScreen } from './clarity';

const SESSION_SENT = new Set();
const RAGE_WINDOW_MS = 900;
const RAGE_MIN_CLICKS = 4;
const clickBuckets = new Map();

const INTERACTIVE_SELECTOR = [
    'a[href]',
    'button',
    'input',
    'select',
    'textarea',
    '[role="button"]',
    '[role="link"]',
    '[role="tab"]',
    '[onclick]',
    '.dock-icon-btn',
    '.bug-option',
    'label',
].join(',');

function describeElement(el) {
    if (!el || !el.tagName) {
        return '';
    }
    const tag = el.tagName.toLowerCase();
    const id = el.id ? `#${el.id}` : '';
    let cls = '';
    if (typeof el.className === 'string' && el.className.trim()) {
        cls = `.${el.className.trim().split(/\s+/).slice(0, 2).join('.')}`;
    }
    const text = (el.innerText || el.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 50);
    return `${tag}${id}${cls}${text ? ` "${text}"` : ''}`.slice(0, 280);
}

function isInteractive(el) {
    if (!el || !el.closest) {
        return false;
    }
    return Boolean(el.closest(INTERACTIVE_SELECTOR));
}

function sessionKey(kind, route, element, detail) {
    return `${kind}|${route}|${element}|${detail}`.slice(0, 400);
}

export async function reportUxFriction(payload) {
    const route = payload.route || window.location.pathname;
    const screen = payload.screen || routeToScreen(route);
    const element = payload.element || '';
    const detail = payload.detail || '';
    const key = sessionKey(payload.kind, route, element, detail);
    if (SESSION_SENT.has(key)) {
        return;
    }
    SESSION_SENT.add(key);

    try {
        await api.post('/tickets/ux-friction/', {
            kind: payload.kind,
            route,
            screen,
            element,
            detail,
            url: window.location.href,
        });
    } catch {
        SESSION_SENT.delete(key);
    }
}

function onRageClick(event) {
    const target = event.target instanceof Element ? event.target : null;
    const element = describeElement(target);
    const bucketKey = element || `${event.clientX},${event.clientY}`;
    const now = Date.now();
    const prev = clickBuckets.get(bucketKey) || [];
    const recent = prev.filter((t) => now - t <= RAGE_WINDOW_MS);
    recent.push(now);
    clickBuckets.set(bucketKey, recent);
    if (recent.length >= RAGE_MIN_CLICKS) {
        clickBuckets.set(bucketKey, []);
        reportUxFriction({
            kind: 'rage_click',
            element,
            detail: `${recent.length} rychlých kliknutí během ${RAGE_WINDOW_MS} ms`,
        });
    }
}

function onDeadClick(event) {
    const target = event.target instanceof Element ? event.target : null;
    if (!target || isInteractive(target)) {
        return;
    }
    let el = target;
    while (el && el !== document.body) {
        if (isInteractive(el)) {
            return;
        }
        const style = window.getComputedStyle(el);
        if (style.cursor === 'pointer') {
            const element = describeElement(el);
            reportUxFriction({
                kind: 'dead_click',
                element,
                detail: 'Prvek vypadá klikací (cursor: pointer), ale neproběhla interakce.',
            });
            return;
        }
        el = el.parentElement;
    }
}

function onGlobalError(event) {
    const msg = event.message || 'Neznámá chyba';
    const src = event.filename ? `${event.filename}:${event.lineno || 0}` : '';
    reportUxFriction({
        kind: 'js_error',
        detail: [msg, src].filter(Boolean).join(' @ ').slice(0, 500),
    });
}

function onUnhandledRejection(event) {
    const reason = event.reason;
    const detail = typeof reason === 'string'
        ? reason
        : (reason?.message || String(reason || 'Unhandled rejection'));
    reportUxFriction({
        kind: 'js_error',
        detail: detail.slice(0, 500),
    });
}

let started = false;

export function startUxFrictionMonitor() {
    if (started || typeof window === 'undefined') {
        return;
    }
    started = true;

    document.addEventListener('click', onRageClick, true);
    document.addEventListener('click', onDeadClick, true);
    window.addEventListener('error', onGlobalError);
    window.addEventListener('unhandledrejection', onUnhandledRejection);
}

export function reportApiUxError(error) {
    const status = error?.response?.status;
    const url = error?.config?.url || '';
    if (!status || status === 401 || status === 403) {
        return;
    }
    if (url.includes('/tickets/ux-friction')) {
        return;
    }
    if (status < 500 && status !== 408 && status !== 429) {
        return;
    }
    const method = (error?.config?.method || 'get').toUpperCase();
    reportUxFriction({
        kind: 'api_error',
        detail: `${method} ${url} → HTTP ${status}`,
    });
}
