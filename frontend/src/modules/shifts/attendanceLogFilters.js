import { formatLocalDate } from '../analytics/sections/celkovaPeriodUtils';

export const PERIOD_OPTIONS = [
    { id: 'uplynule', label: 'Proběhlé' },
    { id: 'dnes', label: 'Dnes' },
    { id: 'vcera', label: 'Včera' },
    { id: 'tyden', label: 'Poslední týden' },
    { id: 'mesic', label: 'Celý měsíc' },
];

export function shiftDateIso(datum) {
    if (!datum) return '';
    return String(datum).slice(0, 10);
}

export function getYesterdayIso(now = new Date()) {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
    return formatLocalDate(d);
}

export function getWeekRangeIso(now = new Date()) {
    const end = formatLocalDate(now);
    const startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 6);
    return [formatLocalDate(startDate), end];
}

/** Směna už začala, skončila, nebo má záznam docházky. */
export function isShiftOccurred(entry, now = new Date()) {
    const todayIso = formatLocalDate(now);
    const datum = shiftDateIso(entry.datum);
    if (datum < todayIso) return true;
    if (datum > todayIso) return false;
    if (entry.stav && entry.stav !== 'bez_zaznamu') return true;
    const planOd = (entry.plan_od || '').substring(0, 5);
    if (!planOd) return false;
    const [h, m] = planOd.split(':').map(Number);
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), h, m, 0, 0);
    return now >= start;
}

export function filterAttendanceEntries(entries, period, now = new Date()) {
    const todayIso = formatLocalDate(now);
    const yesterdayIso = getYesterdayIso(now);
    const [weekStartIso, weekEndIso] = getWeekRangeIso(now);

    let filtered = entries;
    switch (period) {
        case 'dnes':
            filtered = entries.filter((e) => shiftDateIso(e.datum) === todayIso);
            break;
        case 'vcera':
            filtered = entries.filter((e) => shiftDateIso(e.datum) === yesterdayIso);
            break;
        case 'tyden':
            filtered = entries.filter((e) => {
                const d = shiftDateIso(e.datum);
                return d >= weekStartIso && d <= weekEndIso;
            });
            break;
        case 'mesic':
            filtered = entries;
            break;
        case 'uplynule':
        default:
            filtered = entries.filter((e) => isShiftOccurred(e, now));
            break;
    }

    return [...filtered].sort((a, b) => {
        const dateCmp = shiftDateIso(b.datum).localeCompare(shiftDateIso(a.datum));
        if (dateCmp !== 0) return dateCmp;
        return (a.jmeno || '').localeCompare(b.jmeno || '', 'cs');
    });
}

/** Měsíce k načtení z API podle zvoleného období. */
export function resolveFetchMonths(period, calendarMonth, now = new Date()) {
    if (period === 'mesic' || period === 'uplynule') {
        return calendarMonth ? [calendarMonth] : [];
    }

    const months = new Set();
    const todayIso = formatLocalDate(now);
    months.add(todayIso.substring(0, 7));

    if (period === 'vcera') {
        months.add(getYesterdayIso(now).substring(0, 7));
    }
    if (period === 'tyden') {
        months.add(getWeekRangeIso(now)[0].substring(0, 7));
    }

    return [...months].filter(Boolean).sort();
}

export function periodSummaryLabel(period, now = new Date()) {
    switch (period) {
        case 'dnes':
            return `Dnes (${formatLocalDate(now).split('-').reverse().join('.')})`;
        case 'vcera': {
            const y = getYesterdayIso(now);
            return `Včera (${y.split('-').reverse().join('.')})`;
        }
        case 'tyden': {
            const [from, to] = getWeekRangeIso(now);
            const fmt = (iso) => iso.split('-').reverse().slice(0, 2).join('.');
            return `Poslední týden (${fmt(from)} – ${fmt(to)})`;
        }
        case 'mesic':
            return 'Celý vybraný měsíc';
        case 'uplynule':
        default:
            return 'Proběhlé směny (bez budoucích)';
    }
}
