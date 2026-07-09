import { BACKOFFICE_LOCATION, BACKOFFICE_CALENDAR_COLOR } from './shiftBackoffice';

export function shiftStoreKey(shift) {
    if (shift?.pozice_smeny === 'backoffice' && !shift?.prodejna_id) {
        return BACKOFFICE_LOCATION;
    }
    return shift?.prodejna_id ?? 0;
}

/** Seskupí denní směny podle prodejny (pro buňku kalendáře). */
export function groupDayShiftsByStore(workShifts, stores = []) {
    const byStore = new Map();
    for (const shift of workShifts) {
        const storeId = shiftStoreKey(shift);
        if (!byStore.has(storeId)) {
            byStore.set(storeId, {
                ...storeMetaFromShift(shift, stores),
                shifts: [],
            });
        }
        byStore.get(storeId).shifts.push(shift);
    }
    const storeOrder = new Map(stores.map((s, i) => [s.id, i]));
    storeOrder.set(BACKOFFICE_LOCATION, stores.length);
    return [...byStore.values()].sort((a, b) => {
        const orderA = storeOrder.get(a.prodejna_id) ?? 999;
        const orderB = storeOrder.get(b.prodejna_id) ?? 999;
        if (orderA !== orderB) return orderA - orderB;
        return a.prodejna_nazev.localeCompare(b.prodejna_nazev, 'cs');
    });
}

function storeMetaFromShift(shift, stores) {
    const storeKey = shiftStoreKey(shift);
    if (storeKey === BACKOFFICE_LOCATION) {
        return {
            prodejna_id: BACKOFFICE_LOCATION,
            prodejna_nazev: 'Backoffice',
            prodejna_barva: shift.prodejna_barva || BACKOFFICE_CALENDAR_COLOR,
        };
    }
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
