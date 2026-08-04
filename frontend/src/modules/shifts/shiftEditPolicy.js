/** Dočasně: prodejci mohou opravit směny za červenec 2026 do 5. 8. 2026 (3.–4. 8.). */
const JULY_2026_SHIFT_EDIT_UNTIL = new Date(2026, 7, 5); // měsíc 0-index
const JULY_2026_START = new Date(2026, 6, 1);

/** První den aktuálního měsíce – prodejce nesmí zpětně do minulých měsíců (s výjimkou okna výše). */
export function earliestEditableShiftDate(refDate = new Date()) {
    const currentMonthStart = new Date(refDate.getFullYear(), refDate.getMonth(), 1);
    const todayLocal = new Date(refDate.getFullYear(), refDate.getMonth(), refDate.getDate());
    if (todayLocal < JULY_2026_SHIFT_EDIT_UNTIL && JULY_2026_START < currentMonthStart) {
        return new Date(JULY_2026_START.getTime());
    }
    return currentMonthStart;
}

export function sellerMayEditShiftMonth(monthStr, refDate = new Date()) {
    const [y, m] = monthStr.split('-').map(Number);
    const shiftMonthStart = new Date(y, m - 1, 1);
    return shiftMonthStart >= earliestEditableShiftDate(refDate);
}

export function sellerMayEditShiftOnDate(dateStr, refDate = new Date()) {
    const [y, m, d] = String(dateStr).slice(0, 10).split('-').map(Number);
    const shiftDate = new Date(y, m - 1, d);
    return shiftDate >= earliestEditableShiftDate(refDate);
}

export function userMayEditShiftOnDate(user, dateStr, refDate = new Date()) {
    if (user?.role === 'ADMIN' || user?.role === 'VEDOUCI') return true;
    return sellerMayEditShiftOnDate(dateStr, refDate);
}

export function userMayEditShiftMonth(user, monthStr, refDate = new Date()) {
    if (user?.role === 'ADMIN' || user?.role === 'VEDOUCI') return true;
    return sellerMayEditShiftMonth(monthStr, refDate);
}
