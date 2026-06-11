/** Všechny časy v UI docházky / kamer – Europe/Prague (CET/CEST). */
export const PRAGUE_TZ = 'Europe/Prague';

export function formatPragueDateTime(iso, options = {}) {
    if (!iso) return '';
    return new Date(iso).toLocaleString('cs-CZ', {
        timeZone: PRAGUE_TZ,
        ...options,
    });
}

export function formatPragueClock(iso) {
    return formatPragueDateTime(iso, {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    });
}

export function formatPragueEventAt(iso) {
    return formatPragueDateTime(iso, {
        day: '2-digit',
        month: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    });
}
