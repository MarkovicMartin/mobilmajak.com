const formatISODate = (d) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

export const QUICK_RANGE_PRESETS = [
    { id: 'today', label: 'Dnešek' },
    { id: 'yesterday', label: 'Včerejšek' },
    { id: 'thisWeek', label: 'Tento týden' },
    { id: 'thisMonth', label: 'Tento měsíc' },
    { id: 'prevMonth', label: 'Minulý měsíc' },
];

/** Vrátí { start_date, end_date } pro preset id. */
export function computeQuickRange(type) {
    const now = new Date();
    let from;
    let to;

    if (type === 'today') {
        from = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        to = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    } else if (type === 'yesterday') {
        const y = new Date(now);
        y.setDate(now.getDate() - 1);
        from = new Date(y.getFullYear(), y.getMonth(), y.getDate());
        to = new Date(y.getFullYear(), y.getMonth(), y.getDate());
    } else if (type === 'thisWeek') {
        const day = (now.getDay() + 6) % 7;
        from = new Date(now.getFullYear(), now.getMonth(), now.getDate() - day);
        to = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    } else if (type === 'thisMonth') {
        from = new Date(now.getFullYear(), now.getMonth(), 1);
        to = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    } else if (type === 'prevMonth') {
        from = new Date(now.getFullYear(), now.getMonth() - 1, 1);
        to = new Date(now.getFullYear(), now.getMonth(), 0);
    } else {
        return null;
    }

    return {
        start_date: formatISODate(from),
        end_date: formatISODate(to),
    };
}

/** Zjistí aktivní preset podle rozsahu, jinak 'custom'. */
export function detectQuickRangePreset(startDate, endDate) {
    if (!startDate || !endDate) return 'custom';
    for (const { id } of QUICK_RANGE_PRESETS) {
        const range = computeQuickRange(id);
        if (range && range.start_date === startDate && range.end_date === endDate) {
            return id;
        }
    }
    return 'custom';
}

export { formatISODate };
