// Dočasně: prodejci mohou opravit směny za červen 2026 do 1. 8. 2026.
const JUNE_2026_SHIFT_EDIT_UNTIL = new Date(2026, 7, 1);
const JUNE_2026_START = new Date(2026, 5, 1);

export function earliestEditableShiftDate(refDate = new Date()) {
    const currentMonthStart = new Date(refDate.getFullYear(), refDate.getMonth(), 1);
    if (refDate < JUNE_2026_SHIFT_EDIT_UNTIL && JUNE_2026_START < currentMonthStart) {
        return JUNE_2026_START;
    }
    return currentMonthStart;
}

export function sellerMayEditShiftMonth(monthStr, refDate = new Date()) {
    const [y, m] = monthStr.split('-').map(Number);
    const shiftMonthStart = new Date(y, m - 1, 1);
    return shiftMonthStart >= earliestEditableShiftDate(refDate);
}

export function sellerMayEditShiftOnDate(dateStr, refDate = new Date()) {
    const [y, m, d] = dateStr.split('-').map(Number);
    const shiftDate = new Date(y, m - 1, d);
    return shiftDate >= earliestEditableShiftDate(refDate);
}
