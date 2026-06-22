import {
    parse,
    format,
    startOfWeek,
    endOfWeek,
    isBefore,
    startOfDay,
} from 'date-fns';

const isWorkShift = (shift) => shift?.typ_smeny === 'prace';

/** Všechny pracovní směny z kalendářních dat měsíce. */
export function collectMonthWorkShifts(kalendarData) {
    const shifts = [];
    for (const [dateStr, dayShifts] of Object.entries(kalendarData || {})) {
        for (const shift of dayShifts || []) {
            if (!isWorkShift(shift)) continue;
            shifts.push({ ...shift, datum: shift.datum || dateStr });
        }
    }
    return shifts;
}

/** Seskupí směny podle kalendářního týdne (Po–Ne). */
export function groupShiftsByWeek(shifts) {
    const weeks = new Map();
    for (const shift of shifts) {
        const d = parse(String(shift.datum).slice(0, 10), 'yyyy-MM-dd', new Date());
        const weekStart = startOfWeek(d, { weekStartsOn: 1 });
        const key = format(weekStart, 'yyyy-MM-dd');
        if (!weeks.has(key)) {
            weeks.set(key, {
                weekStart,
                weekEnd: endOfWeek(d, { weekStartsOn: 1 }),
                shifts: [],
            });
        }
        weeks.get(key).shifts.push(shift);
    }
    return [...weeks.values()].sort((a, b) => a.weekStart - b.weekStart);
}

export function isPastWeek(weekEnd, today = new Date()) {
    const currentWeekStart = startOfWeek(today, { weekStartsOn: 1 });
    return isBefore(startOfDay(weekEnd), currentWeekStart);
}

function shiftPersonRank(shift) {
    if (shift.brigadnik_rezim === 'vypomoc') return 1;
    return 0;
}

function pickPrimaryShift(existing, candidate) {
    if (!existing) return candidate;
    const existingRank = shiftPersonRank(existing);
    const candidateRank = shiftPersonRank(candidate);
    if (candidateRank < existingRank) return candidate;
    if (candidateRank > existingRank) return existing;
    return existing;
}

function storeMetaFromShift(shift, stores) {
    const fromList = stores.find((s) => s.id === shift.prodejna_id);
    return {
        prodejna_id: shift.prodejna_id,
        prodejna_nazev: shift.prodejna_nazev
            || fromList?.nazev_kratkiy
            || fromList?.nazev
            || `Prodejna ${shift.prodejna_id}`,
        prodejna_barva: shift.prodejna_barva || fromList?.barva || '#0066cc',
    };
}

/**
 * Jedna dlaždice prodejny na týden; u osoby jeden řádek (deduplikace user_id).
 */
export function groupWeekByStore(weekShifts, stores = []) {
    const storeOrder = new Map(stores.map((s, i) => [s.id, i]));
    const byStore = new Map();

    for (const shift of weekShifts) {
        if (!shift.prodejna_id) continue;
        if (!byStore.has(shift.prodejna_id)) {
            byStore.set(shift.prodejna_id, {
                ...storeMetaFromShift(shift, stores),
                people: new Map(),
            });
        }
        const store = byStore.get(shift.prodejna_id);
        const userKey = String(shift.user_id);
        const existing = store.people.get(userKey);
        const dates = new Set(existing?.dates || []);
        dates.add(String(shift.datum).slice(0, 10));
        store.people.set(userKey, {
            user_id: shift.user_id,
            user_jmeno: shift.user_jmeno,
            primary: pickPrimaryShift(existing?.primary, shift),
            dates,
            shiftCount: dates.size,
        });
    }

    return [...byStore.values()]
        .sort((a, b) => {
            const orderA = storeOrder.get(a.prodejna_id) ?? 999;
            const orderB = storeOrder.get(b.prodejna_id) ?? 999;
            if (orderA !== orderB) return orderA - orderB;
            return a.prodejna_nazev.localeCompare(b.prodejna_nazev, 'cs');
        })
        .map((store) => ({
            ...store,
            people: [...store.people.values()].sort((a, b) =>
                (a.user_jmeno || '').localeCompare(b.user_jmeno || '', 'cs'),
            ),
        }));
}

/** Seskupí denní směny podle prodejny (pro buňku kalendáře). */
export function groupDayShiftsByStore(workShifts, stores = []) {
    const byStore = new Map();
    for (const shift of workShifts) {
        const storeId = shift.prodejna_id ?? 0;
        if (!byStore.has(storeId)) {
            byStore.set(storeId, {
                ...storeMetaFromShift(shift, stores),
                shifts: [],
            });
        }
        byStore.get(storeId).shifts.push(shift);
    }
    const storeOrder = new Map(stores.map((s, i) => [s.id, i]));
    return [...byStore.values()].sort((a, b) => {
        const orderA = storeOrder.get(a.prodejna_id) ?? 999;
        const orderB = storeOrder.get(b.prodejna_id) ?? 999;
        if (orderA !== orderB) return orderA - orderB;
        return a.prodejna_nazev.localeCompare(b.prodejna_nazev, 'cs');
    });
}
