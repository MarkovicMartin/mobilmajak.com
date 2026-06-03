const MONTH_SHORT = ['led', 'úno', 'bře', 'dub', 'kvě', 'čer', 'čvc', 'srp', 'zář', 'říj', 'lis', 'pro'];

export const formatLocalDate = (d) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

/** Posune ISO datum o jeden rok zpět (29. 2. → 28. 2.). */
export const shiftIsoDateOneYearBack = (iso) => {
    if (!iso || !/^\d{4}-\d{2}-\d{2}$/.test(iso)) return iso;
    const [y, m, d] = iso.split('-').map(Number);
    const target = new Date(y - 1, m - 1, d);
    if (target.getMonth() !== m - 1) {
        return formatLocalDate(new Date(y - 1, m, 0));
    }
    return formatLocalDate(target);
};

/** Stejné období před rokem – pro srovnání YoY (květen 25 → květen 24, 1.–3. 6. → 1.–3. 6. loni). */
export const shiftFiltersOneYearBack = (filters) => {
    if (!filters) return buildInitialCelkovaFilters();
    const next = {
        ...filters,
        kanal: filters.kanal ?? 'all',
        prodejna_id: filters.prodejna_id ?? '',
        kategorie: filters.kategorie ?? '',
    };
    if (filters.period === 'monthly_select' && filters.selected_month) {
        const [y, m] = filters.selected_month.split('-').map(Number);
        if (y && m) {
            return {
                ...next,
                period: 'monthly_select',
                selected_month: `${y - 1}-${String(m).padStart(2, '0')}`,
                start_date: '',
                end_date: '',
            };
        }
    }
    return {
        ...next,
        period: 'custom',
        start_date: filters.start_date ? shiftIsoDateOneYearBack(filters.start_date) : '',
        end_date: filters.end_date ? shiftIsoDateOneYearBack(filters.end_date) : '',
        selected_month: filters.selected_month
            ? (() => {
                  const [y, m] = filters.selected_month.split('-').map(Number);
                  return y && m ? `${y - 1}-${String(m).padStart(2, '0')}` : filters.selected_month;
              })()
            : next.selected_month,
    };
};

export const buildInitialCelkovaFilters = (preset) => {
    const now = new Date();
    const base = {
        period: 'custom',
        selected_month: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`,
        kanal: 'all',
        prodejna_id: '',
        kategorie: '',
    };
    if (preset === 'prevMonth') {
        const from = new Date(now.getFullYear(), now.getMonth() - 1, 1);
        const to = new Date(now.getFullYear(), now.getMonth(), 0);
        return {
            ...base,
            start_date: formatLocalDate(from),
            end_date: formatLocalDate(to),
        };
    }
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
    return {
        ...base,
        start_date: formatLocalDate(startOfMonth),
        end_date: formatLocalDate(now),
    };
};

export const formatFiltersPeriodLabel = (filters) => {
    if (!filters) return 'Období';
    if (filters.period === 'monthly_select' && filters.selected_month) {
        const [y, m] = filters.selected_month.split('-').map(Number);
        if (y && m) return `${MONTH_SHORT[m - 1]} ${y}`;
    }
    if (filters.start_date && filters.end_date) {
        const fmt = (iso) => {
            const [yy, mm, dd] = iso.split('-').map(Number);
            if (!yy || !mm) return iso;
            if (filters.start_date === filters.end_date) {
                return `${dd}. ${MONTH_SHORT[mm - 1]} ${yy}`;
            }
            return `${dd}. ${MONTH_SHORT[mm - 1]} ${String(yy).slice(2)}`;
        };
        if (filters.start_date === filters.end_date) return fmt(filters.start_date);
        return `${fmt(filters.start_date)} – ${fmt(filters.end_date)}`;
    }
    return 'Období';
};

/** Klíč období pro měsíční graf (YYYY-MM). */
export const periodToMonthKey = (value) => {
    if (!value) return '';
    const s = String(value);
    if (s.length >= 7) return s.slice(0, 7);
    return s;
};

/** Posledních N kalendářních měsíců včetně aktuálního. */
export const buildLastMonthKeys = (count = 12) => {
    const keys = [];
    const now = new Date();
    for (let i = count - 1; i >= 0; i--) {
        const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
        keys.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`);
    }
    return keys;
};

export const formatMonthKeyLabel = (ym) => {
    const [y, m] = ym.split('-').map(Number);
    if (!y || !m) return ym;
    return `${MONTH_SHORT[m - 1]} ${String(y).slice(2)}`;
};

export const formatChartRangeLabel = (chartRange) => {
    if (!chartRange?.start || !chartRange?.end) return 'Posledních 12 měsíců';
    const start = chartRange.start.slice(0, 7);
    const end = chartRange.end.slice(0, 7);
    return `${formatMonthKeyLabel(start)} – ${formatMonthKeyLabel(end)}`;
};
