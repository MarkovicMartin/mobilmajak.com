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
