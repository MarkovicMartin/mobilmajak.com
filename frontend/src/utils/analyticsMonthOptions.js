const MONTH_NAMES = [
    'leden', 'únor', 'březen', 'duben', 'květen', 'červen',
    'červenec', 'srpen', 'září', 'říjen', 'listopad', 'prosinec',
];

/** Měsíční volby pro analytics filtry (včetně „Vlastní období“ na prvním místě). */
export function buildAnalyticsMonthFilterOptions({ startYear = 2024 } = {}) {
    const opts = [];
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth();

    for (let year = startYear; year <= currentYear; year += 1) {
        const monthStart = year === startYear ? 0 : 0;
        const monthEnd = year === currentYear ? currentMonth : 11;
        for (let month = monthStart; month <= monthEnd; month += 1) {
            const ym = `${year}-${String(month + 1).padStart(2, '0')}`;
            const label = `${MONTH_NAMES[month].charAt(0).toUpperCase()}${MONTH_NAMES[month].slice(1)} ${year}`;
            opts.push({ value: `month:${ym}`, label });
        }
    }

    opts.unshift({ value: 'custom', label: '🗓️ Vlastní období' });
    const customOption = opts.shift();
    opts.reverse();
    opts.unshift(customOption);
    return opts;
}
