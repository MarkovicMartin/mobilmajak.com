/** První den aktuálního měsíce – prodejce nesmí zpětně do minulých měsíců. */
export function earliestEditableShiftDate(refDate = new Date()) {
    return new Date(refDate.getFullYear(), refDate.getMonth(), 1);
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
