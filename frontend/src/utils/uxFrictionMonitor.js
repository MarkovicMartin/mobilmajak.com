/**
 * Detekce UX záseků a automatické vytvoření ticketu (POST /api/tickets/ux-friction/).
 */

import api from '../services/api';
import { routeToScreen } from './clarity';

const SESSION_SENT = new Set();
const RAGE_WINDOW_MS = 1500;
const RAGE_MIN_CLICKS = 7;
const DEAD_CLICK_WINDOW_MS = 2500;
const DEAD_CLICK_MIN = 3;
const MIN_REPORT_INTERVAL_MS = 3 * 60 * 1000;
const JS_ERROR_MIN_OCCURRENCES = 2;
const API_ERROR_MIN_OCCURRENCES = 2;

const clickBuckets = new Map();
const deadClickBuckets = new Map();
const jsErrorCounts = new Map();
const apiErrorCounts = new Map();
let lastReportAt = 0;

const JS_ERROR_IGNORE = [
    /resizeobserver loop/i,
    /^script error\.?$/i,
    /loading chunk \d+ failed/i,
    /loading css chunk/i,
    /dynamically imported module/i,
    /non-error promise rejection/i,
    /\bcancel(led|ed)?\b/i,
    /\babort(ed)?\b/i,
    /^network error$/i,
    /chrome-extension:/i,
    /moz-extension:/i,
    /extension context/i,
];

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
    const stableDetail = (kind === 'dead_click' || kind === 'rage_click') ? '' : detail;
    return `${kind}|${route}|${element}|${stableDetail}`.slice(0, 400);
}

function shouldIgnoreJsError(detail) {
    const text = (detail || '').trim();
    if (!text) {
        return true;
    }
    return JS_ERROR_IGNORE.some((re) => re.test(text));
}

function bumpStrikeCounter(map, key, windowMs) {
    const now = Date.now();
    const prev = map.get(key) || [];
    const recent = prev.filter((t) => now - t <= windowMs);
    recent.push(now);
    map.set(key, recent);
    return recent.length;
}

export async function reportUxFriction(payload) {
    const now = Date.now();
    if (now - lastReportAt < MIN_REPORT_INTERVAL_MS) {
        return;
    }

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
        const res = await api.post('/tickets/ux-friction/', {
            kind: payload.kind,
            route,
            screen,
            element,
            detail,
            url: window.location.href,
        });
        if (!res.data?.skipped) {
            lastReportAt = now;
        }
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
            const count = bumpStrikeCounter(deadClickBuckets, element, DEAD_CLICK_WINDOW_MS);
            if (count >= DEAD_CLICK_MIN) {
                deadClickBuckets.delete(element);
                reportUxFriction({
                    kind: 'dead_click',
                    element,
                    detail: `${count}× klik na prvek s cursor:pointer bez očekávané reakce.`,
                });
            }
            return;
        }
        el = el.parentElement;
    }
}

function reportJsErrorIfRepeated(detail) {
    const normalized = detail.slice(0, 500);
    if (shouldIgnoreJsError(normalized)) {
        return;
    }
    const count = bumpStrikeCounter(jsErrorCounts, normalized, 10 * 60 * 1000);
    if (count < JS_ERROR_MIN_OCCURRENCES) {
        return;
    }
    jsErrorCounts.delete(normalized);
    reportUxFriction({
        kind: 'js_error',
        detail: `${normalized} (${count}× v relaci)`,
    });
}

function onGlobalError(event) {
    const msg = event.message || 'Neznámá chyba';
    const src = event.filename ? `${event.filename}:${event.lineno || 0}` : '';
    reportJsErrorIfRepeated([msg, src].filter(Boolean).join(' @ '));
}

function onUnhandledRejection(event) {
    const reason = event.reason;
    const detail = typeof reason === 'string'
        ? reason
        : (reason?.message || String(reason || 'Unhandled rejection'));
    reportJsErrorIfRepeated(detail);
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
    if (status < 500) {
        return;
    }
    const method = (error?.config?.method || 'get').toUpperCase();
    const strikeKey = `${method}|${url}|${status}`;
    const count = bumpStrikeCounter(apiErrorCounts, strikeKey, 5 * 60 * 1000);
    if (count < API_ERROR_MIN_OCCURRENCES) {
        return;
    }
    apiErrorCounts.delete(strikeKey);
    reportUxFriction({
        kind: 'api_error',
        detail: `${method} ${url} → HTTP ${status} (${count}× za 5 min)`,
    });
}
