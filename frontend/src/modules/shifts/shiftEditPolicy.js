function currentMonthKey(refDate = new Date()) {
    return `${refDate.getFullYear()}-${String(refDate.getMonth() + 1).padStart(2, '0')}`;
}

/** První den aktuálního měsíce – pro výběr data v kalendáři. */
export function earliestEditableShiftDate(refDate = new Date()) {
    return new Date(refDate.getFullYear(), refDate.getMonth(), 1);
}

export function sellerMayEditShiftMonth(monthStr, refDate = new Date()) {
    return monthStr === currentMonthKey(refDate);
}

export function sellerMayEditShiftOnDate(dateStr, refDate = new Date()) {
    return String(dateStr).slice(0, 7) === currentMonthKey(refDate);
}

export function userMayEditShiftOnDate(user, dateStr, refDate = new Date()) {
    if (user?.role === 'ADMIN') return true;
    return sellerMayEditShiftOnDate(dateStr, refDate);
}
